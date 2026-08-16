import time
import urllib.parse

import requests

from core import log

BASE = "https://api.crossref.org/works"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class SourceError(Exception):
    pass


def _to_record(it):
    year = ""
    try:
        year = it.get("published", {}).get("date-parts", [[None]])[0][0]
    except Exception:
        pass
    authors = "; ".join(f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in it.get("author", [])[:10])
    title = (it.get("title") or [""])[0]
    journal = (it.get("container-title") or [""])[0]
    doi = it.get("DOI", "")
    vp = ""
    if it.get("volume"):
        vp = str(it["volume"])
        if it.get("issue"):
            vp += f"({it['issue']})"
    if it.get("page"):
        vp += (": " if vp else "") + str(it["page"])
    return {
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": str(year or ""),
        "volume_issue_pages": vp,
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else "",
        "publisher": it.get("publisher") or "",
        "abstract": (it.get("abstract") or "")[:800],
        "source_type": "crossref",
    }


def search(query, rows=10):
    params = {"query": query, "rows": rows}
    lg = log.get()
    for attempt in range(3):
        try:
            r = requests.get(BASE, params=params, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            items = r.json().get("message", {}).get("items", [])
            lg.info("Crossref 检索成功 query=%s 结果=%d", query, len(items))
            return [_to_record(it) for it in items]
        except requests.RequestException as e:
            lg.warning("Crossref 请求失败(第%d次): %s", attempt + 1, e)
            if attempt == 2:
                raise SourceError(f"Crossref 检索失败: {e}")
            time.sleep(2)
    raise SourceError("Crossref 检索失败")


def lookup_doi(doi):
    doi = (doi or "").strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
    if not doi:
        raise SourceError("请输入 DOI")
    url = f"{BASE}/{urllib.parse.quote(doi)}"
    lg = log.get()
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 404:
                raise SourceError(f"DOI 未在 Crossref 中找到: {doi}")
            r.raise_for_status()
            rec = _to_record(r.json().get("message", {}))
            lg.info("Crossref DOI 验证成功 doi=%s", doi)
            return rec
        except requests.RequestException as e:
            lg.warning("Crossref DOI 验证失败(第%d次): %s", attempt + 1, e)
            if attempt == 2:
                raise SourceError(f"Crossref DOI 验证失败: {e}")
            time.sleep(2)
    raise SourceError("Crossref DOI 验证失败")

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
