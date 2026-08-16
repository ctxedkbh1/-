import re


class Document:
    """统一文档中间格式：所有导出格式（DOCX/PPTX/PDF/TXT/MD/HTML）都基于它生成。"""

    def __init__(self):
        self.meta = {}
        self.abstract = ""
        self.keywords = []
        self.blocks = []
        self.references = []
        self.data_sources = []

    def word_count(self):
        return len(re.findall(r"[\u4e00-\u9fff]", "".join(
            b.get("text", "") for b in self.blocks)))


def document_from_text(final_text, meta=None, format_note=""):
    doc = Document()
    doc.meta = dict(meta or {})
    doc.meta.setdefault("format_note", format_note)
    in_refs = False
    for raw in (final_text or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):
            doc.meta.setdefault("title", line[2:].strip())
            continue
        m = re.match(r"\*\*摘要\*\*：?(.*)", line)
        if m:
            doc.abstract = m.group(1).strip()
            continue
        m = re.match(r"\*\*关键词\*\*：?(.*)", line)
        if m:
            doc.keywords = [k.strip() for k in re.split(r"[；;,，]", m.group(1)) if k.strip()]
            continue
        if line.startswith("## 参考文献"):
            in_refs = True
            continue
        if in_refs:
            if re.match(r"^\[\d+\]\s", line):
                doc.references.append(line.strip())
            continue
        if line.startswith("### "):
            doc.blocks.append({"kind": "heading2", "text": line[4:].strip()})
        elif line.startswith("## "):
            doc.blocks.append({"kind": "heading1", "text": line[3:].strip()})
        else:
            doc.blocks.append({"kind": "paragraph", "text": line.strip()})
    return doc

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
