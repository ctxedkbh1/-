import time

import requests

from core import log

BASE = "https://api.openalex.org/works"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class SourceError(Exception):
    pass


def _abstract(ai):
    if not ai:
        return ""
    pos = {}
    for word, idxs in ai.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))[:800]


def _to_record(w):
    src = (w.get("primary_location") or {}).get("source") or {}
    authors = "; ".join(a.get("author", {}).get("display_name", "")
                        for a in w.get("authorships", [])[:10])
    biblio = w.get("biblio") or {}
    vol = biblio.get("volume") or ""
    iss = biblio.get("issue") or ""
    vp = f"{vol}({iss})" if iss else str(vol)
    pages = ""
    if biblio.get("first_page") or biblio.get("last_page"):
        pages = f"{biblio.get('first_page', '')}-{biblio.get('last_page', '')}"
    if vp and pages:
        vp += ": " + pages
    doi = (w.get("doi") or "").replace("https://doi.org/", "")
    return {
        "title": w.get("display_name") or "",
        "authors": authors,
        "journal": src.get("display_name") or "",
        "year": str(w.get("publication_year") or ""),
        "volume_issue_pages": vp,
        "doi": doi,
        "url": w.get("doi") or w.get("id") or "",
        "openalex_id": w.get("id") or "",
        "abstract": _abstract(w.get("abstract_inverted_index") or {}),
        "cited_by_count": w.get("cited_by_count", 0),
        "source_type": "openalex",
    }


def search(query, per_page=10):
    params = {"search": query, "per-page": per_page}
    lg = log.get()
    for attempt in range(3):
        try:
            r = requests.get(BASE, params=params, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            results = r.json().get("results", [])
            lg.info("OpenAlex 检索成功 query=%s 结果=%d", query, len(results))
            return [_to_record(w) for w in results]
        except requests.RequestException as e:
            lg.warning("OpenAlex 请求失败(第%d次): %s", attempt + 1, e)
            if attempt == 2:
                raise SourceError(f"OpenAlex 检索失败: {e}")
            time.sleep(2)
    raise SourceError("OpenAlex 检索失败")

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
