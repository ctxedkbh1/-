import datetime
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "core" / "paths.py"
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".bat", ".ps1"}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[oprsu]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class ReleaseError(RuntimeError):
    pass


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if check and result.returncode:
        raise ReleaseError((result.stdout + result.stderr).strip())
    return result.stdout.strip()


def current_version() -> str:
    match = re.search(r'^VERSION = "(\d+\.\d+\.\d+)"', VERSION_FILE.read_text("utf-8"), re.M)
    if not match:
        raise ReleaseError("core/paths.py 中未找到 VERSION")
    return match.group(1)


def bump_version(version: str, bump: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    match bump:
        case "patch":
            patch += 1
        case "minor":
            minor, patch = minor + 1, 0
        case "major":
            major, minor, patch = major + 1, 0, 0
        case _:
            raise ReleaseError(f"未知版本类型: {bump}")
    return f"{major}.{minor}.{patch}"


def latest_tag() -> str:
    return run("git", "describe", "--tags", "--abbrev=0", check=False)


def suggest_bump() -> str:
    tag = latest_tag()
    range_name = f"{tag}..HEAD" if tag else "HEAD"
    subjects = run("git", "log", range_name, "--pretty=%s").splitlines()
    if not subjects:
        raise ReleaseError("没有可发布的提交")
    if any("BREAKING CHANGE" in subject or re.match(r"\w+(?:\([^)]*\))?!:", subject) for subject in subjects):
        return "major"
    if any(re.match(r"(?:feat|ui)(?:\([^)]*\))?:", subject) for subject in subjects):
        return "minor"
    if all(re.match(r"(?:fix|docs|chore|test|build|ci|style)(?:\([^)]*\))?:", subject) for subject in subjects):
        return "patch"
    raise ReleaseError("提交类型无法可靠判断，请显式指定 patch/minor/major")


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text("utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise ReleaseError(f"版本文本更新失败: {path}")
    path.write_text(updated, "utf-8")


def prepare(bump: str, customer_notes: Path, internal_notes: Path) -> str:
    actual_bump = suggest_bump() if bump == "auto" else bump
    old_version = current_version()
    new_version = bump_version(old_version, actual_bump)
    date = datetime.date.today().isoformat()
    customer = customer_notes.read_text("utf-8").strip()
    internal = internal_notes.read_text("utf-8").strip()
    if not customer or not internal:
        raise ReleaseError("客户与内部更新说明都不能为空")

    paths_text = VERSION_FILE.read_text("utf-8")
    paths_text = re.sub(r'^VERSION = ".*"', f'VERSION = "{new_version}"', paths_text, flags=re.M)
    paths_text = re.sub(r'^RELEASE_DATE = ".*"', f'RELEASE_DATE = "{date}"', paths_text, flags=re.M)
    paths_text = re.sub(
        r'^# 版本: v.*$',
        f"# 版本: v{new_version} ({date}) 更新: 正式版本发布",
        paths_text,
        flags=re.M,
    )
    VERSION_FILE.write_text(paths_text, "utf-8")

    replace_once(ROOT / "README.md", r"\| 当前版本 \| v[^（]+（[^）]+） \|", f"| 当前版本 | v{new_version}（{date}） |")
    replace_once(ROOT / "README.md", r"- 当前版本：\*\*v[^*]+\*\*（[^）]+）", f"- 当前版本：**v{new_version}**（{date}）")
    for path in (
        ROOT / "docs" / "ai" / "CODEX_CONTEXT.md",
        ROOT / "docs" / "ai" / "CURRENT_STATUS.md",
        ROOT / "docs" / "ai" / "AI_HANDOFF.md",
    ):
        replace_once(path, r"^v\d+\.\d+\.\d+（[^\n]+）", f"v{new_version}（{date}）")

    changelog = ROOT / "CHANGELOG.md"
    text = changelog.read_text("utf-8")
    marker = re.search(r"^## \[v", text, re.M)
    if not marker:
        raise ReleaseError("CHANGELOG.md 缺少版本章节")
    text = text[:marker.start()] + f"## [v{new_version}] - {date}\n\n{customer}\n\n" + text[marker.start():]
    changelog.write_text(text, "utf-8")

    internal_log = ROOT / "docs" / "ai" / "CHANGELOG.md"
    text = internal_log.read_text("utf-8")
    marker = re.search(r"^## \d{4}-", text, re.M)
    if not marker:
        raise ReleaseError("docs/ai/CHANGELOG.md 缺少日期章节")
    text = text[:marker.start()] + f"## {date}\n{internal}\n\n" + text[marker.start():]
    internal_log.write_text(text, "utf-8")
    (ROOT / "RELEASE_NOTES.md").write_text(customer + "\n", "utf-8")
    print(f"PREPARED v{old_version} -> v{new_version} ({actual_bump})")
    return new_version


def scan_secrets() -> None:
    files = run("git", "ls-files", "-co", "--exclude-standard").splitlines()
    forbidden = []
    for name in files:
        normalized = name.replace("\\", "/")
        lower = normalized.lower()
        if "/paper_project/" in f"/{lower}/" or lower.endswith((".pem", ".key")) or Path(name).name.startswith(".env"):
            forbidden.append(name)
            continue
        path = ROOT / name
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        text = path.read_text("utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            forbidden.append(name)
    if forbidden:
        raise ReleaseError("发现疑似敏感文件/凭据: " + ", ".join(sorted(set(forbidden))))


def verify() -> None:
    scan_secrets()
    commands = [
        (sys.executable, "tests/dev_ai_center_test.py"),
        (sys.executable, "tests/dev_reference_center_test.py"),
        (sys.executable, "tests/dev_integrations_test.py"),
        (sys.executable, "tests/dev_sett_test.py"),
        (sys.executable, "main.py", "--selfcheck"),
        (sys.executable, "main.py", "--ui-check"),
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    print("RELEASE VERIFY OK")


def publish(confirm: str) -> None:
    if confirm != "--confirm":
        raise ReleaseError("发布必须显式传入 --confirm")
    if run("git", "branch", "--show-current") != "main":
        raise ReleaseError("正式发布只能在 main 分支执行")
    verify()
    version = current_version()
    tag = f"v{version}"
    if run("git", "tag", "-l", tag):
        raise ReleaseError(f"Tag 已存在: {tag}")
    run("git", "add", "-A")
    run("git", "commit", "-m", f"release: {tag}")
    run("git", "tag", "-a", tag, "-m", f"论文助手 {tag}")
    run("git", "push", "origin", "main")
    run("git", "push", "origin", tag)
    print(f"PUBLISHED {tag}; GitHub Actions will build EXE + ZIP")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise ReleaseError("用法: release.py suggest | prepare <auto|patch|minor|major> <customer.md> <internal.md> | verify | publish --confirm")
    match args[0]:
        case "suggest":
            print(suggest_bump())
        case "prepare" if len(args) == 4:
            prepare(args[1], Path(args[2]), Path(args[3]))
        case "verify":
            verify()
        case "publish" if len(args) == 2:
            publish(args[1])
        case _:
            raise ReleaseError("参数不完整或不支持")


if __name__ == "__main__":
    try:
        main()
    except ReleaseError as exc:
        print(f"RELEASE BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

# 版本: v2.0.1 (2026-08-17) 更新: 受控语义版本与 GitHub 发布流程
