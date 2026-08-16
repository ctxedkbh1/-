import re

FONTS = ["微软雅黑", "宋体", "黑体", "楷体", "仿宋", "华文中宋", "Times New Roman"]
SIZE_MAP = {"初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22, "小二": 18,
            "三号": 16, "小三": 15, "四号": 14, "小四": 12, "五号": 10.5, "小五": 9}


def parse_format_note(note):
    """从用户的格式要求中解析字体/字号/行距/缩进/页边距，未指定的用默认值。"""
    note = note or ""
    font = None
    for f in FONTS:
        if f in note:
            font = f
            break
    size = None
    for name, pt in SIZE_MAP.items():
        if name in note:
            size = pt
            break
    spacing = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*倍", note)
    if m:
        spacing = float(m.group(1))
    indent = None
    m = re.search(r"首行缩进\s*(\d+)\s*(?:字符|字)", note)
    if m:
        indent = int(m.group(1))
    margin = None
    m = re.search(r"页边距[^\d]*(\d+(?:\.\d+)?)", note)
    if m:
        margin = float(m.group(1))
    return {"font": font or "宋体", "size": size or 12.0,
            "line_spacing": spacing or 1.5, "indent_chars": indent or 2,
            "margin_cm": margin}

# 版本: v1.6.0 (2026-08-16) 更新: 多格式导出系统
