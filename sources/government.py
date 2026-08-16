import datetime
import html as html_lib
import re
import time
import urllib.parse

import requests

from core import log

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

GOV_SUFFIXES = (".gov.cn", ".edu.cn")

DATE_PATTERNS = [
    r"(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?",
    r"(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*月",
]


class SourceError(Exception):
    pass


def is_official_domain(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host.endswith(s) for s in GOV_SUFFIXES)


def _normalize_date(m):
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if 1 <= mo <= 12 and 1 <= d <= 31:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def _extract_date(page):
    metas = re.findall(
        r'<(?:meta|span|div)[^>]*(?:article:published_time|datePublished|publishTime|pubdate)'
        r'[^>]*?(?:content|datetime)?\s*=\s*["\']?([^"\'>\s]+)',
        page, re.I)
    for val in metas:
        m = re.match(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", val)
        if m:
            d = _normalize_date(m)
            if d:
                return d
    for pat in DATE_PATTERNS:
        m = re.search(pat, page[:8000])
        if m:
            d = _normalize_date(m)
            if d:
                return d
    return ""


def _extract_org(page, url):
    m = re.search(r'<meta[^>]*(?:article:author|author|og:site_name)[^>]*content=["\']([^"\']+)["\']',
                  page, re.I)
    if m:
        return html_lib.unescape(m.group(1)).strip()
    host = urllib.parse.urlparse(url).netloc.lower()
    return host


def fetch(url, timeout=30):
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise SourceError("请输入以 http:// 或 https:// 开头的完整网址")
    lg = log.get()
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            r.raise_for_status()
            if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
                r.encoding = r.apparent_encoding or "utf-8"
            page = r.text
            break
        except requests.RequestException as e:
            lg.warning("网页抓取失败(第%d次) %s: %s", attempt + 1, url, e)
            if attempt == 2:
                raise SourceError(f"网页抓取失败: {e}")
            time.sleep(2)
    m_title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    title = html_lib.unescape(re.sub(r"<[^>]+>", "", m_title.group(1))).strip() if m_title else ""
    paras = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", page, re.S | re.I):
        seg = html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
        seg = re.sub(r"\s+", " ", seg).strip()
        if len(seg) >= 15:
            paras.append(seg)
    content = "\n".join(paras)[:6000]
    record = {
        "title": title,
        "organization": _extract_org(page, url),
        "published_at": _extract_date(page),
        "url": url,
        "content": content,
        "retrieved_at": datetime.date.today().isoformat(),
        "source_type": "government" if is_official_domain(url) else "web",
    }
    lg.info("网页抓取成功 %s title=%s official=%s", url, title[:50], record["source_type"] == "government")
    return record

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
