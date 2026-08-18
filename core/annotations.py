import datetime
import json
import os
import re

from core import paths
from core.evidence import canonical_id

ANNOTATION_MARKER_RE = re.compile(r"\[([^\W\d_][\w.-]*\d+)\]", re.UNICODE)


class AnnotationStoreError(RuntimeError):
    """Raised when an annotation file cannot be safely read or written."""

DEFAULT_STYLE_RECORDS = [
    {
        "style_id": "evidence",
        "name": "证据引用",
        "prefix": "E",
        "separator": "",
        "width": 3,
        "kind": "evidence",
        "color": "#356fd3",
        "description": "正文中的证据标注，自动与参考文献映射。",
        "enabled": True,
        "immutable": True,
    },
    {
        "style_id": "note",
        "name": "普通批注",
        "prefix": "N",
        "separator": "",
        "width": 3,
        "kind": "note",
        "color": "#667085",
        "description": "普通说明或写作批注。",
        "enabled": True,
        "immutable": True,
    },
    {
        "style_id": "todo",
        "name": "待办批注",
        "prefix": "T",
        "separator": "",
        "width": 3,
        "kind": "todo",
        "color": "#dc6803",
        "description": "需要后续处理的待办标记。",
        "enabled": True,
        "immutable": True,
    },
    {
        "style_id": "term",
        "name": "术语说明",
        "prefix": "A",
        "separator": "",
        "width": 3,
        "kind": "note",
        "color": "#039855",
        "description": "解释术语、缩写或概念。",
        "enabled": True,
        "immutable": True,
    },
]


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def normalize_label(label):
    text = str(label or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    return text.upper()


def parse_annotation_markers(text):
    labels = []
    for match in ANNOTATION_MARKER_RE.finditer(text or ""):
        label = normalize_label(match.group(1))
        if label not in labels:
            labels.append(label)
    return labels


def annotation_marker_sequence(text):
    return [normalize_label(match.group(1))
            for match in ANNOTATION_MARKER_RE.finditer(text or "")]


def replace_annotation_markers(text, mapping):
    replacements = {normalize_label(old): normalize_label(new)
                    for old, new in (mapping or {}).items()}
    if not replacements:
        return text or ""

    def sub(match):
        label = normalize_label(match.group(1))
        replacement = replacements.get(label)
        return f"[{replacement}]" if replacement else match.group(0)

    return ANNOTATION_MARKER_RE.sub(sub, text or "")


def remove_annotation_markers(text, labels):
    targets = {_lookup_label(label) for label in (labels or [])}
    if not targets:
        return text or ""

    def sub(match):
        label = normalize_label(match.group(1))
        return "" if _lookup_label(label) in targets else match.group(0)

    return ANNOTATION_MARKER_RE.sub(sub, text or "")


def _lookup_label(label):
    text = normalize_label(label)
    if re.fullmatch(r"E[-_]?0*\d+", text, re.IGNORECASE):
        return canonical_id(text)
    return text


def _safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_number(label):
    m = re.search(r"(\d+)$", str(label or ""))
    return int(m.group(1)) if m else None


class AnnotationStyleStore:
    def __init__(self, path: str = ""):
        self.path = path or paths.annotation_styles_file()
        self.load_error = ""
        self.data = self._load()

    def _load(self):
        raw_records = []
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, list):
                    raw_records = raw
                elif isinstance(raw, dict):
                    raw_records = raw.get("styles") if isinstance(raw.get("styles"), list) else []
            except (OSError, json.JSONDecodeError) as exc:
                self.load_error = f"样式文件读取失败: {exc}"
                raw_records = []
        elif os.path.exists(self.path):
            self.load_error = "样式文件格式无效"
        if os.path.exists(self.path) and not raw_records:
            try:
                with open(self.path, encoding="utf-8") as f:
                    raw = json.load(f)
                if not isinstance(raw, (list, dict)):
                    self.load_error = "样式文件格式无效"
                elif isinstance(raw, dict) and not isinstance(raw.get("styles"), list):
                    self.load_error = "样式文件缺少 styles 数组"
            except Exception:
                pass
        styles = {item["style_id"]: self._normalize_style(item) for item in DEFAULT_STYLE_RECORDS}
        for item in raw_records:
            if isinstance(item, dict):
                normalized = self._normalize_style(item)
                styles[normalized["style_id"]] = normalized
        return list(styles.values())

    def _normalize_style(self, style):
        style = dict(style or {})
        style_id = str(style.get("style_id") or style.get("id") or "").strip().lower()
        if not style_id:
            prefix = str(style.get("prefix") or "").strip().lower()
            style_id = prefix or f"style_{len(self.data) + 1 if hasattr(self, 'data') else 1}"
        style["style_id"] = style_id
        style["name"] = str(style.get("name") or style_id).strip()
        prefix = str(style.get("prefix") or style.get("abbr") or style_id[:1] or "N").strip().upper()
        style["prefix"] = prefix or "N"
        style["separator"] = str(style.get("separator") or "").strip()
        style["width"] = max(1, _safe_int(style.get("width"), 3) or 3)
        style["kind"] = str(style.get("kind") or "note").strip().lower() or "note"
        style["color"] = str(style.get("color") or "#667085").strip()
        style["description"] = str(style.get("description") or "").strip()
        style["enabled"] = bool(style.get("enabled", True))
        style["immutable"] = bool(style.get("immutable", style_id == "evidence"))
        style["created_at"] = str(style.get("created_at") or _now())
        style["updated_at"] = str(style.get("updated_at") or style["created_at"])
        return style

    def save(self):
        if self.load_error:
            raise AnnotationStoreError(self.load_error + "；已阻止覆盖原文件，请先修复或备份。")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def all(self):
        return list(self.data)

    def get(self, style_id):
        sid = str(style_id or "").strip().lower()
        return next((item for item in self.data if item["style_id"] == sid), None)

    def upsert(self, style):
        incoming = self._normalize_style(style)
        if not re.fullmatch(r"[^\W\d_][\w]{0,7}", incoming["prefix"], re.UNICODE):
            raise ValueError("样式前缀必须以字母或中文开头，且只能包含字母、数字或中文。")
        if not re.fullmatch(r"[-_.]?", incoming["separator"]):
            raise ValueError("样式分隔符只能是短横线、下划线、点或留空。")
        current = self.get(incoming["style_id"])
        if current and current.get("immutable") and not incoming.get("immutable"):
            raise ValueError("该样式 ID 属于系统默认样式，不能被新模板覆盖。")
        if current:
            created_at = current.get("created_at") or incoming["created_at"]
            current.update(incoming)
            current["created_at"] = created_at
            current["updated_at"] = _now()
            self.save()
            return current
        self.data.append(incoming)
        self.save()
        return incoming

    def delete(self, style_id):
        current = self.get(style_id)
        if not current or current.get("immutable"):
            return False
        self.data = [item for item in self.data if item["style_id"] != current["style_id"]]
        self.save()
        return True

    def format_label(self, style_id, number):
        style = self.get(style_id) or self.get("note") or DEFAULT_STYLE_RECORDS[1]
        number = max(1, _safe_int(number, 1) or 1)
        return f"{style['prefix']}{style['separator']}{number:0{style['width']}d}"

    def marker_for(self, style_id, number):
        return f"[{self.format_label(style_id, number)}]"


