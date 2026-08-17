import json
import os
from dataclasses import dataclass

from core import paths
from core.evidence import canonical_id, parse_citations


@dataclass(frozen=True, slots=True)
class CitationAnalysis:
    mapping: dict[str, int]
    reference_ids: tuple[str, ...]
    unresolved_evidence: tuple[str, ...]
    unresolved_references: tuple[str, ...]
    unused_references: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.unresolved_evidence and not self.unresolved_references


class CitationMap:
    def __init__(self, path: str = ""):
        self.path = path or os.path.join(paths.data_dir(), "citation_map.json")
        self.data = self._load()

    def _load(self) -> dict[str, str]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
            return {canonical_id(key): str(value) for key, value in raw.items()} if isinstance(raw, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def link(self, evidence_id: str, reference_id: str) -> None:
        self.data[canonical_id(evidence_id)] = str(reference_id)
        self.save()

    def unlink(self, evidence_id: str) -> None:
        self.data.pop(canonical_id(evidence_id), None)
        self.save()

    def reference_for(self, evidence_id: str, evidence_store=None) -> str:
        eid = canonical_id(evidence_id)
        mapped = self.data.get(eid, "")
        if mapped:
            return mapped
        evidence = evidence_store.get(eid) if evidence_store else None
        return str(evidence.get("reference_id") or "") if evidence else ""

    def analyze(self, text: str, evidence_store, reference_store) -> CitationAnalysis:
        mapping = {}
        reference_ids = []
        unresolved_evidence = []
        unresolved_references = []
        for evidence_id in parse_citations(text):
            if evidence_store.get(evidence_id) is None:
                if evidence_id not in unresolved_evidence:
                    unresolved_evidence.append(evidence_id)
                continue
            reference_id = self.reference_for(evidence_id, evidence_store)
            if not reference_id or reference_store.get(reference_id) is None:
                if evidence_id not in unresolved_references:
                    unresolved_references.append(evidence_id)
                continue
            if evidence_id not in mapping:
                mapping[evidence_id] = len(mapping) + 1
                reference_ids.append(reference_id)
        used = set(reference_ids)
        unused = tuple(item.reference_id for item in reference_store.all() if item.reference_id not in used)
        return CitationAnalysis(
            mapping=mapping,
            reference_ids=tuple(reference_ids),
            unresolved_evidence=tuple(unresolved_evidence),
            unresolved_references=tuple(unresolved_references),
            unused_references=unused,
        )

# 版本: v2.0.1 (2026-08-17) 更新: E-ID 与 Reference ID 引用映射
