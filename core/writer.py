import os
import re

from core import deepseek, log, paths
from core.evidence import SOURCE_TYPE_LABELS, canonical_id, parse_citations
from core.prompts import CHAPTER_REVIEW_JSON_SPEC, WRITER_SYSTEM

TEMPLATE_PHRASES = ["综上所述", "不可否认", "随着.*不断发展", "在新时代背景下", "具有重要意义"]


def chapter_file(index):
    return os.path.join(paths.chapters_dir(), f"{index:02d}.md")


def save_chapter(index, text):
    fname = chapter_file(index)
    with open(fname, "w", encoding="utf-8") as f:
        f.write(text)
    return fname


def read_chapter(index):
    fname = chapter_file(index)
    if os.path.exists(fname):
        with open(fname, encoding="utf-8") as f:
            return f.read()
    return ""


def _evidence_lines(store, ids):
    evs = [store.get(x) for x in ids]
    evs = [e for e in evs if e]
    if not evs:
        return "（本章未分配证据，涉及事实之处必须写“暂无足够可靠资料支持该观点”）"
    out = []
    for e in evs:
        content = (e.get("content") or "").strip()
        if len(content) > 800:
            content = content[:800] + "……"
        out.append(f"[{e['id']}] 标题：{e.get('title') or '（无）'}\n"
                   f"    类型：{SOURCE_TYPE_LABELS.get(e.get('source_type'), e.get('source_type'))}；"
                   f"来源：{e.get('organization') or e.get('journal') or e.get('source') or '未标注'}；"
                   f"时间：{e.get('published_at') or e.get('year') or '未标注'}\n"
                   f"    内容：{content or '（无内容，请打开来源核对）'}")
    return "\n".join(out)


def write_chapter(info, outline, index, store):
    sections = outline.get("sections", [])
    if not (1 <= index <= len(sections)):
        raise deepseek.DeepseekError("章节编号超出范围")
    sec = sections[index - 1]
    ids = list(sec.get("evidence_ids", []))
    for sub in sec.get("subsections", []):
        ids += sub.get("evidence_ids", [])
    ids = list(dict.fromkeys(canonical_id(x) for x in ids))
    if not ids:
        ids = [e["id"] for e in store.all()]
    prev = []
    for s in sections[:index - 1]:
        prev.append(f"- {s.get('title')}：{(s.get('core_points') or '')[:120]}")
    outline_txt = []
    for s in sections:
        evs = "".join(f"[{x}]" for x in s.get("evidence_ids", [])) or "（未分配）"
        outline_txt.append(f"{s.get('title')}（约{s.get('target_words', 0)}字；证据：{evs}）"
                           f"　{(s.get('core_points') or '')[:100]}")
    user_msg = (
        f"【任务】撰写论文第 {index} 章（共 {len(sections)} 章）。"
        f"只输出该章正文（Markdown），不要输出章标题（标题由软件统一排版）；"
        f"不要输出任何解释性文字。\n\n"
        f"论文题目：{info.get('topic')}\n"
        f"专业：{info.get('major') or '未标注'}｜课程：{info.get('course') or '未标注'}\n\n"
        f"论文大纲：\n" + "\n".join(outline_txt) + "\n\n"
        f"本章标题：{sec.get('title')}\n"
        f"本章核心观点：{sec.get('core_points')}\n"
        f"目标字数：约 {sec.get('target_words') or 0} 字（按中文字符计，±15% 均可，不要注水）\n\n"
        f"本章可用的证据（只能引用这些，禁止使用证据表之外的任何事实、数据、文献、政策）：\n"
        f"{_evidence_lines(store, ids)}\n\n"
        f"已写章节核心观点（供衔接）：\n" + ("\n".join(prev) or "（本章为第一章）") + "\n\n"
        "要求：\n"
        "1. 所有事实、数据、政策、文献观点必须来自上述证据表，并紧跟标注 [Ex] 编号；\n"
        "2. 段落结构：观点→证据→分析→推论；包含事实层、解释层、分析层、个人观点层；\n"
        "3. 缺乏证据支持的观点，明确写“暂无足够可靠资料支持该观点”；\n"
        "4. 文风为普通大学生正式课程论文，避免模板套话与连续相同句式；\n"
        "5. 小节标题用 ### （一）…… 格式；6. 段落之间自然衔接。")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg}],
                         temperature=0.7, max_tokens=8000, task="generation")
    text = (resp or "").strip()
    if not text:
        raise deepseek.DeepseekError("AI 未返回内容，请重试。")
    save_chapter(index, text)
    log.get().info("章节写作完成 index=%d 字数=%d", index, cjk_count(text))
    return text


def cjk_count(text):
    return len(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", text or ""))


def check_chapter(text, store, assigned_ids):
    cited = parse_citations(text)
    valid_ids = {e["id"] for e in store.all()}
    unknown = sorted({x for x in cited if x not in valid_ids})
    used = sorted(set(cited))
    assigned = [canonical_id(x) for x in (assigned_ids or [])] or valid_ids
    unused = [x for x in assigned if x not in used]
    phrases = []
    for pat in TEMPLATE_PHRASES:
        if re.search(pat, text or ""):
            phrases.append(pat.replace(".*", "……"))
    no_source = []
    for m in re.finditer(r"研究表明|大量研究证明|相关数据显示|专家普遍认为", text or ""):
        tail = text[m.end():m.end() + 20]
        if not re.search(r"\[E\d+\]", tail):
            no_source.append(m.group(0))
    sentences = [s.strip() for s in re.split(r"[。！？；\n]", text or "") if len(s.strip()) >= 15]
    repeats = sorted({s for s in sentences if sentences.count(s) > 1})
    return {
        "cited": used,
        "unknown": unknown,
        "unused_assigned": unused,
        "template_phrases": phrases,
        "no_source_phrases": no_source,
        "repeats": repeats,
        "words": cjk_count(text),
        "ok": not unknown and not no_source,
    }


def ai_review_chapter(text, store, sec_title):
    user_msg = (f"章节：{sec_title}\n\n章节正文：\n\n{text}\n\n"
                f"证据表编号：{'、'.join(e['id'] for e in store.all())}\n\n"
                "请检查本章是否存在问题。")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg + CHAPTER_REVIEW_JSON_SPEC}],
                         temperature=0.2, json_mode=True, task="check")
    data = deepseek.extract_json(resp) or {}
    issues = data.get("issues") if isinstance(data.get("issues"), list) else []
    return {"ok": bool(data.get("ok", True)), "issues": issues}

# 版本: v1.5.0 (2026-08-16) 更新: 多模型供应商系统
