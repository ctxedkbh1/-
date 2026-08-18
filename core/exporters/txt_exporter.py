class TxtExporter:
    def export(self, doc, path):
        lines = [doc.meta.get("title") or "论文", ""]
        info = "　".join(x for x in (
            doc.meta.get("name") and f"姓名：{doc.meta['name']}",
            doc.meta.get("school") and f"学校：{doc.meta['school']}",
            doc.meta.get("major") and f"专业：{doc.meta['major']}",
        ) if x)
        if info:
            lines += [info, ""]
        if doc.abstract:
            lines += ["摘要：" + doc.abstract, ""]
        if doc.keywords:
            lines += ["关键词：" + "；".join(doc.keywords), ""]
        for block in doc.blocks:
            lines.append(block.get("text", ""))
            lines.append("")
        if doc.annotations:
            lines += ["批注说明", ""]
            lines += doc.annotations
            lines.append("")
        if doc.references:
            lines += ["参考文献", ""]
            lines += doc.references
        if doc.data_sources:
            lines += ["", "数据来源", ""]
            for i, s in enumerate(doc.data_sources, 1):
                tag = "" if s.get("verified", True) else "【待核实】"
                lines.append(f"[{i}] {s.get('name', '')}{tag}" +
                             (f"　{s.get('url', '')}" if s.get("url") else ""))
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

# 版本: v2.2.0 (2026-08-18) 更新: 批注说明导出
