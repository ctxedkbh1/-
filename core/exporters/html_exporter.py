import html as html_lib

CSS = """
body { font-family: "Microsoft YaHei", "SimSun", serif; max-width: 800px;
       margin: 40px auto; padding: 0 20px; line-height: 1.8; color: #1d2939; }
h1 { text-align: center; font-size: 22px; margin-bottom: 8px; }
.meta { text-align: center; color: #667085; margin-bottom: 24px; }
h2 { font-size: 17px; border-left: 4px solid #3d8bff; padding-left: 10px;
     margin-top: 28px; }
h3 { font-size: 15px; margin-top: 18px; }
p { text-indent: 2em; margin: 6px 0; }
.abstract, .keywords { text-indent: 2em; }
.refs p { text-indent: 0; font-size: 13px; margin: 2px 0; }
"""


class HtmlExporter:
    def export(self, doc, path):
        parts = [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{html_lib.escape(doc.meta.get('title') or '论文')}</title>",
            f"<style>{CSS}</style>",
            "</head>",
            "<body>",
            f"<h1>{html_lib.escape(doc.meta.get('title') or '论文')}</h1>",
        ]
        info = "　".join(x for x in (
            doc.meta.get("name") and f"姓名：{doc.meta['name']}",
            doc.meta.get("school") and f"学校：{doc.meta['school']}",
            doc.meta.get("major") and f"专业：{doc.meta['major']}",
        ) if x)
        if info:
            parts.append(f'<div class="meta">{html_lib.escape(info)}</div>')
        if doc.abstract:
            parts.append(f'<p class="abstract"><b>摘要：</b>{html_lib.escape(doc.abstract)}</p>')
        if doc.keywords:
            parts.append(f'<p class="keywords"><b>关键词：</b>'
                         f'{html_lib.escape("；".join(doc.keywords))}</p>')
        for block in doc.blocks:
            kind = block.get("kind")
            text = html_lib.escape(block.get("text", ""))
            if kind == "heading1":
                parts.append(f"<h2>{text}</h2>")
            elif kind == "heading2":
                parts.append(f"<h3>{text}</h3>")
            else:
                parts.append(f"<p>{text}</p>")
        if doc.references:
            parts.append("<h2>参考文献</h2>")
            parts.append('<div class="refs">')
            for ref in doc.references:
                parts.append(f"<p>{html_lib.escape(ref)}</p>")
            parts.append("</div>")
        if doc.data_sources:
            parts.append("<h2>数据来源</h2>")
            parts.append('<div class="refs">')
            for i, s in enumerate(doc.data_sources, 1):
                tag = "" if s.get("verified", True) else "【待核实】"
                parts.append(f"<p>[{i}] {html_lib.escape(s.get('name', ''))}{tag}"
                             + (f"　{html_lib.escape(s.get('url', ''))}" if s.get("url") else "")
                             + "</p>")
            parts.append("</div>")
        parts += ["</body>", "</html>"]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
