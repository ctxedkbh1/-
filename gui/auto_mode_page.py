import os

from PySide6.QtCore import QThread, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QScrollArea,
                               QSpinBox, QStackedWidget, QVBoxLayout, QWidget)

from core.auto_pipeline import STAGE_LABELS, AutoPipelineEngine
from core.checkpoint import AutoCheckpoint
from core.history import HistoryManager
from gui.widgets import ThresholdPicker, ask_confirm, msg_err, msg_info, msg_warn

STAGE_STATUS_MAP = {
    "write": "generating", "openalex": "generating", "crossref": "generating",
    "government": "generating", "topic": "generating", "outline_read": "generating",
    "queries": "generating", "structure": "generating", "info": "generating",
    "cnki": "generating", "evidence": "generating", "verify": "generating",
    "export": "generating",
    "quality": "optimizing", "naturalize": "optimizing",
    "factcheck": "checking", "factcheck2": "checking", "citations": "checking",
    "citations2": "checking", "references": "checking",
    "structure_check": "checking", "wordcount_check": "checking",
}

MARK_COLORS = {"done": "#039855", "running": "#3d8bff", "failed": "#d92d20",
               "skipped": "#dc6803", "pending": "#98a2b3"}
MARK_TEXT = {"done": "✓", "running": "▶", "failed": "✗", "skipped": "⚠", "pending": "○"}


