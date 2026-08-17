import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_reference_center_")


def main():
    from core.evidence import EvidenceStore
    from core.references.citations import CitationMap
    from core.references.domain import CitationStyle, ReferenceSource
    from core.references.importers import import_csl_json, import_text
    from core.references.store import ReferenceStore
    from core.references.styles import format_reference

    store = ReferenceStore()
    first = store.upsert({
        "title": "A Real Research Article",
        "authors": "Alice Zhang; Bob Li",
        "year": "2024",
        "journal": "Journal of Evidence",
        "doi": "https://doi.org/10.1234/REAL.001",
        "source": ReferenceSource.MANUAL.value,
    })
    duplicate = store.upsert({
        "title": "A Real Research Article",
        "authors": "Alice Zhang; Bob Li",
        "year": "2024",
        "doi": "10.1234/real.001",
        "source": ReferenceSource.CROSSREF.value,
    })
    assert first.reference_id == duplicate.reference_id == "ref_001"
    assert len(store.all()) == 1

    ris = "TY  - JOUR\nTI  - Second Verified Work\nAU  - Chen, Ming\nPY  - 2023\nDO  - 10.5555/SECOND\nER  - "
    imported = import_text(ris, source=ReferenceSource.RIS)
    assert len(imported) == 1
    second = store.upsert(imported[0].to_dict())
    assert second.reference_id == "ref_002"

    csl = json.dumps([{
        "id": "zotero-key-1",
        "type": "article-journal",
        "title": "CSL Imported Work",
        "author": [{"family": "Wang", "given": "Li"}],
        "issued": {"date-parts": [[2022]]},
        "DOI": "10.9999/csl.1",
        "container-title": "CSL Journal",
    }])
    csl_records = import_csl_json(csl)
    third = store.upsert(csl_records[0].to_dict())
    assert third.reference_id == "ref_003"
    assert store.search("Wang")[0].reference_id == "ref_003"

    evidence = EvidenceStore()
    evidence_id = evidence.add({
        "title": first.title,
        "authors": first.authors,
        "journal": first.journal,
        "year": first.year,
        "doi": first.doi,
        "content": "Verified evidence content.",
        "source_type": "manual",
        "reference_id": first.reference_id,
        "verified": True,
    })
    citation_map = CitationMap()
    citation_map.link(evidence_id, first.reference_id)
    result = citation_map.analyze(f"正文引用[{evidence_id}]，另有未知[E999]。", evidence, store)
    assert result.mapping == {evidence_id: 1}
    assert result.reference_ids == (first.reference_id,)
    assert result.unresolved_evidence == ("E999",)
    assert result.unresolved_references == ()

    from core import exporter, fact_checker, writer
    from core.project import Project

    project = Project()
    project.update_info({"topic": "Reference Test", "name": "Tester", "school": "Test School"})
    project.set_outline({"title": "Reference Test", "sections": [{"title": "正文"}]})
    writer.save_chapter(1, f"真实引用[{evidence_id}]。")
    legacy_analysis = fact_checker.analyze(exporter.build_full_text(project), evidence)
    assert legacy_analysis["reference_ids"] == [first.reference_id]
    exported = exporter.assemble_markdown(project, evidence, legacy_analysis, skip_abstract=True)
    assert "[1]" in exported
    assert "10.1234/real.001" in exported.lower()

    formatted = format_reference(first, CitationStyle.GB_T_7714)
    assert "A Real Research Article" in formatted
    assert "10.1234/real.001" in formatted.lower()
    assert format_reference(first, CitationStyle.APA)
    assert format_reference(first, CitationStyle.IEEE).startswith("[1]") is False

    export_path = os.path.join(os.environ["PAPER_PROJECT_DIR"], "references.json")
    assert os.path.exists(export_path)
    print("REFERENCE CENTER TEST OK")


if __name__ == "__main__":
    main()

# 版本: v2.0.1 (2026-08-17) 更新: 参考文献中心回归测试
