import re

from core import deepseek, log
from core.prompts import WRITER_SYSTEM

TEMPLATE_PHRASES = [
    "综上所述", "不可否认", "众所周知", "不言而喻", "显而易见",
    "随着……不断发展", "随着……的不断发展", "在新时代背景下",
    "具有重要意义", "具有深远意义", "发挥重要作用", "起到重要作用",
    "发挥关键作用", "不断提高", "进一步加强", "深入贯彻", "积极推动",
    "大力加强", "提供有力保障", "奠定坚实基础", "引起广泛关注",
    "有效提升", "全面推动", "日益增长", "蓬勃发展", "日新月异",
    "任重道远", "刻不容缓", "当务之急", "大势所趋", "不可或缺",
    "起到了积极的推动作用", "提供了重要参考", "值得深入探讨",
    "引发深刻变革", "带来深刻影响", "逐步完善", "持续优化",
]

CONNECTIVES = ["随着", "因此", "然而", "同时", "此外", "首先", "其次", "最后",
               "再次", "综上", "总之", "所以", "并且", "而且", "另外", "一方面"]

SENT_SPLIT = r"[。！？；\n]"

STYLE_AI_JSON_SPEC = '''
只输出 JSON 对象，不要输出任何其他文字，格式：
{"ok": true, "issues": [{"problem": "问题描述", "location": "大致位置",
  "severity": "高/中/低", "suggestion": "修改建议"}]}
请检查：论点是否明确、论据是否充分、段落之间是否有逻辑关系、
是否存在大量空话、是否存在重复内容。只指出问题，不要改写。'''


def _sentences(text):
    return [s.strip() for s in re.split(SENT_SPLIT, text or "") if len(s.strip()) >= 2]


def split_paragraphs(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in (text or "").splitlines() if p.strip()]
    return parts


def analyze_paragraph(text):
    """单段分析：返回模板化、连接词开头、空洞、重复句等标记。"""
    sentences = _sentences(text)
    tpl = []
    for phrase in TEMPLATE_PHRASES:
        cnt = len(re.findall(re.escape(phrase), text))
        if cnt:
            tpl.append({"phrase": phrase.replace("……", "…"), "count": cnt})
    conn_start = sum(1 for s in sentences if any(s.startswith(c) for c in CONNECTIVES))
    empties = [s for s in sentences if len(s) <= 10 and any(
        p.replace("……", "") in s for p in ("综上所述", "具有重要意义", "发挥着重要作用",
                                         "总之", "因此", "由此可见"))]
    seen = {}
    dups = []
    for s in sentences:
        if len(s) >= 12:
            seen[s] = seen.get(s, 0) + 1
    for s, c in seen.items():
        if c > 1:
            dups.append(s)
    flags = []
    if tpl:
        flags.append("模板句")
    if conn_start >= 2 and conn_start / max(len(sentences), 1) >= 0.5:
        flags.append("连接词开头")
    if empties:
        flags.append("空洞表达")
    if dups:
        flags.append("段内重复句")
    return {
        "template_hits": tpl,
        "template_count": sum(h["count"] for h in tpl),
        "connective_starts": conn_start,
        "empties": empties,
        "dup_sentences": dups,
        "flags": flags,
        "sentence_count": len(sentences),
        "length": len(text),
    }


def analyze_paragraphs(text):
    """定位问题段落：返回每段分析结果与问题段落编号列表。"""
    paras = split_paragraphs(text)
    results = []
    flagged = []
    for i, p in enumerate(paras, 1):
        r = analyze_paragraph(p)
        r["index"] = i
        r["text"] = p
        results.append(r)
        if r["flags"]:
            flagged.append(i)
    return results, flagged


def analyze(text):
    text = text or ""
    sentences = _sentences(text)

    template_hits = []
    for phrase in TEMPLATE_PHRASES:
        pat = re.escape(phrase)
        cnt = len(re.findall(pat, text))
        if cnt:
            template_hits.append({"phrase": phrase.replace("……", "…"), "count": cnt})

    connective_starts = 0
    first_finally = {"首先": 0, "其次": 0, "最后": 0, "再次": 0}
    for s in sentences:
        for c in CONNECTIVES:
            if s.startswith(c):
                connective_starts += 1
                break
        for k in first_finally:
            if s.startswith(k):
                first_finally[k] += 1
    uniformity = round(connective_starts / len(sentences) * 100, 1) if sentences else 0.0

    seen = {}
    repeats = []
    for s in sentences:
        if len(s) < 12:
            continue
        seen[s] = seen.get(s, 0) + 1
    for s, c in seen.items():
        if c > 1:
            repeats.append({"sentence": s, "count": c})

    short_repeats = 0
    for phrase in TEMPLATE_PHRASES:
        positions = [m.start() for m in re.finditer(re.escape(phrase), text)]
        for i in range(len(positions) - 1):
            if positions[i + 1] - positions[i] < 200:
                short_repeats += 1

    empties = []
    for s in sentences:
        if len(s) <= 10 and any(p.replace("……", "") in s for p in
                               ("综上所述", "具有重要意义", "发挥着重要作用", "总之", "因此", "由此可见")):
            empties.append(s)

    template_count = sum(h["count"] for h in template_hits)
    repeat_count = len(repeats) + short_repeats
    first_finally_chain = first_finally["首先"] >= 3 and first_finally["其次"] >= 3

    if template_count >= 10 or uniformity >= 35 or repeat_count >= 8 or first_finally_chain:
        level = "高"
    elif template_count >= 5 or uniformity >= 20 or repeat_count >= 4:
        level = "中"
    else:
        level = "低"

    needs_work = level in ("中", "高") or bool(empties) or bool(repeats)
    para_results, flagged_paragraphs = analyze_paragraphs(text)
    return {
        "template_score": level,
        "template_hits": template_hits,
        "template_count": template_count,
        "uniformity": uniformity,
        "connective_starts": connective_starts,
        "first_finally": first_finally,
        "repeats": repeats,
        "repeat_count": repeat_count,
        "short_repeats": short_repeats,
        "empties": empties,
        "sentence_count": len(sentences),
        "paragraph_count": len(para_results),
        "flagged_paragraphs": flagged_paragraphs,
        "paragraphs": para_results,
        "needs_work": needs_work,
    }