class AutoModePage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.checkpoint = AutoCheckpoint()
        self.history = HistoryManager()
        self._engine = None
        self._thread = None
        self._paused = False
        self._creating_again = False

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        title = QLabel("全自动论文模式")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        tip = QLabel("只需填写基本信息并粘贴大纲，点击【开始全自动生成】后由程序自动完成"
                     "检索、证据库、写作、核查与输出，全过程无需手动操作。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #667085;")
        root.addWidget(tip)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_form())
        self.stack.addWidget(self._build_progress())
        self.stack.addWidget(self._build_summary())

    # ---------- 表单 ----------

    def _build_form(self):
        outer = QWidget()
        o_lay = QVBoxLayout(outer)
        o_lay.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("论文基本信息（其余信息由程序自动完成）")
        form = QFormLayout(box)
        form.setSpacing(10)
        self.f_class = QLineEdit()
        self.f_name = QLineEdit()
        self.f_topic = QLineEdit()
        self.f_course = QLineEdit()
        self.f_course.setPlaceholderText("可选")
        self.f_school = QLineEdit()
        self.f_school.setPlaceholderText("可选")
        self.f_outline = QPlainTextEdit()
        self.f_outline.setPlaceholderText(
            "粘贴你自己的论文大纲（一、二、三……）。\n留空则由 AI 根据题目与检索到的资料自动设计大纲。")
        self.f_outline.setMinimumHeight(200)
        self.f_words = QSpinBox()
        self.f_words.setRange(500, 100000)
        self.f_words.setSingleStep(100)
        self.f_words.setValue(3000)
        self.f_words.setSuffix(" 字")
        self.f_format = QComboBox()
        self.f_format.addItem("默认格式", "default")
        self.f_format.addItem("学校要求（使用论文信息中已填写的格式要求）", "school")
        form.addRow("班级", self.f_class)
        form.addRow("姓名 *", self.f_name)
        form.addRow("论文题目 *", self.f_topic)
        form.addRow("课程名称", self.f_course)
        form.addRow("学校 / 学院", self.f_school)
        form.addRow("论文大纲", self.f_outline)
        form.addRow("字数要求", self.f_words)
        form.addRow("论文格式", self.f_format)
        lay.addWidget(box)

        qbox = QGroupBox("AI 模型（自动选择 = 系统按能力路由；主模型失败自动切换备用模型）")
        mform = QFormLayout(qbox)
        mform.setSpacing(10)
        self.f_m_gen = QComboBox()
        self.f_m_ana = QComboBox()
        self.f_m_pol = QComboBox()
        self.f_m_chk = QComboBox()
        self.f_m_search = QComboBox()
        self.f_m_summary = QComboBox()
        self.f_plan = QComboBox()
        mform.addRow("论文生成", self.f_m_gen)
        mform.addRow("联网检索", self.f_m_search)
        mform.addRow("资料摘要", self.f_m_summary)
        mform.addRow("结构分析", self.f_m_ana)
        mform.addRow("文本优化", self.f_m_pol)
        mform.addRow("最终检查", self.f_m_chk)
        mform.addRow("模型方案", self.f_plan)
        mnote = QLabel("模型供应商与 API Key 在首页【设置 → AI 模型管理】中配置。")
        mnote.setStyleSheet("color: #667085;")
        mform.addRow("", mnote)
        lay.addWidget(qbox)

        obox = QGroupBox("输出位置（生成完成后直接保存到该目录）")
        oform = QFormLayout(obox)
        self.f_export_choice = QComboBox()
        from core import output_location
        for key, label in output_location.CHOICE_LABELS.items():
            self.f_export_choice.addItem(label, key)
        self.f_export_choice.currentIndexChanged.connect(self._update_export_preview)
        self.f_export_path = QLabel()
        self.f_export_path.setStyleSheet("color: #175cd3;")
        oform.addRow("输出位置", self.f_export_choice)
        oform.addRow("当前路径", self.f_export_path)
        self.btn_pick_dir = QPushButton("选择文件夹…")
        self.btn_pick_dir.clicked.connect(self._pick_export_dir)
        oform.addRow("", self.btn_pick_dir)
        lay.addWidget(obox)

        qbox2 = QGroupBox("自动质量控制（达到设定条件才判定为最终达标）")
        qform = QFormLayout(qbox)
        qform.setSpacing(10)
        self.f_ai_limit = ThresholdPicker(20)
        self.f_repeat_limit = ThresholdPicker(20)
        self.f_max_rounds = QSpinBox()
        self.f_max_rounds.setRange(1, 10)
        self.f_max_rounds.setValue(5)
        self.f_max_rounds.setSuffix(" 轮")
        qform.addRow("AI文本风险上限", self.f_ai_limit)
        qform.addRow("重复/相似内容风险上限", self.f_repeat_limit)
        qform.addRow("最大自动优化次数", self.f_max_rounds)
        qtip = QLabel("风险数值为程序内部分析估算值，非任何第三方检测平台结果。")
        qtip.setStyleSheet("color: #667085;")
        qform.addRow("", qtip)
        lay.addWidget(qbox)

        row = QHBoxLayout()
        self.btn_start = QPushButton("开始全自动生成")
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumHeight(38)
        self.btn_start.setMinimumWidth(200)
        row.addWidget(self.btn_start)
        row.addStretch(1)
        lay.addLayout(row)
        note = QLabel("说明：政府资料与 CNKI 文献可通过手动模式补充；已有 CNKI 证据会自动进入证据库。\n"
                      "程序不会绕过 CNKI 登录、验证码或访问限制，也不会编造任何资料。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #667085;")
        lay.addWidget(note)
        self.btn_start.clicked.connect(self.on_start)
        scroll.setWidget(w)
        o_lay.addWidget(scroll)
        return outer

    # ---------- 进度 ----------

    def _build_progress(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.run_label = QLabel("全自动论文生成中……")
        self.run_label.setObjectName("pageTitle")
        lay.addWidget(self.run_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        lay.addWidget(self.progress_bar)
        self.task_label = QLabel("当前任务：—")
        lay.addWidget(self.task_label)

        self.step_list = QListWidget()
        self.step_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._step_rows = {}
        for key, label in STAGE_LABELS:
            item = QListWidgetItem(f"○ {label}")
            item.setForeground(Qt.GlobalColor.gray)
            self.step_list.addItem(item)
            self._step_rows[key] = self.step_list.count() - 1
        lay.addWidget(self.step_list, 1)

        row = QHBoxLayout()
        self.btn_pause = QPushButton("暂停")
        self.btn_cancel = QPushButton("取消")
        row.addWidget(self.btn_pause)
        row.addWidget(self.btn_cancel)
        row.addStretch(1)
        lay.addLayout(row)
        self.btn_pause.clicked.connect(self.on_pause_toggle)
        self.btn_cancel.clicked.connect(self.on_cancel)
        return w

    # ---------- 完成面板 ----------

    def _build_summary(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        head = QLabel("论文生成完成")
        head.setObjectName("pageTitle")
        lay.addWidget(head)
        self.sum_labels = {}
        for key in ("factcheck", "citations", "references", "trace"):
            lbl = QLabel()
            self.sum_labels[key] = lbl
            lay.addWidget(lbl)
        self.sum_meta = QLabel()
        self.sum_meta.setWordWrap(True)
        lay.addWidget(self.sum_meta)
        self.sum_score = QLabel()
        self.sum_score.setWordWrap(True)
        self.sum_score.setStyleSheet("font-weight: bold; color: #175cd3;")
        lay.addWidget(self.sum_score)
        self.sum_target = QLabel()
        self.sum_target.setWordWrap(True)
        lay.addWidget(self.sum_target)
        self.sum_status = QLabel()
        self.sum_status.setWordWrap(True)
        lay.addWidget(self.sum_status)
        self.sum_insufficient = QLabel()
        self.sum_insufficient.setWordWrap(True)
        self.sum_insufficient.setStyleSheet("color: #dc6803;")
        lay.addWidget(self.sum_insufficient)
        row = QHBoxLayout()
        self.btn_folder = QPushButton("打开输出文件夹")
        self.btn_open_paper = QPushButton("打开论文")
        self.btn_open_report = QPushButton("查看核验报告")
        self.btn_view_log = QPushButton("查看修改记录")
        self.btn_more_fmt = QPushButton("导出其他格式")
        self.btn_restart = QPushButton("再来一篇")
        for b in (self.btn_folder, self.btn_open_paper, self.btn_open_report,
                  self.btn_view_log, self.btn_more_fmt, self.btn_restart):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        self.btn_continue = QPushButton("继续优化")
        self.btn_continue.setObjectName("primary")
        self.btn_use_current = QPushButton("使用当前版本")
        self.btn_back_edit = QPushButton("返回修改")
        for b in (self.btn_continue, self.btn_use_current, self.btn_back_edit):
            row2.addWidget(b)
        row2.addStretch(1)
        lay.addLayout(row2)
        lay.addStretch(1)
        self.btn_folder.clicked.connect(lambda: self._open_folder())
        self.btn_open_paper.clicked.connect(lambda: self._open_file("docx"))
        self.btn_open_report.clicked.connect(lambda: self._open_file("report"))
        self.btn_view_log.clicked.connect(self._show_modification_log)
        self.btn_more_fmt.clicked.connect(lambda: self.mw.go(11))
        self.btn_restart.clicked.connect(self.on_again)
        self.btn_continue.clicked.connect(self.on_continue_optimize)
        self.btn_use_current.clicked.connect(self.on_use_current)
        self.btn_back_edit.clicked.connect(self._back_to_form)
        self._last_result = None
        return w

    # ---------- 表单逻辑 ----------

    def refresh(self):
        if self._thread and self._thread.isRunning():
            return
        result = self.checkpoint.get("result")
        if result:
            self._show_summary(result)
        elif self._last_result is not None and not self.checkpoint.exists():
            self._show_summary(self._last_result)
        else:
            self.stack.setCurrentIndex(0)
        info = self.mw.project.info()
        self.f_name.setText(str(info.get("name") or ""))
        self.f_class.setText(str(info.get("class_name") or ""))
        self.f_topic.setText(str(info.get("topic") or ""))
        self.f_words.setValue(int(info.get("word_count") or 3000))
        fmt_has = bool((info.get("format_note") or "").strip() and
                       info.get("format_note") != "默认格式")
        self.f_format.model().item(1).setEnabled(fmt_has)
        if fmt_has:
            self.f_format.setCurrentIndex(1)
        cfg = self.mw.config
        self.f_ai_limit.set_value(cfg.get_int("ai_risk_limit", 20))
        self.f_repeat_limit.set_value(cfg.get_int("repeat_risk_limit", 20))
        self.f_max_rounds.setValue(max(1, min(10, cfg.get_int("max_optimization_rounds", 5))))
        self._reload_model_combos()
        self._load_export_location()

    def _load_export_location(self):
        cfg = self.mw.config
        choice = cfg.get("export_choice", "default")
        idx = self.f_export_choice.findData(choice)
        if idx >= 0:
            self.f_export_choice.setCurrentIndex(idx)
        self._custom_export_dir = cfg.get("export_custom_path", "")
        self._update_export_preview()

    def _update_export_preview(self):
        from core import output_location
        self.f_export_path.setText(output_location.preview_path(
            self.f_export_choice.currentData(), getattr(self, "_custom_export_dir", "")))

    def _pick_export_dir(self):
        from PySide6.QtWidgets import QFileDialog
        from core import output_location
        start = output_location.preview_path(
            self.f_export_choice.currentData(), getattr(self, "_custom_export_dir", ""))
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹", start)
        if folder:
            self._custom_export_dir = folder
            idx = self.f_export_choice.findData("custom")
            self.f_export_choice.setCurrentIndex(max(0, idx))
            self._update_export_preview()

    def _export_location_input(self):
        choice = self.f_export_choice.currentData()
        return {"export_choice": choice,
                "export_custom_path": getattr(self, "_custom_export_dir", "")
                if choice == "custom" else ""}

    def _reload_model_combos(self):
        cfg = self.mw.config
        from gui.model_options import populate_model_combo

        combos = {"generation": self.f_m_gen, "search": self.f_m_search,
                  "summary": self.f_m_summary, "analysis": self.f_m_ana,
                  "polish": self.f_m_pol, "check": self.f_m_chk}
        for key, combo in combos.items():
            populate_model_combo(combo, cfg, key)
        self.f_plan.blockSignals(True)
        self.f_plan.clear()
        self.f_plan.addItem("（不使用方案）", None)
        for name in cfg.plans():
            self.f_plan.addItem(name, name)
        self.f_plan.blockSignals(False)
        self.f_plan.currentIndexChanged.connect(self._on_plan_changed)

    def _on_plan_changed(self):
        name = self.f_plan.currentData()
        if not name:
            return
        plan = self.mw.config.plans().get(name) or {}
        from gui.model_options import normalize_model_choice

        mapping = {"generation": self.f_m_gen, "search": self.f_m_search,
                   "summary": self.f_m_summary, "analysis": self.f_m_ana,
                   "polish": self.f_m_pol, "check": self.f_m_chk}
        for key, combo in mapping.items():
            idx = combo.findData(normalize_model_choice(self.mw.config, plan.get(key) or "auto"))
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _task_models(self):
        return {k: c.currentData() for k, c in
                (("generation", self.f_m_gen), ("search", self.f_m_search),
                 ("summary", self.f_m_summary), ("analysis", self.f_m_ana),
                 ("polish", self.f_m_pol), ("check", self.f_m_chk))
                if c.currentData() != "auto"}

    def _back_to_form(self):
        self.stack.setCurrentIndex(0)
        self.refresh()

    # ---------- 再来一篇 ----------

    def on_again(self):
        if self._creating_again:
            return
        if self._thread and self._thread.isRunning():
            msg_warn(self, "当前有任务正在运行，请等待完成或先取消。")
            return
        source = (self.history.latest() or {}).get("input") or \
            self.checkpoint.data.get("input") or {}
        if not source:
            msg_warn(self, "没有可复用的论文参数，请填写表单后重新生成。")
            return
        self.on_again_from_input(source)

    def on_again_from_input(self, input_data):
        if self._creating_again:
            return
        if self._thread and self._thread.isRunning():
            msg_warn(self, "当前有任务正在运行，请等待完成或先取消。")
            return
        self._creating_again = True
        self.btn_restart.setEnabled(False)
        self.btn_restart.setText("正在创建…")
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        new_input = dict(input_data)
        self.checkpoint.create(new_input)
        task_id = self.checkpoint.data.get("task_id")
        self._launch()
        self.btn_restart.setEnabled(True)
        self.btn_restart.setText("再来一篇")
        self._creating_again = False
        msg_info(self, f"✓ 已创建新任务\n正在生成：《{new_input.get('topic') or '未命名'}》\n"
                       f"任务 ID：{task_id}\n\n生成进度可在本页或【论文历史】中查看。")

    def on_start(self):
        if self.checkpoint.has_unfinished():
            box = QMessageBox(self)
            box.setWindowTitle("存在未完成的全自动任务")
            box.setText("检测到上次未完成的全自动任务（已保存进度）。\n\n"
                        "选择【继续执行】将从最后成功的步骤断点继续；\n"
                        "选择【重新开始】将清除旧进度并开始新任务。")
            btn_cont = box.addButton("继续执行", QMessageBox.ButtonRole.AcceptRole)
            btn_restart = box.addButton("重新开始", QMessageBox.ButtonRole.DestructiveRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            if box.clickedButton() is btn_cont:
                self.start_resume()
                return
            if box.clickedButton() is not btn_restart:
                return
        topic = self.f_topic.text().strip()
        name = self.f_name.text().strip()
        if not topic or not name:
            msg_warn(self, "论文题目与姓名为必填项。")
            return
        user_outline = self.f_outline.toPlainText().strip()
        if not user_outline:
            if not ask_confirm(self, "未提供论文大纲。程序将根据题目与检索到的资料自动设计大纲。\n确定继续？"):
                return
        format_note = "默认格式"
        if self.f_format.currentData() == "school":
            note = (self.mw.project.info().get("format_note") or "").strip()
            format_note = note or "默认格式"
        input_data = {
            "topic": topic,
            "name": name,
            "class_name": self.f_class.text().strip() or "未填写",
            "course": self.f_course.text().strip(),
            "school": self.f_school.text().strip(),
            "word_count": self.f_words.value(),
            "format_note": format_note,
            "user_outline": user_outline,
            "ai_risk_limit": self.f_ai_limit.value(),
            "repeat_risk_limit": self.f_repeat_limit.value(),
            "max_rounds": self.f_max_rounds.value(),
            "task_models": self._task_models(),
            "plan": self.f_plan.currentData() or "",
            "export_choice": self.f_export_choice.currentData(),
            "export_custom_path": getattr(self, "_custom_export_dir", "")
            if self.f_export_choice.currentData() == "custom" else "",
        }
        self.mw.config.set("ai_risk_limit", self.f_ai_limit.value())
        self.mw.config.set("repeat_risk_limit", self.f_repeat_limit.value())
        self.mw.config.set("max_optimization_rounds", self.f_max_rounds.value())
        if not user_outline and self.mw.evidence.all() and not ask_confirm(
                self, f"证据库中已有 {len(self.mw.evidence.all())} 条资料，本次任务将继续使用。\n"
                      "（不需要可先到【4 证据库】删除）确定继续？"):
            return
        self.checkpoint.create(input_data)
        self._launch()

    def start_resume(self):
        input_data = self.checkpoint.data.get("input") or {}
        self.f_topic.setText(str(input_data.get("topic") or ""))
        self.f_name.setText(str(input_data.get("name") or ""))
        self.f_class.setText(str(input_data.get("class_name") or ""))
        self.f_course.setText(str(input_data.get("course") or ""))
        self.f_school.setText(str(input_data.get("school") or ""))
        self.f_outline.setPlainText(str(input_data.get("user_outline") or ""))
        try:
            self.f_words.setValue(int(input_data.get("word_count") or 3000))
        except (TypeError, ValueError):
            pass
        self._launch()

    def _launch(self):
        self.checkpoint.add_log("启动全自动流程（续跑）" if self.checkpoint.done_count()
                                else "启动全自动流程")
        task_id = self.checkpoint.data.get("task_id")
        if task_id:
            self.history.create(task_id, self.checkpoint.data.get("input") or {})
        self._last_result = None
        self._engine = AutoPipelineEngine(self.mw)
        self._thread = QThread(self)
        self._engine.moveToThread(self._thread)
        self._thread.started.connect(self._engine.run)
        self._engine.stage_changed.connect(self._on_stage)
        self._engine.progress.connect(self.progress_bar.setValue)
        self._engine.log_line.connect(lambda m: self.task_label.setText(f"当前任务：{m}"))
        self._engine.finished.connect(self._on_finished)
        self._engine.aborted.connect(self._on_aborted)
        self._engine.failed.connect(self._on_failed)
        for sig in (self._engine.finished, self._engine.aborted, self._engine.failed):
            sig.connect(self._thread.quit)
        self._thread.finished.connect(self._engine.deleteLater)
        self._paused = False
        self.btn_pause.setText("暂停")
        self._reset_steps()
        self.stack.setCurrentIndex(1)
        self.btn_start.setEnabled(False)
        self._thread.start()

    # ---------- 进度逻辑 ----------

    def _reset_steps(self):
        for key, row in self._step_rows.items():
            item = self.step_list.item(row)
            item.setText(f"○ {dict(STAGE_LABELS)[key]}")
            item.setForeground(Qt.GlobalColor.gray)
        self.progress_bar.setValue(0)

    def _on_stage(self, key, status):
        row = self._step_rows.get(key)
        if row is None:
            return
        item = self.step_list.item(row)
        item.setText(f"{MARK_TEXT.get(status, '○')} {dict(STAGE_LABELS)[key]}")
        from PySide6.QtGui import QColor
        item.setForeground(QColor(MARK_COLORS.get(status, "#98a2b3")))
        task_id = self.checkpoint.data.get("task_id")
        if task_id and status == "running":
            mapped = STAGE_STATUS_MAP.get(key)
            if mapped:
                self.history.update_status(task_id, mapped)
            self.history.update_stage(task_id, key, status)

    def on_pause_toggle(self):
        if not self._engine:
            return
        if self._paused:
            self._engine.controller.resume()
            self._paused = False
            self.btn_pause.setText("暂停")
            self.task_label.setText("当前任务：继续执行……")
        else:
            self._engine.controller.pause()
            self._paused = True
            self.btn_pause.setText("继续")
            self.task_label.setText("已暂停（可在步骤边界安全暂停）")

    def on_cancel(self):
        if not self._engine:
            return
        if ask_confirm(self, "确定取消本次全自动生成？已完成的步骤会保存，之后可断点继续。"):
            self._engine.controller.cancel()
            self.btn_cancel.setEnabled(False)
            self.task_label.setText("正在安全停止……")

    # ---------- 结束逻辑 ----------

    def _on_finished(self, result):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        cp = AutoCheckpoint()
        data = dict(cp.data)
        if data.get("task_id"):
            self.history.finalize(data["task_id"], result, data)
            cp.clear()
        self._last_result = result
        self._show_summary(result)
        ai_ok = result.get("ai_risk") is not None and \
            result["ai_risk"] <= result.get("ai_limit", 0)
        rep_ok = result.get("repeat_risk") is not None and \
            result["repeat_risk"] <= result.get("repeat_limit", 0)
        box = QMessageBox(self)
        box.setWindowTitle("论文生成完成")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"论文生成完成\n\n论文：{os.path.basename(result['paths'].get('docx', ''))}\n"
                    f"资料：{result['evidence_count']} 条\n"
                    f"已验证证据：{result['verified']} 条\n"
                    f"待完善文献：{result['pending']} 条\n"
                    f"事实核查：{'✓ 通过' if result['factcheck_ok'] else '存在问题'}\n"
                    f"引用检查：{'✓ 通过' if result['citations_ok'] else '存在问题'}\n"
                    f"参考文献检查：{'✓ 通过' if result['references_ok'] else '未通过'}\n"
                    f"AI文本风险：{result.get('ai_risk', '—')}% / 目标 ≤ {result.get('ai_limit', '—')}% "
                    f"{'✓' if ai_ok else '✗'}\n"
                    f"重复/相似内容风险：{result.get('repeat_risk', '—')}% / 目标 ≤ {result.get('repeat_limit', '—')}% "
                    f"{'✓' if rep_ok else '✗'}\n"
                    f"状态：{'✓ 满足用户设置的输出条件' if result.get('target_met') else '✗ 未完全达到用户设置的条件'}")
        btn_folder = box.addButton("打开输出文件夹", QMessageBox.ButtonRole.ActionRole)
        btn_paper = box.addButton("打开论文", QMessageBox.ButtonRole.ActionRole)
        btn_report = box.addButton("查看核验报告", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is btn_folder:
            self._open_folder()
        elif box.clickedButton() is btn_paper:
            self._open_file("docx")
        elif box.clickedButton() is btn_report:
            self._open_file("report")

    def _on_aborted(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        task_id = self.checkpoint.data.get("task_id")
        if task_id:
            self.history.update_status(task_id, "waiting", "已取消，可断点继续")
        msg_info(self, "任务已取消。已完成的步骤已保存，重新进入本页可断点继续。")
        self._back_to_form()

    def _on_failed(self, msg):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        cp = AutoCheckpoint()
        data = dict(cp.data)
        if data.get("task_id"):
            self.history.finalize_failed(data["task_id"], msg, data)
            cp.clear()
        msg_err(self, f"{msg}\n\n任务已保存到【论文历史】（状态：失败），可点击【再来一篇】重新生成，"
                      "不会覆盖原记录。", "全自动流程失败")
        self._back_to_form()

    def _show_summary(self, r):
        self._last_result = r
        marks = lambda ok: "✓ 通过" if ok else "存在问题"
        self.sum_labels["factcheck"].setText(f"事实核查：{marks(r['factcheck_ok'])}")
        self.sum_labels["citations"].setText(f"引用完整性：{marks(r['citations_ok'])}")
        self.sum_labels["references"].setText(f"参考文献对应：{marks(r['references_ok'])}")
        self.sum_labels["trace"].setText(f"证据可追溯：{marks(r['citations_ok'] and r['references_ok'])}")
        self.sum_meta.setText(f"著录信息：{r['pending']} 条待完善　写作质量：{r['quality']}　"
                              f"模板化表达：{r['style_level']}　优化轮数：{r['rounds']}　"
                              f"最终状态：{r['final_status']}")
        scores = r.get("scores") or {}
        if scores:
            self.sum_score.setText(
                f"综合质量：{scores.get('综合质量', '—')}/100　"
                f"结构完整度 {scores.get('结构完整度', '—')}　逻辑连贯度 {scores.get('逻辑连贯度', '—')}　"
                f"表达自然度 {scores.get('表达自然度', '—')}　格式完整度 {scores.get('格式完整度', '—')}　"
                f"重复内容风险 {scores.get('重复内容风险', '—')}")
        else:
            self.sum_score.setText("")
        target_met = bool(r.get("target_met"))
        ai_ok = r.get("ai_risk") is not None and r["ai_risk"] <= r.get("ai_limit", 0)
        rep_ok = r.get("repeat_risk") is not None and r["repeat_risk"] <= r.get("repeat_limit", 0)
        src_note = "（" + r.get("detection_source", "内部分析值") + "）"
        self.sum_target.setText(
            f"AI文本风险：{r.get('ai_risk', '—')}% / 目标 ≤ {r.get('ai_limit', '—')}% "
            f"{'✓' if ai_ok else '✗'}　|　"
            f"重复/相似内容风险：{r.get('repeat_risk', '—')}% / 目标 ≤ {r.get('repeat_limit', '—')}% "
            f"{'✓' if rep_ok else '✗'}\n" + src_note)
        if target_met:
            self.sum_status.setText("状态：✓ 满足用户设置的输出条件")
            self.sum_status.setStyleSheet("font-weight: bold; color: #039855;")
        else:
            reached = r.get("rounds", 0) >= r.get("max_rounds", 0) > 0
            self.sum_status.setText("状态：✗ 未完全达到用户设置的条件" +
                                    ("（自动优化已达到最大次数）" if reached else ""))
            self.sum_status.setStyleSheet("font-weight: bold; color: #d92d20;")
        self.btn_continue.setVisible(not target_met)
        self.btn_use_current.setVisible(not target_met)
        self.btn_back_edit.setVisible(not target_met)
        if r.get("insufficient"):
            self.sum_insufficient.setText("⚠ 资料不足章节（正文已标注“暂无足够可靠资料支持该观点”）：\n" +
                                          "、".join(r["insufficient"]))
        else:
            self.sum_insufficient.setText("")
        self.stack.setCurrentIndex(2)

    def on_continue_optimize(self):
        if not self.checkpoint.exists():
            msg_warn(self, "没有可继续优化的任务。")
            return
        if not ask_confirm(self, "将按当前设置的阈值继续定位问题段落并优化，"
                                 "最多再执行设定轮数。是否继续？"):
            return
        self.checkpoint.data.setdefault("input", {}).update({
            "ai_risk_limit": self.f_ai_limit.value(),
            "repeat_risk_limit": self.f_repeat_limit.value(),
            "max_rounds": self.f_max_rounds.value(),
            "task_models": self._task_models(),
        })
        self.checkpoint.reset_steps(["naturalize", "factcheck2", "citations2",
                                     "export", "done"])
        self.checkpoint.save()
        from core import log
        log.get().info("用户选择继续优化，已重置优化步骤")
        self._launch()

    def on_use_current(self):
        msg_info(self, "已保留当前版本。文件位于 paper_project\\output\\ 文件夹，"
                       "可点击【打开输出文件夹】查看。")

    def _show_modification_log(self):
        result = self._last_result or {}
        entries = result.get("modification_log") or []
        if not entries:
            msg_info(self, "本次生成无需修改（质量检测一次通过）。", "修改记录")
            return
        lines = ["修改记录：", ""]
        for e in entries:
            chapters = "、".join(f"第{c}章" for c in e.get("chapters", []))
            lines.append(f"第 {e.get('round')} 轮：修改 {e.get('paragraphs_modified', 0)} 个段落（{chapters}）"
                         + ("，含证据范围内扩充分析" if e.get("expand") else ""))
        r = result
        if r.get("rounds", 0) >= 5 and r.get("style_level") in ("中", "高"):
            lines += ["", "已经完成最大自动优化次数，请检查最终版本。"]
        if r.get("reverted_count"):
            lines += ["", f"另有 {r['reverted_count']} 章修改因引用/数字变化被自动撤销（未改变事实）。"]
        QMessageBox.information(self, "修改记录", "\n".join(lines))

    def _open_folder(self):
        from core import paths
        QDesktopServices.openUrl(QUrl.fromLocalFile(paths.output_dir()))

    def _open_file(self, key):
        paths = self.mw.project.get("exported_paths") or {}
        p = paths.get(key)
        if p and os.path.exists(p):
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))
        else:
            msg_warn(self, "文件不存在。")

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
