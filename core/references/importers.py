import json

from core.references.domain import ReferenceRecord, ReferenceSource
from sources import cnki


def import_text(text: str, source: ReferenceSource = ReferenceSource.MANUAL) -> list[ReferenceRecord]:
    records = cnki.parse_text(text)
    actual_source = source
    if source is ReferenceSource.MANUAL:
        stripped = str(text or "").lstrip()
        if stripped.startswith("TY  -"):
            actual_source = ReferenceSource.RIS
        elif stripped.startswith("@"):
            actual_source = ReferenceSource.BIBTEX
    return [ReferenceRecord.from_dict({**record, "source": actual_source.value}) for record in records]


def import_csl_json(text: str) -> list[ReferenceRecord]:
    try:
        payload = json.loads(text or "[]")
    except json.JSONDecodeError as exc:
        raise ReferenceImportError(message="CSL JSON 格式无效") from exc
    records = payload if isinstance(payload, list) else [payload]
    out = []
    for item in records:
        if not isinstance(item, dict):
            continue
        authors = []
        for author in item.get("author", []):
            if not isinstance(author, dict):
                continue
            name = " ".join(str(author.get(key) or "").strip() for key in ("given", "family")).strip()
            if name:
                authors.append(name)
        date_parts = item.get("issued", {}).get("date-parts", []) if isinstance(item.get("issued"), dict) else []
        year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
        out.append(ReferenceRecord.from_dict({
            "title": item.get("title"),
            "authors": "; ".join(authors),
            "year": year,
            "journal": item.get("container-title"),
            "volume_issue_pages": _volume_pages(item),
            "doi": item.get("DOI"),
            "url": item.get("URL"),
            "abstract": item.get("abstract"),
            "isbn": item.get("ISBN"),
            "pmid": item.get("PMID"),
            "zotero_item_key": item.get("id"),
            "source": ReferenceSource.CSL_JSON.value,
            "verified": bool(item.get("DOI") or item.get("URL")),
        }))
    return out


def _volume_pages(item: dict) -> str:
    volume = str(item.get("volume") or "")
    issue = str(item.get("issue") or "")
    pages = str(item.get("page") or "")
    value = volume + (f"({issue})" if issue else "")
    return value + (f": {pages}" if pages else "")


class ReferenceImportError(ValueError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

# 版本: v2.0.1 (2026-08-17) 更新: RIS、BibTeX 与 CSL JSON 统一导入
