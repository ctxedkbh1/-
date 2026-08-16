import re

from core import log
from core.exporters.docx_exporter import DocxExporter
from core.exporters.html_exporter import HtmlExporter
from core.exporters.md_exporter import MarkdownExporter
from core.exporters.pdf_exporter import PdfExporter
from core.exporters.pptx_exporter import PptxExporter
from core.exporters.txt_exporter import TxtExporter
from core.exporters.verify import verify

FORMAT_LABELS = {
    "docx": "DOCX（Word）",
    "pptx": "PPTX（PowerPoint）",
    "pdf": "PDF",
    "txt": "TXT",
    "md": "Markdown",
    "html": "HTML",
}

EXPORTERS = {
    "docx": DocxExporter(),
    "pptx": PptxExporter(),
    "pdf": PdfExporter(),
    "txt": TxtExporter(),
    "md": MarkdownExporter(),
    "html": HtmlExporter(),
}


class ExportError(Exception):
    pass


def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(name or "")).strip()
    name = name.strip(" .")
    return name or "论文"


def export(document, fmt, path):
    """统一导出入口：导出后自动验证，失败自动重生成一次。"""
    if fmt not in EXPORTERS:
        raise ExportError(f"不支持的格式: {fmt}")
    last_err = None
    for attempt in range(2):
        try:
            EXPORTERS[fmt].export(document, path)
            result = verify(path, fmt)
            if result["ok"]:
                log.get().info("导出成功 format=%s path=%s checks=%s",
                               fmt, path, result["checks"])
                return {"path": path, "verify": result}
            last_err = f"验证未通过: {'；'.join(result['checks'])}"
            log.get().warning("导出验证未通过(第%d次) %s: %s", attempt + 1, fmt, last_err)
        except Exception as e:
            last_err = str(e)
            log.get().warning("导出失败(第%d次) %s: %s", attempt + 1, fmt, e)
    raise ExportError(f"{fmt} 导出失败（已自动重试）: {last_err}")

# 版本: v1.6.0 (2026-08-16) 更新: 多格式导出系统
