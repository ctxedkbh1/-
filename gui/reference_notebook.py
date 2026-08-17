from PySide6.QtWidgets import QDialog

from core.ai.runtime import credential_store
from gui.reference_dialogs import NotebookConnectionDialog
from gui.widgets import Worker, msg_err, msg_info, msg_warn
from sources.notebook import NotebookEnterpriseClient


class ReferenceNotebookMixin:
    def _configure_notebook(self):
        state = self.mw.config.get("reference_center", {}) or {}
        record = state.get("notebook", {}) or {}
        dialog = NotebookConnectionDialog(self, record)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        credentials = credential_store()
        if dialog.disconnect_requested:
            credentials.delete("notebook:enterprise")
            state["notebook"] = {}
            self.mw.config.set("reference_center", state)
            self.status.setText("Notebook Enterprise 已断开。")
            return
        state["notebook"] = dialog.record
        self.mw.config.set("reference_center", state)
        if dialog.access_token:
            credentials.set("notebook:enterprise", dialog.access_token)
        self.status.setText("Notebook Enterprise 配置已保存。")

    def _send_to_notebook(self):
        reference = self._selected()
        if not reference:
            return
        state = self.mw.config.get("reference_center", {}) or {}
        record = state.get("notebook", {}) or {}
        if not record:
            msg_warn(self, "请先配置 Gemini Notebook Enterprise。")
            return
        token = credential_store().get(str(record.get("credential_ref") or "notebook:enterprise"))
        if not token:
            msg_warn(self, "Notebook Enterprise Access Token 未设置或已失效。")
            return
        content = reference.abstract or reference.notes or reference.url
        if not content:
            msg_warn(self, "当前文献没有可发送的摘要、备注或 URL。")
            return
        client = NotebookEnterpriseClient(
            project_number=str(record.get("project_number") or ""),
            location=str(record.get("location") or "global"),
            notebook_id=str(record.get("notebook_id") or ""),
            access_token=token,
        )
        self.notebook_send_button.setEnabled(False)
        self.worker = Worker(client.add_text, reference.title or reference.reference_id, content)
        self.worker.done.connect(self._notebook_done)
        self.worker.failed.connect(self._notebook_failed)
        self.worker.start()

    def _notebook_done(self, _result):
        self.notebook_send_button.setEnabled(True)
        msg_info(self, "已发送到 Gemini Notebook Enterprise。")

    def _notebook_failed(self, message):
        self.notebook_send_button.setEnabled(True)
        msg_err(self, "Notebook Enterprise 操作失败：" + message)

# 版本: v2.0.1 (2026-08-17) 更新: Notebook Enterprise 配置与发送
