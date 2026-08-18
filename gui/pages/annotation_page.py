import copy
import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                               QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPlainTextEdit, QPushButton,
                               QSpinBox, QSplitter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core.annotations import (AnnotationStore, AnnotationStoreError,
                              AnnotationStyleStore, normalize_label,
                              remove_annotation_markers,
                              replace_annotation_markers)
from core import paths
from core.evidence import canonical_id
from gui.widgets import ask_confirm, msg_err, msg_info, msg_warn


class AnnotationStyleDialog(QDialog):
    def __init__(self, parent=None, store=None, style=None):
        super().__init__(parent)
        self.store = store or AnnotationStyleStore()
        self.style = style or {}
        self.setWindowTitle("样式模板")
        self.setMinimumSize(440, 360)
        self.resize(520, 420)

        outer = QVBoxLayout(self)
        form = QFormLayout()
        self.f_style_id = QLineEdit()
        self.f_name = QLineEdit()
        self.f_prefix = QLineEdit()
        self.f_separator = QLineEdit()
        self.f_width = QSpinBox()
        self.f_width.setRange(1, 9)
        self.f_kind = QComboBox()
        self.f_kind.addItems(["evidence", "note", "todo", "term"])
        self.f_color = QLineEdit()
        self.f_description = QPlainTextEdit()
        self.f_description.setMinimumHeight(80)
        self.f_enabled = QCheckBox("启用")
        self.preview = QLabel()
        self.preview.setStyleSheet("color: #667085;")
        self.preview.setWordWrap(True)

        form.addRow("样式 ID", self.f_style_id)
        form.addRow("名称", self.f_name)
        form.addRow("前缀", self.f_prefix)
        form.addRow("分隔符", self.f_separator)
        form.addRow("编号位数", self.f_width)
        form.addRow("类别", self.f_kind)
        form.addRow("颜色", self.f_color)
        form.addRow("描述", self.f_description)
        form.addRow("", self.f_enabled)
        form.addRow("预览", self.preview)
        outer.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self.f_style_id.textChanged.connect(self._update_preview)
        self.f_prefix.textChanged.connect(self._update_preview)
        self.f_separator.textChanged.connect(self._update_preview)
        self.f_width.valueChanged.connect(self._update_preview)
        self.f_kind.currentIndexChanged.connect(self._update_preview)
        self._load(style)

    def _load(self, style):
        if style:
            self.f_style_id.setText(str(style.get("style_id") or ""))
            self.f_name.setText(str(style.get("name") or ""))
            self.f_prefix.setText(str(style.get("prefix") or ""))
            self.f_separator.setText(str(style.get("separator") or ""))
            self.f_width.setValue(int(style.get("width") or 3))
            idx = self.f_kind.findText(str(style.get("kind") or "note"))
            self.f_kind.setCurrentIndex(max(0, idx))
            self.f_color.setText(str(style.get("color") or "#667085"))
            self.f_description.setPlainText(str(style.get("description") or ""))
            self.f_enabled.setChecked(bool(style.get("enabled", True)))
            self._immutable = bool(style.get("immutable"))
        else:
            self.f_style_id.setText("")
            self.f_prefix.setText("N")
            self.f_separator.setText("")
            self.f_width.setValue(3)
            self.f_kind.setCurrentIndex(max(0, self.f_kind.findText("note")))
            self.f_color.setText("#667085")
            self.f_enabled.setChecked(True)
            self._immutable = False
        if self._immutable:
            self.f_style_id.setReadOnly(True)
        self._update_preview()

    def _sample_label(self):
        style_id = normalize_label(self.f_style_id.text()).lower() or "custom"
        prefix = self.f_prefix.text().strip().upper() or style_id[:1].upper() or "N"
        sep = self.f_separator.text()
        width = max(1, self.f_width.value())
        return f"{prefix}{sep}{1:0{width}d}"

    def _update_preview(self, *_args):
        self.preview.setText(f"示例：[{self._sample_label()}]")

    def get_style(self):
        style_id = normalize_label(self.f_style_id.text()).lower() or "custom_style"
        return {
            "style_id": style_id,
            "name": self.f_name.text().strip() or style_id,
            "prefix": self.f_prefix.text().strip().upper() or "N",
            "separator": self.f_separator.text(),
            "width": self.f_width.value(),
            "kind": self.f_kind.currentText(),
            "color": self.f_color.text().strip() or "#667085",
            "description": self.f_description.toPlainText().strip(),
            "enabled": self.f_enabled.isChecked(),
            "immutable": self._immutable,
        }

    def _accept(self):
        style = self.get_style()
        if not style["style_id"]:
            msg_warn(self, "请填写样式 ID。")
            return
        if not style["name"]:
            msg_warn(self, "请填写样式名称。")
            return
        if not re.fullmatch(r"[^\W\d_][\w]{0,7}", style["prefix"], re.UNICODE):
            msg_warn(self, "样式前缀必须以字母或中文开头，最多 8 个字符。")
            return
        if not re.fullmatch(r"[-_.]?", style["separator"]):
            msg_warn(self, "样式分隔符只能是短横线、下划线、点或留空。")
            return
        self.style = style
        self.accept()


