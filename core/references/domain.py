import datetime
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Mapping


class ReferenceSource(StrEnum):
    MANUAL = "manual"
    RIS = "ris"
    BIBTEX = "bibtex"
    CSL_JSON = "csl_json"
    ZOTERO_LOCAL = "zotero_local"
    ZOTERO_WEB = "zotero_web"
    LOCAL_FILE = "local_file"
    CROSSREF = "crossref"
    OPENALEX = "openalex"
    NOTEBOOK_ENTERPRISE = "notebook_enterprise"
    WEB = "web"


class CitationStyle(StrEnum):
    GB_T_7714 = "gb_t_7714"
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    VANCOUVER = "vancouver"


@dataclass(frozen=True, slots=True)
class ReferenceRecord:
    reference_id: str = ""
    title: str = ""
    authors: str = ""
    year: str = ""
    journal: str = ""
    volume_issue_pages: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    keywords: str = ""
    tags: tuple[str, ...] = ()
    collections: tuple[str, ...] = ()
    isbn: str = ""
    pmid: str = ""
    zotero_item_key: str = ""
    source: ReferenceSource = ReferenceSource.MANUAL
    source_path: str = ""
    attachment_path: str = ""
    verified: bool = False
    favorite: bool = False
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ReferenceRecord":
        now = datetime.datetime.now().isoformat(timespec="seconds")
        source = str(data.get("source") or data.get("source_type") or "manual")
        if source not in {item.value for item in ReferenceSource}:
            source = ReferenceSource.MANUAL.value
        return cls(
            reference_id=str(data.get("reference_id") or data.get("id") or ""),
            title=_clean(data.get("title")),
            authors=_clean(data.get("authors")),
            year=_clean(data.get("year"))[:4],
            journal=_clean(data.get("journal")),
            volume_issue_pages=_clean(data.get("volume_issue_pages")),
            doi=normalize_doi(data.get("doi")),
            url=_clean(data.get("url")),
            abstract=_clean(data.get("abstract")),
            keywords=_clean(data.get("keywords")),
            tags=_tuple(data.get("tags")),
            collections=_tuple(data.get("collections")),
            isbn=_clean(data.get("isbn")),
            pmid=_clean(data.get("pmid")),
            zotero_item_key=_clean(data.get("zotero_item_key")),
            source=ReferenceSource(source),
            source_path=_clean(data.get("source_path")),
            attachment_path=_clean(data.get("attachment_path")),
            verified=bool(data.get("verified", False)),
            favorite=bool(data.get("favorite", False)),
            created_at=_clean(data.get("created_at")) or now,
            updated_at=_clean(data.get("updated_at")) or now,
            notes=_clean(data.get("notes")),
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["source"] = self.source.value
        data["tags"] = list(self.tags)
        data["collections"] = list(self.collections)
        return data


def normalize_doi(value: object) -> str:
    doi = _clean(value).lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    return doi.strip()


def normalized_text(value: object) -> str:
    return re.sub(r"\W+", "", _clean(value).lower(), flags=re.UNICODE)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    text = _clean(value)
    return tuple(part.strip() for part in re.split(r"[;,，；]", text) if part.strip())

# 版本: v2.0.1 (2026-08-17) 更新: Reference ID 与引用样式数据模型
