import html as html_lib
import re
import time
import urllib.parse

import requests

from core import log

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

DDG = "https://html.duckduckgo.com/html/"


class SourceError(Exception):
    pass


def search_links(query, max_results=8):
    """尽力而为的网页搜索：返回结果链接列表。可能被网络环境限制，调用方需容错。"""
    lg = log.get()
    for attempt in range(2):
        try:
            r = requests.post(DDG, data={"q": query}, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            links = []
            for href in re.findall(r'class="result__a"[^>]*href="([^"]+)"', r.text):
                href = html_lib.unescape(href)
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    u = urllib.parse.unquote(m.group(1))
                    if re.match(r"^https?://", u) and u not in links:
                        links.append(u)
            lg.info("网页搜索成功 query=%s 结果=%d", query, len(links))
            return links[:max_results]
        except requests.RequestException as e:
            lg.warning("网页搜索失败(第%d次): %s", attempt + 1, e)
            time.sleep(2)
    raise SourceError(f"网页搜索不可用: {query}")


def search_government_links(query, max_results=6):
    """搜索政府官方域名（.gov.cn / .edu.cn）链接，尽力而为。"""
    links = search_links(f"site:gov.cn {query}", max_results * 2)
    gov = [u for u in links if urllib.parse.urlparse(u).netloc.lower().endswith(".gov.cn")]
    return gov[:max_results]

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
