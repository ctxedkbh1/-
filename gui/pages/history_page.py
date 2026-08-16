import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from core.history import STATUS_LABELS, HistoryManager
from gui.widgets import ask_confirm, msg_err, msg_info, msg_warn

STATUS_COLORS = {
    "completed": "#039855",
    "generating": "#3d8bff",
    "optimizing": "#3d8bff",
    "checking": "#3d8bff",
    "waiting": "#dc6803",
    "failed": "#d92d20",
}


class _Card(QWidget):
    def __init__(self, parent_page, record):
        super().__init__()
        self.page = parent_page
        self.record = record
        self.check = QCheckBox()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(self.check)
        info = QVBoxLayout()
        mode_badge = "高级模式" if record.get("mode") == "advanced" else "全自动"
        title = QLabel(f"[{mode_badge}] {record.get('title') or '（无标题）'}")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        info.addWidget(title)
        meta = QLabel(f"{record.get('name') or '—'} · {record.get('class_name') or '—'}　"
                      f"{record.get('created_at') or ''}")
        meta.setStyleSheet("color: #667085;")
        info.addWidget(meta)
        status_text = record.get("status_text") or record.get("status") or ""
        color = STATUS_COLORS.get(record.get("status"), "#667085")
        if record.get("status") == "failed" and record.get("failure_reason"):
            status_text += f"（{record['failure_reason'][:40]}）"
        status_label = QLabel(f"状态：{status_text}")
        status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        info.addWidget(status_label)
        lay.addLayout(info, 1)
        self.btn_open = QPushButton("打开")
        self.btn_download = QPushButton("下载")
        self.btn_again = QPushButton("再来一篇")
        self.btn_delete = QPushButton("删除")
        for b in (self.btn_open, self.btn_download, self.btn_again, self.btn_delete):
            lay.addWidget(b)
        self.btn_open.clicked.connect(lambda: self.page._open_detail(record["task_id"]))
        self.btn_download.clicked.connect(lambda: self.page._download_record(record["task_id"]))
        self.btn_again.clicked.connect(lambda: self.page.again_from_record(record))
        self.btn_delete.clicked.connect(lambda: self.page.delete_records([record["task_id"]]))
        if record.get("mode") == "advanced":
            self.btn_edit = QPushButton("继续编辑")
            self.btn_edit.clicked.connect(lambda: self.page.mw.go(2))
            lay.addWidget(self.btn_edit)


