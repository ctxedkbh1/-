import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog,
                               QGroupBox, QHBoxLayout, QInputDialog, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QRadioButton,
                               QVBoxLayout, QWidget)

from core import output_location
from core.exporters import FORMAT_LABELS, sanitize_filename
from gui.widgets import Worker, ask_confirm, msg_err, msg_info, msg_warn


class ExportPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self._last_exported = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        title = QLabel("第八阶段：导出论文（多格式）")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        tip = QLabel("生成真实的标准化文件，可脱离本程序用 Word / WPS / PowerPoint / 浏览器独立打开。"
                     "支持同时导出多种格式，导出后自动验证文件结构。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)

        fmt_box = QGroupBox("输出格式（可多选，保存到同一个目录）")
        fmt_row = QHBoxLayout(fmt_box)
        self.fmt_checks = {}
        for key, label in FORMAT_LABELS.items():
            cb = QCheckBox(label)
            cb.setChecked(key == "docx")
            self.fmt_checks[key] = cb
            fmt_row.addWidget(cb)
        fmt_row.addStretch(1)
        lay.addWidget(fmt_box)

        loc_box = QGroupBox("输出位置")
        loc_lay = QVBoxLayout(loc_box)
        self.loc_group = QButtonGroup(self)
        loc_row = QHBoxLayout()
        self.loc_radios = {}
        for key, label in output_location.CHOICE_LABELS.items():
            rb = QRadioButton(label)
            self.loc_group.addButton(rb)
            rb.setProperty("loc_key", key)
            self.loc_radios[key] = rb
            loc_row.addWidget(rb)
            if key == "default":
                rb.setChecked(True)
        loc_row.addStretch(1)
        loc_lay.addLayout(loc_row)
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("当前路径："))
        self.path_label = QLabel()
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setStyleSheet("color: #175cd3;")
        path_row.addWidget(self.path_label, 1)
        self.btn_choose = QPushButton("选择文件夹…")
        self.btn_manual = QPushButton("手动输入路径")
        path_row.addWidget(self.btn_choose)
        path_row.addWidget(self.btn_manual)
        loc_lay.addLayout(path_row)
        self.chk_remember = QCheckBox("记住这个位置（下次打开程序仍使用）")
        self.chk_remember.setChecked(True)
        loc_lay.addWidget(self.chk_remember)
        lay.addWidget(loc_box)

        name_box = QGroupBox("文件命名")
        nrow = QHBoxLayout(name_box)
        nrow.addWidget(QLabel("文件名："))
        self.f_name = QLineEdit()
        nrow.addWidget(self.f_name, 1)
        nrow.addWidget(QLabel(".扩展名（自动添加）"))
        self.chk_date = QCheckBox("自动添加日期")
        self.chk_name = QCheckBox("自动添加姓名")
        self.chk_date.setChecked(True)
        self.chk_name.setChecked(True)
        nrow.addWidget(self.chk_date)
        nrow.addWidget(self.chk_name)
        lay.addWidget(name_box)

        row = QHBoxLayout()
        self.btn_export = QPushButton("开始导出")
        self.btn_export.setObjectName("primary")
        self.btn_export.setMinimumHeight(36)
        self.btn_export.setMinimumWidth(160)
        self.btn_folder = QPushButton("打开输出文件夹")
        self.btn_open_file = QPushButton("打开选中文件")
        row.addWidget(self.btn_export)
        row.addWidget(self.btn_folder)
        row.addWidget(self.btn_open_file)
        row.addStretch(1)
        lay.addLayout(row)

        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        lay.addWidget(self.result_label)

        self.exported_list = QListWidget()
        self.exported_list.setMinimumHeight(60)
        self.exported_list.itemDoubleClicked.connect(self._open_selected_export)
        lay.addWidget(self.exported_list)

        file_box = QGroupBox("默认输出文件夹中的文件（双击打开，可删除）")
        frow = QHBoxLayout(file_box)
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self._open_selected)
        frow.addWidget(self.file_list, 1)
        brow = QVBoxLayout()
        self.btn_del = QPushButton("删除选中文件")
        self.btn_del_all = QPushButton("删除全部输出")
        self.btn_refresh = QPushButton("刷新列表")
        brow.addWidget(self.btn_del)
        brow.addWidget(self.btn_del_all)
        brow.addWidget(self.btn_refresh)
        brow.addStretch(1)
        frow.addLayout(brow)
        lay.addWidget(file_box, 1)

        self.btn_export.clicked.connect(self.on_export)
        self.btn_folder.clicked.connect(self._open_folder)
        self.btn_open_file.clicked.connect(self._open_selected_export)
        self.btn_del.clicked.connect(self.on_delete_selected)
        self.btn_del_all.clicked.connect(self.on_delete_all)
        self.btn_refresh.clicked.connect(self.refresh_files)
        self.btn_choose.clicked.connect(self.on_choose_folder)
        self.btn_manual.clicked.connect(self.on_manual_path)
        self.loc_group.buttonToggled.connect(lambda *_: self._update_path_preview())

    # ---------- 数据 ----------

    def refresh(self):
        info = self.mw.project.info()
        if not self.f_name.text().strip():
            base = sanitize_filename(
                f"{info.get('topic') or '论文'}_{info.get('name') or '作者'}")
            self.f_name.setText(base)
        cfg = self.mw.config
        choice = cfg.get("export_choice", "default")
        rb = self.loc_radios.get(choice)
        if rb:
            rb.setChecked(True)
        self._custom_path = cfg.get("export_custom_path", "")
        self._update_path_preview()
        self.refresh_files()

    def _current_choice(self):
        for key, rb in self.loc_radios.items():
            if rb.isChecked():
                return key
        return "default"

    def _update_path_preview(self):
        self.path_label.setText(output_location.preview_path(
            self._current_choice(), getattr(self, "_custom_path", "")))

    def on_choose_folder(self):
        start = output_location.preview_path(self._current_choice(),
                                             getattr(self, "_custom_path", ""))
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹", start)
        if not folder:
            return
        self._custom_path = folder
        self.loc_radios["custom"].setChecked(True)
        self._update_path_preview()

    def on_manual_path(self):
        text, ok = QInputDialog.getText(self, "手动输入路径", "输出文件夹路径：",
                                        text=getattr(self, "_custom_path", ""))
        if ok and text.strip():
            self._custom_path = text.strip()
            self.loc_radios["custom"].setChecked(True)
            self._update_path_preview()

    def _remember(self, directory):
        if self.chk_remember.isChecked():
            self.mw.config.set("export_choice", self._current_choice())
            self.mw.config.set("export_custom_path", getattr(self, "_custom_path", ""))
        self.mw.config.set("last_export_dir", directory)

    def refresh_files(self):
        from core import paths
        self.file_list.clear()
        out_dir = paths.output_dir()
        if not os.path.isdir(out_dir):
            return
        for name in sorted(os.listdir(out_dir)):
            p = os.path.join(out_dir, name)
            if not os.path.isfile(p):
                continue
            item = QListWidgetItem(f"{name}（{os.path.getsize(p) // 1024} KB）")
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setToolTip(p)
            self.file_list.addItem(item)

    def _selected_path(self):
        item = self.file_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _open_selected(self):
        p = self._selected_path()
        if p and os.path.exists(p):
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))
        else:
            msg_warn(self, "请先在下方列表中选中一个文件。")

    def _open_selected_export(self):
        item = self.exported_list.currentItem()
        p = item.data(Qt.ItemDataRole.UserRole) if item else None
        if p and os.path.exists(p):
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))
        else:
            msg_warn(self, "请先在上方导出结果中选中一个文件。")

    def _open_folder(self):
        self._open_dir(getattr(self, "_last_export_dir", ""))

    def _open_dir(self, directory):
        if directory and os.path.isdir(directory):
            QDesktopServices.openUrl(QUrl.fromLocalFile(directory))
        else:
            from core import paths
            QDesktopServices.openUrl(QUrl.fromLocalFile(paths.output_dir()))

    # ---------- 删除 ----------

    def on_delete_selected(self):
        p = self._selected_path()
        if not p:
            msg_warn(self, "请先选中要删除的文件。")
            return
        if not ask_confirm(self, f"确定删除文件？\n{p}"):
            return
        try:
            os.remove(p)
            from core import log
            log.get().info("已删除输出文件 %s", p)
            self.refresh_files()
            msg_info(self, "已删除。")
        except OSError as e:
            msg_err(self, f"删除失败: {e}")

    def on_delete_all(self):
        from core import paths
        out_dir = paths.output_dir()
        files = [f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))]
        if not files:
            msg_info(self, "输出文件夹为空。")
            return
        if not ask_confirm(self, f"确定删除输出文件夹中的全部 {len(files)} 个文件？\n"
                                 "（删除后不可恢复，论文数据本身不受影响）"):
            return
        deleted = 0
        for f in files:
            try:
                os.remove(os.path.join(out_dir, f))
                deleted += 1
            except OSError:
                pass
        from core import log
        log.get().info("清空输出文件夹 删除=%d", deleted)
        self.refresh_files()
        msg_info(self, f"已删除 {deleted} 个文件。")

    # ---------- 导出 ----------

    def on_export(self):
        from core import writer as writer_mod
        sections = self.mw.project.outline().get("sections") or []
        done = [i for i in range(1, len(sections) + 1)
                if writer_mod.read_chapter(i).strip()]
        if not done:
            msg_warn(self, "尚无已写章节，请先完成写作（手动模式或全自动模式）。")
            return
        formats = [k for k, cb in self.fmt_checks.items() if cb.isChecked()]
        if not formats:
            msg_warn(self, "请至少选择一种输出格式。")
            return
        directory = output_location.resolve_output_dir(
            self._current_choice(), getattr(self, "_custom_path", ""))
        if not os.path.isdir(directory):
            if not ask_confirm(self, f"目标文件夹不存在：\n{directory}\n\n是否创建？",
                               "创建文件夹"):
                return
            ok, err = output_location.ensure_dir(directory)
            if not ok:
                msg_err(self, err, "创建失败")
                return
        writable, werr = output_location.is_writable(directory)
        if not writable:
            box = QMessageBox(self)
            box.setWindowTitle("无法保存文件")
            box.setText(f"无法保存文件。\n原因：{werr}\n\n请选择其他文件夹。")
            box.addButton("重新选择", QMessageBox.ButtonRole.AcceptRole)
            box.exec()
            self.on_choose_folder()
            return
        base = sanitize_filename(self.f_name.text().strip())
        info = self.mw.project.info()
        if self.chk_name.isChecked() and info.get("name"):
            name_part = sanitize_filename(info["name"])
            if name_part not in base:
                base = f"{base}_{name_part}"
        if self.chk_date.isChecked():
            import datetime
            base = f"{base}_{datetime.date.today().strftime('%Y%m%d')}"
        conflicts = []
        for fmt in formats:
            p = os.path.join(directory, f"{base}.{fmt}")
            if os.path.exists(p):
                conflicts.append(os.path.basename(p))
        rename_mode = False
        if conflicts:
            box = QMessageBox(self)
            box.setWindowTitle("检测到同名文件")
            box.setText("检测到同名文件：\n" + "\n".join(conflicts) +
                        "\n\n请选择处理方式：")
            btn_over = box.addButton("覆盖", QMessageBox.ButtonRole.AcceptRole)
            btn_ren = box.addButton("自动重命名", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            if box.clickedButton() is None:
                return
            if box.clickedButton() is btn_ren:
                rename_mode = True
            elif box.clickedButton() is not btn_over:
                return
        self._last_export_dir = directory
        self._rename_mode = rename_mode
        self._remember(directory)
        self.btn_export.setEnabled(False)
        self.result_label.setText("正在导出，请稍候……")
        self._worker = Worker(self._export_all, formats, base, directory, rename_mode)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _export_all(self, formats, base, directory, rename_mode):
        from core import exporter, fact_checker
        store = self.mw.evidence
        full_text = exporter.build_full_text(self.mw.project)
        analysis = self.mw.project.get("check") or fact_checker.analyze(full_text, store)
        doc = exporter.build_document(self.mw.project, store, analysis)
        from core.exporters import export as export_format
        results = []
        for fmt in formats:
            path = os.path.join(directory, f"{base}.{fmt}")
            if rename_mode:
                path = output_location.unique_path(path)
            export_format(doc, fmt, path)
            results.append((fmt, path))
        return results

    def _on_done(self, results):
        self.btn_export.setEnabled(True)
        lines = [f"✓ 导出成功，保存位置：\n{self._last_export_dir}", "", "文件："]
        self.exported_list.clear()
        for fmt, path in results:
            lines.append(f"  {os.path.basename(path)}")
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.exported_list.addItem(item)
        self.result_label.setText("\n".join(lines))
        self.refresh_files()
        self._associate_files(results)
        msg_info(self, "\n".join(lines) + "\n\n可点击【打开文件夹】或双击上方文件直接打开。",
                 "导出成功")

    def _associate_files(self, results):
        from core.history import HistoryManager
        history = HistoryManager()
        rec = history.latest()
        if rec and rec.get("status") == "completed":
            files = [{"name": os.path.basename(p), "path": p, "format": f}
                     for f, p in results]
            history.add_files(rec["task_id"], files)

    def _on_failed(self, msg):
        self.btn_export.setEnabled(True)
        self.result_label.setText("✗ 导出失败，请重试。")
        msg_err(self, f"{msg}\n\n导出失败且自动重试仍未通过验证。", "导出失败", retry=True)

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
