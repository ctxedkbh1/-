from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QVBoxLayout)

from core import paths


class AboutDialog(QDialog):
    def __init__(self, parent=None):
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
            "参考文献映射、事实核查、DOCX/PDF/PPTX 等导出。\n\n"
            "GitHub：https://github.com/ctxedkbh1/paper-workbench\n"
            "许可证：MIT"
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

# 版本: v2.0.1 (2026-08-17) 更新: About 页面
