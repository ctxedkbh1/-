from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton,
                               QTabWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from gui.pages.evidence_page import EvidenceDialog
from gui.widgets import Worker, msg_err, msg_info, msg_warn


def _fill_table(table, records, cols, fields):
    table.setRowCount(len(records))
    for i, rec in enumerate(records):
        for j, f in enumerate(fields):
            table.setItem(i, j, QTableWidgetItem(str(rec.get(f, ""))))
    table.resizeRowsToContents()


class OpenAlexTab(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("关键词:"))
        self.query = QLineEdit()
        self.query.setPlaceholderText("中英文均可，例如: artificial intelligence employment")
        self.query.returnPressed.connect(self.on_search)
        row.addWidget(self.query, 1)
        self.btn = QPushButton("检索 OpenAlex")
        row.addWidget(self.btn)
        lay.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["标题", "作者", "期刊", "年份", "DOI"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table, 1)
        self.btn_add = QPushButton("添加选中条目到证据库")
        lay.addWidget(self.btn_add)
        self.btn.clicked.connect(self.on_search)
        self.btn_add.clicked.connect(self.on_add)
        self._records = []

    def on_search(self):
        q = self.query.text().strip()
        if not q:
            msg_warn(self, "请输入检索关键词。")
            return
        self.btn.setEnabled(False)
        from sources import openalex
        self._worker = Worker(openalex.search, q, 10)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, records):
        self.btn.setEnabled(True)
        self._records = records
        _fill_table(self.table, records, 5,
                    ["title", "authors", "journal", "year", "doi"])
        msg_info(self, f"检索到 {len(records)} 条真实文献记录，请选择需要的条目加入证据库。")

    def _on_failed(self, msg):
        self.btn.setEnabled(True)
        msg_err(self, msg, "OpenAlex 检索失败", retry=True)

    def on_add(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            msg_warn(self, "请先选择要添加的条目。")
            return
        added = []
        for i in rows:
            rec = dict(self._records[i])
            rec["content"] = rec.get("abstract") or "（无摘要，请打开来源核对后补充证据内容）"
            rec["organization"] = rec.get("journal") or ""
            added.append(self.mw.evidence.add(rec))
        from core import log
        log.get().info("OpenAlex 条目加入证据库 数量=%d", len(added))
        msg_info(self, f"已加入证据库：{'、'.join(added)}")


class CrossrefTab(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)

        g1 = QGroupBox("DOI 验证（验证文献著录信息，防止文献信息错误）")
        f1 = QHBoxLayout(g1)
        self.doi = QLineEdit()
        self.doi.setPlaceholderText("输入 DOI，例如 10.1038/nature12345")
        self.doi.returnPressed.connect(self.on_verify)
        f1.addWidget(self.doi, 1)
        self.btn_verify = QPushButton("验证 DOI")
        f1.addWidget(self.btn_verify)
        self.btn_add_doi = QPushButton("添加到证据库")
        f1.addWidget(self.btn_add_doi)
        lay.addWidget(g1)
        self.verify_view = QPlainTextEdit()
        self.verify_view.setReadOnly(True)
        self.verify_view.setMinimumHeight(80)
        lay.addWidget(self.verify_view)

        g2 = QGroupBox("关键词搜索")
        f2 = QHBoxLayout(g2)
        self.query = QLineEdit()
        self.query.setPlaceholderText("英文关键词效果更好")
        self.query.returnPressed.connect(self.on_search)
        f2.addWidget(self.query, 1)
        self.btn_search = QPushButton("搜索 Crossref")
        f2.addWidget(self.btn_search)
        lay.addWidget(g2)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["标题", "作者", "期刊", "年份", "DOI"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table, 1)
        self.btn_add = QPushButton("添加选中条目到证据库")
        lay.addWidget(self.btn_add)

        self.btn_verify.clicked.connect(self.on_verify)
        self.btn_search.clicked.connect(self.on_search)
        self.btn_add.clicked.connect(self.on_add)
        self.btn_add_doi.clicked.connect(self.on_add_doi)
        self._records = []
        self._doi_rec = None

    def on_verify(self):
        doi = self.doi.text().strip()
        if not doi:
            msg_warn(self, "请输入 DOI。")
            return
        self.btn_verify.setEnabled(False)
        from sources import crossref
        self._worker = Worker(crossref.lookup_doi, doi)
        self._worker.done.connect(self._on_verify_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_verify_done(self, rec):
        self.btn_verify.setEnabled(True)
        self._doi_rec = rec
        self.verify_view.setPlainText(
            f"标题: {rec.get('title')}\n作者: {rec.get('authors')}\n期刊: {rec.get('journal')}\n"
            f"年份: {rec.get('year')}\n卷期页: {rec.get('volume_issue_pages')}\n"
            f"DOI: {rec.get('doi')}\n出版社: {rec.get('publisher')}")
        msg_info(self, "DOI 验证成功，著录信息已显示在上方。")

    def on_add_doi(self):
        if not self._doi_rec:
            msg_warn(self, "请先验证 DOI。")
            return
        rec = dict(self._doi_rec)
        rec["content"] = rec.get("abstract") or "（无摘要，请打开来源核对后补充证据内容）"
        rec["organization"] = rec.get("journal") or ""
        eid = self.mw.evidence.add(rec)
        from core import log
        log.get().info("Crossref DOI 记录加入证据库 id=%s", eid)
        msg_info(self, f"已加入证据库：{eid}")

    def on_search(self):
        q = self.query.text().strip()
        if not q:
            msg_warn(self, "请输入检索关键词。")
            return
        self.btn_search.setEnabled(False)
        from sources import crossref
        self._worker = Worker(crossref.search, q, 10)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, records):
        self.btn_search.setEnabled(True)
        self._records = records
        _fill_table(self.table, records, 5, ["title", "authors", "journal", "year", "doi"])
        msg_info(self, f"检索到 {len(records)} 条真实文献记录。")

    def _on_failed(self, msg):
        self.btn_search.setEnabled(True)
        self.btn_verify.setEnabled(True)
        msg_err(self, msg, "Crossref 操作失败", retry=True)

    def on_add(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            msg_warn(self, "请先选择要添加的条目。")
            return
        added = []
        for i in rows:
            rec = dict(self._records[i])
            rec["content"] = rec.get("abstract") or "（无摘要，请打开来源核对后补充证据内容）"
            rec["organization"] = rec.get("journal") or ""
            added.append(self.mw.evidence.add(rec))
        from core import log
        log.get().info("Crossref 条目加入证据库 数量=%d", len(added))
        msg_info(self, f"已加入证据库：{'、'.join(added)}")


class GovTab(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        tip = QLabel("仅抓取你确认存在的网页。适合 gov.cn 等政府官网、教育部、统计局等权威页面。")
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)
        row = QHBoxLayout()
        row.addWidget(QLabel("URL:"))
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://www.stats.gov.cn/…（本工具不会猜测网址）")
        self.url.returnPressed.connect(self.on_fetch)
        row.addWidget(self.url, 1)
        self.btn_fetch = QPushButton("抓取网页")
        row.addWidget(self.btn_fetch)
        lay.addLayout(row)

        form = QFormLayout()
        self.f_title = QLineEdit()
        self.f_org = QLineEdit()
        self.f_date = QLineEdit()
        form.addRow("标题", self.f_title)
        form.addRow("发布机构", self.f_org)
        form.addRow("发布日期", self.f_date)
        lay.addLayout(form)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("抓取到的网页正文预览……")
        lay.addWidget(self.preview, 1)
        self.btn_add = QPushButton("添加到证据库")
        lay.addWidget(self.btn_add)
        self.btn_fetch.clicked.connect(self.on_fetch)
        self.btn_add.clicked.connect(self.on_add)
        self._rec = None

    def on_fetch(self):
        url = self.url.text().strip()
        if not url:
            msg_warn(self, "请输入网页 URL。")
            return
        self.btn_fetch.setEnabled(False)
        from sources import government
        self._worker = Worker(government.fetch, url)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, rec):
        self.btn_fetch.setEnabled(True)
        self._rec = rec
        self.f_title.setText(rec.get("title") or "")
        self.f_org.setText(rec.get("organization") or "")
        self.f_date.setText(rec.get("published_at") or "")
        self.preview.setPlainText((rec.get("content") or "")[:2000])
        official = "官方" if rec.get("source_type") == "government" else "普通网页"
        msg_info(self, f"抓取成功（类型：{official}）。请核对标题/机构/日期，再添加到证据库。")

    def _on_failed(self, msg):
        self.btn_fetch.setEnabled(True)
        msg_err(self, msg, "网页抓取失败", retry=True)

    def on_add(self):
        if not self._rec:
            msg_warn(self, "请先抓取网页。")
            return
        rec = dict(self._rec)
        rec["title"] = self.f_title.text().strip() or rec["title"]
        rec["organization"] = self.f_org.text().strip() or rec["organization"]
        rec["published_at"] = self.f_date.text().strip() or rec["published_at"]
        eid = self.mw.evidence.add(rec)
        from core import log
        log.get().info("网页资料加入证据库 id=%s url=%s", eid, rec.get("url"))
        msg_info(self, f"已加入证据库：{eid}")


class CnkiTab(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        tip = QLabel("不绕过 CNKI 登录、验证码或访问限制。请从知网页面复制标准引用信息手动录入，"
                     "或导入知网导出的 RIS / BibTeX / EndNote 文件。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)
        row = QHBoxLayout()
        self.btn_manual = QPushButton("手动录入 CNKI 文献")
        self.btn_manual.setObjectName("primary")
        self.btn_import = QPushButton("导入 RIS / BibTeX / TXT 文件")
        row.addWidget(self.btn_manual)
        row.addWidget(self.btn_import)
        row.addStretch(1)
        lay.addLayout(row)
        self.info = QLabel("提示：录入时请直接粘贴知网页面上的标准引用信息，避免转录错误。\n"
                           "若某条文献无法确认真实存在，请不要录入。")
        self.info.setWordWrap(True)
        self.info.setStyleSheet("color: #667085;")
        lay.addWidget(self.info)
        lay.addStretch(1)
        self.btn_manual.clicked.connect(self.on_manual)
        self.btn_import.clicked.connect(self.on_import)

    def on_manual(self):
        dlg = EvidenceDialog(self, preset_type="cnki")
        if dlg.exec() and dlg.record:
            eid = self.mw.evidence.add(dlg.record)
            from core import log
            log.get().info("CNKI 文献手动录入 id=%s", eid)
            msg_info(self, f"已加入证据库：{eid}")

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 CNKI 导出文献文件", "",
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
            msg_warn(self, "未能解析出文献记录。支持 CNKI 导出的 RIS / BibTeX 格式。")
            return
        if not msg_confirm(self, f"解析到 {len(records)} 条文献，全部加入证据库（类型标记为 CNKI）？"):
            return
        added = [self.mw.evidence.add(rec) for rec in records]
        from core import log
        log.get().info("CNKI 文献导入 数量=%d", len(added))
        msg_info(self, f"已导入：{'、'.join(added)}")


def msg_confirm(parent, text):
    from PySide6.QtWidgets import QMessageBox
    return QMessageBox.question(parent, "确认", text) == QMessageBox.StandardButton.Yes


class SearchPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        title = QLabel("第三阶段：资料检索（真实来源）")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        self.tabs = QTabWidget()
        self.tab_oa = OpenAlexTab(mw)
        self.tab_cr = CrossrefTab(mw)
        self.tab_gov = GovTab(mw)
        self.tab_cnki = CnkiTab(mw)
        self.tabs.addTab(self.tab_oa, "A. OpenAlex 学术检索")
        self.tabs.addTab(self.tab_cr, "B. Crossref 检索 / DOI 验证")
        self.tabs.addTab(self.tab_gov, "C. 政府官方网站")
        self.tabs.addTab(self.tab_cnki, "D. CNKI 手动录入 / 导入")
        lay.addWidget(self.tabs, 1)

    def refresh(self):
        pass

# 版本: v1.9.0 (2026-08-16) 更新: 响应式窗口与DPI适配
