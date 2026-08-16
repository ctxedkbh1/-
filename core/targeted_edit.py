import re

from core import deepseek, log
from core.prompts import WRITER_SYSTEM

EDIT_RULES = """你是论文定向修改助手。任务：只修改用户指定的内容范围，其余内容原样保留。

只能改变：句式、表达、逻辑、补充用户要求的分析（在证据允许范围内）。

绝对不能改变：
- 数字（数值、年份、百分比、日期）
- 事实、数据、政策名称、机构名称
- 作者、论文名称、文献信息
- 引用编号 [Ex]（必须原样保留）
- 参考文献、核心观点

禁止引入原文中没有的新事实、新数据、新文献。
禁止用同义词无意义替换专业术语。
如果原文有“暂无足够可靠资料支持该观点”，必须原样保留。

只输出修改后的完整内容，不要输出任何解释。"""


def edit_region(full_text, region_text, instruction, info, section_title=""):
    """定向修改：只改 region_text 范围，返回新全文。"""
    if not region_text or not region_text.strip():
        raise deepseek.DeepseekError("请先指定要修改的内容范围。")
    user_msg = (f"论文题目：{info.get('topic')}\n章节：{section_title}\n\n"
                f"【需要修改的内容范围（只改这一段）】\n{region_text}\n\n"
                f"【修改要求】{instruction}")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM + "\n\n" + EDIT_RULES},
                          {"role": "user", "content": user_msg}],
                         temperature=0.6, max_tokens=8000, task="polish")
    new_region = (resp or "").strip()
    if not new_region:
        raise deepseek.DeepseekError("定向修改未返回内容")
    if region_text not in full_text:
        raise deepseek.DeepseekError("修改范围在正文中未找到（可能内容已被改动）")
    return full_text.replace(region_text, new_region, 1)


def safe_apply(original, new_text):
    """安全应用：引用编号与数字集合不得变化，否则返回 None（拒绝应用）。"""
    from core.evidence import parse_citations
    if not new_text or not new_text.strip():
        return None
    if set(parse_citations(original)) != set(parse_citations(new_text)):
        return None
    orig_nums = set(re.findall(r"\d+(?:\.\d+)?%?", original))
    new_nums = set(re.findall(r"\d+(?:\.\d+)?%?", new_text))
    if orig_nums != new_nums:
        return None
    marker = "暂无足够可靠资料支持该观点"
    if (marker in original) != (marker in new_text):
        return None
    return new_text


AI_PARSE_FORMAT_SPEC = '''
只输出 JSON 对象，不要输出任何其他文字，格式：
{"format": {"font": "宋体", "size": 12, "line_spacing": 1.5, "first_indent_chars": 2,
  "align": "justify", "title_font": "黑体", "title_size": 22,
  "h1_font": "黑体", "h1_size": 15, "h2_size": 14, "h3_size": 12,
  "header": "", "footer": "", "page_number": "bottom_center"},
 "ambiguous": ["存在歧义的项目说明，没有则空数组"]}
字号映射：小四=12，五号=10.5，四号=14，小三=15，三号=16，小二=18，二号=22。
align 取值：justify/left/center/right。'''

SIZE_NAMES = {"小五": 9, "五号": 10.5, "小四": 12, "四号": 14, "小三": 15,
              "三号": 16, "小二": 18, "二号": 22, "一号": 26}


def ai_parse_format(text):
    """把自然语言格式要求解析为结构化格式（存在歧义时列出 ambiguous 供用户确认）。"""
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": "用户的格式要求：\n" + text +
                           AI_PARSE_FORMAT_SPEC}],
                         temperature=0.2, json_mode=True, task="analysis")
    data = deepseek.extract_json(resp) or {}
    fmt = data.get("format") if isinstance(data.get("format"), dict) else {}
    return fmt, list(data.get("ambiguous") or [])


