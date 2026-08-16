import re

from core import deepseek, log
from core.evidence import parse_citations
from core.prompts import WRITER_SYSTEM

NATURALIZE_RULES = """你是论文语言自然化助手。任务：在不改变任何事实、数据、引用、论点的前提下，改写所给章节，让语言更像普通大学生自然写作。

只能改变：句式结构、表达方式、段落衔接、重复表达、空洞套话、语言流畅度。

绝对不能改变：
- 数字（包括数值、年份、百分比、日期）
- 事实、数据、政策名称、机构名称
- 作者、论文名称、文献信息
- 引用编号 [Ex]（必须原样保留，可随句子移动位置）
- 参考文献、观点与结论

禁止引入原文中没有的新事实、新数据、新文献、新案例。
如果原文中有“暂无足够可靠资料支持该观点”，必须原样保留这句话。

只输出改写后的完整章节正文（Markdown），不要输出任何解释。"""


def naturalize_chapter(text, info, section_title):
    user_msg = (f"论文题目：{info.get('topic')}\n"
                f"章节：{section_title}\n\n原始章节正文：\n\n{text}")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM + "\n\n" + NATURALIZE_RULES},
                          {"role": "user", "content": user_msg}],
                         temperature=0.6, max_tokens=8000, task="polish")
    out = (resp or "").strip()
    if not out:
        raise deepseek.DeepseekError("自然化修改未返回内容")
    return out


PARAGRAPH_RULES = """你是论文段落定向修改助手。任务：只改写用户指定的问题段落，其他段落必须原样保留。

只能改变：句式结构、表达方式、段落内部逻辑、重复表达、空洞套话、语言流畅度、段落衔接。

绝对不能改变：
- 数字（数值、年份、百分比、日期）
- 事实、数据、政策名称、机构名称
- 作者、论文名称、文献信息
- 引用编号 [Ex]（必须原样保留）
- 参考文献、观点与结论

禁止引入原文中没有的新事实、新数据、新文献、新案例。
禁止用无意义同义词替换专业术语。
如果原文中有“暂无足够可靠资料支持该观点”，必须原样保留。

输出：改写后的完整章节正文（Markdown），只改指定段落，其余段落逐字保留。不要输出任何解释。"""


def naturalize_paragraphs(text, flagged_indexes, info, section_title, expand=False, focus=""):
    """只改写指定段落，其余段落原样保留。expand=True 时允许在证据范围内补充分析（不得新增事实）。"""
    from core import style_checker
    paras = style_checker.split_paragraphs(text)
    targets = []
    for i, p in enumerate(paras, 1):
        if i in flagged_indexes:
            targets.append(f"[第{i}段，必须修改]\n{p}")
        else:
            targets.append(f"[第{i}段，原样保留]\n{p}")
    focus_note = (f"\n\n本次修改重点：{focus}。" if focus else "")
    expand_note = ("\n\n当前章节字数低于要求，可以在证据范围内、不新增任何事实与数据的前提下，"
                   "适度增加分析与推论以充实内容。" if expand else "")
    user_msg = (f"论文题目：{info.get('topic')}\n章节：{section_title}\n\n"
                f"章节全文（分段编号）：\n\n" + "\n\n".join(targets) + focus_note + expand_note)
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM + "\n\n" + PARAGRAPH_RULES},
                          {"role": "user", "content": user_msg}],
                         temperature=0.6, max_tokens=8000, task="polish")
    out = (resp or "").strip()
    if not out:
        raise deepseek.DeepseekError("段落修改未返回内容")
    return out


def safe_rewrite(original, rewritten):
    """事实安全校验：引用编号、数字集合、'证据不足'标注均不得变化，否则返回 None（撤销修改）。"""
    if not rewritten or not rewritten.strip():
        return None
    if set(parse_citations(original)) != set(parse_citations(rewritten)):
        return None
    orig_nums = set(re.findall(r"\d+(?:\.\d+)?%?", original or ""))
    new_nums = set(re.findall(r"\d+(?:\.\d+)?%?", rewritten or ""))
    if orig_nums != new_nums:
        return None
    marker = "暂无足够可靠资料支持该观点"
    if (marker in original) != (marker in rewritten):
        return None
    return rewritten

# 版本: v1.5.0 (2026-08-16) 更新: 多模型供应商系统
