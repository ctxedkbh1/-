from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

_FONT = "STSong-Light"
_registered = False


def _register_font():
    global _registered
    if not _registered:
        pdfmetrics.registerFont(UnicodeCIDFont(_FONT))
        _registered = True


class PdfExporter:
    def export(self, doc, path):
        _register_font()
        d = SimpleDocTemplate(path, pagesize=A4)
        story = []
        title_style = ParagraphStyle("t", fontName=_FONT, fontSize=16, leading=24,
                                     alignment=TA_CENTER, spaceAfter=10)
        h1_style = ParagraphStyle("h1", fontName=_FONT, fontSize=14, leading=22,
                                  spaceBefore=12, spaceAfter=6)
        body_style = ParagraphStyle("b", fontName=_FONT, fontSize=12, leading=22,
                                    firstLineIndent=24, spaceAfter=4)
        ref_style = ParagraphStyle("r", fontName=_FONT, fontSize=10.5, leading=16)
        meta_style = ParagraphStyle("m", fontName=_FONT, fontSize=12, leading=20,
                                    alignment=TA_CENTER, spaceAfter=8)

        story.append(Paragraph(escape(doc.meta.get("title") or "论文"), title_style))
        info = "　".join(x for x in (
            doc.meta.get("name") and f"{doc.meta['name']}",
            doc.meta.get("school") and f"{doc.meta['school']}",
            doc.meta.get("major") and f"{doc.meta['major']}",
        ) if x)
        if info:
            story.append(Paragraph(escape(info), meta_style))
        if doc.abstract:
            story.append(Paragraph(escape("摘要：" + doc.abstract), body_style))
        if doc.keywords:
            story.append(Paragraph(escape("关键词：" + "；".join(doc.keywords)), body_style))

        for block in doc.blocks:
            kind = block.get("kind")
            text = block.get("text", "")
            if kind == "heading1":
                story.append(Paragraph(escape(text), h1_style))
            elif kind == "heading2":
                story.append(Paragraph(escape(text), body_style))
            else:
                story.append(Paragraph(escape(text), body_style))

        if doc.references:
            story.append(Spacer(1, 12))
            story.append(Paragraph(escape("参考文献"), h1_style))
            for ref in doc.references:
                story.append(Paragraph(escape(ref), ref_style))
        d.build(story)

# 版本: v1.6.0 (2026-08-16) 更新: 多格式导出系统