class AnnotationDialog(QDialog):
    def __init__(self, parent=None, store=None, record=None, readonly=False,
                 preset_style_id=None, preset_target_text=""):
        super().__init__(parent)
        self.mw = getattr(parent, "mw", None)
        self.store = store or AnnotationStore()
        self.style_store = self.store.styles
        self.record = None
        self.readonly = readonly
        self.setWindowTitle("批注详情" if readonly else ("编辑批注" if record else "添加批注"))
        self.setMinimumSize(560, 500)
        self.resize(720, 720)

        outer = QVBoxLayout(self)
        form = QFormLayout()
        self.f_style = QComboBox()
        self._load_styles()
        self.f_number = QSpinBox()
        self.f_number.setRange(1, 9999)
        self.f_label = QLabel()
        self.f_label.setStyleSheet("color: #667085;")
        self.f_title = QLineEdit()
        self.f_body = QPlainTextEdit()
        self.f_body.setPlaceholderText("批注正文、说明或备注。")
        self.f_tags = QLineEdit()
        self.f_status = QComboBox()
        self.f_status.addItems(["active", "todo", "resolved", "archived"])
        self.f_color = QLineEdit()
        self.f_evidence_id = QLineEdit()
        self.f_reference_id = QLineEdit()
        self.f_target_text = QPlainTextEdit()
        self.f_target_text.setMinimumHeight(72)
        self.f_notes = QPlainTextEdit()
        self.f_notes.setMinimumHeight(72)

        form.addRow("样式", self.f_style)
        form.addRow("编号", self.f_number)
        form.addRow("标记预览", self.f_label)
        form.addRow("标题", self.f_title)
        form.addRow("内容", self.f_body)
        form.addRow("标签", self.f_tags)
        form.addRow("状态", self.f_status)
        form.addRow("颜色", self.f_color)
        form.addRow("关联证据 ID", self.f_evidence_id)
        form.addRow("参考文献 ID", self.f_reference_id)
        form.addRow("关联文本", self.f_target_text)
        form.addRow("备注", self.f_notes)
        outer.addLayout(form)

        buttons = QDialogButtonBox()
        if readonly:
            self.btn_source = QPushButton("打开关联来源")
            buttons.addButton(self.btn_source, QDialogButtonBox.ButtonRole.ActionRole)
            self.btn_source.clicked.connect(self._open_source)
            buttons.addButton(QDialogButtonBox.StandardButton.Close)
        else:
            buttons.addButton(QDialogButtonBox.StandardButton.Save)
            buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        outer.addWidget(buttons)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        self.f_style.currentIndexChanged.connect(self._update_preview)
        self.f_number.valueChanged.connect(self._update_preview)
        self.f_evidence_id.textChanged.connect(self._update_preview)
        self._editing_existing = bool(record)
        self._load(record, preset_style_id)
        if not record and preset_target_text:
            self.f_target_text.setPlainText(str(preset_target_text).strip())
        if readonly:
            for widget in (
                self.f_style, self.f_number, self.f_title, self.f_body, self.f_tags,
                self.f_status, self.f_color, self.f_evidence_id, self.f_reference_id,
                self.f_target_text, self.f_notes,
            ):
                widget.setEnabled(False)

    def _load_styles(self):
        self.f_style.clear()
        for style in self.style_store.all():
            label = f"{style.get('name') or style.get('style_id')} ({style.get('style_id')})"
            self.f_style.addItem(label, style.get("style_id"))

    def _style(self):
        return self.style_store.get(self.f_style.currentData()) or self.style_store.get("note")

    def _load(self, record, preset_style_id):
        if record:
            idx = self.f_style.findData(record.get("style_id") or "note")
            self.f_style.setCurrentIndex(max(0, idx))
            self.f_number.setValue(int(record.get("number") or 1))
            self.f_title.setText(str(record.get("title") or ""))
            self.f_body.setPlainText(str(record.get("body") or ""))
            self.f_tags.setText("、".join(record.get("tags") or []))
            status = str(record.get("status") or "active")
            idx = self.f_status.findText(status)
            self.f_status.setCurrentIndex(max(0, idx))
            self.f_color.setText(str(record.get("color") or "#667085"))
            self.f_evidence_id.setText(str(record.get("evidence_id") or ""))
            self.f_reference_id.setText(str(record.get("reference_id") or ""))
            self.f_target_text.setPlainText(str(record.get("target_text") or ""))
            self.f_notes.setPlainText(str(record.get("notes") or ""))
            self.record = record
        elif preset_style_id:
            idx = self.f_style.findData(preset_style_id)
            self.f_style.setCurrentIndex(max(0, idx))
            self.f_number.setValue(self.store.next_number(self.f_style.currentData() or "note"))
        else:
            self.f_number.setValue(self.store.next_number(self.f_style.currentData() or "note"))
        self._update_preview()

    def _update_preview(self, *_args):
        if not getattr(self, "_editing_existing", False) and self.sender() is self.f_style:
            self.f_number.blockSignals(True)
            self.f_number.setValue(self.store.next_number(self.f_style.currentData() or "note"))
            self.f_number.blockSignals(False)
        style = self._style() or {}
        label = self.f_evidence_id.text().strip()
        if style.get("style_id") == "evidence" and label:
            display = canonical_id(label)
        else:
            number = max(1, self.f_number.value())
            display = self.style_store.format_label(style.get("style_id") or "note", number)
        self.f_label.setText(f"示例：[{display}]")

    def _open_source(self):
        evidence_id = canonical_id(self.f_evidence_id.text()) if self.f_evidence_id.text().strip() else ""
        if not evidence_id:
            msg_warn(self, "该批注没有关联证据。")
            return
        if self.mw and getattr(self.mw, "evidence", None):
            evidence = self.mw.evidence.get(evidence_id)
        else:
            evidence = None
        if not evidence:
            msg_warn(self, f"找不到关联证据 {evidence_id}。")
            return
        from gui.pages.evidence_page import EvidenceDialog
        dlg = EvidenceDialog(self, record={
            "id": evidence.get("id") or evidence_id,
            "source_type": evidence.get("source_type") or "manual",
            "title": evidence.get("title") or "",
            "authors": evidence.get("authors") or "",
            "journal": evidence.get("journal") or "",
            "year": evidence.get("year") or "",
            "volume_issue_pages": evidence.get("volume_issue_pages") or "",
            "doi": evidence.get("doi") or "",
            "url": evidence.get("url") or "",
            "organization": evidence.get("organization") or "",
            "published_at": evidence.get("published_at") or "",
            "content": evidence.get("content") or "",
            "abstract": evidence.get("abstract") or "",
            "keywords": evidence.get("keywords") or "",
            "verified": bool(evidence.get("verified", True)),
        }, readonly=True)
        dlg.exec()

    def get_record(self):
        style = self._style() or self.style_store.get("note")
        evidence_id = canonical_id(self.f_evidence_id.text()) if self.f_evidence_id.text().strip() else ""
        number = max(1, self.f_number.value())
        display_label = (
            evidence_id if style and style.get("style_id") == "evidence" and evidence_id
            else self.style_store.format_label(style.get("style_id") or "note", number)
        )
        tags = [t.strip() for t in self.f_tags.text().replace("，", ",").split(",") if t.strip()]
        return {
            "annotation_id": (self.record or {}).get("annotation_id") or "",
            "style_id": style.get("style_id") or "note",
            "style_name": style.get("name") or style.get("style_id") or "批注",
            "number": number,
            "display_label": display_label,
            "label": display_label,
            "kind": style.get("kind") or "note",
            "title": self.f_title.text().strip(),
            "body": self.f_body.toPlainText().strip(),
            "tags": tags,
            "status": self.f_status.currentText(),
            "color": self.f_color.text().strip() or style.get("color") or "#667085",
            "evidence_id": evidence_id,
            "source_id": evidence_id,
            "reference_id": self.f_reference_id.text().strip(),
            "source_type": "manual",
            "target_type": "evidence" if evidence_id else "note",
            "target_text": self.f_target_text.toPlainText().strip(),
            "summary": "",
            "notes": self.f_notes.toPlainText().strip(),
        }

    def _accept(self):
        rec = self.get_record()
        if not rec["display_label"]:
            msg_warn(self, "请填写批注编号。")
            return
        existing = self.store.get_by_label(rec["display_label"])
        if existing and existing.get("annotation_id") != rec.get("annotation_id"):
            msg_warn(self, f"批注标记 [{rec['display_label']}] 已存在，请调整编号或样式。")
            return
        self.record = rec
        self.accept()