class DetailDialog(QDialog):
    def __init__(self, parent, record, archive):
        super().__init__(parent)
        self.setWindowTitle("论文详情")
        self.setMinimumSize(480, 440)
        self.resize(640, 560)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        title = QLabel(record.get("title") or "（无标题）")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        lay.addWidget(title)
        form = QFormLayout()
        form.addRow("作者", QLabel(f"{record.get('name') or '—'}　{record.get('class_name') or ''}"))
        form.addRow("课程", QLabel(record.get("course") or "—"))
        form.addRow("创建时间", QLabel(record.get("created_at") or "—"))
        form.addRow("完成时间", QLabel(record.get("finished_at") or "—"))
        models = record.get("models") or {}
        model_txt = "、".join(f"{k}:{v}" for k, v in models.items()) or "自动选择"
        form.addRow("使用模型", QLabel(model_txt))
        form.addRow("优化次数", QLabel(str(record.get("rounds") or 0)))
        ai = record.get("ai_risk")
        rep = record.get("repeat_risk")
        form.addRow("质量检测", QLabel(f"AI文本风险 {ai}%　重复风险 {rep}%"
                                       if ai is not None else "—"))
        scores = record.get("scores") or {}
        if scores.get("综合质量"):
            form.addRow("综合质量", QLabel(f"{scores['综合质量']}/100"))
        form.addRow("任务耗时", QLabel(f"{record.get('duration_sec') or 0} 秒"))
        lay.addLayout(form)

        files = record.get("files") or []
        flabel = QLabel("生成文件（点击打开）：")
        flabel.setStyleSheet("font-weight: bold;")
        lay.addWidget(flabel)
        for f in files:
            p = f.get("path")
            exists = p and os.path.exists(p)
            btn = QPushButton(f"{f.get('name')}" + ("" if exists else "（文件已不存在）"))
            btn.setEnabled(bool(exists))
            if exists:
                btn.clicked.connect(lambda checked=False, path=p: self._open(path))
            lay.addWidget(btn)
        if not files:
            lay.addWidget(QLabel("（无关联文件）"))
        export_dir = record.get("export_dir") or (
            os.path.dirname(files[0].get("path")) if files and os.path.exists(files[0].get("path")) else "")
        if export_dir:
            dir_row = QHBoxLayout()
            dir_row.addWidget(QLabel("输出目录："))
            dir_label = QLabel(export_dir)
            dir_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            dir_label.setStyleSheet("color: #175cd3;")
            dir_row.addWidget(dir_label, 1)
            btn_dir = QPushButton("打开文件夹")
            btn_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(export_dir)))
            dir_row.addWidget(btn_dir)
            lay.addLayout(dir_row)

        steps = archive.get("steps") if archive else None
        if steps:
            slabel = QLabel("任务日志：")
            slabel.setStyleSheet("font-weight: bold;")
            lay.addWidget(slabel)
            log_text = "\n".join(
                f"{'✓' if v.get('status') == 'done' else '✗' if v.get('status') == 'failed' else '○'} "
                f"{k}（{v.get('status', '')}）" for k, v in steps.items())
            from PySide6.QtWidgets import QPlainTextEdit
            log_view = QPlainTextEdit()
            log_view.setReadOnly(True)
            log_view.setPlainText(log_text)
            lay.addWidget(log_view, 1)

        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    @staticmethod
    def _open(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


class HistoryPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.history = HistoryManager()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        title = QLabel("论文历史")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        tip = QLabel("全自动模式生成的每篇论文都会自动保存历史记录，"
                     "与生成文件、任务日志完整关联，程序重启后仍然保留。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)

        bar = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索论文（标题/姓名/班级/课程/时间）…")
        self.search_box.textChanged.connect(self.rebuild)
        bar.addWidget(self.search_box, 1)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "已完成", "生成中", "失败"])
        self.filter_combo.currentIndexChanged.connect(self.rebuild)
        self.order_combo = QComboBox()
        self.order_combo.addItems(["最新", "最旧"])
        self.order_combo.currentIndexChanged.connect(self.rebuild)
        bar.addWidget(self.filter_combo)
        bar.addWidget(self.order_combo)
        self.btn_select_all = QCheckBox("全选")
        self.btn_select_all.toggled.connect(self._toggle_all)
        self.btn_batch = QPushButton("批量删除")
        self.btn_batch.clicked.connect(self.on_batch_delete)
        bar.addWidget(self.btn_select_all)
        bar.addWidget(self.btn_batch)
        lay.addLayout(bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_lay = QVBoxLayout(self.list_container)
        self.list_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.list_container)
        lay.addWidget(scroll, 1)

        self.empty_widget = QWidget()
        elay = QVBoxLayout(self.empty_widget)
        elay.addStretch(1)
        elabel = QLabel("还没有生成论文\n开始创建你的第一篇论文吧。")
        elabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        elabel.setStyleSheet("color: #98a2b3; font-size: 15px;")
        elay.addWidget(elabel)
        self.btn_start = QPushButton("开始生成")
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumHeight(36)
        self.btn_start.setMaximumWidth(200)
        self.btn_start.clicked.connect(lambda: self.mw.go(1))
        erow = QHBoxLayout()
        erow.addStretch(1)
        erow.addWidget(self.btn_start)
        erow.addStretch(1)
        elay.addLayout(erow)
        elay.addStretch(1)
        lay.addWidget(self.empty_widget, 1)

    def refresh(self):
        self.history = HistoryManager()
        self.rebuild()

    def rebuild(self):
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        records = self.history.search(self.search_box.text(),
                                      self.filter_combo.currentText(),
                                      self.order_combo.currentText())
        self._cards = []
        for rec in records:
            card = _Card(self, rec)
            self._cards.append(card)
            self.list_lay.addWidget(card)
        self.list_lay.addStretch(1)
        has_records = bool(records)
        self.empty_widget.setVisible(not has_records)

    def _toggle_all(self, checked):
        for card in getattr(self, "_cards", []):
            card.check.setChecked(checked)

    def _checked_ids(self):
        return [c.record.get("task_id") for c in getattr(self, "_cards", [])
                if c.check.isChecked()]

    # ---------- 详情 / 下载 ----------

    def _record_of(self, task_id):
        rec = self.history.get(task_id)
        return rec, self.history.load_archive(task_id) if rec else {}

    def _open_detail(self, task_id):
        rec, archive = self._record_of(task_id)
        if not rec:
            msg_warn(self, "记录不存在。")
            return
        DetailDialog(self, rec, archive).exec()

    def _download_record(self, task_id):
        rec = self.history.get(task_id)
        if not rec:
            msg_warn(self, "记录不存在。")
            return
        files = [f for f in rec.get("files", []) if os.path.exists(f.get("path"))]
        if not files:
            msg_warn(self, "该论文没有可下载的文件（文件可能已被删除）。")
            return
        for f in files:
            default = os.path.join(os.path.expanduser("~"), "Desktop", f.get("name"))
            path, _ = QFileDialog.getSaveFileName(self, f"下载 {f.get('name')}",
                                                  default)
            if not path:
                continue
            try:
                with open(f.get("path"), "rb") as src, open(path, "wb") as dst:
                    dst.write(src.read())
                msg_info(self, f"已保存到：{path}")
            except OSError as e:
                msg_err(self, f"下载失败: {e}")

    # ---------- 再来一篇 ----------

    def again_from_record(self, record):
        page = self.mw.pages[1]
        page.on_again_from_input(record.get("input") or {})

    # ---------- 删除 ----------

    def on_batch_delete(self):
        ids = self._checked_ids()
        if not ids:
            msg_warn(self, "请先勾选要删除的论文。")
            return
        self.delete_records(ids)

    def delete_records(self, task_ids):
        if not task_ids:
            return
        files = []
        for tid in task_ids:
            rec = self.history.get(tid)
            if rec:
                files.extend(f.get("name") for f in rec.get("files", []))
        lines = [f"确定删除选中的 {len(task_ids)} 篇论文吗？", "",
                 "删除以后将同时删除：", "✓ 历史记录", "✓ 生成任务记录（任务日志归档）",
                 "✓ 相关临时数据", "✓ 本地生成文件"]
        if files:
            lines += ["", "关联文件："] + [f"- {n}" for n in files]
        lines += ["", "此操作无法恢复。"]
        if not ask_confirm(self, "\n".join(lines)):
            return
        failed = self.history.delete_many(task_ids)
        self.refresh()
        if failed:
            lines = ["历史记录已删除，但以下文件无法删除："]
            for f in failed:
                lines.append(f"- {f.get('name')}（原因：{f.get('reason') or '文件被占用'}）")
            lines.append("请关闭正在使用该文件的程序后手动删除。")
            msg_err(self, "\n".join(lines), "部分文件删除失败")
        else:
            msg_info(self, f"已删除 {len(task_ids)} 篇论文及其关联文件。")

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
