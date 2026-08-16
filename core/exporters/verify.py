import os
import re

from core import log


def verify(path, fmt):
    checks = []
    try:
        if not os.path.exists(path):
            return {"ok": False, "checks": ["文件不存在"]}
        size = os.path.getsize(path)
        if size <= 0:
            return {"ok": False, "checks": ["文件大小为 0"]}
        checks.append(f"文件存在，大小 {size} 字节")
        if fmt == "docx":
            from docx import Document
            d = Document(path)
            paras = [p.text for p in d.paragraphs if p.text.strip()]
            checks.append(f"DOCX 结构正常，可解析（{len(paras)} 个段落）")
            text = "".join(paras)
            if not paras:
                return {"ok": False, "checks": checks + ["正文为空"]}
            if "参考文献" in text:
                checks.append("参考文献存在")
            else:
                checks.append("未检测到参考文献章节（不强制）")
            return {"ok": True, "checks": checks}
        if fmt == "pptx":
            from pptx import Presentation
            prs = Presentation(path)
            n = len(prs.slides)
            checks.append(f"PPTX 结构正常，Slide 数量 {n}")
            if n < 2:
                return {"ok": False, "checks": checks + ["Slide 数量异常"]}
            return {"ok": True, "checks": checks}
        if fmt == "pdf":
            with open(path, "rb") as f:
                head = f.read(8)
            if not head.startswith(b"%PDF"):
                return {"ok": False, "checks": checks + ["PDF 文件头损坏"]}
            with open(path, "rb") as f:
                data = f.read()
            pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
            checks.append(f"PDF 生成成功，页面约 {max(pages, 1)} 页")
            if pages < 1:
                return {"ok": False, "checks": checks + ["页面数量异常"]}
            return {"ok": True, "checks": checks}
        if fmt in ("txt", "md", "html"):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            checks.append(f"文本内容 {len(text)} 字符，UTF-8 正常")
            if len(text) < 50:
                return {"ok": False, "checks": checks + ["内容过短"]}
            if fmt == "html" and ("<html" not in text.lower() or "</html>" not in text.lower()):
                return {"ok": False, "checks": checks + ["HTML 结构异常"]}
            return {"ok": True, "checks": checks}
        return {"ok": True, "checks": checks + [f"格式 {fmt} 无需额外校验"]}
    except Exception as e:
        log.get().warning("文件验证失败 %s %s: %s", fmt, path, e)
        return {"ok": False, "checks": checks + [f"验证异常: {e}"]}

# 版本: v1.6.0 (2026-08-16) 更新: 多格式导出系统
