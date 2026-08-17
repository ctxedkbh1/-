from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QLineEdit, QPushButton,
                               QVBoxLayout)

from gui.widgets import msg_warn


class ZoteroConnectionDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.record = None
        self.api_key = ""
        self.disconnect_requested = False
        self.setWindowTitle("连接 Zotero")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItem("Zotero 桌面 Local API（推荐）", "local")
        self.mode.addItem("Zotero Web API", "web")
        self.base_url = QLineEdit()
        self.user_id = QLineEdit()
        self.user_id.setPlaceholderText("Web API 必填；Local API 使用 0")
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Web API Key，保存到 Windows Credential Manager")
        form.addRow("连接方式", self.mode)
        form.addRow("Base URL", self.base_url)
        form.addRow("User ID", self.user_id)
        form.addRow("API Key", self.key)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.disconnect = QPushButton("断开连接")
        self.disconnect.setObjectName("danger")
        buttons.addButton(self.disconnect, QDialogButtonBox.ButtonRole.DestructiveRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        self.disconnect.clicked.connect(self._disconnect)
        layout.addWidget(buttons)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self._load(record or {})

    def _load(self, record):
        mode = str(record.get("mode") or "local")
        self.mode.setCurrentIndex(max(0, self.mode.findData(mode)))
        self.base_url.setText(str(record.get("base_url") or ""))
        self.user_id.setText(str(record.get("user_id") or ("0" if mode == "local" else "")))
        self._mode_changed()

    def _mode_changed(self):
        local = self.mode.currentData() == "local"
        if local and not self.base_url.text().strip():
            self.base_url.setText("http://localhost:23119/api")
        self.user_id.setEnabled(not local)
        self.key.setEnabled(not local)

    def _save(self):
        mode = str(self.mode.currentData())
        user_id = "0" if mode == "local" else self.user_id.text().strip()
        if mode == "web" and not user_id:
            msg_warn(self, "Zotero Web API 需要 User ID。")
            return
        self.record = {
            "mode": mode,
            "base_url": self.base_url.text().strip().rstrip("/"),
            "user_id": user_id,
            "credential_ref": "zotero:web",
            "local_version": 0,
            "web_version": 0,
            "partition_id": "",
        }
        self.api_key = self.key.text().strip()
        self.accept()

    def _disconnect(self):
        self.disconnect_requested = True
        self.accept()


class NotebookConnectionDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.record = None
        self.access_token = ""
        self.disconnect_requested = False
        self.setWindowTitle("Gemini Notebook Enterprise")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.project = QLineEdit()
        self.location = QLineEdit("global")
        self.notebook = QLineEdit()
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("Google Cloud Access Token，保存到系统凭据")
        form.addRow("Project Number", self.project)
        form.addRow("Location", self.location)
        form.addRow("Notebook ID", self.notebook)
        form.addRow("Access Token", self.token)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        disconnect = QPushButton("断开连接")
        disconnect.setObjectName("danger")
        buttons.addButton(disconnect, QDialogButtonBox.ButtonRole.DestructiveRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        disconnect.clicked.connect(self._disconnect)
        layout.addWidget(buttons)
        values = record or {}
        self.project.setText(str(values.get("project_number") or ""))
        self.location.setText(str(values.get("location") or "global"))
        self.notebook.setText(str(values.get("notebook_id") or ""))

    def _save(self):
        if not self.project.text().strip() or not self.notebook.text().strip():
            msg_warn(self, "Project Number 与 Notebook ID 不能为空。")
            return
        self.record = {
            "project_number": self.project.text().strip(),
            "location": self.location.text().strip() or "global",
            "notebook_id": self.notebook.text().strip(),
            "credential_ref": "notebook:enterprise",
        }
        self.access_token = self.token.text().strip()
        self.accept()

    def _disconnect(self):
        self.disconnect_requested = True
        self.accept()

# 版本: v2.0.1 (2026-08-17) 更新: Zotero 与 Notebook Enterprise 连接配置
