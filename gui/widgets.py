import html
import re

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QMessageBox,
                               QSpinBox, QTextBrowser, QWidget)

RISK_PRESETS = [5, 10, 20, 30, 40, 50, 60]


class ThresholdPicker(QWidget):
    """风险阈值选择：预设 5%~60% + 自定义 0~100。"""

    def __init__(self, default=20, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.combo = QComboBox()
        for v in RISK_PRESETS:
            self.combo.addItem(f"{v}%", v)
        self.combo.addItem("自定义…", "custom")
        self.spin = QSpinBox()
        self.spin.setRange(0, 100)
        self.spin.setSuffix(" %")
        self.spin.setVisible(False)
        lay.addWidget(self.combo)
        lay.addWidget(self.spin)
        lay.addStretch(1)
        self.combo.currentIndexChanged.connect(self._on_change)
        self.set_value(default)

    def _on_change(self):
        self.spin.setVisible(self.combo.currentData() == "custom")

    def value(self):
        data = self.combo.currentData()
        if data == "custom":
            return self.spin.value()
        return int(data)

    def set_value(self, v):
        try:
            v = int(v)
        except (TypeError, ValueError):
            v = 20
        v = max(0, min(100, v))
        idx = self.combo.findData(v)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
            self.spin.setVisible(False)
        else:
            self.combo.setCurrentIndex(self.combo.findData("custom"))
            self.spin.setValue(v)
            self.spin.setVisible(True)


class Worker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.done.emit(self._fn(*self._args, **self._kwargs))
        except Exception as e:
            from core import log
            log.get().exception("后台任务失败: %s", e)
            self.failed.emit(str(e))


def msg_info(parent, text, title="提示"):
    QMessageBox.information(parent, title, text)


def msg_warn(parent, text, title="警告"):
    QMessageBox.warning(parent, title, text)


def msg_err(parent, text, title="出错了", retry=False):
    if retry:
        box = QMessageBox(parent)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(text)
        retry_btn = box.addButton("重试", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("跳过", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is retry_btn
    QMessageBox.critical(parent, title, text)
    return False


def ask_confirm(parent, text, title="确认"):
    return QMessageBox.question(parent, title, text) == QMessageBox.StandardButton.Yes


def linkify(text):
    return re.sub(r"\[E(\d+)\]", r'<a href="eid://E\1">[E\1]</a>', html.escape(text or ""))


def md_to_html(text):
    out = []
    for line in (text or "").splitlines():
        line = linkify(line)
        s = line.strip()
        if s.startswith("### "):
            out.append(f"<h3>{s[4:]}</h3>")
        elif s.startswith("## "):
            out.append(f"<h2>{s[3:]}</h2>")
        elif s.startswith("# "):
            out.append(f"<h1>{s[2:]}</h1>")
        elif s.startswith("- "):
            out.append(f"<li>{s[2:]}</li>")
        elif not s:
            out.append("<br>")
        else:
            out.append(f"<p>{s}</p>")
    return "".join(out)


def to_rich_text(text):
    body = linkify(text).replace("\n", "<br>")
    return f"<div style='white-space:normal;'>{body}</div>"


def open_url(url):
    if not url:
        return
    QDesktopServices.openUrl(QUrl(url))


class LinkBrowser(QTextBrowser):
    link_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self._on_anchor)

    def _on_anchor(self, url):
        if url.scheme() == "eid":
            self.link_clicked.emit(url.path().lstrip("/"))
        elif url.scheme() in ("http", "https"):
            open_url(url.toString())

    def show_markdown(self, text):
        self.setHtml(md_to_html(text))

    def show_rich(self, text):
        self.setHtml(to_rich_text(text))

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
