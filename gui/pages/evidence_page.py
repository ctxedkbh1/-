from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                               QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core.evidence import SOURCE_TYPE_LABELS
from gui.widgets import ask_confirm, msg_err, msg_info, msg_warn, open_url


class EvidenceDialog(QDialog):
    def __init__(self, parent=None, record=None, preset_type=None, readonly=False):
        super().__init__(parent)
        self.setWindowTitle("证据详情" if readonly else ("编辑证据" if record else "添加证据"))
        self.setMinimumSize(480, 460)
        self.resize(640, 640)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        form = QFormLayout()
        self.f_type = QComboBox()
        for key, label in SOURCE_TYPE_LABELS.items():
            self.f_type.addItem(label, key)
        self.f_title = QLineEdit()
        self.f_authors = QLineEdit()
        self.f_journal = QLineEdit()
        self.f_year = QLineEdit()
        self.f_vp = QLineEdit()
        self.f_doi = QLineEdit()
        self.f_url = QLineEdit()
        self.f_org = QLineEdit()
        self.f_pub = QLineEdit()
        self.f_content = QPlainTextEdit()
        self.f_content.setPlaceholderText("证据内容（数据、结论、政策原文等），AI 写作时只能使用这里的内容。")
        self.f_abstract = QPlainTextEdit()
        self.f_abstract.setFixedHeight(56)
        self.f_keywords = QLineEdit()
        self.f_verified = QCheckBox("已验证（已到原始来源核对真实存在）")
        form.addRow("来源类型", self.f_type)
        form.addRow("标题 *", self.f_title)
        form.addRow("作者", self.f_authors)
        form.addRow("期刊", self.f_journal)
        form.addRow("年份", self.f_year)
        form.addRow("卷期页码", self.f_vp)
        form.addRow("DOI", self.f_doi)
        form.addRow("URL / 链接", self.f_url)
        form.addRow("发布机构", self.f_org)
        form.addRow("发布日期", self.f_pub)
        form.addRow("证据内容 *", self.f_content)
        form.addRow("摘要", self.f_abstract)
        form.addRow("关键词", self.f_keywords)
        form.addRow("", self.f_verified)
        lay.addLayout(form)
        self.ref_label = QLabel()
        self.ref_label.setWordWrap(True)
        self.ref_label.setStyleSheet("color: #667085;")
        lay.addWidget(self.ref_label)

        buttons = QDialogButtonBox()
        if readonly:
            self.btn_open = QPushButton("打开来源")
            buttons.addButton(self.btn_open, QDialogButtonBox.ButtonRole.ActionRole)
            self.btn_open.clicked.connect(self._open_source)
            buttons.addButton(QDialogButtonBox.StandardButton.Close)
        else:
            buttons.addButton(QDialogButtonBox.StandardButton.Save)
            buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        lay.addWidget(buttons)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.record = None
        if record:
            self._load(record)
        elif preset_type:
            self.f_type.setCurrentIndex(max(0, self.f_type.findData(preset_type)))
        if readonly:
            for w in (self.f_type, self.f_title, self.f_authors, self.f_journal,
                      self.f_year, self.f_vp, self.f_doi, self.f_url, self.f_org,
                      self.f_pub, self.f_content, self.f_abstract, self.f_keywords,
                      self.f_verified):
                w.setEnabled(False)

    def _load(self, rec):
        idx = self.f_type.findData(rec.get("source_type", "manual"))
        self.f_type.setCurrentIndex(max(0, idx))
        self.f_title.setText(str(rec.get("title") or ""))
        self.f_authors.setText(str(rec.get("authors") or ""))
        self.f_journal.setText(str(rec.get("journal") or ""))
        self.f_year.setText(str(rec.get("year") or ""))
        self.f_vp.setText(str(rec.get("volume_issue_pages") or ""))
        self.f_doi.setText(str(rec.get("doi") or ""))
        self.f_url.setText(str(rec.get("url") or ""))
        self.f_org.setText(str(rec.get("organization") or ""))
        self.f_pub.setText(str(rec.get("published_at") or ""))
        self.f_content.setPlainText(str(rec.get("content") or ""))
        self.f_abstract.setPlainText(str(rec.get("abstract") or ""))
        self.f_keywords.setText(str(rec.get("keywords") or ""))
        self.f_verified.setChecked(bool(rec.get("verified")))
        self._update_ref(rec)

    def _update_ref(self, rec):
        from core.evidence import EvidenceStore
        ref = EvidenceStore().to_reference(rec)
        self.ref_label.setText("参考文献著录预览：" + ref)

    def _on_accept(self):
        rec = self.get_record()
        if not rec["title"] and not rec["content"]:
            msg_warn(self, "标题与证据内容至少填写一项。")
            return
        self.record = rec
        self.accept()

    def _open_source(self):
        rec = self.record or self.get_record()
        url = rec.get("url") or ("https://doi.org/" + rec["doi"] if rec.get("doi") else "")
        if url:
            open_url(url)
        else:
            msg_warn(self, "该证据没有可打开的 URL 或 DOI。")

    def get_record(self):
        return {
            "source_type": self.f_type.currentData(),
            "title": self.f_title.text().strip(),
            "authors": self.f_authors.text().strip(),
            "journal": self.f_journal.text().strip(),
            "year": self.f_year.text().strip(),
            "volume_issue_pages": self.f_vp.text().strip(),
            "doi": self.f_doi.text().strip(),
            "url": self.f_url.text().strip(),
            "organization": self.f_org.text().strip(),
            "published_at": self.f_pub.text().strip(),
            "content": self.f_content.toPlainText().strip(),
            "abstract": self.f_abstract.toPlainText().strip(),
            "keywords": self.f_keywords.text().strip(),
            "verified": self.f_verified.isChecked(),
        }


