class MarkdownExporter:
    def export(self, doc, path):
        lines = [f"# {doc.meta.get('title') or '论文'}", ""]
        if doc.abstract:
            lines += [f"**摘要**：{doc.abstract}", ""]
        if doc.keywords:
            lines += ["**关键词**：" + "；".join(doc.keywords), ""]
        for block in doc.blocks:
            kind = block.get("kind")
            text = block.get("text", "")
            if kind == "heading1":
                lines += [f"## {text}", ""]
            elif kind == "heading2":
                lines += [f"### {text}", ""]
            else:
                lines += [text, ""]
        if doc.references:
            lines += ["## 参考文献", ""]
            lines += doc.references
        if doc.data_sources:
            lines += ["", "## 数据来源", ""]
            for i, s in enumerate(doc.data_sources, 1):
                tag = "" if s.get("verified", True) else "【待核实】"
                lines.append(f"[{i}] {s.get('name', '')}{tag}" +
                             (f"　{s.get('url', '')}" if s.get("url") else ""))
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
