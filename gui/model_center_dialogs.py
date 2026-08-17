from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QSpinBox,
                               QTextBrowser, QVBoxLayout)

from core.ai.domain import AIProvider, AdapterType, DiscoveryMode
from core.model_presets import LEGACY_PRESETS
from gui.widgets import msg_warn


class ProviderEditDialog(QDialog):
    def __init__(self, parent=None, provider: AIProvider | None = None,
                 key_present: bool = False):
        super().__init__(parent)
        self.provider = provider
        self.record = None
        self.api_key = ""
        self.clear_key = False
        self.key_present = key_present
        self.setWindowTitle("编辑 Provider" if provider else "添加 AI Provider")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.provider_id = QLineEdit()
        self.display_name = QLineEdit()
        self.adapter = QComboBox()
        for adapter, label in (
            (AdapterType.OPENAI, "OpenAI"),
            (AdapterType.OPENAI_COMPATIBLE, "OpenAI Compatible"),
            (AdapterType.ANTHROPIC, "Anthropic"),
            (AdapterType.GEMINI, "Google Gemini"),
            (AdapterType.OLLAMA, "Ollama"),
        ):
            self.adapter.addItem(label, adapter.value)
        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("https://api.example.com/v1")
        self.discovery_mode = QComboBox()
        self.discovery_mode.addItem("标准 /models", DiscoveryMode.STANDARD.value)
        self.discovery_mode.addItem("官方专用接口", DiscoveryMode.OFFICIAL.value)
        self.discovery_mode.addItem("仅手动模型", DiscoveryMode.MANUAL.value)
        self.discovery_url = QLineEdit()
        self.discovery_url.setPlaceholderText("可选：完整模型列表 URL")
        self.env_key = QLineEdit()
        self.env_key.setPlaceholderText("可选，例如 OPENAI_API_KEY")
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("留空不修改；保存到 Windows Credential Manager")
        self.key_status = QLabel("已保存" if key_present else "未保存")
        self.clear_key_checkbox = QCheckBox("清除已保存的 API Key")
        self.clear_key_checkbox.setEnabled(key_present)
        self.enabled = QCheckBox("启用 Provider")
        self.enabled.setChecked(True)
        form.addRow("Provider ID", self.provider_id)
        form.addRow("显示名称", self.display_name)
        form.addRow("Adapter", self.adapter)
        form.addRow("Base URL", self.base_url)
        form.addRow("模型发现", self.discovery_mode)
        form.addRow("模型列表 URL", self.discovery_url)
        form.addRow("环境变量", self.env_key)
        form.addRow("API Key", self.key)
        form.addRow("凭据状态", self.key_status)
        form.addRow("", self.clear_key_checkbox)
        form.addRow("", self.enabled)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if provider:
            self._load(provider)

    def _load(self, provider: AIProvider) -> None:
        self.provider_id.setText(provider.provider_id)
        self.provider_id.setEnabled(False)
        self.display_name.setText(provider.display_name)
        self.adapter.setCurrentIndex(max(0, self.adapter.findData(provider.adapter_type.value)))
        self.base_url.setText(provider.base_url)
        self.discovery_mode.setCurrentIndex(
            max(0, self.discovery_mode.findData(provider.discovery_mode.value))
        )
        self.discovery_url.setText(provider.discovery_url)
        self.env_key.setText(provider.env_key)
        self.enabled.setChecked(provider.enabled)

    def _save(self) -> None:
        provider_id = self.provider_id.text().strip().lower().replace(" ", "-")
        display_name = self.display_name.text().strip()
        if not provider_id or not display_name or not self.base_url.text().strip():
            msg_warn(self, "Provider ID、显示名称和 Base URL 不能为空。")
            return
        self.record = {
            "name": display_name,
            "display_name": display_name,
            "adapter_type": self.adapter.currentData(),
            "base_url": self.base_url.text().strip().rstrip("/"),
            "env_key": self.env_key.text().strip(),
            "enabled": self.enabled.isChecked(),
            "discovery_mode": self.discovery_mode.currentData(),
            "discovery_url": self.discovery_url.text().strip(),
            "credential_ref": f"provider:{provider_id}",
            "status": "not_checked",
            "last_checked": "",
            "last_error": "",
        }
        self.provider_key = provider_id
        self.api_key = self.key.text().strip()
        self.clear_key = self.clear_key_checkbox.isChecked()
        self.accept()


