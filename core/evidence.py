import datetime
import json
import os
import re

from core import paths

SOURCE_TYPE_LABELS = {
    "government": "政府",
    "cnki": "CNKI",
    "openalex": "OpenAlex",
    "crossref": "Crossref",
    "web": "网页",
    "manual": "手动录入",
}

ARTICLE_TYPES = ("cnki", "openalex", "crossref")

CITE_RE = re.compile(r"\[E(\d+)\]")


def canonical_id(eid):
    if isinstance(eid, int):
        return "E%03d" % eid
    m = re.fullmatch(r"E?0*(\d+)", str(eid))
    return "E%03d" % int(m.group(1)) if m else str(eid)


class EvidenceStore:
    def __init__(self):
        self.path = paths.evidence_file()
        self.data = self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        return d
            except Exception:
                pass
        return []

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _next_id(self):
        nums = []
        for e in self.data:
            m = re.fullmatch(r"E?0*(\d+)", str(e.get("id", "")))
            if m:
                nums.append(int(m.group(1)))
        return "E%03d" % (max(nums, default=0) + 1)

    def add(self, record):
        record = dict(record)
        record["id"] = canonical_id(record.get("id") or self._next_id())
        record.setdefault("retrieved_at", datetime.date.today().isoformat())
        record.setdefault("verified", True)
        record.setdefault("source_type", record.get("source_type") or "manual")
        self.data.append(record)
        self.save()
        return record["id"]

    def get(self, eid):
        cid = canonical_id(eid)
        for e in self.data:
            if canonical_id(e.get("id")) == cid:
                return e
        return None

    def update(self, eid, values):
        e = self.get(eid)
        if not e:
            return False
        e.update(values)
        e["id"] = canonical_id(e.get("id"))
        self.save()
        return True

    def delete(self, eid):
        cid = canonical_id(eid)
        self.data = [e for e in self.data if canonical_id(e.get("id")) != cid]
        self.save()

    def all(self):
        return list(self.data)

    def search(self, text):
        t = (text or "").strip().lower()
        if not t:
            return self.all()
        out = []
        for e in self.data:
            blob = " ".join(str(v) for v in e.values()).lower()
            if t in blob:
                out.append(e)
        return out

    def count_by_type(self):
        counts = {k: 0 for k in SOURCE_TYPE_LABELS}
        for e in self.data:
            counts[e.get("source_type", "manual")] = counts.get(e.get("source_type", "manual"), 0) + 1
        return counts

    def verified_count(self):
        return sum(1 for e in self.data if e.get("verified"))

    def pending_count(self):
        out = []
        for e in self.data:
            miss = self.missing_fields(e)
            if miss:
                out.append((e["id"], miss))
        return out

    def missing_fields(self, e):
        if e.get("source_type") not in ARTICLE_TYPES:
            url_miss = [] if e.get("url") else ["URL"]
            return url_miss
        checks = [("authors", "作者"), ("journal", "期刊"), ("year", "年份"),
                  ("volume_issue_pages", "卷期页码"), ("doi", "DOI")]
        return [label for key, label in checks if not str(e.get(key) or "").strip()]

    def to_reference(self, e, cite_date=None):
        cite_date = cite_date or datetime.date.today().isoformat()
        st = e.get("source_type", "manual")
        if st in ARTICLE_TYPES:
            authors = str(e.get("authors") or "").strip()
            title = str(e.get("title") or "").strip()
            journal = str(e.get("journal") or "").strip()
            year = str(e.get("year") or "").strip()
            vp = str(e.get("volume_issue_pages") or "").strip()
            doi = str(e.get("doi") or "").strip()
            parts = []
            if authors:
                parts.append(authors)
            if title:
                parts.append(title)
            loc_parts = []
            if journal:
                loc_parts.append(journal)
            if year:
                loc_parts.append(year)
            if vp:
                loc_parts.append(vp)
            loc = ", ".join(loc_parts)
            if loc:
                parts.append(loc)
            text = ". ".join(parts)
            if text and not text.endswith("."):
                text += "."
            if doi:
                text += f" DOI: {doi}."
            missing = self.missing_fields(e)
            if missing:
                text += f"（著录信息待完善：缺{'、'.join(missing)}）"
            return text
        title = str(e.get("title") or "").strip()
        org = str(e.get("organization") or e.get("source") or "来源未标注").strip()
        url = str(e.get("url") or "").strip()
        pub = str(e.get("published_at") or "").strip()
        if url:
            text = f"{org}. {title}[EB/OL]" if title else f"{org}[EB/OL]"
            if pub:
                text += f". ({pub})"
            text += f"[引用日期 {cite_date}]. {url}."
            return text
        text = f"{org}. {title}." if title else f"{org}."
        return text + "（著录信息待完善：缺 URL，请补充完整著录信息）"

    def export_json(self):
        return json.dumps(self.data, ensure_ascii=False, indent=2)

    def export_markdown(self):
        lines = ["# 证据表", "",
                 f"导出时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                 f"证据总数：{len(self.data)} 条", ""]
        for e in self.data:
            lines.append(f"## {e.get('id')}")
            lines.append(f"- 类型：{SOURCE_TYPE_LABELS.get(e.get('source_type'), e.get('source_type'))}")
            lines.append(f"- 标题：{e.get('title') or '（无）'}")
            if e.get("authors"):
                lines.append(f"- 作者：{e.get('authors')}")
            if e.get("organization"):
                lines.append(f"- 机构：{e.get('organization')}")
            if e.get("journal"):
                lines.append(f"- 期刊：{e.get('journal')}")
            if e.get("year"):
                lines.append(f"- 年份：{e.get('year')}")
            if e.get("volume_issue_pages"):
                lines.append(f"- 卷期页码：{e.get('volume_issue_pages')}")
            if e.get("doi"):
                lines.append(f"- DOI：{e.get('doi')}")
            if e.get("url"):
                lines.append(f"- URL：{e.get('url')}")
            if e.get("published_at"):
                lines.append(f"- 发布日期：{e.get('published_at')}")
            lines.append(f"- 抓取/录入时间：{e.get('retrieved_at') or '未标注'}")
            lines.append(f"- 状态：{'已验证' if e.get('verified') else '未验证'}"
                         + ("，著录待完善" if self.missing_fields(e) else ""))
            if e.get("content"):
                lines.append(f"- 证据内容：{e.get('content')}")
            lines.append("")
        return "\n".join(lines)


def parse_citations(text):
    return [canonical_id(int(m.group(1))) for m in CITE_RE.finditer(text or "")]

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