class AnnotationStore:
    def __init__(self, path: str = "", style_store: AnnotationStyleStore | None = None):
        self.path = path or paths.annotations_file()
        self.styles = style_store or AnnotationStyleStore()
        self.load_error = ""
        self.data = []
        self.data = self._load()

    def _load(self):
        raw_records = []
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, list):
                    raw_records = raw
                elif isinstance(raw, dict):
                    raw_records = raw.get("annotations") if isinstance(raw.get("annotations"), list) else []
            except (OSError, json.JSONDecodeError) as exc:
                self.load_error = f"批注文件读取失败: {exc}"
                raw_records = []
        if os.path.exists(self.path) and not raw_records:
            try:
                with open(self.path, encoding="utf-8") as f:
                    raw = json.load(f)
                if not isinstance(raw, (list, dict)):
                    self.load_error = "批注文件格式无效"
                elif isinstance(raw, dict) and not isinstance(raw.get("annotations"), list):
                    self.load_error = "批注文件缺少 annotations 数组"
            except Exception:
                pass
        self.data = []
        for idx, item in enumerate(raw_records, 1):
            if isinstance(item, dict):
                self.data.append(self._normalize_record(item, idx))
        return self.data

    def _normalize_record(self, record, index=0, preserve_id=""):
        record = dict(record or {})
        style_id = str(record.get("style_id") or "note").strip().lower() or "note"
        style = self.styles.get(style_id) or self.styles.get("note") or DEFAULT_STYLE_RECORDS[1]
        annotation_id = str(record.get("annotation_id") or record.get("id") or "").strip()
        existing_ids = {item.get("annotation_id") for item in self.data}
        if not annotation_id or (annotation_id in existing_ids and annotation_id != preserve_id):
            annotation_id = self._next_annotation_id()
        evidence_id = canonical_id(record.get("evidence_id")) if record.get("evidence_id") else ""
        source_id = str(record.get("source_id") or record.get("target_id") or evidence_id or "").strip()
        display_label = normalize_label(record.get("display_label") or record.get("label") or "")
        number = _safe_int(record.get("number"), None)
        if number is None:
            number = _extract_number(display_label)
        if not display_label:
            if style_id == "evidence" and evidence_id:
                display_label = evidence_id
            else:
                number = number or index or 1
                display_label = self.styles.format_label(style_id, number)
        if number is None:
            number = _extract_number(display_label) or (index or 1)
        tags = record.get("tags")
        if isinstance(tags, str):
            tags = [t.strip() for t in re.split(r"[，,;；\s]+", tags) if t.strip()]
        elif not isinstance(tags, list):
            tags = []
        created_at = str(record.get("created_at") or _now())
        updated_at = str(record.get("updated_at") or created_at)
        body = str(record.get("body") or record.get("content") or "").strip()
        title = str(record.get("title") or "").strip()
        color = str(record.get("color") or style.get("color") or "#667085").strip()
        status = str(record.get("status") or "active").strip().lower() or "active"
        kind = str(record.get("kind") or style.get("kind") or ("evidence" if style_id == "evidence" else "note")).strip().lower() or "note"
        return {
            "annotation_id": annotation_id,
            "style_id": style_id,
            "style_name": style.get("name") or style_id,
            "number": number,
            "display_label": display_label,
            "label": display_label,
            "kind": kind,
            "title": title,
            "body": body,
            "tags": tags,
            "status": status,
            "color": color,
            "evidence_id": evidence_id,
            "source_id": source_id,
            "reference_id": str(record.get("reference_id") or "").strip(),
            "source_type": str(record.get("source_type") or "").strip(),
            "target_type": str(record.get("target_type") or ("evidence" if evidence_id else "")).strip(),
            "target_text": str(record.get("target_text") or "").strip(),
            "summary": str(record.get("summary") or "").strip(),
            "notes": str(record.get("notes") or "").strip(),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    def _next_annotation_id(self):
        numbers = []
        for item in self.data:
            m = re.fullmatch(r"ann_(\d+)", str(item.get("annotation_id") or ""), re.IGNORECASE)
            if m:
                numbers.append(int(m.group(1)))
        candidate = max(numbers, default=0) + 1
        existing = {str(item.get("annotation_id") or "") for item in self.data}
        while f"ann_{candidate:03d}" in existing:
            candidate += 1
        return f"ann_{candidate:03d}"

    def save(self):
        if self.load_error:
            raise AnnotationStoreError(self.load_error + "；已阻止覆盖原文件，请先修复或备份。")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def all(self):
        return list(self.data)

    def next_number(self, style_id):
        sid = str(style_id or "note").strip().lower() or "note"
        numbers = [
            _safe_int(item.get("number"), 0) or 0
            for item in self.data
            if item.get("style_id") == sid
        ]
        return max(numbers, default=0) + 1

    def get(self, annotation_id):
        aid = str(annotation_id or "").strip()
        return next((item for item in self.data if item["annotation_id"] == aid), None)

    def get_by_label(self, label):
        target = _lookup_label(label)
        if not target:
            return None
        direct = next((item for item in self.data
                       if _lookup_label(item.get("display_label")) == target), None)
        if direct:
            return direct
        return next((item for item in self.data
                     if _lookup_label(item.get("evidence_id")) == target), None)

    def add(self, record):
        normalized = self._normalize_record(record)
        self.data.append(normalized)
        self.save()
        return normalized

    def update(self, annotation_id, values):
        record = self.get(annotation_id)
        if not record:
            return False
        merged = dict(record)
        merged.update(dict(values or {}))
        merged["annotation_id"] = record["annotation_id"]
        merged["created_at"] = record.get("created_at") or merged.get("created_at") or _now()
        merged["updated_at"] = _now()
        normalized = self._normalize_record(merged, preserve_id=record["annotation_id"])
        for idx, item in enumerate(self.data):
            if item["annotation_id"] == record["annotation_id"]:
                self.data[idx] = normalized
                self.save()
                return True
        return False

    def delete(self, annotation_id):
        aid = str(annotation_id or "").strip()
        for index, item in enumerate(self.data):
            if item["annotation_id"] == aid:
                self.data.pop(index)
                self.save()
                return True
        return False

    def delete_many(self, annotation_ids):
        ids = {str(item or "").strip() for item in annotation_ids or []}
        before = len(self.data)
        self.data = [item for item in self.data if item["annotation_id"] not in ids]
        if len(self.data) != before:
            self.save()
        return before - len(self.data)

    def search(self, query, style_id="", status=""):
        needle = str(query or "").strip().lower()
        sid = str(style_id or "").strip().lower()
        st = str(status or "").strip().lower()
        out = []
        for item in self.data:
            if sid and item.get("style_id") != sid:
                continue
            if st and item.get("status") != st:
                continue
            if not needle:
                out.append(item)
                continue
            blob = " ".join(str(v) for v in item.values()).lower()
            if needle in blob:
                out.append(item)
        return out

    def resolve_label(self, label):
        target = _lookup_label(label)
        if not target:
            return None
        return self.get_by_label(target)

    def marker_for(self, record):
        label = record.get("display_label") or record.get("label") or ""
        return f"[{normalize_label(label)}]" if label else ""

    def used_records(self, text, include_evidence=True):
        labels = []
        seen = set()
        for label in parse_annotation_markers(text):
            if label in seen:
                continue
            record = self.get_by_label(label)
            if not record:
                continue
            if not include_evidence and record.get("style_id") == "evidence":
                continue
            labels.append(record)
            seen.add(label)
        return labels

    def export_json(self):
        return json.dumps(self.data, ensure_ascii=False, indent=2)

    def export_markdown(self):
        lines = [
            "# 批注表",
            "",
            f"导出时间：{_now()}",
            f"批注总数：{len(self.data)} 条",
            "",
        ]
        for item in self.data:
            style = self.styles.get(item.get("style_id")) or {}
            lines.append(f"## [{item.get('display_label') or item.get('annotation_id')}] {item.get('title') or '（无标题）'}")
            lines.append(f"- 批注ID：{item.get('annotation_id')}")
            lines.append(f"- 样式：{style.get('name') or item.get('style_id')}")
            lines.append(f"- 状态：{item.get('status') or 'active'}")
            if item.get("evidence_id"):
                lines.append(f"- 关联证据：{item.get('evidence_id')}")
            if item.get("target_text"):
                lines.append(f"- 关联文本：{item.get('target_text')}")
            if item.get("body"):
                lines.append(f"- 内容：{item.get('body')}")
            if item.get("tags"):
                lines.append(f"- 标签：{'、'.join(item.get('tags') or [])}")
            lines.append("")
        return "\n".join(lines)

    def sync_legacy_evidence(self, evidence_store):
        if self.load_error:
            raise AnnotationStoreError(self.load_error + "；已阻止同步以保护原文件。")
        evidence_items = evidence_store.all() if evidence_store else []
        by_evidence = {}
        for item in self.data:
            if item.get("style_id") != "evidence":
                continue
            key = _lookup_label(item.get("evidence_id") or item.get("source_id") or item.get("display_label"))
            if key:
                by_evidence[key] = item
        changed = False
        now = _now()
        active_evidence = {canonical_id(item.get("id")) for item in evidence_items}
        retained = [
            item for item in self.data
            if item.get("style_id") != "evidence"
            or canonical_id(item.get("evidence_id")) in active_evidence
        ]
        if len(retained) != len(self.data):
            self.data = retained
            changed = True
        compare_keys = (
            "style_id", "style_name", "number", "display_label", "label", "kind",
            "title", "body", "status", "color", "evidence_id", "source_id",
            "reference_id", "source_type", "target_type", "target_text", "summary",
            "notes", "tags",
        )
        for idx, evidence in enumerate(evidence_items, 1):
            eid = canonical_id(evidence.get("id"))
            style = self.styles.get("evidence") or DEFAULT_STYLE_RECORDS[0]
            payload = {
                "annotation_id": by_evidence.get(eid, {}).get("annotation_id") or self._next_annotation_id(),
                "style_id": "evidence",
                "style_name": style.get("name") or "证据引用",
                "number": _safe_int(eid[1:], idx),
                "display_label": eid,
                "label": eid,
                "kind": "evidence",
                "title": str(evidence.get("title") or "").strip() or str(evidence.get("content") or "")[:40].strip(),
                "body": str(evidence.get("content") or "").strip(),
                "status": "active" if evidence.get("verified", True) else "unverified",
                "color": style.get("color") or "#356fd3",
                "evidence_id": eid,
                "source_id": eid,
                "reference_id": str(evidence.get("reference_id") or "").strip(),
                "source_type": str(evidence.get("source_type") or "").strip(),
                "target_type": "evidence",
                "target_text": str(evidence.get("content") or "").strip()[:120],
                "summary": str(evidence.get("abstract") or "").strip(),
                "notes": "",
                "created_at": by_evidence.get(eid, {}).get("created_at") or now,
                "updated_at": now,
                "tags": by_evidence.get(eid, {}).get("tags") or [],
            }
            current = by_evidence.get(eid)
            if current:
                normalized = self._normalize_record(payload, idx,
                                                    preserve_id=current["annotation_id"])
                current_snapshot = {key: current.get(key) for key in compare_keys}
                normalized_snapshot = {key: normalized.get(key) for key in compare_keys}
                if current_snapshot != normalized_snapshot:
                    for i, item in enumerate(self.data):
                        if item["annotation_id"] == current["annotation_id"]:
                            normalized["created_at"] = current.get("created_at") or normalized.get("created_at")
                            normalized["updated_at"] = now
                            self.data[i] = normalized
                            changed = True
                            break
            else:
                self.data.append(self._normalize_record(payload, idx))
                changed = True
        if changed:
            self.save()
        return changed

    def renumber(self, style_id=None, include_evidence=False):
        sid = str(style_id or "").strip().lower()
        targets = [item for item in self.data if (not sid or item.get("style_id") == sid)]
        if not include_evidence:
            targets = [item for item in targets if item.get("style_id") != "evidence"]
        targets.sort(key=lambda item: (item.get("number") or 0, item.get("created_at") or ""))
        mapping = {}
        changed = False
        for idx, item in enumerate(targets, 1):
            old = item.get("display_label") or item.get("label") or ""
            if item.get("style_id") == "evidence" and not include_evidence:
                continue
            item["number"] = idx
            item["display_label"] = self.styles.format_label(item.get("style_id"), idx)
            item["label"] = item["display_label"]
            item["updated_at"] = _now()
            if old and old != item["display_label"]:
                mapping[old] = item["display_label"]
                changed = True
        if changed:
            self.save()
        return mapping

# 版本: v2.2.0 (2026-08-18) 更新: 批注与样式数据层
