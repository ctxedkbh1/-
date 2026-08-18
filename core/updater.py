import re

import requests


LATEST_RELEASE_API = "https://api.github.com/repos/ctxedkbh1/paper-workbench/releases/latest"
RELEASES_URL = "https://github.com/ctxedkbh1/paper-workbench/releases"
USER_AGENT = "PaperAssistant-UpdateChecker"


class UpdateCheckError(RuntimeError):
    pass


def version_tuple(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value or "").strip())
    if not match:
        raise UpdateCheckError(f"无法识别版本号：{value or '空值'}")
    return tuple(int(part) for part in match.groups())


def check_for_update(current_version, api_url=LATEST_RELEASE_API, timeout=15):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise UpdateCheckError(f"无法连接 GitHub：{exc}") from exc
    if response.status_code != 200:
        detail = ""
        try:
            detail = str(response.json().get("message") or "")
        except (ValueError, AttributeError):
            detail = response.text[:160]
        suffix = f"：{detail}" if detail else ""
        raise UpdateCheckError(f"GitHub 返回 HTTP {response.status_code}{suffix}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpdateCheckError("GitHub 返回的数据不是有效 JSON") from exc
    latest_tag = str(payload.get("tag_name") or "").strip()
    latest = version_tuple(latest_tag)
    current = version_tuple(current_version)
    release_url = str(payload.get("html_url") or RELEASES_URL).strip()
    if not release_url.startswith("https://github.com/ctxedkbh1/paper-workbench/releases"):
        release_url = RELEASES_URL
    assets = []
    for item in payload.get("assets") or []:
        url = str(item.get("browser_download_url") or "")
        if url.startswith("https://github.com/ctxedkbh1/paper-workbench/releases/"):
            assets.append({
                "name": str(item.get("label") or item.get("name") or "下载文件"),
                "url": url,
                "size": int(item.get("size") or 0),
            })
    return {
        "current_version": str(current_version).lstrip("v"),
        "latest_version": latest_tag.lstrip("v"),
        "update_available": latest > current,
        "release_url": release_url,
        "release_name": str(payload.get("name") or latest_tag),
        "published_at": str(payload.get("published_at") or ""),
        "assets": assets,
    }


# Version: v2.3.0 (2026-08-19) Update: GitHub Release update checks
