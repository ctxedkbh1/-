import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_annotation_test_")


def main():
    from core import exporter, fact_checker, naturalizer, writer
    from core.annotations import (AnnotationStore, AnnotationStoreError,
                                  AnnotationStyleStore,
                                  parse_annotation_markers,
                                  remove_annotation_markers,
                                  replace_annotation_markers)
    from core.document import document_from_text
    from core.evidence import EvidenceStore, canonical_id, parse_citations
    from core.project import Project
    from core.targeted_edit import safe_apply

    styles = AnnotationStyleStore()
    assert styles.format_label("note", 1) == "N001"
    assert canonical_id("001") == canonical_id("E-001") == canonical_id("E_001") == "E001"

    evidence = EvidenceStore()
    e1 = evidence.add({
        "title": "示例资料",
        "organization": "测试机构",
        "source_type": "government",
        "url": "https://example.com/source",
        "published_at": "2026-01-01",
        "content": "2026年示例指标为100。",
        "verified": True,
    })

    annotations = AnnotationStore(style_store=styles)
    annotations.sync_legacy_evidence(evidence)
    legacy = annotations.get_by_label("[E-001]")
    assert legacy and legacy["evidence_id"] == e1

    note = annotations.add({
        "style_id": "note",
        "number": annotations.next_number("note"),
        "title": "方法说明",
        "body": "这里说明统计口径。",
        "target_text": "示例指标",
        "status": "active",
    })
    assert note["display_label"] == "N001"

    second = annotations.add({"style_id": "note", "number": 9, "title": "后续处理"})
    assert second["display_label"] == "N009"
    mapping = annotations.renumber("note")
    assert mapping.get("N009") == "N002", mapping
    assert replace_annotation_markers("旧号[N009]，保留[E001]。", mapping) == "旧号[N002]，保留[E001]。"
    assert remove_annotation_markers("删除[N002]，保留[N001]。", ["N002"]) == "删除，保留[N001]。"

    text = "正文引用[E-001]，另有批注[N001]。"
    assert parse_citations(text) == ["E001"]
    assert parse_annotation_markers(text) == ["E-001", "N001"]

    project = Project()
    project.update_info({"topic": "批注测试", "name": "Tester", "school": "Test School"})
    project.set_outline({"title": "批注测试", "sections": [{"title": "正文"}]})
    writer.save_chapter(1, text)

    full_text = exporter.build_full_text(project)
    analysis = fact_checker.analyze(full_text, evidence)
    assert analysis["refs"] == ["E001"], analysis
    assert analysis["annotation_count"] == 1, analysis
    assert analysis["unresolved_annotations"] == [], analysis

    exported = exporter.assemble_markdown(project, evidence, analysis, skip_abstract=True)
    assert "[1]" in exported, exported
    assert "## 批注说明" in exported, exported
    assert "[N001] 方法说明" in exported, exported

    doc = document_from_text(exported, meta={"title": "批注测试"})
    assert doc.annotations and doc.references

    original = "2026年示例指标为100[N001]。"
    assert naturalizer.safe_rewrite(original, "2026年示例指标为100[N001]。")
    assert naturalizer.safe_rewrite(original, "2026年示例指标为100。") is None
    assert safe_apply(original, "2026年示例指标为100[N001]。")
    assert safe_apply(original, "2026年示例指标为100。") is None

    linked = annotations.add({
        "style_id": "note",
        "number": annotations.next_number("note"),
        "title": "关联证据的普通批注",
        "evidence_id": e1,
    })
    e2 = evidence.add({"title": "第二条资料", "source_type": "manual", "content": "第二条内容。"})
    annotations.sync_legacy_evidence(evidence)
    assert len({item["annotation_id"] for item in annotations.all()}) == len(annotations.all())
    assert annotations.get(linked["annotation_id"])["style_id"] == "note"
    assert annotations.get_by_label(e2)["style_id"] == "evidence"

    fresh = AnnotationStore()
    fresh.sync_legacy_evidence(evidence)
    assert fresh.get(linked["annotation_id"])["style_id"] == "note"

    duplicate_path = os.path.join(os.environ["PAPER_PROJECT_DIR"], "duplicate_annotations.json")
    with open(duplicate_path, "w", encoding="utf-8") as f:
        json.dump([{"annotation_id": "ann_001", "style_id": "note", "title": "a"},
                   {"annotation_id": "ann_001", "style_id": "note", "title": "b"}], f)
    duplicate_store = AnnotationStore(path=duplicate_path, style_store=styles)
    duplicate_ids = [item["annotation_id"] for item in duplicate_store.all()]
    assert len(set(duplicate_ids)) == 2, duplicate_ids

    broken_path = os.path.join(os.environ["PAPER_PROJECT_DIR"], "broken_annotations.json")
    with open(broken_path, "w", encoding="utf-8") as f:
        f.write("{broken")
    broken = AnnotationStore(path=broken_path, style_store=styles)
    try:
        broken.add({"style_id": "note", "title": "must not overwrite"})
    except AnnotationStoreError:
        pass
    else:
        raise AssertionError("invalid annotation JSON must not be overwritten")
    assert open(broken_path, encoding="utf-8").read() == "{broken"

    evidence.delete(e1)
    annotations.sync_legacy_evidence(evidence)
    assert not any(item.get("style_id") == "evidence" and item.get("evidence_id") == e1
                   for item in annotations.all())
    assert annotations.get(linked["annotation_id"])["style_id"] == "note"

    print("ANNOTATION TEST OK")


if __name__ == "__main__":
    main()

# 版本: v2.2.0 (2026-08-18) 更新: 批注系统回归测试
