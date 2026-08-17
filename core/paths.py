import os
import sys

APP_NAME = "论文智能研究与写作助手"
VERSION = "2.1.2"
RELEASE_DATE = "2026-08-18"


def frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> str:
    if frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_data_dir() -> str:
    env = os.environ.get("PAPER_PROJECT_DIR", "").strip()
    if env:
        os.makedirs(env, exist_ok=True)
        return env
    d = os.path.join(app_dir(), "paper_project")
    try:
        os.makedirs(d, exist_ok=True)
        probe = os.path.join(d, ".write_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return d
    except Exception:
        fallback = os.path.join(os.path.expanduser("~"), "paper_project")
        os.makedirs(fallback, exist_ok=True)
        return fallback


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

# 版本: v2.1.2 (2026-08-18) 更新: 正式版本发布
