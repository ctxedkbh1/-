import datetime
import email.utils
import os
import threading
import time

import requests

from core import log
from core import paths

BASE = "https://api.openalex.org/works"
UA = f"PaperAssistant/{paths.VERSION} (OpenAlex client)"
MAX_ATTEMPTS = 4
MIN_REQUEST_INTERVAL = 0.5
_RATE_LOCK = threading.Lock()
_NEXT_REQUEST_AT = 0.0


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
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    if mailto:
        params["mailto"] = mailto
    lg = log.get()
    for attempt in range(MAX_ATTEMPTS):
        try:
            _wait_for_request_slot()
            r = requests.get(BASE, params=params, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 429:
                wait = _retry_after_seconds(r, attempt)
                lg.warning(
                    "OpenAlex 请求被限流(429)，第%d/%d次重试前等待 %.1f 秒",
                    attempt + 1, MAX_ATTEMPTS, wait,
                )
                if attempt == MAX_ATTEMPTS - 1:
                    raise SourceError(
                        "OpenAlex 暂时限制了请求频率（HTTP 429）。请稍后再试；"
                        "如需提高稳定性，可设置 OPENALEX_MAILTO 环境变量。"
                    )
                time.sleep(wait)
                continue
            r.raise_for_status()
            results = r.json().get("results", [])
            lg.info("OpenAlex 检索成功 query=%s 结果=%d", query, len(results))
            return [_to_record(w) for w in results]
        except SourceError:
            raise
        except requests.RequestException as e:
            lg.warning("OpenAlex 请求失败(第%d次): %s", attempt + 1, e)
            if attempt == MAX_ATTEMPTS - 1:
                raise SourceError(f"OpenAlex 检索失败: {e}")
            time.sleep(min(2 ** attempt, 8))
    raise SourceError("OpenAlex 检索失败")


def _wait_for_request_slot():
    global _NEXT_REQUEST_AT
    with _RATE_LOCK:
        wait = max(0.0, _NEXT_REQUEST_AT - time.monotonic())
        _NEXT_REQUEST_AT = max(_NEXT_REQUEST_AT, time.monotonic()) + MIN_REQUEST_INTERVAL
    if wait:
        time.sleep(wait)


def _retry_after_seconds(response, attempt):
    value = response.headers.get("Retry-After", "")
    try:
        return min(30.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        pass
    if value:
        try:
            retry_at = email.utils.parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=datetime.timezone.utc)
            return min(30.0, max(0.0, (retry_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            pass
    return float(min(30, 2 ** (attempt + 1)))

# 版本: v2.1.2 (2026-08-18) 更新: OpenAlex 429 限流恢复与礼貌访问