def risk_level(n):
    if n >= 8:
        return "高"
    if n >= 4:
        return "中"
    return "低"


def risk_percent(style):
    """内部分析风险估算（0-100）。不是任何第三方检测平台的结果。"""
    template = style.get("template_count", 0)
    uniformity = style.get("uniformity", 0)
    empties = len(style.get("empties", []))
    repeats = style.get("repeat_count", 0)
    short_repeats = style.get("short_repeats", 0)
    chain = style.get("first_finally", {})
    chain_bad = chain.get("首先", 0) >= 3 and chain.get("其次", 0) >= 3
    ai_risk = round(template * 5 + uniformity * 0.8 + empties * 4 + (12 if chain_bad else 0))
    repeat_risk = round(repeats * 8 + short_repeats * 4)
    return {
        "ai_risk": min(100, ai_risk),
        "repeat_risk": min(100, repeat_risk),
    }


def score(style, structure_stats=None, word_ok=None, refs_count=0):
    """启发式质量评分（仅程序内部辅助参考，非任何机构官方结果）。"""
    structure_stats = structure_stats or {}
    template = style.get("template_count", 0)
    repeats = style.get("repeat_count", 0)
    empties = len(style.get("empties", []))
    uniformity = style.get("uniformity", 0)
    chain = style.get("first_finally", {})
    chain_bad = chain.get("首先", 0) >= 3 and chain.get("其次", 0) >= 3

    sec_count = structure_stats.get("sections", 0)
    if 4 <= sec_count <= 7:
        structure_score = 100
    elif sec_count >= 8:
        structure_score = 92
    elif sec_count >= 2:
        structure_score = 78
    else:
        structure_score = 55
    if structure_stats.get("headings", 0) < sec_count:
        structure_score -= 6
    if not structure_stats.get("has_abstract"):
        structure_score -= 4

    logic_score = 100 - min(30, round(uniformity * 1.2)) - (10 if chain_bad else 0)
    logic_score = max(45, logic_score)

    natural_score = 100 - template * 3 - repeats * 2 - empties * 5
    natural_score = max(40, min(100, natural_score))

    format_score = 100
    if not structure_stats.get("has_abstract"):
        format_score -= 10
    if not structure_stats.get("has_keywords"):
        format_score -= 8
    if refs_count == 0:
        format_score -= 15
    if word_ok is False:
        format_score -= 8
    format_score = max(40, format_score)

    total = round((structure_score + logic_score + natural_score + format_score) / 4)
    return {
        "结构完整度": structure_score,
        "逻辑连贯度": logic_score,
        "表达自然度": natural_score,
        "重复内容风险": risk_level(repeats + template),
        "模板化表达": style.get("template_score", "低"),
        "格式完整度": format_score,
        "综合质量": total,
    }


def structure_stats(full_text, outline_sections=0, meta=None):
    meta = meta or {}
    headings = len(re.findall(r"^#{2,3}\s", full_text or "", re.M))
    return {
        "sections": outline_sections,
        "headings": headings,
        "paragraphs": len(split_paragraphs(full_text)),
        "words": len(re.findall(r"[\u4e00-\u9fff]", full_text or "")),
        "has_abstract": bool(meta.get("abstract")),
        "has_keywords": bool(meta.get("keywords")),
    }


def summarize(style):
    parts = []
    if style.get("template_hits"):
        parts.append(f"模板化表达 {style['template_count']} 处："
                     + "、".join(f"{h['phrase']}×{h['count']}" for h in style["template_hits"][:8]))
    if style.get("repeats"):
        parts.append(f"重复句子 {len(style['repeats'])} 组")
    if style.get("short_repeats"):
        parts.append(f"短距离重复表达 {style['short_repeats']} 处")
    if style.get("empties"):
        parts.append(f"空洞表达 {len(style['empties'])} 处")
    parts.append(f"连接词开头占比 {style.get('uniformity')}%")
    return "；".join(parts)


def ai_content_check(text, store):
    try:
        user_msg = (f"论文全文：\n\n{text[:14000]}\n\n"
                    f"证据表编号：{'、'.join(e['id'] for e in store.all())}")
        resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                              {"role": "user", "content": user_msg + STYLE_AI_JSON_SPEC}],
                             temperature=0.2, json_mode=True, task="check")
        data = deepseek.extract_json(resp) or {}
        issues = data.get("issues") if isinstance(data.get("issues"), list) else []
        log.get().info("AI 写作质量检查完成 问题数=%d", len(issues))
        return issues
    except deepseek.DeepseekError as e:
        log.get().warning("AI 写作质量检查失败（跳过）: %s", e)
        return []

# 版本: v1.5.0 (2026-08-16) 更新: 多模型供应商系统
