import re

from core import deepseek, log
from core.annotations import AnnotationStore, parse_annotation_markers
from core.evidence import SOURCE_TYPE_LABELS, canonical_id, parse_citations
from core.prompts import FACTCHECK_JSON_SPEC, WRITER_SYSTEM


def analyze(text, store):
    cited = parse_citations(text)
    annotations = [
        label for label in parse_annotation_markers(text)
        if not re.fullmatch(r"E[-_]?0*\d+", label, re.IGNORECASE)
    ]
    mapping, refs = {}, []
    for cid in cited:
        if cid not in mapping:
            mapping[cid] = len(mapping) + 1
            refs.append(cid)
    valid = {canonical_id(e["id"]) for e in store.all()}
    unresolved = sorted({x for x in cited if x not in valid})
    unused = [canonical_id(e["id"]) for e in store.all()
              if canonical_id(e["id"]) not in refs]
    result = {
        "mapping": mapping,
        "refs": refs,
        "unresolved": unresolved,
        "unused": unused,
        "citation_count": len(cited),
        "annotation_count": len(annotations),
        "annotation_labels": list(dict.fromkeys(annotations)),
        "unresolved_annotations": [],
        "annotation_ok": True,
        "bidirectional_ok": not unresolved and not unused,
    }
    try:
        from core.references.citations import CitationMap
        from core.references.store import ReferenceStore

        reference_store = ReferenceStore()
        if reference_store.all():
            reference_analysis = CitationMap().analyze(text, store, reference_store)
            result.update({
                "reference_ids": list(reference_analysis.reference_ids),
                "unresolved_references": list(reference_analysis.unresolved_references),
                "unused_reference_ids": list(reference_analysis.unused_references),
                "citation_map_ok": reference_analysis.ok,
            })
            result["bidirectional_ok"] = result["bidirectional_ok"] and reference_analysis.ok
    except (OSError, ValueError, KeyError) as exc:
        log.get().warning("Reference Citation Mapping 检查失败: %s", exc)
    try:
        annotation_store = AnnotationStore()
        annotation_store.sync_legacy_evidence(store)
        unresolved_annotations = sorted({x for x in annotations if not annotation_store.get_by_label(x)})
        result.update({
            "annotation_labels": list(dict.fromkeys(annotations)),
            "unresolved_annotations": unresolved_annotations,
            "annotation_ok": not unresolved_annotations,
        })
        result["bidirectional_ok"] = result["bidirectional_ok"] and not unresolved_annotations
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        result["annotation_ok"] = False
        result["bidirectional_ok"] = False
        log.get().warning("Annotation Mapping 检查失败: %s", exc)
    return result


def ai_fact_check(text, store):
    ev_lines = []
    for e in store.all():
        ev_lines.append(f"[{e['id']}] {e.get('title') or ''} | {e.get('content') or ''}")
    user_msg = (f"证据表（唯一可采信的事实来源）:\n" + "\n".join(ev_lines) +
                f"\n\n论文全文（[Ex] 为证据表编号，[n] 为参考文献编号）:\n\n{text}\n\n"
                "请逐项核查：数据是否与证据表一致、日期是否真实、政策名称是否真实、"
                "作者与文献是否真实、引用编号是否与证据表内容相符、是否存在证据表之外的"
                "事实或 AI 自行推断后伪装成事实的内容、是否存在无来源结论。")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg + FACTCHECK_JSON_SPEC}],
                         temperature=0.2, json_mode=True, task="check")
    data = deepseek.extract_json(resp) or {}
    issues = data.get("issues") if isinstance(data.get("issues"), list) else []
    log.get().info("AI 事实核查完成 问题数=%d", len(issues))
    return issues


