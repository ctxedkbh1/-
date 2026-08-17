import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QListWidgetItem,
                               QMessageBox, QPushButton, QSplitter, QVBoxLayout)

from core.ai.credentials import migrate_legacy_credentials, resolve_api_key
from core.ai.discovery import ModelDiscovery
from core.ai.runtime import ai_service, credential_store, model_registry
from gui.model_center_view import ModelCenterViewMixin
from gui.model_center_dialogs import ManualModelDialog, ProviderEditDialog
from gui.theme import APP_QSS
from gui.widgets import Worker, msg_err, msg_info, msg_warn


class AIModelCenterDialog(ModelCenterViewMixin, QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.registry = model_registry(config)
        self.credentials = credential_store()
        self.service = ai_service(config)
        self.worker = None
        self.setStyleSheet(APP_QSS)
        self.setWindowTitle("AI 模型中心")
        self.setMinimumSize(880, 620)
        self.resize(1080, 760)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        header = QHBoxLayout()
        title = QLabel("AI 模型中心")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch(1)
        close = QPushButton("返回设置")
        close.clicked.connect(self.accept)
        header.addWidget(close)
        root.addLayout(header)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._provider_panel())
        splitter.addWidget(self._model_panel())
        splitter.setSizes([260, 780])
        root.addWidget(splitter, 1)
        self._load_providers()

    def _load_providers(self):
        selected = self._provider_id()
        self.provider_list.clear()
        for provider in self.registry.providers():
            count = len(self.registry.models(provider.provider_id))
            state = "已启用" if provider.enabled else "已禁用"
            item = QListWidgetItem(f"{provider.display_name}\n{state} · {count} models")
            item.setData(Qt.ItemDataRole.UserRole, provider.provider_id)
            self.provider_list.addItem(item)
            if provider.provider_id == selected:
                self.provider_list.setCurrentItem(item)
        if self.provider_list.count() and self.provider_list.currentRow() < 0:
            self.provider_list.setCurrentRow(0)
        legacy_secrets = bool(str(self.config.get("deepseek_api_key") or "").strip()) or any(
            str(model.get("api_key") or "").strip()
            for model in self.config.models().values()
        )
        pending = legacy_secrets and not self.config.ai_center().get("migration", {}).get(
            "credentials_migrated"
        )
        self.migrate_button.setVisible(pending)

    def _provider_changed(self, _current=None, _previous=None):
        provider_id = self._provider_id()
        if not provider_id:
            return
        provider = self.registry.provider(provider_id)
        self.provider_title.setText(provider.display_name)
        self.provider_status.setText(provider.status.value.replace("_", " "))
        self.last_refresh.setText("最后刷新：" + (self.registry.cache.fetched_at(provider_id) or "—"))
        self._load_models()

    def _load_models(self):
        provider_id = self._provider_id()
        if not provider_id:
            return
        models = self.registry.search(self.search.text(), provider_id, self.filter.currentData() or "")
        match self.sort.currentData():
            case "name":
                models.sort(key=lambda model: model.display_name.lower())
            case "context":
                models.sort(key=lambda model: model.capabilities.context_window or 0, reverse=True)
            case "updated":
                models.sort(key=lambda model: model.updated_at or model.created_at, reverse=True)
            case "favorite":
                models.sort(key=lambda model: (not model.favorite, model.display_name.lower()))
        self.model_list.clear()
        for model in models:
            status = model.status.value.replace("_", " ")
            context = model.capabilities.context_window or "未知"
            prefix = "[收藏] " if model.favorite else ""
            item = QListWidgetItem(
                f"{prefix}{model.display_name}\n{model.model_id} · {status} · Context {context} · {model.source.value}"
            )
            item.setData(Qt.ItemDataRole.UserRole, model.ref.value)
            self.model_list.addItem(item)
        if self.model_list.count():
            self.model_list.setCurrentRow(0)
        else:
            self.details.setText("没有匹配模型。可刷新官方列表或手动添加模型。")

    def _show_model(self, current=None, _previous=None):
        reference = current.data(Qt.ItemDataRole.UserRole) if current else ""
        if not reference:
            return
        model = self.registry.model(reference)
        caps = model.capabilities
        values = [
            f"Model ID：{model.model_id}", f"Provider：{model.provider_id}",
            f"状态：{model.status.value}", f"来源：{model.source.value}",
            f"上下文：{caps.context_window or '未知'}",
            f"Reasoning：{_flag(caps.supports_reasoning)} · Vision：{_flag(caps.supports_vision)} · "
            f"Tools：{_flag(caps.supports_tools)} · Streaming：{_flag(caps.supports_streaming)}",
            f"最后检测：{model.last_checked or '未检测'}",
        ]
        if model.notes:
            values.append("备注：" + model.notes)
        self.details.setPlainText("\n".join(values))

    def _add_provider(self):
        dialog = ProviderEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.record:
            self.config.save_ai_provider(dialog.provider_key, dialog.record)
            if dialog.api_key:
                self.credentials.set(f"provider:{dialog.provider_key}", dialog.api_key)
            self.registry = model_registry(self.config)
            self.service = ai_service(self.config)
            self._load_providers()

    def _edit_provider(self):
        provider_id = self._provider_id()
        if not provider_id:
            return
        dialog = ProviderEditDialog(self, self.registry.provider(provider_id))
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.record:
            self.config.save_ai_provider(provider_id, dialog.record)
            if dialog.api_key:
                self.credentials.set(f"provider:{provider_id}", dialog.api_key)
            self.registry = model_registry(self.config)
            self.service = ai_service(self.config)
            self._load_providers()

    def _delete_provider(self):
        provider_id = self._provider_id()
        if provider_id and QMessageBox.question(self, "确认", "删除 Provider 及其手动模型？") == QMessageBox.StandardButton.Yes:
            self.config.remove_ai_provider(provider_id)
            self.credentials.delete(f"provider:{provider_id}")
            self.registry = model_registry(self.config)
            self._load_providers()

    def _add_model(self):
        dialog = ManualModelDialog(self.registry.providers(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.record:
            self.config.save_ai_model(dialog.reference, dialog.record)
            self._load_models()
            self._load_providers()

    def _refresh_models_online(self):
        provider = self.registry.provider(self._provider_id())
        legacy = self.config.models().get(provider.provider_id, {})
        key = resolve_api_key(provider, self.credentials, str(legacy.get("api_key") or ""))
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("正在获取模型…")
        self.worker = Worker(ModelDiscovery().discover, provider, key)
        self.worker.done.connect(lambda models: self._models_refreshed(provider.provider_id, models))
        self.worker.failed.connect(self._refresh_failed)
        self.worker.start()

    def _models_refreshed(self, provider_id, models):
        self.registry.update_discovered(provider_id, models)
        record = self.config.ai_providers()[provider_id]
        record.update({"status": "available", "last_checked": _now(), "last_error": ""})
        self.config.save()
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("刷新模型")
        self._load_providers()
        msg_info(self, f"模型列表已更新，发现 {len(models)} 个模型。")

    def _refresh_failed(self, message):
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("刷新模型")
        msg_err(self, "模型列表获取失败：" + message)

    def _test_model(self):
        reference = self._model_ref()
        if not reference:
            msg_warn(self, "请先选择模型。")
            return
        self.test_button.setEnabled(False)
        self.worker = Worker(self.service.health_check, reference)
        self.worker.done.connect(self._health_done)
        self.worker.failed.connect(lambda message: (self.test_button.setEnabled(True), msg_err(self, message)))
        self.worker.start()

    def _health_done(self, result):
        self.test_button.setEnabled(True)
        self.registry.update_health(self._model_ref(), result)
        provider_record = self.config.ai_providers().get(result.provider_id)
        if provider_record is not None:
            provider_record.update({
                "status": "available" if result.ok else "unavailable",
                "last_checked": result.checked_at,
                "last_error": "" if result.ok else result.message,
            })
            self.config.save()
        self._load_models()
        http = f"\nHTTP: {result.http_status}" if result.http_status else ""
        text = f"{result.provider_id} / {result.model_id}\n{result.message}{http}\nLatency: {result.latency_ms} ms"
        (msg_info if result.ok else msg_err)(self, text, "模型健康检测")

    def _toggle_favorite(self):
        reference = self._model_ref()
        if reference:
            model = self.registry.model(reference)
            self.registry.set_favorite(reference, not model.favorite)
            self._load_models()

    def _set_default(self):
        reference = "latest" if self.task_policy.currentData() == "latest" else self._model_ref()
        if not reference:
            return
        self.config.set_ai_task_model(self.task.currentData(), reference)
        msg_info(self, f"已设置为{self.task.currentText()}默认模型。")

    def _migrate_credentials(self):
        report = migrate_legacy_credentials(self.config, self.credentials)
        self.migrate_button.setVisible(bool(report.failed))
        if report.failed:
            msg_err(self, "部分旧 Key 未迁移：\n" + "\n".join(report.failed))
        else:
            msg_info(self, f"已安全迁移 {report.migrated} 个旧凭据。")

    def _provider_id(self):
        item = self.provider_list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""

    def _model_ref(self):
        item = self.model_list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""


def _flag(value):
    return "是" if value is True else ("否" if value is False else "未知")


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# 版本: v2.0.1 (2026-08-17) 更新: AI 模型中心二级页面