class AnnotationStyleManagerDialog(QDialog):
    def __init__(self, parent=None, store=None):
        super().__init__(parent)
        self.store = store or AnnotationStyleStore()
        self.setWindowTitle("样式模板管理")
        self.setMinimumSize(520, 420)
        self.resize(640, 500)

        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._show_style)
        top.addWidget(self.list, 1)

        right = QVBoxLayout()
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        right.addWidget(self.details, 1)
        row = QHBoxLayout()
        self.btn_add = QPushButton("新建")
        self.btn_edit = QPushButton("编辑")
        self.btn_delete = QPushButton("删除")
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_edit)
        row.addWidget(self.btn_delete)
        row.addStretch(1)
        right.addLayout(row)
        top.addLayout(right, 1)
        outer.addLayout(top)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_delete.clicked.connect(self.on_delete)
        self.refresh()

    def refresh(self):
        self.store = AnnotationStyleStore()
        self.list.clear()
        for style in self.store.all():
            item = QListWidgetItem(f"{style.get('name')} ({style.get('style_id')})")
            item.setData(Qt.ItemDataRole.UserRole, style.get("style_id"))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        else:
            self.details.setPlainText("暂无样式模板。")

    def _selected(self):
        item = self.list.currentItem()
        sid = str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""
        return self.store.get(sid) if sid else None

    def _show_style(self, *_args):
        style = self._selected()
        if not style:
            return
        lines = [
            f"样式 ID：{style.get('style_id')}",
            f"名称：{style.get('name')}",
            f"前缀：{style.get('prefix')}",
            f"分隔符：{style.get('separator') or '（无）'}",
            f"编号位数：{style.get('width')}",
            f"类别：{style.get('kind')}",
            f"启用：{'是' if style.get('enabled', True) else '否'}",
            f"颜色：{style.get('color')}",
            f"预览：{self.store.marker_for(style.get('style_id'), 1)}",
            "",
            style.get('description') or "",
        ]
        self.details.setPlainText("\n".join(lines))

    def on_add(self):
        dlg = AnnotationStyleDialog(self, self.store)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.style:
            try:
                self.store.upsert(dlg.style)
            except (OSError, ValueError, AnnotationStoreError) as exc:
                msg_warn(self, str(exc), "样式未保存")
                return
            self.refresh()
            msg_info(self, f"已新增样式：{dlg.style['style_id']}")

    def on_edit(self):
        style = self._selected()
        if not style:
            msg_warn(self, "请先选择样式。")
            return
        dlg = AnnotationStyleDialog(self, self.store, style=style)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.style:
            try:
                self.store.upsert(dlg.style)
            except (OSError, ValueError, AnnotationStoreError) as exc:
                msg_warn(self, str(exc), "样式未保存")
                return
            self.refresh()
            msg_info(self, f"已更新样式：{dlg.style['style_id']}")

    def on_delete(self):
        style = self._selected()
        if not style:
            msg_warn(self, "请先选择样式。")
            return
        if style.get("immutable"):
            msg_warn(self, "默认样式不能删除。")
            return
        try:
            used = any(item.get("style_id") == style.get("style_id")
                       for item in AnnotationStore(style_store=self.store).all())
        except AnnotationStoreError as exc:
            msg_warn(self, str(exc), "样式未删除")
            return
        if used:
            msg_warn(self, "该样式仍被批注使用，请先修改或删除相关批注。")
            return
        if not ask_confirm(self, f"确定删除样式 {style.get('style_id')} 吗？"):
            return
        try:
            deleted = self.store.delete(style.get("style_id"))
        except (OSError, AnnotationStoreError) as exc:
            msg_warn(self, str(exc), "样式未删除")
            return
        if deleted:
            self.refresh()
            msg_info(self, "样式已删除。")


class AnnotationPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.store = AnnotationStore()
        self.style_store = self.store.styles

        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)

        title = QLabel("批注管理")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        tip = QLabel("这里管理正文中的批注、证据标记和样式模板。证据编号会自动从证据库同步。")
        tip.setStyleSheet("color: #667085;")
        tip.setWordWrap(True)
        lay.addWidget(tip)

        bar = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索批注编号 / 标题 / 内容 / 标签 …")
        self.search_box.textChanged.connect(self.rebuild)
        self.filter_style = QComboBox()
        self.filter_style.currentIndexChanged.connect(self.rebuild)
        self.filter_status = QComboBox()
        self.filter_status.addItem("全部状态", "")
        for key in ("active", "todo", "resolved", "archived", "unverified"):
            self.filter_status.addItem(key, key)
        self.filter_status.currentIndexChanged.connect(self.rebuild)
        bar.addWidget(self.search_box, 1)
        bar.addWidget(self.filter_style)
        bar.addWidget(self.filter_status)
        lay.addLayout(bar)

        actions = QHBoxLayout()
        self.btn_sync = QPushButton("同步证据编号")
        self.btn_add = QPushButton("添加批注")
        self.btn_edit = QPushButton("编辑批注")
        self.btn_delete = QPushButton("批量删除")
        self.btn_renumber = QPushButton("重新编号")
        self.btn_export = QPushButton("导出批注")
        self.btn_styles = QPushButton("样式模板")
        for b in (self.btn_sync, self.btn_add, self.btn_edit, self.btn_delete,
                  self.btn_renumber, self.btn_export, self.btn_styles):
            actions.addWidget(b)
        actions.addStretch(1)
        self.btn_select_all = QCheckBox("全选")
        self.btn_select_all.toggled.connect(self._toggle_all)
        actions.addWidget(self.btn_select_all)
        lay.addLayout(actions)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["标记", "样式", "标题", "状态", "关联证据", "标签", "更新时间"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.on_edit)
        lay.addWidget(self.table, 1)

        self.btn_sync.clicked.connect(self.on_sync)
        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_renumber.clicked.connect(self.on_renumber)
        self.btn_export.clicked.connect(self.on_export)
        self.btn_styles.clicked.connect(self.on_styles)

    def refresh(self):
        self.store = AnnotationStore()
        self.style_store = self.store.styles
        self._load_style_filter()
        self.on_sync(silent=True)
        self.rebuild()

    def _load_style_filter(self):
        current = self.filter_style.currentData()
        self.filter_style.blockSignals(True)
        self.filter_style.clear()
        self.filter_style.addItem("全部样式", "")
        for style in self.style_store.all():
            self.filter_style.addItem(f"{style.get('name')} ({style.get('style_id')})", style.get("style_id"))
        idx = self.filter_style.findData(current)
        self.filter_style.setCurrentIndex(max(0, idx))
        self.filter_style.blockSignals(False)

    def rebuild(self):
        records = self.store.search(
            self.search_box.text(),
            self.filter_style.currentData(),
            self.filter_status.currentData(),
        )
        records.sort(key=lambda item: (item.get("style_id") != "evidence", item.get("display_label") or item.get("annotation_id")))
        self.table.setRowCount(len(records))
        for row, item in enumerate(records):
            values = [
                item.get("display_label") or item.get("annotation_id") or "",
                self.style_store.get(item.get("style_id")).get("name") if self.style_store.get(item.get("style_id")) else item.get("style_id") or "",
                item.get("title") or item.get("body") or "（无标题）",
                item.get("status") or "active",
                item.get("evidence_id") or "",
                "、".join(item.get("tags") or []),
                item.get("updated_at") or item.get("created_at") or "",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, item.get("annotation_id"))
                    cell.setForeground(Qt.GlobalColor.blue)
                self.table.setItem(row, col, cell)
        self.table.resizeRowsToContents()

    def _selected_ids(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        ids = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                ids.append(str(item.data(Qt.ItemDataRole.UserRole) or ""))
        return [i for i in ids if i]

    def _toggle_all(self, checked):
        if checked:
            self.table.selectAll()
        else:
            self.table.clearSelection()

    def _chapter_files(self):
        directory = paths.chapters_dir()
        files = []
        for name in os.listdir(directory):
            match = re.fullmatch(r"(\d+)\.md", name)
            if match:
                files.append((int(match.group(1)), os.path.join(directory, name)))
        return sorted(files)

    @staticmethod
    def _write_chapter_file(path, text):
        tmp = path + ".annotation.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)

    def _rewrite_chapters(self, mapping=None, remove_labels=None):
        originals = {}
        updates = {}
        for index, path in self._chapter_files():
            with open(path, encoding="utf-8") as f:
                original = f.read()
            updated = replace_annotation_markers(original, mapping or {})
            if remove_labels:
                updated = remove_annotation_markers(updated, remove_labels)
            if updated != original:
                originals[path] = original
                updates[path] = updated
        try:
            for path, updated in updates.items():
                self._write_chapter_file(path, updated)
        except OSError:
            for path, original in originals.items():
                try:
                    self._write_chapter_file(path, original)
                except OSError:
                    pass
            raise
        return originals, len(updates)

    def _restore_chapters(self, originals):
        for path, original in (originals or {}).items():
            self._write_chapter_file(path, original)

    def on_sync(self, silent=False):
        self.store = AnnotationStore()
        try:
            changed = self.store.sync_legacy_evidence(self.mw.evidence)
        except AnnotationStoreError as exc:
            if not silent:
                msg_warn(self, str(exc), "批注数据未同步")
            self.style_store = self.store.styles
            self._load_style_filter()
            self.rebuild()
            return False
        self.mw.annotations = self.store
        self.style_store = self.store.styles
        self._load_style_filter()
        self.rebuild()
        if not silent:
            msg_info(self, "证据编号已同步到批注库。" if changed else "批注库已是最新。")
        return changed

    def on_add(self):
        dlg = AnnotationDialog(self, store=self.store, preset_style_id=self.filter_style.currentData() or None)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.record:
            try:
                self.store.add(dlg.record)
            except AnnotationStoreError as exc:
                msg_warn(self, str(exc), "批注未保存")
                return
            self.on_sync(silent=True)
            self.rebuild()
            msg_info(self, f"已添加批注：{dlg.record['display_label']}")

    def on_edit(self, *_args):
        ids = self._selected_ids()
        if not ids:
            msg_warn(self, "请先选择一条批注。")
            return
        record = self.store.get(ids[0])
        if not record:
            msg_warn(self, "批注记录不存在。")
            return
        if record.get("style_id") == "evidence":
            msg_warn(self, "证据批注由证据库维护，请在证据库中编辑。")
            return
        dlg = AnnotationDialog(self, store=self.store, record=record)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.record:
            old_label = record.get("display_label") or record.get("label") or ""
            new_label = dlg.record.get("display_label") or dlg.record.get("label") or ""
            originals = {}
            try:
                if normalize_label(old_label) != normalize_label(new_label):
                    originals, _ = self._rewrite_chapters({old_label: new_label})
                self.store.update(record["annotation_id"], dlg.record)
            except AnnotationStoreError as exc:
                if originals:
                    self._restore_chapters(originals)
                msg_warn(self, str(exc), "批注未保存")
                return
            except OSError as exc:
                msg_warn(self, str(exc), "正文未更新")
                return
            self.on_sync(silent=True)
            self.rebuild()

    def on_delete(self):
        ids = self._selected_ids()
        if not ids:
            msg_warn(self, "请先选择要删除的批注。")
            return
        if not ask_confirm(self, f"确定删除选中的 {len(ids)} 条批注吗？"):
            return
        records = [self.store.get(aid) for aid in ids]
        records = [record for record in records if record]
        if any(record.get("style_id") == "evidence" for record in records):
            msg_warn(self, "证据批注由证据库维护，不能在这里删除。")
            return
        labels = [record.get("display_label") or record.get("label") for record in records]
        originals = {}
        try:
            originals, _ = self._rewrite_chapters(remove_labels=labels)
            removed = self.store.delete_many(ids)
        except (OSError, AnnotationStoreError) as exc:
            try:
                self._restore_chapters(originals)
            except OSError:
                pass
            msg_warn(self, str(exc), "批注未删除")
            return
        self.rebuild()
        msg_info(self, f"已删除 {removed} 条批注。")

    def on_renumber(self):
        style_id = self.filter_style.currentData()
        if not style_id:
            msg_warn(self, "请先选择一个具体样式再重新编号。")
            return
        if style_id == "evidence":
            msg_warn(self, "证据编号与正文引用绑定，不允许在批注页重新编号。")
            return
        if not ask_confirm(self, f"确定重新编号样式 {style_id} 的批注吗？"):
            return
        before = copy.deepcopy(self.store.data)
        try:
            mapping = self.store.renumber(style_id)
        except (OSError, AnnotationStoreError) as exc:
            self.store.data = before
            msg_warn(self, str(exc), "重新编号未完成")
            return
        updated_chapters = 0
        try:
            originals, updated_chapters = self._rewrite_chapters(mapping=mapping)
        except OSError as exc:
            self.store.data = before
            self.store.save()
            msg_warn(self, str(exc), "重新编号未完成")
            return
        self.rebuild()
        msg_info(self, f"已重新编号 {len(mapping)} 条批注，并更新 {updated_chapters} 个章节。")

    def on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出批注", "批注表.md", "Markdown (*.md);;JSON (*.json)")
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.store.export_json())
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.store.export_markdown())
            msg_info(self, f"批注已导出：{path}")
        except Exception as exc:
            msg_err(self, f"导出失败: {exc}")

    def on_styles(self):
        dlg = AnnotationStyleManagerDialog(self, self.style_store)
        dlg.exec()
        self.refresh()

# 版本: v2.2.0 (2026-08-18) 更新: 批注管理与样式模板界面
