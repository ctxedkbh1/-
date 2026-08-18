import datetime

from core import detector, quality_gate


def build(project, store, analysis, style, rounds, insufficient, naturalized_count,
          ai_style_issues, structure_stats=None, wordcount=None, scores=None,
          modification_log=None, reverted_count=0, detection=None,
          ai_limit=None, repeat_limit=None, max_rounds=None,
          factcheck_status="not_run", factcheck_issue_count=0,
          requirement_failures=None):
    info = project.info()
    pending = store.pending_count()
    structure_stats = structure_stats or {}
    wordcount = wordcount or {}
    scores = scores or {}
    modification_log = modification_log or []
    ok_citations = not analysis.get("unresolved")
    ok_references = analysis.get("bidirectional_ok", False)
    ok_trace = ok_citations and ok_references
    fact_labels = {
        "passed": "✓ 通过",
        "issues": f"发现问题（{factcheck_issue_count} 处）",
        "skipped": "未完成（AI 调用失败或步骤被跳过）",
        "not_run": "未执行",
    }
    fact_label = fact_labels.get(factcheck_status, "状态未知")

    if style.get("template_score") == "低" and not style.get("repeats") and not style.get("empties"):
        quality = "良好"
    elif style.get("template_score") == "高":
        quality = "较差"
    else:
        quality = "一般"

    if requirement_failures is None:
        target_met = None
        if detection:
            ai_risk = detection.get("ai_risk")
            repeat_risk = detection.get("repeat_risk")
            target_met = ai_risk is not None and repeat_risk is not None and \
                (ai_limit is None or ai_risk <= ai_limit) and \
                (repeat_limit is None or repeat_risk <= repeat_limit)
        requirement_failures = quality_gate.evaluate(
            factcheck_status, ok_citations, ok_references,
            structure_stats=structure_stats, wordcount=wordcount,
            insufficient=insufficient, target_met=target_met, style=style,
            ai_style_issues=ai_style_issues)
    final_status = "可以导出" if not requirement_failures else "自动判定未达标"
    problems = []
    if not ok_citations:
        problems.append("正文引用存在未知编号")
    if analysis.get("unresolved"):
        problems.append(f"引用异常: {analysis['unresolved']}")
    problems.extend(requirement_failures)
    high_issues = [i for i in ai_style_issues if i.get("severity") == "高"]
    if high_issues and not any("高优先级" in item for item in problems):
        problems.append(f"高优先级质量问题 {len(high_issues)} 处")

    lines = ["# 论文质量报告", "", f"生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             f"论文题目：{info.get('topic') or '（未填写）'}", ""]
    lines += ["## 一、质量状态", ""]
    lines.append(f"- 事实核查：{fact_label}")
    lines.append(f"- 引用完整性：{'✓ 通过' if ok_citations else '未通过'}")
    lines.append(f"- 参考文献对应：{'✓ 通过' if ok_references else '未通过'}")
    lines.append(f"- 证据可追溯：{'✓ 通过' if ok_trace else '未通过'}")
    lines.append(f"- 著录信息：{len(pending)} 条待完善")
    lines.append(f"- 写作质量：{quality}")
    lines.append(f"- 模板化表达：{style.get('template_score')}")
    lines.append(f"- 优化轮数：{rounds}")
    lines.append(f"- 已修改章节数：{naturalized_count}（撤销 {reverted_count} 章）")
    if insufficient:
        lines.append("- 资料不足章节：" + "、".join(insufficient))
    lines.append(f"- 最终状态：{final_status}")
    if problems:
        lines += ["", "## 二、自动判定未通过的原因"]
        for p in problems:
            lines.append(f"- {p}")

    if detection:
        ai_risk = detection.get("ai_risk")
        repeat_risk = detection.get("repeat_risk")
        ai_ok = ai_risk is not None and ai_limit is not None and ai_risk <= ai_limit
        rep_ok = repeat_risk is not None and repeat_limit is not None and repeat_risk <= repeat_limit
        target_met = ai_ok and rep_ok
        lines += ["", "## 三、检测目标与结果", ""]
        lines.append(f"- 目标：AI文本风险 ≤ {ai_limit}%　重复/相似内容风险 ≤ {repeat_limit}%　"
                     f"最大优化次数 {max_rounds} 轮")
        lines.append(f"- AI文本风险：{ai_risk}% / 目标 ≤ {ai_limit}% {'✓' if ai_ok else '✗'}")
        lines.append(f"- 重复/相似内容风险：{repeat_risk}% / 目标 ≤ {repeat_limit}% {'✓' if rep_ok else '✗'}")
        lines.append(f"- 检测来源：{detector.source_label(detection)}")
        lines.append(f"- 状态：{'✓ 满足用户设置的输出条件' if target_met else '✗ 未完全达到用户设置的条件'}")
        if not target_met and rounds >= (max_rounds or 0) > 0:
            lines.append("- 自动优化已达到最大次数，未自动宣称通过。")

    lines += ["", "## 四、检测统计", ""]
    lines.append(f"- 总字数：{structure_stats.get('words', '—')} 字"
                 + (f"（要求 {wordcount.get('required', '—')} 字，"
                    f"{'达标' if wordcount.get('ok') else '未达标'}）" if wordcount else ""))
    lines.append(f"- 段落数量：{structure_stats.get('paragraphs', '—')}")
    lines.append(f"- 标题数量：{structure_stats.get('headings', '—')}")
    lines.append(f"- 参考文献数量：{len(analysis.get('refs', []))}")
    lines.append(f"- 重复/相似内容风险：{scores.get('重复内容风险', '—')}")
    lines.append(f"- 模板化表达风险：{scores.get('模板化表达', '—')}")
    lines.append(f"- 修改次数：{rounds} 轮")

    if scores:
        lines += ["", "## 五、质量评分", ""]
        for key in ("结构完整度", "逻辑连贯度", "表达自然度", "格式完整度"):
            lines.append(f"- {key}：{scores.get(key, '—')}")
        lines.append(f"- 重复内容风险：{scores.get('重复内容风险', '—')}")
        lines.append(f"- 模板化表达：{scores.get('模板化表达', '—')}")
        lines.append(f"- 综合质量：{scores.get('综合质量', '—')}/100")
        lines.append("")
        lines.append("> 评分为程序内部启发式评估，仅供参考，不代表任何学校或检测机构的官方结果。")

    if modification_log:
        lines += ["", "## 六、修改记录", ""]
        for entry in modification_log:
            rnd = entry.get("round", "?")
            paras = entry.get("paragraphs_modified", 0)
            chapters = "、".join(f"第{c}章" for c in entry.get("chapters", []))
            before = f"（风险 {entry.get('ai_risk_before')}%/{entry.get('repeat_risk_before')}%）" \
                if entry.get("ai_risk_before") is not None else ""
            lines.append(f"第 {rnd} 轮：修改 {paras} 个段落（{chapters}）{before}")
        if rounds >= (max_rounds or 0) > 0 and style.get("needs_work"):
            lines.append("")
            lines.append("已经完成最大自动优化次数，请检查最终版本。")

    lines += ["", "## 七、写作质量明细", ""]
    from core import style_checker
    lines.append("- " + style_checker.summarize(style))
    if style.get("flagged_paragraphs"):
        lines.append(f"- 问题段落定位：{len(style['flagged_paragraphs'])} 处")
    if style.get("template_hits"):
        lines += ["", "### 模板化表达明细"]
        for h in style["template_hits"][:20]:
            lines.append(f"- {h['phrase']} × {h['count']}")
    if style.get("repeats"):
        lines += ["", "### 重复句子"]
        for r in style["repeats"][:10]:
            lines.append(f"- （{r['count']} 次）{r['sentence'][:60]}")
    if style.get("empties"):
        lines += ["", "### 空洞表达"]
        for s in style["empties"][:10]:
            lines.append(f"- {s}")
    if ai_style_issues:
        lines += ["", "### AI 内容质量检查"]
        for it in ai_style_issues[:15]:
            lines.append(f"- [{it.get('severity', '')}] {it.get('problem', '')}"
                         f"（{it.get('location', '')}）：{it.get('suggestion', '')}")
    return "\n".join(lines)

# 版本: v2.3.0 (2026-08-19) 更新: 自动质量门和事实核查状态报告
