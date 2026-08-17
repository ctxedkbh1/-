from PySide6.QtWidgets import QDialog

from core.ai.runtime import credential_store
from gui.reference_dialogs import ZoteroConnectionDialog
from gui.widgets import Worker, msg_err, msg_info
from sources.zotero import ZoteroClient


class ReferenceZoteroMixin:
    def _configure_zotero(self):
        state = self.mw.config.get("reference_center", {}) or {}
        record = state.get("zotero", {}) or {}
        dialog = ZoteroConnectionDialog(self, record)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        credentials = credential_store()
        if dialog.disconnect_requested:
            credentials.delete("zotero:web")
            state["zotero"] = {}
            self.mw.config.set("reference_center", state)
            self.status.setText("Zotero 已断开。")
            return
        state["zotero"] = dialog.record
        self.mw.config.set("reference_center", state)
        if dialog.api_key:
            credentials.set("zotero:web", dialog.api_key)
        self.status.setText("Zotero 配置已保存，请测试连接。")

    def _zotero_client(self):
        state = self.mw.config.get("reference_center", {}) or {}
        record = state.get("zotero", {}) or {}
        mode = str(record.get("mode") or "local")
        if mode == "web":
            key = credential_store().get(str(record.get("credential_ref") or "zotero:web"))
            return ZoteroClient.web(
                user_id=str(record.get("user_id") or ""),
                api_key=key,
                base_url=str(record.get("base_url") or "https://api.zotero.org"),
            )
        return ZoteroClient.local(
            base_url=str(record.get("base_url") or "http://localhost:23119/api")
        )

    def _test_zotero(self):
        self.zotero_test_button.setEnabled(False)
        self.worker = Worker(self._zotero_client().test_connection)
        self.worker.done.connect(self._zotero_test_done)
        self.worker.failed.connect(self._zotero_failed)
        self.worker.start()

    def _zotero_test_done(self, result):
        self.zotero_test_button.setEnabled(True)
        self.status.setText(
            f"Zotero {result.mode} 已连接 · API v{result.api_version}"
        )
        msg_info(self, result.message, "Zotero 连接测试")

    def _sync_zotero(self):
        state = self.mw.config.get("reference_center", {}) or {}
        record = state.get("zotero", {}) or {}
        mode = str(record.get("mode") or "local")
        since_key = "local_version" if mode == "local" else "web_version"
        since = int(record.get(since_key) or 0)
        self.zotero_button.setEnabled(False)
        self.zotero_button.setText("正在同步…")
        self.worker = Worker(self._zotero_client().sync_items, since)
        self.worker.done.connect(lambda result: self._zotero_done(result, since_key))
        self.worker.failed.connect(self._zotero_failed)
        self.worker.start()

    def _zotero_done(self, result, since_key):
        for reference in result.references:
            self.store.upsert(reference)
        state = self.mw.config.get("reference_center", {}) or {}
        record = state.setdefault("zotero", {})
        record[since_key] = result.version
        record["partition_id"] = result.partition_id
        self.mw.config.set("reference_center", state)
        self.zotero_button.setEnabled(True)
        self.zotero_button.setText("同步")
        self._load_list()
        msg_info(self, f"Zotero 同步完成：{len(result.references)} 条更新。")

    def _zotero_failed(self, message):
        self.zotero_button.setEnabled(True)
        self.zotero_button.setText("同步")
        self.zotero_test_button.setEnabled(True)
        msg_err(self, "Zotero 操作失败：" + message)

# 版本: v2.0.1 (2026-08-17) 更新: Zotero 连接、测试、同步与断开
