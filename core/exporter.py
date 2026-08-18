import datetime
import os
import re

from core import deepseek, log, paths
from core.annotations import AnnotationStore
from core.evidence import CITE_RE, canonical_id
from core.prompts import ABSTRACT_JSON_SPEC, WRITER_SYSTEM


def _load_chapters():
    outline_dir = paths.chapters_dir()
    chapters = []
    names = sorted(f for f in os.listdir(outline_dir) if re.fullmatch(r"\d+\.md", f))
    for name in names:
        with open(os.path.join(outline_dir, name), encoding="utf-8") as f:
            chapters.append((int(name.split(".")[0]), f.read().strip()))
    return chapters


def build_full_text(project):
    outline = project.outline() or {}
    sections = outline.get("sections") or []
    parts = []
    for idx, text in _load_chapters():
        title = ""
        if 1 <= idx <= len(sections):
            title = sections[idx - 1].get("title", "")
        if not text:
            continue
        parts.append(f"## {title}\n\n{text}" if title else text)
    return "\n\n".join(parts)


def _replace_citations(text, mapping):
    def sub(m):
        cid = canonical_id(f"E{m.group(1)}")
        return f"[{mapping[cid]}]" if cid in mapping else m.group(0)
    return CITE_RE.sub(sub, text or "")


def _annotation_appendix(text, store):
    try:
        annotations = AnnotationStore()
        annotations.sync_legacy_evidence(store)
        records = annotations.used_records(text, include_evidence=False)
    except Exception as exc:
        log.get().warning("批注附录生成失败: %s", exc)
        return []
    if not records:
        return []
    lines = ["", "## 批注说明", ""]
    for item in records:
        label = item.get("display_label") or item.get("annotation_id")
        title = item.get("title") or item.get("body") or "（无标题）"
        body = item.get("body") or item.get("summary") or ""
        line = f"- [{label}] {title}"
        if body and body != title:
            line += f"：{body}"
        lines.append(line)
    return lines


def _generate_abstract(project, full_text):
    user_msg = (f"论文题目：{project.info().get('topic')}\n\n论文全文：\n\n{full_text[:12000]}")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg + ABSTRACT_JSON_SPEC}],
                         temperature=0.4, json_mode=True, task="summary")
    data = deepseek.extract_json(resp) or {}
    if not data.get("abstract"):
        raise deepseek.DeepseekError("摘要生成失败")
    return {"abstract": data["abstract"], "keywords": data.get("keywords") or []}


def assemble_markdown(project, store, analysis, skip_abstract=False):
    outline = project.outline() or {}
    full_text = build_full_text(project)
    meta = project.get("final_meta") or {}
    if not meta.get("abstract") and not skip_abstract:
        try:
            meta = _generate_abstract(project, full_text)
            project.set("final_meta", meta)
        except deepseek.DeepseekError as e:
            log.get().warning("摘要生成失败: %s", e)
    title = outline.get("title") or project.info().get("topic") or "论文"
    lines = [f"# {title}", ""]
    if meta.get("abstract"):
        lines += [f"**摘要**：{meta['abstract']}", ""]
    if meta.get("keywords"):
        lines += ["**关键词**：" + "；".join(meta["keywords"]), ""]
    lines += [_replace_citations(full_text, analysis.get("mapping", {})), ""]
    lines += _annotation_appendix(full_text, store)
    lines += ["", "## 参考文献", ""]
    reference_store = None
    citation_map = None
    try:
        from core.references.citations import CitationMap
        from core.references.store import ReferenceStore

        reference_store = ReferenceStore()
        citation_map = CitationMap()
    except (OSError, ValueError) as exc:
        log.get().warning("ReferenceStore 加载失败，使用旧证据格式: %s", exc)
    for i, eid in enumerate(analysis.get("refs", []), 1):
        e = store.get(eid)
        rendered = ""
        if e and reference_store and citation_map:
            reference_id = citation_map.reference_for(eid, store)
            reference = reference_store.get(reference_id) if reference_id else None
            if reference:
                from core.references.domain import CitationStyle
                from core.references.styles import format_reference

                style_name = str(project.get("citation_style") or CitationStyle.GB_T_7714.value)
                try:
                    style = CitationStyle(style_name)
                except ValueError:
                    style = CitationStyle.GB_T_7714
                rendered = format_reference(reference, style)
        lines.append(f"[{i}] {rendered or (store.to_reference(e) if e else '（记录缺失，请检查）')}")
    return "\n".join(lines)


def build_document(project, store, analysis, final_text=None, skip_abstract=False):
    """把最终论文文本解析为统一 Document 模型（供所有格式导出）。"""
    from core.document import document_from_text
    if final_text is None:
        final_text = assemble_markdown(project, store, analysis, skip_abstract=skip_abstract)
    info = project.info()
    meta = {
        "title": (project.outline() or {}).get("title") or info.get("topic") or "论文",
        "name": info.get("name") or "",
        "school": info.get("school") or "",
        "major": info.get("major") or "",
        "class_name": info.get("class_name") or "",
        "course": info.get("course") or "",
        "word_count": info.get("word_count") or 3000,
        "format_note": info.get("format_note") or "",
    }
    return document_from_text(final_text, meta=meta, format_note=meta["format_note"])


def export_files(project, store, analysis, ai_issues, chapter_count, total_words,
                 chapter_checks=None, skip_abstract=False, out_dir=None):
    out_dir = out_dir or paths.output_dir()
    os.makedirs(out_dir, exist_ok=True)
    final_text = assemble_markdown(project, store, analysis, skip_abstract=skip_abstract)
    md_path = os.path.join(out_dir, "论文.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_text)
    docx_path = os.path.join(out_dir, "论文.docx")
    from core.exporters import export as export_format
    doc = build_document(project, store, analysis, final_text=final_text)
    export_format(doc, "docx", docx_path)
    from core import fact_checker
    report_path = os.path.join(out_dir, "资料核验报告.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(fact_checker.build_report(project, store, analysis, ai_issues,
                                          chapter_count, total_words, chapter_checks))
    project.set("exported", datetime.datetime.now().isoformat())
    project.set("exported_paths", {"md": md_path, "docx": docx_path, "report": report_path})
    log.get().info("导出完成 md=%s docx=%s report=%s", md_path, docx_path, report_path)
    return {"md": md_path, "docx": docx_path, "report": report_path}

# 版本: v2.2.0 (2026-08-18) 更新: 批注附录导出
