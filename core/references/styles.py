from core.references.domain import CitationStyle, ReferenceRecord


def format_reference(record: ReferenceRecord, style: CitationStyle) -> str:
    match style:
        case CitationStyle.GB_T_7714:
            return _gbt(record)
        case CitationStyle.APA:
            return _apa(record)
        case CitationStyle.MLA:
            return _mla(record)
        case CitationStyle.CHICAGO:
            return _chicago(record)
        case CitationStyle.IEEE:
            return _ieee(record)
        case CitationStyle.VANCOUVER:
            return _vancouver(record)


def _gbt(record: ReferenceRecord) -> str:
    lead = _lead(record)
    source = _source(record)
    text = f"{lead}. {record.title}[J]. {source}"
    return _identifier(text, record)


def _apa(record: ReferenceRecord) -> str:
    text = f"{record.authors or 'Unknown author'} ({record.year or 'n.d.'}). {record.title}. {_source(record)}"
    return _identifier(text, record)


def _mla(record: ReferenceRecord) -> str:
    text = f"{record.authors or 'Unknown author'}. \"{record.title}.\" {_source(record)}"
    return _identifier(text, record)


def _chicago(record: ReferenceRecord) -> str:
    text = f"{record.authors or 'Unknown author'}. \"{record.title}.\" {_source(record)}"
    return _identifier(text, record)


def _ieee(record: ReferenceRecord) -> str:
    text = f"{_lead(record)}, \"{record.title},\" {_source(record)}"
    return _identifier(text, record)


def _vancouver(record: ReferenceRecord) -> str:
    text = f"{_lead(record)}. {record.title}. {_source(record)}"
    return _identifier(text, record)


def _lead(record: ReferenceRecord) -> str:
    return record.authors or "作者不详"


def _source(record: ReferenceRecord) -> str:
    parts = [record.journal, record.year, record.volume_issue_pages]
    value = ", ".join(part for part in parts if part)
    return value or "来源待完善"


def _identifier(text: str, record: ReferenceRecord) -> str:
    value = text.rstrip(". ") + "."
    if record.doi:
        return value + f" DOI: {record.doi}."
    if record.url:
        return value + f" {record.url}."
    return value + "（著录信息待完善）"

# 版本: v2.0.1 (2026-08-17) 更新: 多引用样式格式化入口
