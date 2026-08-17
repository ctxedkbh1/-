import json
import os
from dataclasses import replace

from core import paths
from core.references.domain import ReferenceRecord, normalized_text


class ReferenceStore:
    def __init__(self, path: str = ""):
        self.path = path or os.path.join(paths.data_dir(), "references.json")
        self.data = self._load()

    def _load(self) -> list[ReferenceRecord]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                return [ReferenceRecord.from_dict(item) for item in raw if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([item.to_dict() for item in self.data], f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def upsert(self, record: dict[str, object] | ReferenceRecord) -> ReferenceRecord:
        incoming = record if isinstance(record, ReferenceRecord) else ReferenceRecord.from_dict(record)
        duplicate = self._find_duplicate(incoming)
        if duplicate:
            merged = self._merge(duplicate, incoming)
            self.data = [merged if item.reference_id == duplicate.reference_id else item for item in self.data]
            self.save()
            return merged
        reference_id = incoming.reference_id or self._next_id()
        created = replace(incoming, reference_id=reference_id)
        self.data.append(created)
        self.save()
        return created

    def all(self) -> list[ReferenceRecord]:
        return list(self.data)

    def get(self, reference_id: str) -> ReferenceRecord | None:
        return next((item for item in self.data if item.reference_id == reference_id), None)

    def search(self, query: str) -> list[ReferenceRecord]:
        needle = str(query or "").strip().lower()
        if not needle:
            return self.all()
        return [item for item in self.data if needle in self._blob(item)]

    def delete(self, reference_id: str) -> None:
        self.data = [item for item in self.data if item.reference_id != reference_id]
        self.save()

    def set_favorite(self, reference_id: str, favorite: bool) -> None:
        self.data = [
            replace(item, favorite=favorite) if item.reference_id == reference_id else item
            for item in self.data
        ]
        self.save()

    def _next_id(self) -> str:
        numbers = [
            int(item.reference_id.removeprefix("ref_"))
            for item in self.data
            if item.reference_id.removeprefix("ref_").isdigit()
        ]
        return f"ref_{max(numbers, default=0) + 1:03d}"

    def _find_duplicate(self, incoming: ReferenceRecord) -> ReferenceRecord | None:
        key = self._unique_key(incoming)
        if not key:
            return None
        return next((item for item in self.data if self._unique_key(item) == key), None)

    @staticmethod
    def _unique_key(item: ReferenceRecord) -> str:
        for prefix, value in (
            ("doi", item.doi),
            ("isbn", item.isbn),
            ("pmid", item.pmid),
            ("zotero", item.zotero_item_key),
        ):
            if value:
                return f"{prefix}:{normalized_text(value)}"
        title = normalized_text(item.title)
        if title:
            return f"fallback:{title}|{normalized_text(item.authors)}|{item.year}"
        return ""

    @staticmethod
    def _merge(current: ReferenceRecord, incoming: ReferenceRecord) -> ReferenceRecord:
        values = current.to_dict()
        for key, value in incoming.to_dict().items():
            if value not in ("", None, [], (), False):
                values[key] = value
        values["reference_id"] = current.reference_id
        values["created_at"] = current.created_at
        return ReferenceRecord.from_dict(values)

    @staticmethod
    def _blob(item: ReferenceRecord) -> str:
        return " ".join(str(value) for value in item.to_dict().values()).lower()

# 版本: v2.0.1 (2026-08-17) 更新: 参考文献存储、检索与去重
