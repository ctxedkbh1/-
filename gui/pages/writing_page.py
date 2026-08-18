import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton,
                               QSplitter, QVBoxLayout, QWidget)

from gui.pages.evidence_page import EvidenceDialog
from gui.widgets import LinkBrowser, Worker, ask_confirm, msg_err, msg_info, msg_warn


class WritingPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self._current_idx = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        title = QLabel("第六阶段：分章节写作")
        title.setObjectName("pageTitle")
        lay.addWidget(title)

        row = QHBoxLayout()
        self.btn_gen = QPushButton("生成本章")
        self.btn_gen.setObjectName("primary")
        self.btn_regen = QPushButton("重新生成")
        self.btn_confirm = QPushButton("确认本章")
        self.btn_next = QPushButton("下一章")
        self.btn_auto = QPushButton("自动生成剩余章节")
        self.btn_annotate = QPushButton("添加批注")
        self.chk_review = QCheckBox("生成后 AI 复查本章")
        for b in (self.btn_gen, self.btn_regen, self.btn_confirm, self.btn_next,
                  self.btn_auto, self.btn_annotate):
            row.addWidget(b)
        row.addWidget(self.chk_review)
        row.addStretch(1)
        lay.addLayout(row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.chapter_list = QListWidget()
        self.chapter_list.setMinimumWidth(160)
        self.chapter_list.currentRowChanged.connect(self.on_select)
        splitter.addWidget(self.chapter_list)

        right = QSplitter(Qt.Orientation.Vertical)
        self.view = LinkBrowser()
        self.view.setPlaceholderText("生成的章节将在此显示，点击 [E编号] 查看证据，点击 [N编号] 查看批注。")
        right.addWidget(self.view)
        self.check_panel = QPlainTextEdit()
        self.check_panel.setReadOnly(True)
        self.check_panel.setMinimumHeight(80)
        self.check_panel.setPlaceholderText("本章检查结果：引用检查 / 证据检查 / 事实检查 / 逻辑检查……")
        right.addWidget(self.check_panel)
        splitter.addWidget(right)
        splitter.setSizes([280, 900])
        right.setSizes([520, 150])
        lay.addWidget(splitter, 1)

        self.btn_gen.clicked.connect(lambda: self.on_write())
        self.btn_regen.clicked.connect(lambda: self.on_write(force=True))
        self.btn_confirm.clicked.connect(self.on_confirm)
        self.btn_next.clicked.connect(self.on_next)
        self.btn_auto.clicked.connect(self.on_auto)
        self.btn_annotate.clicked.connect(self.on_annotate)
        self.view.link_clicked.connect(self.on_link)

    def _sections(self):
        return self.mw.project.outline().get("sections") or []

    def _status(self):
        st = self.mw.project.get("chapter_status") or {}
        return st if isinstance(st, dict) else {}

    def refresh(self):
        from core import writer as writer_mod
        sections = self._sections()
        status = self._status()
        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        for i, sec in enumerate(sections, 1):
            text = writer_mod.read_chapter(i)
            st = status.get(str(i), "")
            if st == "confirmed":
                mark = "[已确认]"
            elif text.strip():
                mark = f"[已写 {writer_mod.cjk_count(text)} 字]"
            else:
                mark = "[未写]"
            self.chapter_list.addItem(QListWidgetItem(f"{i:02d} {sec.get('title', '')} {mark}"))
        if self._current_idx >= self.chapter_list.count():
            self._current_idx = 0
        self.chapter_list.setCurrentRow(self._current_idx)
        self.chapter_list.blockSignals(False)
        self.on_select(self._current_idx)

    def on_select(self, row):
        if row < 0:
            return
        self._current_idx = row
        from core import writer as writer_mod
        text = writer_mod.read_chapter(row + 1)
        self.view.show_rich(text if text.strip() else "本章尚未生成。点击【生成本章】开始。")

    def on_link(self, eid):
        rec = self.mw.evidence.get(eid)
        if rec:
            EvidenceDialog(self, record=rec, readonly=True).exec()
            return
        from core.annotations import AnnotationStore
        ann_store = AnnotationStore()
        ann_store.sync_legacy_evidence(self.mw.evidence)
        record = ann_store.get_by_label(eid)
        if record:
            from gui.pages.annotation_page import AnnotationDialog
            AnnotationDialog(self, store=ann_store, record=record, readonly=True).exec()
            return
        msg_warn(self, f"记录库中不存在 {eid}。")

    def on_annotate(self):
        cursor = self.view.textCursor()
        selected_raw = cursor.selectedText().replace("\u2028", "\n").replace("\u2029", "\n")
        selected = selected_raw.strip()
        if not selected:
            msg_warn(self, "请先在本章正文中选中要批注的文字。")
            return
        from core import writer as writer_mod
        chapter_index = self._current_idx + 1
        original = writer_mod.read_chapter(chapter_index)
        plain = self.view.toPlainText().replace("\u2028", "\n").replace("\u2029", "\n")
        before = plain[:cursor.selectionStart()]
        occurrence = max(0, before.count(selected))
        position = -1
        start = -1
        for _ in range(occurrence + 1):
            start = original.find(selected, start + 1)
            if start < 0:
                break
            position = start
        if position < 0:
            position = original.find(selected)
        if position < 0:
            msg_warn(self, "选中的文字无法在章节源文中定位，请缩短选择范围后重试。")
            return

        from core.annotations import AnnotationStore
        from gui.pages.annotation_page import AnnotationDialog
        store = AnnotationStore()
        try:
            store.sync_legacy_evidence(self.mw.evidence)
        except RuntimeError as exc:
            msg_warn(self, str(exc), "批注数据未同步")
            return
        dlg = AnnotationDialog(self, store=store, preset_style_id="note",
                               preset_target_text=selected)
        if dlg.exec() != AnnotationDialog.DialogCode.Accepted or not dlg.record:
            return
        added = store.add(dlg.record)
        marker = store.marker_for(added)
        insert_at = position + len(selected)
        updated = original[:insert_at] + marker + original[insert_at:]
        try:
            writer_mod.save_chapter(chapter_index, updated)
        except OSError as exc:
            store.delete(added["annotation_id"])
            msg_err(self, f"批注写入失败: {exc}")
            return
        self.view.show_rich(updated)
        self._run_checks(chapter_index, updated)
        msg_info(self, f"已添加批注 {marker}。")

    def _assigned_ids(self, idx):
        sections = self._sections()
        if not (1 <= idx <= len(sections)):
            return []
        sec = sections[idx - 1]
        ids = list(sec.get("evidence_ids", []))
        for sub in sec.get("subsections", []):
            ids += sub.get("evidence_ids", [])
        return ids

    def on_write(self, force=False):
        sections = self._sections()
        if not sections:
            msg_warn(self, "请先生成大纲（第五阶段）。")
            return
        idx = self._current_idx + 1
        from core import writer as writer_mod
        existing_text = writer_mod.read_chapter(idx)
        if not force:
            if existing_text.strip():
                if not ask_confirm(self, f"第 {idx} 章已写。确认覆盖重新生成？"):
                    return
        from core.annotations import AnnotationStore, parse_annotation_markers
        annotation_store = AnnotationStore()
        try:
            annotation_store.sync_legacy_evidence(self.mw.evidence)
        except RuntimeError as exc:
            annotation_store = None
        if annotation_store and existing_text.strip():
            labels = [label for label in parse_annotation_markers(existing_text)
                      if not re.fullmatch(r"E[-_]?0*\d+", label, re.IGNORECASE)]
            records = [annotation_store.get_by_label(label) for label in labels]
            records = [record for record in records if record]
            if records:
                if not ask_confirm(self, f"本章包含 {len(records)} 条普通批注，覆盖后将同时移除这些批注记录。继续？"):
                    return
                annotation_store.delete_many([record["annotation_id"] for record in records])
        elif existing_text.strip():
            labels = [label for label in parse_annotation_markers(existing_text)
                      if not re.fullmatch(r"E[-_]?0*\d+", label, re.IGNORECASE)]
            if labels:
                msg_warn(self, "批注数据文件无法安全读取，已阻止覆盖本章以保护批注。")
                return
        self.btn_gen.setEnabled(False)
        self.btn_regen.setEnabled(False)
        self._worker = Worker(self._write, idx)
        self._worker.done.connect(lambda r: self._on_written(idx, r))
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _write(self, idx):
        from core import writer
        return writer.write_chapter(self.mw.project.info(), self.mw.project.outline(),
                                    idx, self.mw.evidence)

    def _on_written(self, idx, text):
        self.btn_gen.setEnabled(True)
        self.btn_regen.setEnabled(True)
        self.view.show_rich(text)
        self._run_checks(idx, text)
        self.refresh()

    def _on_failed(self, msg):
        self.btn_gen.setEnabled(True)
        self.btn_regen.setEnabled(True)
        msg_err(self, msg, "本章写作失败", retry=True)

    def _run_checks(self, idx, text):
        from core import writer as writer_mod
        check = writer_mod.check_chapter(text, self.mw.evidence, self._assigned_ids(idx))
        from core.annotations import AnnotationStore, parse_annotation_markers
        ann_store = AnnotationStore()
        ann_store.sync_legacy_evidence(self.mw.evidence)
        ann_labels = [
            label for label in parse_annotation_markers(text)
            if not re.fullmatch(r"E[-_]?0*\d+", label, re.IGNORECASE)
        ]
        unresolved_annotations = [label for label in ann_labels if not ann_store.get_by_label(label)]
        lines = [f"第 {idx} 章检查结果：",
                 f"- 引用检查：引用证据 {check['cited'] or '（无引用）'}；"
                 + ("未知编号 " + "、".join(check["unknown"]) if check["unknown"] else "全部存在"),
                 f"- 证据检查：本章分配但未使用的证据 {check['unused_assigned'] or '无'}",
                 f"- 事实检查：无来源套话 {check['no_source_phrases'] or '无'}；"
                 f"模板化表达 {check['template_phrases'] or '无'}",
                 f"- 重复检查：重复句子 {len(check['repeats'])} 处",
                 f"- 批注检查：{ann_labels or '无'}"
                 + ("；未登记 " + "、".join(unresolved_annotations) if unresolved_annotations else "；全部已登记"),
                 f"- 字数：{check['words']} 字"]
        self.check_panel.setPlainText("\n".join(lines))
        if self.chk_review.isChecked():
            self._run_ai_review(idx, text)

    def _run_ai_review(self, idx, text):
        from core import writer as writer_mod
        sections = self._sections()
        sec_title = sections[idx - 1].get("title", "") if idx <= len(sections) else ""
        self._worker2 = Worker(writer_mod.ai_review_chapter, text, self.mw.evidence, sec_title)
        self._worker2.done.connect(lambda r: self._on_review(idx, r))
        self._worker2.failed.connect(lambda m: msg_warn(self, f"AI 复查失败: {m}"))
        self._worker2.start()

    def _on_review(self, idx, result):
        if result.get("ok") and not result.get("issues"):
            self.check_panel.appendPlainText("- 逻辑检查（AI）：通过")
            return
        self.check_panel.appendPlainText("- 逻辑检查（AI）：存在问题")
        for it in result.get("issues", []):
            self.check_panel.appendPlainText(
                f"  * {it.get('problem', '')} → {it.get('suggestion', '')}")

    def on_confirm(self):
        idx = self._current_idx + 1
        from core import writer as writer_mod
        if not writer_mod.read_chapter(idx).strip():
            msg_warn(self, f"第 {idx} 章尚未生成。")
            return
        status = self._status()
        status[str(idx)] = "confirmed"
        self.mw.project.set("chapter_status", status)
        from core import log
        log.get().info("章节已确认 index=%d", idx)
        self.refresh()
        msg_info(self, f"第 {idx} 章已确认。")

    def on_next(self):
        if self._current_idx + 1 < self.chapter_list.count():
            self.chapter_list.setCurrentRow(self._current_idx + 1)

    def on_auto(self):
        from core import writer as writer_mod
        sections = self._sections()
        if not sections:
            msg_warn(self, "请先生成大纲。")
            return
        todo = [i for i in range(1, len(sections) + 1)
                if not writer_mod.read_chapter(i).strip()]
        if not todo:
            msg_info(self, "所有章节均已生成。")
            return
        if not ask_confirm(self, f"将依次自动生成 {len(todo)} 章（第 {'、'.join(map(str, todo))} 章），"
                                 "每章生成后自动保存并检查。继续？"):
            return
        self._auto_queue = todo
        self._auto_next()

    def _auto_next(self):
        if not self._auto_queue:
            msg_info(self, "自动生成完成。请逐章检查后点击【确认本章】。")
            self.refresh()
            return
        idx = self._auto_queue.pop(0)
        self.chapter_list.setCurrentRow(idx - 1)
        self._current_idx = idx - 1
        self.btn_gen.setEnabled(False)
        self.btn_regen.setEnabled(False)
        self._worker = Worker(self._write, idx)
        self._worker.done.connect(lambda r: self._auto_done(idx, r))
        self._worker.failed.connect(lambda m: (msg_err(self, m, "自动生成失败"),
                                               self.refresh()))
        self._worker.start()

    def _auto_done(self, idx, text):
        self._run_checks(idx, text)
        self.btn_gen.setEnabled(True)
        self.btn_regen.setEnabled(True)
        self._auto_next()

# 版本: v2.2.0 (2026-08-18) 更新: 批注跳转与登记检查
