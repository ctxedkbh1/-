import os
import sys

APP_NAME = "论文智能研究与写作助手"
VERSION = "2.3.0"
RELEASE_DATE = "2026-08-19"

_DATA_DIR = None


def frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> str:
    if frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _writable_directory(directory):
    os.makedirs(directory, exist_ok=True)
    probe = os.path.join(directory, ".write_test")
    with open(probe, "w", encoding="utf-8") as f:
        f.write("ok")
    os.remove(probe)
    return directory


def _desktop_dirs():
    candidates = [os.path.join(os.path.expanduser("~"), "Desktop")]
    one_drive = os.environ.get("OneDrive", "").strip()
    if one_drive:
        candidates.append(os.path.join(one_drive, "Desktop"))
    if os.name == "nt":
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "Desktop")
            candidates.append(os.path.expandvars(value))
        except (OSError, ImportError):
            pass
    unique = []
    for item in candidates:
        normalized = os.path.normcase(os.path.abspath(item))
        if normalized not in {os.path.normcase(os.path.abspath(path)) for path in unique}:
            unique.append(item)
    return unique


def _legacy_data_dirs(target):
    candidates = [
        os.path.join(app_dir(), "paper_project"),
        os.path.join(os.path.expanduser("~"), "paper_project"),
    ]
    for desktop in _desktop_dirs():
        candidates.extend([
            os.path.join(desktop, "paper_project"),
            os.path.join(desktop, "论文智能研究与写作助手_完整版", "paper_project"),
        ])
        try:
            for name in os.listdir(desktop):
                package = os.path.join(desktop, name)
                if os.path.isdir(package) and name.startswith("论文智能研究与写作助手"):
                    candidates.append(os.path.join(package, "paper_project"))
        except OSError:
            pass
    target_norm = os.path.normcase(os.path.realpath(target))
    unique = []
    seen = set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.realpath(candidate))
        if normalized != target_norm and normalized not in seen:
            seen.add(normalized)
            unique.append(candidate)
    return unique


def _stable_data_dir():
    root = os.environ.get("LOCALAPPDATA", "").strip() or \
        os.environ.get("APPDATA", "").strip()
    if not root:
        root = os.path.join(os.path.expanduser("~"), "AppData", "Local") \
            if os.name == "nt" else os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(root, "PaperAssistant", "paper_project")


def default_data_dir() -> str:
    global _DATA_DIR
    env = os.environ.get("PAPER_PROJECT_DIR", "").strip()
    if env:
        return _writable_directory(env)
    if _DATA_DIR:
        return _DATA_DIR
    target = _stable_data_dir()
    try:
        _DATA_DIR = _writable_directory(target)
    except OSError:
        fallback = os.path.join(os.path.expanduser("~"), "PaperAssistant", "paper_project")
        _DATA_DIR = _writable_directory(fallback)
    from core.data_migration import merge_legacy_data
    merge_legacy_data(_DATA_DIR, _legacy_data_dirs(_DATA_DIR))
    return _DATA_DIR


def subdir(name: str) -> str:
    d = os.path.join(default_data_dir(), name)
    os.makedirs(d, exist_ok=True)
    return d


def data_dir() -> str:
    return default_data_dir()


def output_dir() -> str:
    return subdir("output")


def chapters_dir() -> str:
    return subdir("chapters")


def logs_dir() -> str:
    return subdir("logs")


def cache_dir() -> str:
    return subdir("cache")


def config_file() -> str:
    return os.path.join(default_data_dir(), "config.json")


def project_file() -> str:
    return os.path.join(default_data_dir(), "project.json")


def evidence_file() -> str:
    return os.path.join(default_data_dir(), "evidence.json")


def annotations_file() -> str:
    return os.path.join(default_data_dir(), "annotations.json")


def annotation_styles_file() -> str:
    return os.path.join(default_data_dir(), "annotation_styles.json")


def outline_md() -> str:
    return os.path.join(default_data_dir(), "outline.md")


def research_plan_md() -> str:
    return os.path.join(default_data_dir(), "research_plan.md")


def ensure_all_dirs():
    default_data_dir()
    subdir("output")
    subdir("chapters")
    subdir("logs")
    subdir("cache")

# 版本: v2.3.0 (2026-08-19) 更新: 统一用户数据目录与无损兼容迁移