def build_report(project, store, analysis, ai_issues, chapter_count, total_words, chapter_checks=None):
    info = project.info()
    counts = store.count_by_type()
    pending = store.pending_count()
    lines = [
        "# 资料核验报告", "",
        f"生成时间：{_now()}", "",
        "## 一、论文基本信息",
        f"- 论文题目：{info.get('topic') or '（未填写）'}",
        f"- 姓名：{info.get('name') or '（未填写）'}　学校：{info.get('school') or '（未填写）'}",
        f"- 专业：{info.get('major') or '（未填写）'}　班级：{info.get('class_name') or '（未填写）'}",
        f"- 学号：{info.get('student_id') or '（未填写）'}　课程：{info.get('course') or '（未填写）'}",
        f"- 字数要求：{info.get('word_count')}　截止时间：{info.get('deadline') or '（未填写）'}",
        "", "## 二、资料来源统计",
        f"- 政府：{counts.get('government', 0)} 条",
        f"- CNKI：{counts.get('cnki', 0)} 条",
        f"- OpenAlex：{counts.get('openalex', 0)} 条",
        f"- Crossref：{counts.get('crossref', 0)} 条",
        f"- 网页/手动：{counts.get('web', 0) + counts.get('manual', 0)} 条",
        f"- 证据总数：{len(store.all())} 条",
        f"- 已验证：{store.verified_count()} 条　待完善：{len(pending)} 条",
    ]
    if pending:
        for eid, miss in pending:
            lines.append(f"  - {eid} 著录待完善：缺{'、'.join(miss)}")
    lines += ["", "## 三、引用与参考文献"]
    lines.append(f"- 已完成章节数：{chapter_count}")
    lines.append(f"- 全文字数（约）：{total_words}")
    lines.append(f"- 正文引用数量：{analysis.get('citation_count', 0)}")
    lines.append(f"- 批注数量：{analysis.get('annotation_count', 0)}")
    lines.append(f"- 批注登记检查：{'通过' if analysis.get('annotation_ok', True) else '未通过'}")
    lines.append(f"- 参考文献数量：{len(analysis.get('refs', []))}")
    lines.append(f"- 引用↔参考文献检查：{'通过' if analysis.get('bidirectional_ok') else '未通过'}")
    if analysis.get("unresolved"):
        lines.append(f"  - 【问题】正文引用了证据表中不存在的编号：{analysis['unresolved']}")
    if analysis.get("unused"):
        lines.append(f"  - 【提示】证据表中未在正文使用的证据：{analysis['unused']}")
    if analysis.get("unresolved_references"):
        lines.append(f"  - 【问题】证据缺少真实 Reference ID 映射：{analysis['unresolved_references']}")
    if analysis.get("unresolved_annotations"):
        lines.append(f"  - 【问题】正文出现未登记批注：{analysis['unresolved_annotations']}")
    lines += ["", "## 四、事实核查"]
    lines.append(f"- 事实核查：{'通过' if analysis.get('bidirectional_ok') and not ai_issues else '存在问题'}")
    lines.append("- 存在待核实内容：")
    if ai_issues:
        for it in ai_issues:
            lines.append(f"  - [{it.get('verdict', '待核实')}] {_clip(it.get('claim'))}"
                         f"（{_clip(it.get('reason'))}）")
    else:
        lines.append("  - 无")
    if chapter_checks:
        for idx, ch in chapter_checks.items():
            if ch.get("unknown") or ch.get("no_source_phrases"):
                lines.append(f"  - 第 {idx} 章存在可疑无来源表述："
                             f"未知引用 {ch.get('unknown')}，无来源套话 {ch.get('no_source_phrases')}")
    lines += ["", "## 五、参考文献对照表"]
    for i, eid in enumerate(analysis.get("refs", []), 1):
        e = store.get(eid)
        if e:
            src = e.get("organization") or e.get("journal") or e.get("source") or "来源未标注"
            link = e.get("doi") or e.get("url") or ""
            lines.append(f"- [{i}] ← {eid} ← "
                         f"{SOURCE_TYPE_LABELS.get(e.get('source_type'), e.get('source_type'))} "
                         f"《{_clip(e.get('title'))}》 {src}" +
                         (f"（{link}）" if link else ""))
        else:
            lines.append(f"- [{i}] ← {eid} ← （记录缺失）")
    return "\n".join(lines)


def _clip(s, limit=80):
    s = str(s or "").replace("\n", " ").strip()
    return s[:limit] + ("……" if len(s) > limit else "")


def _now():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 版本: v2.2.0 (2026-08-18) 更新: 批注登记检查