class EvidencePage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)

        title = QLabel("第四阶段：证据库")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        tip = QLabel("正文只能引用证据库中的真实资料。双击某行可查看完整来源；点击编号可追溯原始来源。")
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)

        row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索证据（标题/来源/内容）…")
        self.search_box.textChanged.connect(self.refresh)
        row.addWidget(self.search_box, 1)
        self.btn_add = QPushButton("添加证据")
        self.btn_import = QPushButton("导入文献")
        self.btn_export = QPushButton("导出证据表")
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_import)
        row.addWidget(self.btn_export)
        lay.addLayout(row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["编号", "类型", "标题", "来源", "年份", "URL/DOI", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        lay.addWidget(self.table, 1)

        row2 = QHBoxLayout()
        self.btn_edit = QPushButton("编辑证据")
        self.btn_del = QPushButton("删除证据")
        self.btn_verify = QPushButton("验证证据")
        self.btn_open = QPushButton("打开来源")
        self.btn_ok = QPushButton("证据已建好，进入大纲")
        self.btn_ok.setObjectName("primary")
        for b in (self.btn_edit, self.btn_del, self.btn_verify, self.btn_open):
            row2.addWidget(b)
        row2.addStretch(1)
        row2.addWidget(self.btn_ok)
        lay.addLayout(row2)

        self.btn_add.clicked.connect(self.on_add)
        self.btn_import.clicked.connect(self.on_import)
        self.btn_export.clicked.connect(self.on_export)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_del.clicked.connect(self.on_delete)
        self.btn_verify.clicked.connect(self.on_verify)
        self.btn_open.clicked.connect(self.on_open_source)
        self.btn_ok.clicked.connect(lambda: self.mw.go(5))

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.text() if item else None

    def refresh(self):
        store = self.mw.evidence
        records = store.search(self.search_box.text())
        self.table.setRowCount(len(records))
        for i, e in enumerate(records):
            src = e.get("organization") or e.get("journal") or e.get("source") or ""
            yr = e.get("year") or e.get("published_at") or ""
            link = e.get("doi") or e.get("url") or ""
            status = "已验证" if e.get("verified") else "未验证"
            if store.missing_fields(e):
                status += "·待完善"
            cells = [e.get("id", ""),
                     SOURCE_TYPE_LABELS.get(e.get("source_type"), e.get("source_type")),
                     e.get("title") or "（无标题）",
                     src, yr, link, status]
            for j, v in enumerate(cells):
                item = QTableWidgetItem(str(v))
                if j == 0:
                    item.setForeground(Qt.GlobalColor.blue)
                self.table.setItem(i, j, item)
        self.table.resizeColumnToContents(0)

    def on_add(self):
        dlg = EvidenceDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.record:
            eid = self.mw.evidence.add(dlg.record)
            from core import log
            log.get().info("证据已添加 id=%s", eid)
            msg_info(self, f"证据已加入证据库：{eid}")
            self.refresh()

    def on_edit(self):
        eid = self._selected_id()
        if not eid:
            msg_warn(self, "请先选择一条证据。")
            return
        rec = self.mw.evidence.get(eid)
        dlg = EvidenceDialog(self, record=rec)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.record:
            self.mw.evidence.update(eid, dlg.record)
            from core import log
            log.get().info("证据已更新 id=%s", eid)
            self.refresh()

    def on_delete(self):
        eid = self._selected_id()
        if not eid:
            msg_warn(self, "请先选择一条证据。")
            return
        if ask_confirm(self, f"确定删除证据 {eid}？正文中若已引用该证据需重新检查。"):
            self.mw.evidence.delete(eid)
            from core import log
            log.get().info("证据已删除 id=%s", eid)
            self.refresh()

    def on_verify(self):
        eid = self._selected_id()
        if not eid:
            msg_warn(self, "请先选择一条证据。")
            return
        rec = self.mw.evidence.get(eid)
        if ask_confirm(self, f"请确认已到原始来源核对过 {eid}《{rec.get('title') or '（无标题）'}》"
                             "真实存在且内容一致。\n是 = 标记为已验证；否 = 标记为未验证。"):
            self.mw.evidence.update(eid, {"verified": True})
            from core import log
            log.get().info("证据已验证 id=%s", eid)
        else:
            self.mw.evidence.update(eid, {"verified": False})
        self.refresh()

    def on_open_source(self):
        eid = self._selected_id()
        if not eid:
            msg_warn(self, "请先选择一条证据。")
            return
        rec = self.mw.evidence.get(eid)
        url = rec.get("url") or ("https://doi.org/" + rec["doi"] if rec.get("doi") else "")
        if url:
            open_url(url)
        else:
            msg_warn(self, "该证据没有可打开的 URL 或 DOI。")

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入文献文件（CNKI 导出 RIS / EndNote / BibTeX / TXT）", "",
            "文献文件 (*.ris *.bib *.txt);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            msg_err(self, f"读取文件失败: {e}")
            return
        from sources import cnki
        records = cnki.parse_text(text)
        if not records:
            msg_warn(self, "未能从文件中解析出文献记录。支持 CNKI 导出的 RIS / BibTeX 格式。")
            return
        if not ask_confirm(self, f"解析到 {len(records)} 条文献，全部加入证据库（类型标记为 CNKI）？"):
            return
        added = []
        for rec in records:
            added.append(self.mw.evidence.add(rec))
        from core import log
        log.get().info("文献导入完成 条数=%d", len(added))
        msg_info(self, f"已导入 {len(added)} 条：{'、'.join(added)}")
        self.refresh()

    def on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出证据表", "证据表.md",
                                              "Markdown (*.md);;JSON (*.json)")
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.mw.evidence.export_json())
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.mw.evidence.export_markdown())
            msg_info(self, f"证据表已导出：{path}")
        except Exception as e:
            msg_err(self, f"导出失败: {e}")

    def _on_double_click(self, row, col):
        item = self.table.item(row, 0)
        if item:
            self._show_detail(item.text())

    def _show_detail(self, eid):
        rec = self.mw.evidence.get(eid)
        if rec:
            dlg = EvidenceDialog(self, record=rec, readonly=True)
            dlg.exec()

# 版本: v1.9.0 (2026-08-16) 更新: 响应式窗口与DPI适配
