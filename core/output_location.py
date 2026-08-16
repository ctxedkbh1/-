import os

from PySide6.QtCore import QStandardPaths

from core import paths

SPECIAL_CHOICES = ["default", "desktop", "documents", "downloads", "custom"]

CHOICE_LABELS = {
    "default": "默认位置",
    "desktop": "桌面",
    "documents": "文档",
    "downloads": "下载",
    "custom": "自定义文件夹",
}


def resolve_output_dir(choice="default", custom_path=""):
    """解析输出目录。桌面/文档/下载使用系统 API 动态获取，
    兼容 OneDrive 重定向、中文/英文系统与自定义桌面位置。"""
    if choice == "desktop":
        p = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        if p:
            return p
    elif choice == "documents":
        p = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if p:
            return p
    elif choice == "downloads":
        p = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        if p:
            return p
    elif choice == "custom":
        p = (custom_path or "").strip()
        if p:
            return p
    return paths.output_dir()


def preview_path(choice="default", custom_path=""):
    return resolve_output_dir(choice, custom_path)


def ensure_dir(directory):
    """自动创建目录，返回 (ok, error_message)。"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True, ""
    except OSError as e:
        return False, f"无法创建文件夹：{e}"


def is_writable(directory):
    """写权限探测（不修改系统权限，只检测）。"""
    try:
        if not os.path.isdir(directory):
            return False, "文件夹不存在"
        probe = os.path.join(directory, ".write_probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True, ""
    except OSError as e:
        if hasattr(e, "winerror"):
            if e.winerror in (5, 32, 33):
                return False, "当前文件夹没有写入权限或文件被占用。请选择其他文件夹。"
            if e.winerror in (112, 39):
                return False, "磁盘空间不足或路径过长。请选择其他文件夹。"
        return False, f"当前文件夹无法写入：{e}"


def unique_path(path):
    """同名文件自动重命名：论文 (1).docx、论文 (2).docx……"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 1
    while True:
        candidate = f"{base} ({n}){ext}"
        if not os.path.exists(candidate):
            return candidate
        n += 1

# 版本: v1.8.0 (2026-08-16) 更新: 自定义输出文件夹
