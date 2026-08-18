from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QPushButton,
                               QSplitter, QTextBrowser, QVBoxLayout, QWidget)

from core import exporter
from core.references.citations import CitationMap
from core.references.domain import CitationStyle
from core.references.store import ReferenceStore
from core.references.styles import format_reference
from gui.widgets import Worker, msg_err, msg_info, msg_warn
from gui.reference_zotero import ReferenceZoteroMixin
from gui.reference_notebook import ReferenceNotebookMixin
from sources.notebook import LocalDocumentImporter


class ReferenceCenterPage(ReferenceZoteroMixin, ReferenceNotebookMixin, QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.store = ReferenceStore()
        self.citations = CitationMap()
        self.worker = None
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 18)
        header = QHBoxLayout()
        title = QLabel("参考文献中心")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.import_button = QPushButton("导入本地文件")
        self.zotero_config_button = QPushButton("连接 Zotero")
        self.zotero_test_button = QPushButton("测试")
        self.zotero_button = QPushButton("同步")
        self.notebook_button = QPushButton("Notebook Enterprise")
        self.check_button = QPushButton("检查引用")
        self.import_button.clicked.connect(self._import_files)
        self.zotero_config_button.clicked.connect(self._configure_zotero)
        self.zotero_test_button.clicked.connect(self._test_zotero)
        self.zotero_button.clicked.connect(self._sync_zotero)
        self.notebook_button.clicked.connect(self._configure_notebook)
        self.check_button.clicked.connect(self._check_citations)
        header.addWidget(self.import_button)
        header.addWidget(self.zotero_config_button)
        header.addWidget(self.zotero_test_button)
        header.addWidget(self.zotero_button)
        header.addWidget(self.notebook_button)
        header.addWidget(self.check_button)
        root.addLayout(header)
        self.status = QLabel("本地文献、Zotero 与联网检索记录可统一加入论文。")
        self.status.setObjectName("muted")
        root.addWidget(self.status)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._list_panel())
        splitter.addWidget(self._detail_panel())
        splitter.setSizes([430, 650])
        root.addWidget(splitter, 1)
        self.refresh()

    def _list_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 10, 0)
        filters = QHBoxLayout()
        from PySide6.QtWidgets import QLineEdit

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索标题、作者、DOI、期刊、年份、Tags、Collection")
        self.filter = QComboBox()
        self.filter.addItem("全部", "")
        self.filter.addItem("收藏", "favorite")
        self.filter.addItem("已验证", "verified")
        filters.addWidget(self.search, 1)
        filters.addWidget(self.filter)
        layout.addLayout(filters)
        self.search.textChanged.connect(self._load_list)
        self.filter.currentIndexChanged.connect(self._load_list)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._show_reference)
        layout.addWidget(self.list, 1)
        return panel

    def _detail_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 0, 0, 0)
        tools = QHBoxLayout()
        self.style = QComboBox()
        for item, label in (
            (CitationStyle.GB_T_7714, "GB/T 7714"),
            (CitationStyle.APA, "APA"),
            (CitationStyle.MLA, "MLA"),
            (CitationStyle.CHICAGO, "Chicago"),
            (CitationStyle.IEEE, "IEEE"),
            (CitationStyle.VANCOUVER, "Vancouver"),
        ):
            self.style.addItem(label, item.value)
        self.style.currentIndexChanged.connect(self._show_reference)
        self.favorite_button = QPushButton("收藏 / 取消收藏")
        self.notebook_send_button = QPushButton("发送到 Notebook")
        self.add_button = QPushButton("加入论文证据库")
        self.add_button.setObjectName("primary")
        self.favorite_button.clicked.connect(self._toggle_favorite)
        self.notebook_send_button.clicked.connect(self._send_to_notebook)
        self.add_button.clicked.connect(self._add_to_evidence)
        tools.addWidget(QLabel("引用样式"))
        tools.addWidget(self.style)
        tools.addStretch(1)
        tools.addWidget(self.favorite_button)
        tools.addWidget(self.notebook_send_button)
        tools.addWidget(self.add_button)
        layout.addLayout(tools)
        self.details = QTextBrowser()
        layout.addWidget(self.details, 1)
        return panel

    def refresh(self):
        self.store = ReferenceStore()
        self.citations = CitationMap()
        self._load_list()

    def _load_list(self):
        items = self.store.search(self.search.text())
        mode = self.filter.currentData()
        if mode == "favorite":
            items = [item for item in items if item.favorite]
        if mode == "verified":
            items = [item for item in items if item.verified]
        items.sort(key=lambda item: (not item.favorite, item.year or "0000", item.title), reverse=False)
        self.list.clear()
        for reference in items:
            prefix = "[收藏] " if reference.favorite else ""
            item = QListWidgetItem(
                f"{prefix}{reference.title or '（无标题）'}\n"
                f"{reference.authors or '作者未知'} · {reference.year or '年份未知'} · {reference.source.value}"
            )
            item.setData(Qt.ItemDataRole.UserRole, reference.reference_id)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        else:
            self.details.setText("暂无参考文献。可导入本地文件或同步 Zotero。")

    def _show_reference(self, *_args):
        reference = self._selected()
        if not reference:
            return
        style = CitationStyle(str(self.style.currentData()))
        lines = [
            f"Reference ID：{reference.reference_id}",
            f"标题：{reference.title or '未知'}",
            f"作者：{reference.authors or '未知'}",
            f"年份：{reference.year or '未知'}",
            f"期刊：{reference.journal or '未知'}",
            f"DOI：{reference.doi or '未知'}",
            f"URL：{reference.url or '未知'}",
            f"来源：{reference.source.value}",
            f"Tags：{'、'.join(reference.tags) or '无'}",
            f"Collections：{'、'.join(reference.collections) or '无'}",
            "",
            "引用预览：",
            format_reference(reference, style),
        ]
        if reference.abstract:
            lines += ["", "摘要/内容：", reference.abstract[:3000]]
        self.details.setPlainText("\n".join(lines))

    def _import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "导入参考资料",
            "",
            "支持文件 (*.pdf *.docx *.txt *.md *.ris *.bib *.json);;所有文件 (*)",
        )
        if not paths:
            return
        imported, failed = 0, []
        importer = LocalDocumentImporter()
        for path in paths:
            try:
                self.store.upsert(importer.import_file(path))
                imported += 1
            except (OSError, ValueError, RuntimeError) as exc:
                failed.append(f"{path}: {exc}")
        self._load_list()
        self.status.setText(f"已导入 {imported} 条资料" + (f"，失败 {len(failed)} 条" if failed else ""))
        if failed:
            msg_err(self, "\n".join(failed[:10]), "部分导入失败")

    def _add_to_evidence(self):
        reference = self._selected()
        if not reference:
            return
        evidence_id = self.mw.evidence.add({
            "title": reference.title,
            "authors": reference.authors,
            "journal": reference.journal,
            "year": reference.year,
            "volume_issue_pages": reference.volume_issue_pages,
            "doi": reference.doi,
            "url": reference.url,
            "content": reference.abstract or reference.notes,
            "source_type": "manual",
            "reference_id": reference.reference_id,
            "verified": reference.verified,
        })
        from core.annotations import AnnotationStore
        annotations = AnnotationStore()
        annotations.sync_legacy_evidence(self.mw.evidence)
        self.mw.annotations = annotations
        self.citations.link(evidence_id, reference.reference_id)
        msg_info(self, f"已加入论文证据库：{evidence_id}")

    def _toggle_favorite(self):
        reference = self._selected()
        if reference:
            self.store.set_favorite(reference.reference_id, not reference.favorite)
            self._load_list()

    def _check_citations(self):
        text = exporter.build_full_text(self.mw.project)
        result = self.citations.analyze(text, self.mw.evidence, self.store)
        msg = (
            f"已映射引用：{len(result.mapping)}\n"
            f"缺失证据：{list(result.unresolved_evidence) or '无'}\n"
            f"缺失参考文献映射：{list(result.unresolved_references) or '无'}\n"
            f"未引用文献：{len(result.unused_references)}"
        )
        (msg_info if result.ok else msg_warn)(self, msg, "引用检查")

    def _selected(self):
        item = self.list.currentItem()
        reference_id = str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""
        return self.store.get(reference_id) if reference_id else None

# 版本: v2.2.0 (2026-08-18) 更新: 参考文献证据批注同步
