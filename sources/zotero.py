import re
from dataclasses import dataclass

import requests

from core.references.domain import ReferenceRecord, ReferenceSource


@dataclass(frozen=True, slots=True)
class ZoteroConnectionResult:
    ok: bool
    mode: str
    server_id: str
    api_version: str
    message: str


@dataclass(frozen=True, slots=True)
class ZoteroSyncResult:
    references: tuple[ReferenceRecord, ...]
    version: int
    partition_id: str


class ZoteroClient:
    def __init__(self, base_url: str, user_id: str, api_key: str = "", mode: str = "local"):
        self.base_url = base_url.rstrip("/")
        self.user_id = str(user_id)
        self.api_key = str(api_key or "")
        self.mode = mode

    @classmethod
    def local(cls, base_url: str = "http://localhost:23119/api") -> "ZoteroClient":
        return cls(base_url=base_url, user_id="0", mode="local")

    @classmethod
    def web(cls, user_id: str, api_key: str,
            base_url: str = "https://api.zotero.org") -> "ZoteroClient":
        return cls(base_url=base_url, user_id=user_id, api_key=api_key, mode="web")

    def test_connection(self) -> ZoteroConnectionResult:
        url = self.base_url + ("/" if self.mode == "local" else "/keys/current")
        response = self._get(url)
        return ZoteroConnectionResult(
            ok=True,
            mode=self.mode,
            server_id=str(response.headers.get("Zotero-Server-ID") or ""),
            api_version=str(response.headers.get("Zotero-API-Version") or "3"),
            message="Zotero 连接正常",
        )

    def sync_items(self, since: int = 0) -> ZoteroSyncResult:
        url = f"{self.base_url}/users/{self.user_id}/items"
        response = self._get(url, params={"since": max(0, int(since)), "format": "json", "include": "data"})
        try:
            payload = response.json()
        except ValueError as exc:
            raise ZoteroError("Zotero items 响应不是有效 JSON") from exc
        references = []
        for item in payload if isinstance(payload, list) else []:
            record = self._to_reference(item)
            if record:
                references.append(record)
        version = int(response.headers.get("Last-Modified-Version") or since or 0)
        server_id = str(response.headers.get("Zotero-Server-ID") or "")
        partition = f"local:{server_id or 'unknown'}" if self.mode == "local" else f"web:user:{self.user_id}"
        return ZoteroSyncResult(tuple(references), version, partition)

    def collections(self, since: int = 0) -> list[dict]:
        response = self._get(
            f"{self.base_url}/users/{self.user_id}/collections",
            params={"since": max(0, int(since)), "format": "json"},
        )
        data = response.json()
        return data if isinstance(data, list) else []

    def tags(self, since: int = 0) -> list[dict]:
        response = self._get(
            f"{self.base_url}/users/{self.user_id}/tags",
            params={"since": max(0, int(since))},
        )
        data = response.json()
        return data if isinstance(data, list) else []

    def _get(self, url: str, params: dict | None = None):
        headers = {"Zotero-API-Version": "3", "Accept": "application/json"}
        if self.api_key:
            headers["Zotero-API-Key"] = self.api_key
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
        except requests.RequestException as exc:
            raise ZoteroError(f"Zotero 网络错误: {exc}") from exc
        if response.status_code != 200:
            raise ZoteroHttpError(response.status_code, _safe_message(response))
        return response

    def _to_reference(self, item: dict) -> ReferenceRecord | None:
        data = item.get("data") if isinstance(item.get("data"), dict) else item
        if not isinstance(data, dict) or data.get("itemType") in {"attachment", "note", "annotation"}:
            return None
        creators = []
        for creator in data.get("creators", []):
            if not isinstance(creator, dict):
                continue
            name = creator.get("name") or " ".join(
                str(creator.get(key) or "").strip() for key in ("firstName", "lastName")
            ).strip()
            if name:
                creators.append(str(name))
        date_match = re.search(r"\d{4}", str(data.get("date") or ""))
        source = ReferenceSource.ZOTERO_LOCAL if self.mode == "local" else ReferenceSource.ZOTERO_WEB
        return ReferenceRecord.from_dict({
            "title": data.get("title"),
            "authors": "; ".join(creators),
            "year": date_match.group(0) if date_match else "",
            "journal": data.get("publicationTitle") or data.get("proceedingsTitle"),
            "volume_issue_pages": _volume_pages(data),
            "doi": data.get("DOI"),
            "url": data.get("url"),
            "abstract": data.get("abstractNote"),
            "isbn": data.get("ISBN"),
            "pmid": data.get("PMID"),
            "tags": [tag.get("tag") for tag in data.get("tags", []) if isinstance(tag, dict)],
            "collections": data.get("collections", []),
            "zotero_item_key": item.get("key") or data.get("key"),
            "source": source.value,
            "verified": True,
        })


class ZoteroError(RuntimeError):
    pass


class ZoteroHttpError(ZoteroError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


def _volume_pages(data: dict) -> str:
    volume = str(data.get("volume") or "")
    issue = str(data.get("issue") or "")
    pages = str(data.get("pages") or data.get("page") or "")
    return volume + (f"({issue})" if issue else "") + (f": {pages}" if pages else "")


def _safe_message(response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            return str(data.get("message") or data.get("error") or "请求失败")[:300]
    except ValueError:
        pass
    return str(response.text or "请求失败")[:300]

# 版本: v2.0.1 (2026-08-17) 更新: Zotero Local/Web 官方增量读取
