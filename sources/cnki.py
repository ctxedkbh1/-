import re

from core import log


def _rec(base):
    rec = dict(base)
    rec["source_type"] = "cnki"
    return rec


def parse_ris(text):
    records = []
    cur = None
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if len(line) >= 6 and line[2:6] in ("  - ", " - "):
            tag, val = line[:2].upper(), line[6:].strip()
        else:
            continue
        if tag == "TY":
            cur = {"_ris": {}}
            records.append(cur)
        elif cur is None:
            continue
        elif tag == "ER":
            cur = None
        else:
            cur["_ris"].setdefault(tag, []).append(val)
    out = []
    for c in records:
        r = c.get("_ris", {})
        sp = r.get("SP", [""])[0]
        ep = r.get("EP", [""])[0]
        pages = f"{sp}-{ep}" if sp and ep else (sp or ep or "")
        vp = ""
        if r.get("VL"):
            vp = r["VL"][0]
            if r.get("IS"):
                vp += f"({r['IS'][0]})"
        if pages:
            vp += (": " if vp else "") + pages
        out.append(_rec({
            "title": "; ".join(r.get("TI", [])) or "",
            "authors": "; ".join(r.get("AU", [])) or "",
            "journal": "; ".join(r.get("JO", []) or r.get("JF", []) or r.get("T2", [])) or "",
            "year": (r.get("PY", [""])[0] or "")[:4],
            "volume_issue_pages": vp,
            "doi": "; ".join(r.get("DO", [])) or "",
            "url": "; ".join(r.get("UR", []) or r.get("SN", [])) or "",
            "abstract": "; ".join(r.get("AB", [])) or "",
            "keywords": "; ".join(r.get("KW", [])) or "",
            "published_at": (r.get("Y1", [""])[0] or ""),
        }))
    log.get().info("RIS 解析完成 条数=%d", len(out))
    return out


def parse_bibtex(text):
    out = []
    for m in re.finditer(r"@\w+\s*\{[^,]*,\s*", text or ""):
        start = m.end()
        depth = 0
        end = None
        for i in range(m.start(), len(text)):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            continue
        body = text[start:end]
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*[{\"]([^}\"]*)[}\"]", body):
            fields[fm.group(1).lower()] = fm.group(2).strip()
        def clean(v):
            return v.replace("{", "").replace("}", "").strip()
        authors = clean(fields.get("author", ""))
        authors = re.sub(r"\s+and\s+", "; ", authors)
        out.append(_rec({
            "title": clean(fields.get("title", "")),
            "authors": authors,
            "journal": clean(fields.get("journal", "") or fields.get("booktitle", "")),
            "year": clean(fields.get("year", ""))[:4],
            "volume_issue_pages": clean(fields.get("volume", "")) +
                                  (f"({clean(fields.get('number', ''))})" if fields.get("number") else "") +
                                  (": " + clean(fields["pages"]) if fields.get("pages") else ""),
            "doi": clean(fields.get("doi", "")),
            "url": clean(fields.get("url", "")),
            "abstract": clean(fields.get("abstract", "")),
            "keywords": clean(fields.get("keywords", "")),
        }))
    log.get().info("BibTeX 解析完成 条数=%d", len(out))
    return out


def parse_text(text):
    t = (text or "").strip()
    if not t:
        return []
    if t.startswith("TY  -"):
        return parse_ris(t)
    if "@" in t and re.search(r"@\w+\s*\{", t):
        return parse_bibtex(t)
    return []

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
