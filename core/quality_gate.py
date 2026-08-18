def evaluate(factcheck_status, citations_ok, references_ok, structure_stats=None,
             wordcount=None, insufficient=None, target_met=None, style=None,
             ai_style_issues=None):
    """Return deterministic reasons why the generated result is not eligible."""
    failures = []
    if factcheck_status != "passed":
        labels = {
            "issues": "事实核查发现问题",
            "skipped": "事实核查未完成",
            "not_run": "事实核查未执行",
        }
        failures.append(labels.get(factcheck_status, "事实核查状态未知"))
    if not citations_ok:
        failures.append("正文引用完整性未通过")
    if not references_ok:
        failures.append("参考文献对应关系未通过")
    if structure_stats:
        sections = int(structure_stats.get("sections") or 0)
        if sections and int(structure_stats.get("headings") or 0) < sections:
            failures.append("论文结构检查未通过")
        if sections and int(structure_stats.get("paragraphs") or 0) < sections:
            failures.append("部分章节缺少段落内容")
        if not structure_stats.get("has_abstract"):
            failures.append("摘要未生成")
    if wordcount and wordcount.get("ok") is False:
        failures.append("正文未达到字数要求")
    if insufficient:
        failures.append("存在资料不足章节")
    if target_met is False:
        failures.append("AI 文本或重复风险未达到设定阈值")
    high_issues = [item for item in (ai_style_issues or [])
                   if item.get("severity") == "高"]
    if high_issues:
        failures.append(f"存在 {len(high_issues)} 处高优先级写作质量问题")
    if style and style.get("template_score") == "高":
        failures.append("模板化表达风险过高")
    return list(dict.fromkeys(failures))


# Version: v2.3.0 (2026-08-19) Update: deterministic automatic quality gate
