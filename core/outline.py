from core import deepseek, log
from core.evidence import canonical_id
from core.prompts import OUTLINE_JSON_SPEC, WRITER_SYSTEM

USER_OUTLINE_JSON_SPEC = '''
只输出 JSON 对象，不要输出任何其他文字，格式：
{"title": "论文标题", "sections": [
  {"title": "一、章节标题", "core_points": "本章核心观点（50-150字）",
   "target_words": 400, "subsections": [{"title": "（一）小节标题", "core_points": "要点"}]}
]}
要求：
1. 保持用户大纲原有的章节结构、标题与顺序，不要新增用户没写的实质性内容；
2. 章节标题统一为"一、二、三、……"格式，小节为"（一）（二）……"格式；
3. target_words 按用户要求的总字数合理分配（引言约 10%，结论约 8%）。'''

ASSIGN_JSON_SPEC = '''
只输出 JSON 对象，不要输出任何其他文字，格式：
{"assignments": [{"index": 1, "evidence_ids": ["E001", "E002"]}]}
index 从 1 开始对应章节顺序，evidence_ids 只能使用证据表中真实存在的编号，
只给与该章内容相关的章节分配证据，无关的章节填空数组。'''


def structure_user_outline(info, user_text):
    """把用户粘贴的大纲文本结构化（保持原结构，不新增实质内容）。"""
    user_msg = (f"论文题目：{info.get('topic')}\n"
                f"总字数要求：{info.get('word_count') or 3000} 字\n\n"
                f"用户提供的论文大纲：\n\n{user_text[:6000]}")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg + USER_OUTLINE_JSON_SPEC}],
                         temperature=0.3, json_mode=True, task="analysis")
    data = deepseek.extract_json(resp)
    if not data or not isinstance(data.get("sections"), list) or not data["sections"]:
        raise deepseek.DeepseekError("大纲结构化失败，请检查大纲文本后重试。")
    sections = []
    for i, s in enumerate(data["sections"], 1):
        sections.append({
            "id": i,
            "title": str(s.get("title") or f"第{i}节"),
            "core_points": str(s.get("core_points") or ""),
            "target_words": int(s.get("target_words") or 0),
            "evidence_ids": [],
            "subsections": [{
                "title": str(sub.get("title") or ""),
                "core_points": str(sub.get("core_points") or ""),
                "evidence_ids": [],
            } for sub in (s.get("subsections") or [])],
        })
    log.get().info("用户大纲结构化成功 章节数=%d", len(sections))
    return {"title": data.get("title") or info.get("topic"), "keywords": [],
            "abstract_plan": "", "sections": sections}


def assign_evidence(outline, store):
    """为大纲各章节分配证据编号（只允许使用证据表中真实存在的编号）。"""
    if not store.all():
        return outline
    sec_titles = "\n".join(f"{i}. {s.get('title')}　{s.get('core_points')[:80]}"
                           for i, s in enumerate(outline.get("sections", []), 1))
    ev_lines = "\n".join(f"{e['id']} | {(e.get('title') or '（无标题）')[:50]} | "
                         f"{(e.get('content') or '')[:60]}"
                         for e in store.all())
    user_msg = (f"大纲章节：\n{sec_titles}\n\n证据表（编号 | 标题 | 内容摘要）：\n{ev_lines}")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg + ASSIGN_JSON_SPEC}],
                         temperature=0.2, json_mode=True, task="analysis")
    data = deepseek.extract_json(resp) or {}
    assignments = data.get("assignments") if isinstance(data.get("assignments"), list) else []
    valid = {e["id"] for e in store.all()}
    for a in assignments:
        idx = int(a.get("index", 0))
        ids = [canonical_id(x) for x in a.get("evidence_ids", []) if canonical_id(x) in valid]
        if 1 <= idx <= len(outline.get("sections", [])):
            outline["sections"][idx - 1]["evidence_ids"] = ids
    log.get().info("证据分配完成 有效分配=%d", len(assignments))
    return outline


def _evidence_summary(store):
    lines = []
    for e in store.all():
        title = (e.get("title") or e.get("content") or "").strip()
        if len(title) > 60:
            title = title[:60] + "……"
        src = e.get("organization") or e.get("journal") or e.get("source") or "未标注"
        lines.append(f"{e['id']} | {e.get('source_type')} | {title} | {src} | {e.get('year') or e.get('published_at') or ''}")
    return "\n".join(lines) or "（证据表为空）"


def generate_outline(info, store):
    total = info.get("word_count") or 3000
    user_msg = (
        f"论文题目：{info.get('topic')}\n"
        f"专业：{info.get('major') or '未标注'}　课程：{info.get('course') or '未标注'}\n"
        f"总字数要求：{total} 字\n\n"
        f"证据表（正文只能引用这些证据，每行格式：编号 | 类型 | 标题 | 来源 | 年份）:\n"
        f"{_evidence_summary(store)}\n\n"
        "请根据论文题目与证据表设计论文大纲。证据不足的部分不要安排事实性论述。")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg + OUTLINE_JSON_SPEC}],
                         temperature=0.4, json_mode=True, task="analysis")
    data = deepseek.extract_json(resp)
    if not data or not isinstance(data.get("sections"), list) or not data["sections"]:
        raise deepseek.DeepseekError("AI 返回格式异常，请重试。")
    valid_ids = {canonical_id(e["id"]) for e in store.all()}
    sections = []
    for i, s in enumerate(data["sections"], 1):
        sec = {
            "id": i,
            "title": str(s.get("title") or f"第{i}节"),
            "core_points": str(s.get("core_points") or ""),
            "target_words": int(s.get("target_words") or 0),
            "evidence_ids": [canonical_id(x) for x in s.get("evidence_ids", [])
                             if canonical_id(x) in valid_ids],
        }
        subs = []
        for j, sub in enumerate(s.get("subsections", []) or [], 1):
            subs.append({
                "title": str(sub.get("title") or f"（{j}）"),
                "core_points": str(sub.get("core_points") or ""),
                "evidence_ids": [canonical_id(x) for x in sub.get("evidence_ids", [])
                                 if canonical_id(x) in valid_ids],
            })
        sec["subsections"] = subs
        sections.append(sec)
    outline = {
        "title": data.get("title") or info.get("topic"),
        "keywords": data.get("keywords") or [],
        "abstract_plan": data.get("abstract_plan") or "",
        "sections": sections,
    }
    log.get().info("大纲生成成功 章节数=%d", len(sections))
    return outline


def outline_markdown(outline, store):
    lines = ["# 论文大纲", "", f"论文标题：{outline.get('title', '')}", ""]
    if outline.get("keywords"):
        lines += ["关键词：" + "、".join(outline["keywords"]), ""]
    for sec in outline.get("sections", []):
        evs = "".join(f"[{x}]" for x in sec.get("evidence_ids", [])) or "（未分配证据）"
        lines.append(f"## {sec.get('title')}（约 {sec.get('target_words', 0)} 字）")
        lines.append(f"核心观点：{sec.get('core_points', '')}")
        lines.append(f"证据：{evs}")
        for sub in sec.get("subsections", []):
            sevs = "".join(f"[{x}]" for x in sub.get("evidence_ids", [])) or "（未分配证据）"
            lines.append(f"- {sub.get('title')}：{sub.get('core_points', '')} 证据：{sevs}")
        lines.append("")
    lines.append("## 证据编号对照")
    for e in store.all():
        lines.append(f"- {e['id']}：{(e.get('title') or '（无标题）')[:60]}")
    return "\n".join(lines)

# 版本: v1.5.0 (2026-08-16) 更新: 多模型供应商系统
