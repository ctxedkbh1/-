import datetime
import logging
import os

from core import paths

_ROOT_NAME = "paper"


def setup_logging():
    root = logging.getLogger(_ROOT_NAME)
    if root.handlers:
        return root
    root.setLevel(logging.INFO)
    root.propagate = False
    fh = logging.FileHandler(os.path.join(paths.logs_dir(),
                                          datetime.date.today().strftime("%Y-%m-%d") + ".log"),
                             encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(fh)
    try:
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root.addHandler(ch)
    except Exception:
        pass
    return root


def get(name=None):
    return logging.getLogger(_ROOT_NAME if name is None else f"{_ROOT_NAME}.{name}")

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