class ManualModelDialog(QDialog):
    def __init__(self, providers: list[AIProvider], parent=None):
        super().__init__(parent)
        self.record = None
        self.setWindowTitle("添加自定义模型")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.provider = QComboBox()
        for item in providers:
            self.provider.addItem(item.display_name, item.provider_id)
        self.display_name = QLineEdit()
        self.model_id = QLineEdit()
        self.context_window = QSpinBox()
        self.context_window.setRange(0, 10_000_000)
        self.context_window.setSpecialValueText("未知")
        self.reasoning = QCheckBox("Reasoning")
        self.vision = QCheckBox("Vision")
        self.tools = QCheckBox("Tools")
        self.streaming = QCheckBox("Streaming")
        self.notes = QLineEdit()
        self.enabled = QCheckBox("启用模型")
        self.enabled.setChecked(True)
        form.addRow("Provider", self.provider)
        form.addRow("显示名称", self.display_name)
        form.addRow("Model ID", self.model_id)
        form.addRow("", self.enabled)
        form.addRow("Context Window", self.context_window)
        form.addRow("", self.reasoning)
        form.addRow("", self.vision)
        form.addRow("", self.tools)
        form.addRow("", self.streaming)
        form.addRow("备注", self.notes)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        model_id = self.model_id.text().strip()
        provider_id = str(self.provider.currentData() or "")
        if not provider_id or not model_id:
            msg_warn(self, "Provider 和 Model ID 不能为空。")
            return
        self.reference = f"{provider_id}::{model_id}"
        self.record = {
            "provider_id": provider_id,
            "model_id": model_id,
            "display_name": self.display_name.text().strip() or model_id,
            "enabled": self.enabled.isChecked(),
            "status": "not_checked",
            "source": "manual",
            "capabilities": {
                "context_window": self.context_window.value() or None,
                "max_output_tokens": None,
                "supports_reasoning": self.reasoning.isChecked(),
                "supports_vision": self.vision.isChecked(),
                "supports_tools": self.tools.isChecked(),
                "supports_streaming": self.streaming.isChecked(),
                "supports_text": True,
                "supports_image": None,
                "input_modalities": ["text", "image"] if self.vision.isChecked() else ["text"],
                "output_modalities": ["text"],
                "supported_parameters": [],
            },
            "notes": self.notes.text().strip(),
        }
        self.accept()


class PresetLibraryDialog(QDialog):
    """A local view of built-in presets; hiding a preset never changes source code."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.selected_preset = ""
        self.setWindowTitle("预设模型库")
        self.setMinimumSize(680, 460)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("预设只提供初始配置，不会自动覆盖你的模型。导入同名模型时必须再次确认。"))
        body = QHBoxLayout()
        self.preset_list = QListWidget()
        self.preset_list.currentItemChanged.connect(self._show_preset)
        body.addWidget(self.preset_list, 1)
        self.details = QTextBrowser()
        body.addWidget(self.details, 1)
        layout.addLayout(body, 1)
        actions = QHBoxLayout()
        self.import_button = QPushButton("导入预设")
        self.hide_button = QPushButton("从本地库移除")
        self.restore_button = QPushButton("恢复内置预设")
        close_button = QPushButton("关闭")
        self.import_button.clicked.connect(self._import)
        self.hide_button.clicked.connect(self._hide)
        self.restore_button.clicked.connect(self._restore)
        close_button.clicked.connect(self.reject)
        actions.addWidget(self.import_button)
        actions.addWidget(self.hide_button)
        actions.addWidget(self.restore_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        layout.addLayout(actions)
        self._load()

    def _load(self):
        hidden = set(self.config.ai_center().get("hidden_presets", []))
        self.preset_list.clear()
        for key, preset in LEGACY_PRESETS.items():
            if key in hidden:
                continue
            item = QListWidgetItem(f"{preset.get('name', key)}\n{key} / {preset.get('model_id', '')}")
            item.setData(0x0100, key)
            self.preset_list.addItem(item)
        if self.preset_list.count():
            self.preset_list.setCurrentRow(0)
        else:
            self.details.setText("本地预设库为空，可点击“恢复内置预设”。")

    def _show_preset(self, current=None, _previous=None):
        key = str(current.data(0x0100) or "") if current else ""
        preset = LEGACY_PRESETS.get(key, {})
        self.details.setPlainText(
            "名称：{}\nProvider ID：{}\nModel ID：{}\nBase URL：{}\n能力：{}".format(
                preset.get("name", ""), key, preset.get("model_id", ""),
                preset.get("base_url", ""), "、".join(preset.get("capabilities", []))
            )
        )

    def _import(self):
        item = self.preset_list.currentItem()
        if not item:
            msg_warn(self, "请先选择预设。")
            return
        self.selected_preset = str(item.data(0x0100) or "")
        self.accept()

    def _hide(self):
        item = self.preset_list.currentItem()
        key = str(item.data(0x0100) or "") if item else ""
        if not key:
            return
        if QMessageBox.question(
            self, "二次确认：移除预设",
            f"将从本机预设库隐藏 {key}。不会删除你的模型配置，也不会修改源码。\n\n确定继续？",
        ) != QMessageBox.StandardButton.Yes:
            return
        hidden = list(dict.fromkeys(self.config.ai_center().get("hidden_presets", [])))
        if key not in hidden:
            hidden.append(key)
        self.config.ai_center()["hidden_presets"] = hidden
        self.config.save()
        self._load()

    def _restore(self):
        if QMessageBox.question(
            self, "二次确认：恢复预设",
            "恢复全部内置预设不会覆盖现有模型。确定继续？",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.config.ai_center()["hidden_presets"] = []
        self.config.save()
        self._load()

# 版本: v2.0.1 (2026-08-17) 更新: Provider 与自定义模型编辑器