def preview_html(fmt, sample_meta=None, sample_sections=None):
    """格式实时预览：按当前格式渲染样例 HTML。"""
    import html as html_lib
    meta = sample_meta or {"title": "论文标题（预览）", "name": "姓名"}
    sections = sample_sections or [
        ("h1", "一、研究背景"),
        ("h2", "（一）小节标题"),
        ("p", "这是正文段落预览。正文采用" + fmt.get("font", "宋体") +
         "，体现当前设置的字体、字号、行距与首行缩进效果，数字示例 2025 年。" * 2),
        ("p", "正文第二段用于查看段落间距与对齐方式。" * 3),
    ]
    css = f"""
    body {{ font-family: "{fmt.get('font', '宋体')}", "{fmt.get('latin_font', 'Times New Roman')}";
           font-size: {fmt.get('size', 12)}pt; line-height: {fmt.get('line_spacing', 1.5)};
           text-align: {'justify' if fmt.get('align') == 'justify' else fmt.get('align', 'left')};
           padding: 24px; max-width: 760px; margin: 0 auto; color: #1d2939; }}
    .title {{ font-family: "{fmt.get('title_font', '黑体')}"; font-size: {fmt.get('title_size', 22)}pt;
             font-weight: {'bold' if fmt.get('title_bold') else 'normal'};
             text-align: center; margin-bottom: 10px; }}
    .meta {{ text-align: center; color: #667085; margin-bottom: 20px; }}
    .abstract {{ margin-bottom: 8px; }}
    .keywords {{ margin-bottom: 16px; }}
    h1 {{ font-family: "{fmt.get('h1_font', '黑体')}"; font-size: {fmt.get('h1_size', 15)}pt; }}
    h2 {{ font-family: "{fmt.get('h2_font', '黑体')}"; font-size: {fmt.get('h2_size', 14)}pt; }}
    h3 {{ font-family: "{fmt.get('h3_font', '黑体')}"; font-size: {fmt.get('h3_size', 12)}pt; }}
    p {{ text-indent: {fmt.get('first_indent_chars', 2)}em; margin: 4px 0; }}
    .refs p {{ text-indent: 0; font-size: 10.5pt; }}
    """
    body = [f'<div class="title">{html_lib.escape(meta.get("title", ""))}</div>',
            f'<div class="meta">{html_lib.escape(meta.get("name", ""))}　{html_lib.escape(meta.get("school", ""))}</div>',
            '<p class="abstract"><b>摘要：</b>这是摘要预览文本，用于查看摘要段落的排版效果。</p>',
            '<p class="keywords"><b>关键词：</b>预览；格式；排版</p>']
    for kind, text in sections:
        tag = "h1" if kind == "h1" else "h2" if kind == "h2" else "h3" if kind == "h3" else "p"
        body.append(f"<{tag}>{html_lib.escape(text)}</{tag}>")
    body.append('<div class="refs"><h1>参考文献</h1>'
                '<p>[1] 张三. 示例文献[J]. 示例学报, 2025, 12(3): 45-52.</p></div>')
    return (f"<html><head><meta charset='utf-8'><style>{css}</style></head>"
            f"<body>{''.join(body)}</body></html>")


def build_format_note(fmt):
    """从结构化格式生成标准格式说明串（供 style_parser / 其他导出使用）。"""
    size_name = "小四"
    for name, pt in SIZE_NAMES.items():
        if abs(pt - float(fmt.get("size", 12))) < 0.01:
            size_name = name
            break
    parts = [f"正文{fmt.get('font', '宋体')}{size_name}",
             f"{fmt.get('line_spacing', 1.5)}倍行距",
             f"首行缩进{fmt.get('first_indent_chars', 2)}字符",
             ALIGN_TEXT.get(fmt.get('align', 'justify'), '两端对齐')]
    if fmt.get("header"):
        parts.append(f"页眉:{fmt['header']}")
    return "，".join(parts) + "。"


ALIGN_TEXT = {"justify": "两端对齐", "left": "左对齐", "center": "居中", "right": "右对齐"}

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
