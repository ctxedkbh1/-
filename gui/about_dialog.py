from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QHBoxLayout,
                               QLabel, QPushButton, QVBoxLayout)

from core import paths


class AboutDialog(QDialog):
    def __init__(self, parent=None, auto_check=False):
        super().__init__(parent)
        self.setWindowTitle("关于论文助手")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        title = QLabel(paths.APP_NAME)
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        version = QLabel(f"版本 v{paths.VERSION} · 更新日期 {paths.RELEASE_DATE}")
        version.setObjectName("muted")
        layout.addWidget(version)
        description = QLabel(
            "面向论文研究、证据管理、写作核查和多格式导出的 Windows 桌面工具。\n\n"
            "核心能力：普通/全自动/高级模式、多 Provider AI、联网检索、证据库、"
            "参考文献映射、事实核查、DOCX/PDF/PPTX 等导出。\n\n许可证：MIT"
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        self.update_status = QLabel("尚未检查更新")
        self.update_status.setWordWrap(True)
        self.update_status.setObjectName("muted")
        layout.addWidget(self.update_status)
        update_row = QHBoxLayout()
        self.check_button = QPushButton("检查更新")
        self.check_button.clicked.connect(self.start_check)
        self.release_button = QPushButton("打开 GitHub 下载页")
        self.release_button.setEnabled(False)
        self.release_button.clicked.connect(self._open_release)
        update_row.addWidget(self.check_button)
        update_row.addWidget(self.release_button)
        update_row.addStretch(1)
        layout.addLayout(update_row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._release_url = ""
        self._worker = None
        if auto_check:
            self.start_check()

    def start_check(self):
        if self._worker and self._worker.isRunning():
            return
        from gui.update_check import UpdateCheckThread
        owner = self.parent() or QApplication.instance()
        self._worker = UpdateCheckThread(owner)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self.check_button.setEnabled(False)
        self.release_button.setEnabled(False)
        self.update_status.setText("正在连接 GitHub 检查最新版本…")
        self._worker.start()

    def _on_result(self, result):
        self.check_button.setEnabled(True)
        self._release_url = result.get("release_url", "")
        self.release_button.setEnabled(bool(self._release_url))
        if result.get("update_available"):
            self.update_status.setText(
                f"发现新版本 v{result['latest_version']}，当前为 v{result['current_version']}。"
                "请打开下载页查看发布说明并选择安装包。")
        else:
            self.update_status.setText(
                f"已是最新版本 v{result['current_version']}（GitHub 最新："
                f"v{result['latest_version']}）。")

    def _on_error(self, message):
        self.check_button.setEnabled(True)
        self.release_button.setEnabled(False)
        self.update_status.setText(f"检查失败：{message}")

    def _open_release(self):
        if self._release_url:
            QDesktopServices.openUrl(QUrl(self._release_url))

# 版本: v2.3.0 (2026-08-19) 更新: 异步 GitHub Release 更新检查
