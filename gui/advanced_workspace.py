import os
import re

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QGroupBox, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMenu, QMessageBox, QPlainTextEdit, QPushButton,
                               QRadioButton, QScrollArea, QSpinBox,
                               QStackedWidget, QTableWidget, QTableWidgetItem,
                               QTextBrowser, QVBoxLayout, QWidget)

from core import exporter, fact_checker, output_location, research as research_mod, \
    writer as writer_mod
from core.advanced_state import (ALIGN_LABELS, FORMAT_PRESET,
                                 AdvancedStateManager, VersionManager)
from core.exporters import FORMAT_LABELS, sanitize_filename
from core.targeted_edit import (build_format_note, edit_region, preview_html,
                                safe_apply)
from gui.pages.evidence_page import EvidenceDialog
from gui.widgets import Worker, ask_confirm, msg_err, msg_info, msg_warn

NAV_ITEMS = ["论文信息", "AI模型", "联网检索", "资料库", "论文格式",
             "数据来源", "定向修改", "质量检查", "版本管理", "导出"]

FONT_OPTIONS = ["宋体", "黑体", "楷体", "仿宋", "微软雅黑", "华文中宋"]
SIZE_OPTIONS = ["小五(9)", "五号(10.5)", "小四(12)", "四号(14)", "小三(15)",
                "三号(16)", "小二(18)", "二号(22)"]
SIZE_VALUES = [9, 10.5, 12, 14, 15, 16, 18, 22]


class AdvancedWorkspacePage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.state = AdvancedStateManager()
        self.versions = VersionManager(self.state)
        self._undo_stack = []
        self._redo_stack = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setObjectName("advNav")
        self.nav.setMinimumWidth(130)
        self.nav.setMaximumWidth(200)
        self.nav.addItems(NAV_ITEMS)
        self.nav.setStyleSheet(
            "QListWidget#advNav { background: #1d2939; color: #e6e9ef; font-size: 13px; }"
            "QListWidget#advNav::item { height: 38px; padding-left: 12px; }"
            "QListWidget#advNav::item:selected { background: #3d8bff; color: white; }")
        root.addWidget(self.nav)

        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        top.setContentsMargins(20, 10, 20, 6)
        self.title_label = QLabel("高级论文工作台")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1d2939;")
        top.addWidget(self.title_label, 1)
        self.save_state_label = QLabel("● 已保存")
        self.save_state_label.setStyleSheet("color: #039855;")
        top.addWidget(self.save_state_label)
        self.btn_save = QPushButton("保存")
        self.btn_export_top = QPushButton("导出")
        self.btn_export_top.setObjectName("primary")
        top.addWidget(self.btn_save)
        top.addWidget(self.btn_export_top)
        rlay.addLayout(top)

        self.stack = QStackedWidget()
        self.pages = [
            self._build_info_page(), self._build_ai_page(), self._build_web_page(),
            self._build_library_page(), self._build_format_page(), self._build_sources_page(),
            self._build_edit_page(), self._build_quality_page(), self._build_versions_page(),
            self._build_export_page(),
        ]
        for p in self.pages:
            self.stack.addWidget(p)
        rlay.addWidget(self.stack, 1)
        root.addWidget(right, 1)

        self.nav.currentRowChanged.connect(self._on_nav)
        self.btn_save.clicked.connect(self.on_save_all)
        self.btn_export_top.clicked.connect(lambda: self.nav.setCurrentRow(9))
        self._refresh_title()

    # ============ 通用 ============

    def refresh(self):
        self.state = AdvancedStateManager()
        self._load_info_fields()
        self._load_ai_combos()
        self._load_format_fields()
        self._load_sources()
        self._load_library()
        self._load_versions()
        self._load_queue()
        self._load_export_defaults()
        self._refresh_chapter_combo()
        self._refresh_title()
        self.save_state_label.setText("● 已保存")

    def _refresh_title(self):
        topic = self.mw.project.info().get("topic") or "（未填写题目）"
        self.title_label.setText(f"高级论文工作台　|　{topic[:40]}")

    def _on_nav(self, row):
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

    def on_save_all(self):
        self._save_info(go=False)
        self.state.save()
        self.mw.project.save()
        self.save_state_label.setText("● 已保存")
        msg_info(self, "已保存全部高级模式设置。")

    def _advanced_run(self, func, *args):
        """Run an AI operation with the advanced-mode fallback model."""
        from core import deepseek

        reference = str(self.mw.config.ai_task_model("advanced") or "auto")
        if reference == "auto":
            return func(*args)
        tasks = ("generation", "analysis", "polish", "check", "search", "summary", "quick_edit")
        overrides = {task: reference for task in tasks}
        with deepseek.get_router().service.override_models(overrides):
            return func(*args)

    def _build_scroll_page(self, content):
        wrapper = QWidget()
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return wrapper

    # ============ 1. 论文信息 ============

    def _build_info_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        box = QGroupBox("论文信息")
        form = QFormLayout(box)
        self.a_topic = QLineEdit()
        self.a_class = QLineEdit()
        self.a_name = QLineEdit()
        self.a_student_id = QLineEdit()
        self.a_school = QLineEdit()
        self.a_college = QLineEdit()
        self.a_major = QLineEdit()
        self.a_course = QLineEdit()
        self.a_teacher = QLineEdit()
        self.a_type = QComboBox()
        self.a_type.addItems(["课程论文", "毕业论文", "研究报告", "文献综述", "其他"])
        self.a_outline = QPlainTextEdit()
        self.a_outline.setMinimumHeight(90)
        self.a_outline.setPlaceholderText("论文大纲（一、二、三……，可留空由 AI 生成）")
        self.a_words = QSpinBox()
        self.a_words.setRange(500, 100000)
        self.a_words.setValue(3000)
        self.a_words.setSuffix(" 字")
        self.a_requirements = QPlainTextEdit()
        self.a_requirements.setMinimumHeight(70)
        self.a_requirements.setPlaceholderText("用户自定义要求，例如：老师要求论文必须结合中医学专业；"
                                               "必须包含三个案例；正文不少于3000字。")
        form.addRow("论文标题 *", self.a_topic)
        form.addRow("班级", self.a_class)
        form.addRow("姓名 *", self.a_name)
        form.addRow("学号", self.a_student_id)
        form.addRow("学校", self.a_school)
        form.addRow("学院", self.a_college)
        form.addRow("专业", self.a_major)
        form.addRow("课程名称", self.a_course)
        form.addRow("指导老师", self.a_teacher)
        form.addRow("论文类型", self.a_type)
        form.addRow("字数要求", self.a_words)
        form.addRow("论文大纲", self.a_outline)
        form.addRow("自定义要求", self.a_requirements)
        lay.addWidget(box)

        gen_box = QGroupBox("论文生成")
        grow = QHBoxLayout(gen_box)
        self.btn_plan = QPushButton("生成研究方案")
        self.btn_outline = QPushButton("生成论文结构")
        self.btn_write = QPushButton("逐章生成正文")
        self.btn_auto = QPushButton("使用全自动生成引擎")
        self.btn_auto.setObjectName("primary")
        for b in (self.btn_plan, self.btn_outline, self.btn_write, self.btn_auto):
            b.setMinimumHeight(34)
            grow.addWidget(b)
        grow.addStretch(1)
        lay.addWidget(gen_box)
        self.gen_status = QLabel("生成状态：—")
        lay.addWidget(self.gen_status)
        lay.addStretch(1)

        self.btn_plan.clicked.connect(self.on_generate_plan)
        self.btn_outline.clicked.connect(self.on_generate_outline)
        self.btn_write.clicked.connect(self.on_generate_chapters)
        self.btn_auto.clicked.connect(self.on_use_auto_engine)
        return self._build_scroll_page(content)

    def _load_info_fields(self):
        info = self.mw.project.info()
        self.a_topic.setText(str(info.get("topic") or ""))
        self.a_class.setText(str(info.get("class_name") or ""))
        self.a_name.setText(str(info.get("name") or ""))
        self.a_student_id.setText(str(info.get("student_id") or ""))
        self.a_school.setText(str(info.get("school") or ""))
        self.a_major.setText(str(info.get("major") or ""))
        self.a_course.setText(str(info.get("course") or ""))
        self.a_words.setValue(int(info.get("word_count") or 3000))
        extra = self.state.info_extra()
        self.a_college.setText(str(extra.get("college") or ""))
        self.a_teacher.setText(str(extra.get("teacher") or ""))
        self.a_type.setCurrentText(str(extra.get("paper_type") or "课程论文"))
        self.a_requirements.setPlainText(str(extra.get("custom_requirements") or ""))
        outline = (self.mw.project.outline() or {})
        self.a_outline.setPlainText(str(info.get("format_note") and "" or ""))
        from core import outline as outline_mod
        if outline.get("sections"):
            lines = []
            for s in outline["sections"]:
                lines.append(f"{s.get('title')}：{s.get('core_points', '')}")
                for sub in s.get("subsections", []):
                    lines.append(f"  {sub.get('title')}：{sub.get('core_points', '')}")
            self.a_outline.setPlainText("\n".join(lines))

    def _save_info(self, go=True):
        topic = self.a_topic.text().strip()
        name = self.a_name.text().strip()
        if not topic or not name:
            msg_warn(self, "论文标题与姓名为必填项。")
            return False
        self.mw.project.update_info({
            "topic": topic, "class_name": self.a_class.text().strip(),
            "name": name, "student_id": self.a_student_id.text().strip(),
            "school": self.a_school.text().strip(), "major": self.a_major.text().strip(),
            "course": self.a_course.text().strip(),
            "word_count": self.a_words.value(),
        })
        self.state.update_info_extra({
            "college": self.a_college.text().strip(),
            "teacher": self.a_teacher.text().strip(),
            "paper_type": self.a_type.currentText(),
            "custom_requirements": self.a_requirements.toPlainText().strip(),
        })
        self._refresh_title()
        self.save_state_label.setText("● 已保存")
        return True

    def on_generate_plan(self):
        if not self._save_info():
            return
        self.gen_status.setText("生成状态：正在生成研究方案……")
        self._worker = Worker(self._advanced_run, research_mod.generate_plan,
                              self.mw.project.info())
        self._worker.done.connect(self._on_plan_done)
        self._worker.failed.connect(lambda m: (self.gen_status.setText("生成状态：失败"),
                                               msg_err(self, m, "生成失败", retry=True)))
        self._worker.start()

    def _on_plan_done(self, plan):
        self.mw.project.set("research_plan", plan)
        self.gen_status.setText("生成状态：研究方案已生成（可在普通模式第二步查看）。")
        msg_info(self, "研究方案已生成。")

    def on_generate_outline(self):
        if not self._save_info():
            return
        if not self.mw.evidence.all():
            if not ask_confirm(self, "资料库为空，生成的论文结构将缺少证据支撑（正文会标注"
                                    "“暂无足够可靠资料支持该观点”）。仍要继续吗？"):
                return
        self.gen_status.setText("生成状态：正在生成论文结构……")
        from core import outline as outline_mod
        self._worker = Worker(self._advanced_run, outline_mod.generate_outline,
                              self.mw.project.info(), self.mw.evidence)
        self._worker.done.connect(self._on_outline_done)
        self._worker.failed.connect(lambda m: (self.gen_status.setText("生成状态：失败"),
                                               msg_err(self, m, "生成失败", retry=True)))
        self._worker.start()

    def _on_outline_done(self, outline):
        self.mw.project.set_outline(outline)
        self.gen_status.setText(f"生成状态：结构已生成（{len(outline.get('sections', []))} 章）。")
        self._load_info_fields()
        msg_info(self, "论文结构已生成，可点击【逐章生成正文】。")

    def on_generate_chapters(self):
        if not self._save_info():
            return
        outline = self.mw.project.outline() or {}
        sections = outline.get("sections") or []
        if not sections:
            msg_warn(self, "请先点击【生成论文结构】。")
            return
        self.btn_write.setEnabled(False)
        self.gen_status.setText("生成状态：正在逐章生成正文……")
        self._worker = Worker(self._advanced_run, self._write_all, sections)
        self._worker.done.connect(self._on_chapters_done)
        self._worker.failed.connect(lambda m: (self.btn_write.setEnabled(True),
                                               self.gen_status.setText("生成状态：失败"),
                                               msg_err(self, m, "生成失败", retry=True)))
        self._worker.start()

    def _write_all(self, sections):
        results = []
        for idx in range(1, len(sections) + 1):
            if writer_mod.read_chapter(idx).strip():
                results.append(f"第{idx}章：已存在，跳过")
                continue
            text = writer_mod.write_chapter(self.mw.project.info(),
                                            self.mw.project.outline(), idx,
                                            self.mw.evidence)
            results.append(f"第{idx}章：完成（{writer_mod.cjk_count(text)} 字）")
        return results

    def _on_chapters_done(self, results):
        self.btn_write.setEnabled(True)
        self.gen_status.setText("生成状态：" + "；".join(results))
        self.versions.snapshot_chapters("V%d" % (len(self.state.versions()) + 1),
                                        "高级模式初始生成")
        self._load_versions()
        msg_info(self, "正文生成完成，已自动保存初始版本。")

    def on_use_auto_engine(self):
        if not self._save_info():
            return
        page = self.mw.pages[1]
        page.f_topic.setText(self.a_topic.text())
        page.f_name.setText(self.a_name.text())
        page.f_class.setText(self.a_class.text())
        page.f_course.setText(self.a_course.text())
        page.f_school.setText(self.a_school.text())
        page.f_words.setValue(self.a_words.value())
        page.f_outline.setPlainText(self.a_outline.toPlainText())
        self.mw.go(1)
        msg_info(self, "已把当前论文信息带入全自动模式，点击【开始全自动生成】即可运行全自动引擎。")

    # ============ 2. AI 模型 ============

    def _build_ai_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        box = QGroupBox("任务级模型选择（自动选择 = 系统按能力路由，失败自动切换备用）")
        form = QFormLayout(box)
        self.adv_model_combos = {}
        for key, label in (("generation", "论文生成"), ("polish", "论文润色"),
                           ("search", "联网检索"), ("summary", "资料摘要"),
                           ("quick_edit", "快速修改"), ("analysis", "结构分析"),
                           ("check", "最终检查"), ("advanced", "高级模式总默认")):
            combo = QComboBox()
            self.adv_model_combos[key] = combo
            form.addRow(label, combo)
        lay.addWidget(box)
        row = QHBoxLayout()
        self.btn_mgr = QPushButton("AI 模型管理（供应商/自定义Provider/测试/方案/成本）")
        self.btn_test = QPushButton("测试当前生成模型")
        row.addWidget(self.btn_mgr)
        row.addWidget(self.btn_test)
        row.addStretch(1)
        lay.addLayout(row)
        self.model_status = QLabel()
        self.model_status.setWordWrap(True)
        lay.addWidget(self.model_status)
        lay.addStretch(1)
        self.btn_mgr.clicked.connect(self.on_open_manager)
        self.btn_test.clicked.connect(self.on_test_model)
        for key, combo in self.adv_model_combos.items():
            combo.currentIndexChanged.connect(lambda *_: self._save_ai_combos())
        return self._build_scroll_page(content)

    def _load_ai_combos(self):
        cfg = self.mw.config
        from gui.model_options import populate_model_combo

        for key, combo in self.adv_model_combos.items():
            populate_model_combo(combo, cfg, key)
        from gui.model_options import enabled_model_options
        enabled = enabled_model_options(cfg)
        self.model_status.setText("已启用模型：" +
                                  ("、".join(label for _ref, label in enabled)
                                   if enabled else "（无）"))

    def _save_ai_combos(self):
        for key, combo in self.adv_model_combos.items():
            self.mw.config.set_ai_task_model(key, combo.currentData() or "auto")
        self._load_ai_combos()

    def on_open_manager(self):
        from gui.model_center import AIModelCenterDialog
        AIModelCenterDialog(self, self.mw.config).exec()
        self._load_ai_combos()

    def on_test_model(self):
        key = self.adv_model_combos["generation"].currentData()
        if not key or key == "auto":
            msg_warn(self, "请先在【论文生成】中选择具体模型，或到模型管理中测试。")
            return
        from core.llm import ModelRouter
        self._worker = Worker(ModelRouter(self.mw.config).health_check, key)
        self._worker.done.connect(lambda r: msg_info(self, ("✓ " if r.get("ok") else "✗ ") +
                                                     r.get("message", ""), "模型测试"))
        self._worker.failed.connect(lambda m: msg_err(self, m))
        self._worker.start()

    # ============ 3. 联网检索 ============

    def _build_web_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        box = QGroupBox("联网检索")
        form = QFormLayout(box)
        self.web_enabled = QCheckBox("启用联网（关闭后论文生成不访问互联网）")
        self.web_enabled.setChecked(True)
        self.web_query = QLineEdit()
        self.web_query.setPlaceholderText("搜索关键词，例如：人工智能 大学生就业 政策")
        self.web_query.returnPressed.connect(self.on_search)
        self.web_scope_gov = QCheckBox("政府网站")
        self.web_scope_org = QCheckBox("官方机构")
        self.web_scope_acad = QCheckBox("学术资料")
        self.web_scope_zh = QCheckBox("中文网页")
        for cb in (self.web_scope_gov, self.web_scope_org, self.web_scope_acad, self.web_scope_zh):
            cb.setChecked(True)
        self.web_time = QComboBox()
        self.web_time.addItems(["不限", "近一年", "近三年", "近五年"])
        form.addRow("", self.web_enabled)
        form.addRow("搜索关键词", self.web_query)
        scope_row = QHBoxLayout()
        for cb in (self.web_scope_gov, self.web_scope_org, self.web_scope_acad, self.web_scope_zh):
            scope_row.addWidget(cb)
        scope_row.addStretch(1)
        form.addRow("检索范围", scope_row)
        form.addRow("时间范围", self.web_time)
        lay.addWidget(box)
        srow = QHBoxLayout()
        self.btn_search = QPushButton("开始检索")
        self.btn_search.setObjectName("primary")
        self.btn_refresh_web = QPushButton("刷新资料（忽略缓存）")
        srow.addWidget(self.btn_search)
        srow.addWidget(self.btn_refresh_web)
        srow.addStretch(1)
        lay.addLayout(srow)
        self.search_status = QLabel("说明：结果仅作参考资料，未经核实不能直接当作事实。")
        self.search_status.setStyleSheet("color: #667085;")
        lay.addWidget(self.search_status)
        self.web_table = QTableWidget(0, 5)
        self.web_table.setHorizontalHeaderLabels(["标题", "来源", "日期", "可信度", "URL"])
        self.web_table.horizontalHeader().setSectionResizeMode(0, __import__("PySide6.QtWidgets", fromlist=["QHeaderView"]).QHeaderView.ResizeMode.Stretch)
        self.web_table.horizontalHeader().setSectionResizeMode(4, __import__("PySide6.QtWidgets", fromlist=["QHeaderView"]).QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.web_table, 1)
        arow = QHBoxLayout()
        self.btn_view_web = QPushButton("查看")
        self.btn_add_lib = QPushButton("加入资料库")
        self.btn_exclude = QPushButton("排除")
        self.btn_copy_ref = QPushButton("复制引用信息")
        for b in (self.btn_view_web, self.btn_add_lib, self.btn_exclude, self.btn_copy_ref):
            arow.addWidget(b)
        arow.addStretch(1)
        lay.addLayout(arow)
        self.btn_search.clicked.connect(self.on_search)
        self.btn_refresh_web.clicked.connect(lambda: self.on_search(force=True))
        self.btn_view_web.clicked.connect(self.on_view_web)
        self.btn_add_lib.clicked.connect(self.on_add_library)
        self.btn_exclude.clicked.connect(self.on_exclude)
        self.btn_copy_ref.clicked.connect(self.on_copy_ref)
        self._web_results = []
        return content

    def on_search(self, force=False):
        if not self.web_enabled.isChecked():
            msg_warn(self, "联网检索已关闭。请先勾选【启用联网】。")
            return
        q = self.web_query.text().strip()
        if not q:
            msg_warn(self, "请输入搜索关键词。")
            return
        if not force:
            cached = self.state.cache_get(q)
            if cached:
                self._web_results = cached.get("results", [])
                self._fill_web_table()
                self.search_status.setText(f"使用缓存结果（{cached.get('at')}）。点击【刷新资料】重新搜索。")
                return
        self.btn_search.setEnabled(False)
        self.search_status.setText("正在检索……")
        self._worker = Worker(self._do_search, q)
        self._worker.done.connect(lambda r: self._on_search_done(q, r))
        self._worker.failed.connect(self._on_search_failed)
        self._worker.start()

    def _do_search(self, query):
        results = []
        seen = set()
        from sources import openalex, websearch

        def add(rec):
            key = rec.get("url") or rec.get("title", "")
            if key in seen:
                return
            seen.add(key)
            results.append(rec)

        if self.web_scope_acad.isChecked():
            try:
                for r in openalex.search(query, 6):
                    add({"title": r.get("title", ""), "source": r.get("journal") or "OpenAlex",
                         "date": str(r.get("year") or ""), "credibility": "学术",
                         "url": r.get("url") or "", "kind": "academic",
                         "abstract": r.get("abstract", "")})
            except Exception as e:
                results.append({"title": "（学术检索失败，请重试）", "source": "OpenAlex",
                                "date": "", "credibility": "—", "url": "",
                                "kind": "error", "abstract": str(e)})
        if self.web_scope_gov.isChecked() or self.web_scope_org.isChecked():
            try:
                links = websearch.search_government_links(query, 5)
                for u in links:
                    add({"title": u, "source": "政府/机构网页", "date": "",
                         "credibility": "高", "url": u, "kind": "web", "abstract": ""})
            except Exception:
                pass
        if self.web_scope_zh.isChecked():
            try:
                for u in websearch.search_links(query, 5):
                    add({"title": u, "source": "网页", "date": "",
                         "credibility": "待核实", "url": u, "kind": "web", "abstract": ""})
            except Exception:
                pass
        return results

    def _on_search_done(self, query, results):
        self.btn_search.setEnabled(True)
        self._web_results = results
        self.state.cache_set(query, results)
        self._fill_web_table()
        self.search_status.setText(f"检索完成，共 {len(results)} 条。请核实后再加入资料库。")

    def _on_search_failed(self, msg):
        self.btn_search.setEnabled(True)
        self.search_status.setText("联网检索失败，请检查网络连接。")
        msg_err(self, f"联网检索失败，请检查网络连接。\n{msg}", "检索失败", retry=True)

    def _fill_web_table(self):
        self.web_table.setRowCount(len(self._web_results))
        for i, r in enumerate(self._web_results):
            cells = [r.get("title", ""), r.get("source", ""), r.get("date", ""),
                     r.get("credibility", ""), r.get("url", "")]
            for j, v in enumerate(cells):
                self.web_table.setItem(i, j, QTableWidgetItem(str(v)[:120]))

    def _selected_web(self):
        row = self.web_table.currentRow()
        if 0 <= row < len(self._web_results):
            return self._web_results[row]
        return None

    def on_view_web(self):
        r = self._selected_web()
        if not r:
            msg_warn(self, "请先选择一条结果。")
            return
        if r.get("url", "").startswith("http"):
            QDesktopServices.openUrl(QUrl(r["url"]))
        elif r.get("kind") == "academic" and r.get("abstract"):
            msg_info(self, f"标题：{r.get('title')}\n来源：{r.get('source')}\n摘要：{r.get('abstract')[:300]}",
                     "查看结果")
        else:
            msg_info(self, "该结果没有可打开的链接（不提供网址猜测）。", "查看结果")

    def on_add_library(self):
        r = self._selected_web()
        if not r:
            msg_warn(self, "请先选择一条结果。")
            return
        if r.get("kind") == "error":
            msg_warn(self, "错误条目不能加入资料库。")
            return
        eid = self.mw.evidence.add({
            "title": r.get("title", "")[:200], "source_type": "web",
            "organization": r.get("source", "网页"), "url": r.get("url", ""),
            "published_at": r.get("date", ""), "content": r.get("abstract", ""),
            "verified": r.get("credibility") in ("高", "学术"),
        })
        self._load_library()
        msg_info(self, f"已加入资料库：{eid}（生成论文时 AI 会优先参考资料库内容）。")

    def on_exclude(self):
        row = self.web_table.currentRow()
        if 0 <= row < len(self._web_results):
            self._web_results.pop(row)
            self._fill_web_table()

    def on_copy_ref(self):
        r = self._selected_web()
        if not r:
            msg_warn(self, "请先选择一条结果。")
            return
        text = f"{r.get('title', '')}. {r.get('source', '')}[EB/OL]. ({r.get('date', '')})" \
               f"[引用日期 2026-01-01]. {r.get('url', '')}."
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        msg_info(self, "引用信息已复制到剪贴板。")

    # ============ 4. 资料库 ============

    def _build_library_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        tip = QLabel("论文资料库 = 证据库。论文生成时 AI 只能引用这里的真实资料并标注 [E编号]，"
                     "资料不足处会写“暂无足够可靠资料支持该观点”。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)
        row = QHBoxLayout()
        self.btn_add_ev = QPushButton("添加资料（含 CNKI 文献）")
        self.btn_view_ev = QPushButton("查看来源")
        self.btn_open_ev = QPushButton("打开链接")
        self.btn_del_ev = QPushButton("移除")
        row.addWidget(self.btn_add_ev)
        row.addWidget(self.btn_view_ev)
        row.addWidget(self.btn_open_ev)
        row.addWidget(self.btn_del_ev)
        row.addStretch(1)
        lay.addLayout(row)
        self.lib_table = QTableWidget(0, 5)
        self.lib_table.setHorizontalHeaderLabels(["编号", "标题", "来源", "时间", "状态"])
        self.lib_table.horizontalHeader().setSectionResizeMode(1, __import__("PySide6.QtWidgets", fromlist=["QHeaderView"]).QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.lib_table, 1)
        self.btn_add_ev.clicked.connect(self.on_add_evidence)
        self.btn_view_ev.clicked.connect(self.on_view_evidence)
        self.btn_open_ev.clicked.connect(self.on_open_evidence)
        self.btn_del_ev.clicked.connect(self.on_del_evidence)
        return content

    def _load_library(self):
        self.lib_table.setRowCount(0)
        for e in self.mw.evidence.all():
            row = self.lib_table.rowCount()
            self.lib_table.insertRow(row)
            cells = [e.get("id", ""), (e.get("title") or "（无标题）")[:80],
                     e.get("organization") or e.get("journal") or e.get("source") or "",
                     e.get("published_at") or e.get("year") or "",
                     "已验证" if e.get("verified") else "未验证"]
            for j, v in enumerate(cells):
                self.lib_table.setItem(row, j, QTableWidgetItem(str(v)))

    def _selected_evidence(self):
        row = self.lib_table.currentRow()
        if row < 0:
            return None
        item = self.lib_table.item(row, 0)
        return self.mw.evidence.get(item.text()) if item else None

    def on_add_evidence(self):
        dlg = EvidenceDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.record:
            eid = self.mw.evidence.add(dlg.record)
            self._load_library()
            msg_info(self, f"已添加：{eid}")

    def on_view_evidence(self):
        e = self._selected_evidence()
        if e:
            EvidenceDialog(self, record=e, readonly=True).exec()
        else:
            msg_warn(self, "请先选择一条资料。")

    def on_open_evidence(self):
        e = self._selected_evidence()
        if not e:
            msg_warn(self, "请先选择一条资料。")
            return
        url = e.get("url") or ("https://doi.org/" + e["doi"] if e.get("doi") else "")
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            msg_warn(self, "该资料没有可打开的链接。")

    def on_del_evidence(self):
        e = self._selected_evidence()
        if not e:
            msg_warn(self, "请先选择一条资料。")
            return
        if ask_confirm(self, f"从资料库移除 {e.get('id')}？"):
            self.mw.evidence.delete(e["id"])
            self._load_library()

    # ============ 5. 论文格式 ============

    def _build_format_page(self):
        content = QWidget()
        lay = QHBoxLayout(content)
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(24, 16, 8, 16)
        preset_row = QHBoxLayout()
        self.format_name_label = QLabel(FORMAT_PRESET["name"])
        self.format_name_label.setStyleSheet("font-weight: bold;")
        preset_row.addWidget(self.format_name_label)
        self.btn_preset = QPushButton("恢复通用预设")
        preset_row.addWidget(self.btn_preset)
        preset_row.addStretch(1)
        llay.addLayout(preset_row)
        form = QFormLayout()
        self.fm_font = QComboBox()
        self.fm_font.addItems(FONT_OPTIONS)
        self.fm_latin = QComboBox()
        self.fm_latin.addItems(["Times New Roman", "Arial", "Calibri"])
        self.fm_size = QComboBox()
        for name, val in zip(SIZE_OPTIONS, SIZE_VALUES):
            self.fm_size.addItem(name, val)
        self.fm_spacing = QComboBox()
        self.fm_spacing.addItems(["1.0", "1.25", "1.5", "2.0"])
        self.fm_indent = QSpinBox()
        self.fm_indent.setRange(0, 4)
        self.fm_align = QComboBox()
        for k, v in ALIGN_LABELS.items():
            self.fm_align.addItem(v, k)
        self.fm_title_font = QComboBox()
        self.fm_title_font.addItems(FONT_OPTIONS)
        self.fm_title_size = QComboBox()
        for name, val in zip(SIZE_OPTIONS, SIZE_VALUES):
            self.fm_title_size.addItem(name, val)
        self.fm_h1_font = QComboBox()
        self.fm_h1_font.addItems(FONT_OPTIONS)
        self.fm_h1_size = QComboBox()
        for name, val in zip(SIZE_OPTIONS, SIZE_VALUES):
            self.fm_h1_size.addItem(name, val)
        self.fm_h2_size = QComboBox()
        for name, val in zip(SIZE_OPTIONS, SIZE_VALUES):
            self.fm_h2_size.addItem(name, val)
        self.fm_h3_size = QComboBox()
        for name, val in zip(SIZE_OPTIONS, SIZE_VALUES):
            self.fm_h3_size.addItem(name, val)
        self.fm_pagenum = QComboBox()
        self.fm_pagenum.addItems(["无", "底部居中"])
        self.fm_header = QLineEdit()
        self.fm_footer = QLineEdit()
        self.fm_margin = QDoubleSpinBox()
        self.fm_margin.setRange(1.0, 5.0)
        self.fm_margin.setSingleStep(0.1)
        self.fm_margin.setSuffix(" 厘米")
        form.addRow("中文字体", self.fm_font)
        form.addRow("英文字体", self.fm_latin)
        form.addRow("正文字号", self.fm_size)
        form.addRow("行距（倍）", self.fm_spacing)
        form.addRow("首行缩进（字符）", self.fm_indent)
        form.addRow("对齐方式", self.fm_align)
        form.addRow("标题字体", self.fm_title_font)
        form.addRow("标题字号", self.fm_title_size)
        form.addRow("一级标题字体", self.fm_h1_font)
        form.addRow("一级标题字号", self.fm_h1_size)
        form.addRow("二级标题字号", self.fm_h2_size)
        form.addRow("三级标题字号", self.fm_h3_size)
        form.addRow("页码", self.fm_pagenum)
        form.addRow("页眉（默认关闭）", self.fm_header)
        form.addRow("页脚", self.fm_footer)
        form.addRow("页边距", self.fm_margin)
        llay.addLayout(form)
        req_row = QHBoxLayout()
        self.fm_requirements = QLineEdit()
        self.fm_requirements.setPlaceholderText("自定义格式要求，如：正文使用宋体小四，固定值28磅。")
        self.btn_ai_parse = QPushButton("AI 解析格式要求")
        req_row.addWidget(self.fm_requirements, 1)
        req_row.addWidget(self.btn_ai_parse)
        llay.addLayout(req_row)
        self.fm_parse_status = QLabel()
        self.fm_parse_status.setStyleSheet("color: #667085;")
        llay.addWidget(self.fm_parse_status)
        llay.addStretch(1)

        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(8, 16, 24, 16)
        plabel = QLabel("格式实时预览")
        plabel.setStyleSheet("font-weight: bold;")
        rlay.addWidget(plabel)
        self.preview_browser = QTextBrowser()
        rlay.addWidget(self.preview_browser, 1)

        lay.addWidget(left, 1)
        lay.addWidget(right, 1)

        self.btn_preset.clicked.connect(self.on_reset_format)
        self.btn_ai_parse.clicked.connect(self.on_ai_parse_format)
        for w in (self.fm_font, self.fm_latin, self.fm_size, self.fm_spacing,
                  self.fm_align, self.fm_title_font, self.fm_title_size,
                  self.fm_h1_font, self.fm_h1_size, self.fm_h2_size, self.fm_h3_size,
                  self.fm_pagenum):
            w.currentIndexChanged.connect(lambda *_: self._apply_format_from_widgets())
        for w in (self.fm_indent, self.fm_margin):
            w.valueChanged.connect(lambda *_: self._apply_format_from_widgets())
        for w in (self.fm_header, self.fm_footer):
            w.textChanged.connect(lambda *_: self._apply_format_from_widgets())
        return self._build_scroll_page(content)

    def _load_format_fields(self):
        fmt = self.state.format()
        self.fm_font.setCurrentText(fmt.get("font", "宋体"))
        self.fm_latin.setCurrentText(fmt.get("latin_font", "Times New Roman"))
        self._set_combo_value(self.fm_size, fmt.get("size", 12))
        self.fm_spacing.setCurrentText(str(fmt.get("line_spacing", 1.5)))
        self.fm_indent.setValue(int(fmt.get("first_indent_chars", 2)))
        self.fm_align.setCurrentIndex(max(0, self.fm_align.findData(fmt.get("align", "justify"))))
        self.fm_title_font.setCurrentText(fmt.get("title_font", "黑体"))
        self._set_combo_value(self.fm_title_size, fmt.get("title_size", 22))
        self.fm_h1_font.setCurrentText(fmt.get("h1_font", "黑体"))
        self._set_combo_value(self.fm_h1_size, fmt.get("h1_size", 15))
        self._set_combo_value(self.fm_h2_size, fmt.get("h2_size", 14))
        self._set_combo_value(self.fm_h3_size, fmt.get("h3_size", 12))
        self.fm_pagenum.setCurrentText("底部居中" if fmt.get("page_number") == "bottom_center" else "无")
        self.fm_header.setText(fmt.get("header", ""))
        self.fm_footer.setText(fmt.get("footer", ""))
        self.fm_margin.setValue(float(fmt.get("margin_top", 2.54)))
        self._update_preview()

    @staticmethod
    def _set_combo_value(combo, value):
        idx = combo.findData(float(value)) if combo.itemData(0) is not None else -1
        if idx < 0:
            for i in range(combo.count()):
                if combo.itemData(i) is not None and abs(float(combo.itemData(i)) - float(value)) < 0.01:
                    idx = i
                    break
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _format_from_widgets(self):
        return {
            "name": self.format_name_label.text(),
            "font": self.fm_font.currentText(),
            "latin_font": self.fm_latin.currentText(),
            "size": float(self.fm_size.currentData()),
            "line_spacing": float(self.fm_spacing.currentText()),
            "first_indent_chars": self.fm_indent.value(),
            "align": self.fm_align.currentData(),
            "title_font": self.fm_title_font.currentText(),
            "title_size": float(self.fm_title_size.currentData()),
            "title_bold": True, "title_align": "center",
            "h1_font": self.fm_h1_font.currentText(),
            "h1_size": float(self.fm_h1_size.currentData()),
            "h1_bold": True, "h2_bold": True, "h3_bold": True,
            "h2_font": self.fm_h1_font.currentText(),
            "h2_size": float(self.fm_h2_size.currentData()),
            "h3_font": self.fm_h1_font.currentText(),
            "h3_size": float(self.fm_h3_size.currentData()),
            "page_number": "bottom_center" if self.fm_pagenum.currentText() == "底部居中" else "",
            "header": self.fm_header.text().strip(),
            "footer": self.fm_footer.text().strip(),
            "page": "A4", "orientation": "纵向",
            "margin_top": self.fm_margin.value(), "margin_bottom": self.fm_margin.value(),
            "margin_left": self.fm_margin.value(), "margin_right": self.fm_margin.value(),
        }

    def _apply_format_from_widgets(self):
        self.state.update_format(self._format_from_widgets())
        self._update_preview()

    def _update_preview(self):
        fmt = self.state.format()
        info = self.mw.project.info()
        self.preview_browser.setHtml(preview_html(
            fmt, {"title": info.get("topic") or "论文标题（预览）",
                  "name": info.get("name") or "姓名",
                  "school": info.get("school") or "学校"}))

    def on_reset_format(self):
        self.state.reset_format_to_preset()
        self._load_format_fields()
        msg_info(self, "已恢复中国高校通用论文格式。")

    def on_ai_parse_format(self):
        text = self.fm_requirements.text().strip()
        if not text:
            msg_warn(self, "请先输入自定义格式要求。")
            return
        from core.targeted_edit import ai_parse_format
        self.fm_parse_status.setText("正在解析……")
        self._worker = Worker(self._advanced_run, ai_parse_format, text)
        self._worker.done.connect(self._on_ai_format_parsed)
        self._worker.failed.connect(lambda m: (self.fm_parse_status.setText("解析失败"),
                                               msg_err(self, m)))
        self._worker.start()

    def _on_ai_format_parsed(self, result):
        fmt, ambiguous = result
        if not fmt:
            self.fm_parse_status.setText("解析失败：未能识别格式要求。")
            return
        if ambiguous:
            if not ask_confirm(self, "以下要求存在歧义，请确认是否按 AI 的理解应用：\n" +
                               "\n".join(f"- {a}" for a in ambiguous) +
                               "\n\n（选择「是」应用解析结果，可在界面中手动微调）"):
                self.fm_parse_status.setText("已取消应用（存在歧义，请手动设置）。")
                return
        merged = dict(self.state.format())
        merged.update({k: v for k, v in fmt.items() if v not in (None, "")})
        self.state.update_format(merged)
        self._load_format_fields()
        self.fm_parse_status.setText("✓ 已应用解析结果（请核对预览）。")

    # ============ 6. 数据来源 ============

    def _build_sources_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        box = QGroupBox("数据来源（与参考文献分开，导出时附于文末）")
        blay = QVBoxLayout(box)
        self.src_group = QButtonGroup(self)
        self.src_none = QRadioButton("不添加")
        self.src_auto = QRadioButton("自动添加（仅使用正文实际引用的真实证据，绝不虚构）")
        self.src_manual = QRadioButton("用户指定")
        self.src_none.setChecked(True)
        for rb in (self.src_none, self.src_auto, self.src_manual):
            self.src_group.addButton(rb)
            blay.addWidget(rb)
        self.src_auto_btn = QPushButton("立即从正文引用生成数据来源")
        blay.addWidget(self.src_auto_btn)
        lay.addWidget(box)
        self.src_table = QTableWidget(0, 4)
        self.src_table.setHorizontalHeaderLabels(["名称", "URL", "备注", "状态"])
        self.src_table.horizontalHeader().setSectionResizeMode(0, __import__("PySide6.QtWidgets", fromlist=["QHeaderView"]).QHeaderView.ResizeMode.Stretch)
        self.src_table.horizontalHeader().setSectionResizeMode(1, __import__("PySide6.QtWidgets", fromlist=["QHeaderView"]).QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.src_table, 1)
        mrow = QHBoxLayout()
        self.btn_src_add = QPushButton("添加来源")
        self.btn_src_del = QPushButton("删除选中")
        self.btn_src_clear = QPushButton("清空")
        for b in (self.btn_src_add, self.btn_src_del, self.btn_src_clear):
            mrow.addWidget(b)
        mrow.addStretch(1)
        lay.addLayout(mrow)
        note = QLabel("注意：无法确认来源的内容必须标记【待核实】，程序绝不虚构来源。")
        note.setStyleSheet("color: #dc6803;")
        lay.addWidget(note)
        for rb in (self.src_none, self.src_auto, self.src_manual):
            rb.toggled.connect(lambda *_: self._save_src_mode())
        self.src_auto_btn.clicked.connect(self.on_auto_sources)
        self.btn_src_add.clicked.connect(self.on_add_source)
        self.btn_src_del.clicked.connect(self.on_del_source)
        self.btn_src_clear.clicked.connect(self.on_clear_sources)
        return content

    def _load_sources(self):
        mode = self.state.data_source_mode()
        {"none": self.src_none, "auto": self.src_auto, "manual": self.src_manual}[mode].setChecked(True)
        self._fill_src_table()

    def _fill_src_table(self):
        self.src_table.setRowCount(0)
        for s in self.state.data_sources():
            row = self.src_table.rowCount()
            self.src_table.insertRow(row)
            cells = [s.get("name", ""), s.get("url", ""), s.get("note", ""),
                     "" if s.get("verified", True) else "【待核实】"]
            for j, v in enumerate(cells):
                self.src_table.setItem(row, j, QTableWidgetItem(str(v)))

    def _save_src_mode(self):
        mode = "none"
        if self.src_auto.isChecked():
            mode = "auto"
        elif self.src_manual.isChecked():
            mode = "manual"
        self.state.set("data_source_mode", mode)

    def on_auto_sources(self):
        full = exporter.build_full_text(self.mw.project)
        analysis = fact_checker.analyze(full, self.mw.evidence)
        cited = analysis.get("refs") or []
        if not cited:
            msg_warn(self, "正文中未找到引用证据。")
            return
        n = self.state.auto_data_sources_from_evidence(self.mw.evidence, cited)
        self.src_auto.setChecked(True)
        self._save_src_mode()
        self._fill_src_table()
        msg_info(self, f"已根据正文引用的真实证据生成 {n} 条数据来源（未引用的资料不会出现）。")

    def on_add_source(self):
        name, ok = QInputDialog.getText(self, "添加数据来源", "来源名称（如：国家统计局《2025年统计公报》）:")
        if not ok or not name.strip():
            return
        url, ok2 = QInputDialog.getText(self, "添加数据来源", "URL（没有可留空）:")
        url = url.strip() if ok2 else ""
        verified = ask_confirm(self, f"是否已确认该来源真实存在？\n\n{name}\n\n"
                                     "是 = 标记已验证；否 = 标记【待核实】")
        self.state.add_data_source(name.strip(), url, verified=verified)
        self.src_manual.setChecked(True)
        self._save_src_mode()
        self._fill_src_table()

    def on_del_source(self):
        row = self.src_table.currentRow()
        if 0 <= row < len(self.state.data_sources()):
            self.state.remove_data_source(row)
            self._fill_src_table()

    def on_clear_sources(self):
        if ask_confirm(self, "清空全部数据来源？"):
            self.state.clear_data_sources()
            self._fill_src_table()

    # ============ 7. 定向修改 ============

    def _build_edit_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        self.chapter_viewer = QTextBrowser()
        self.chapter_viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chapter_viewer.customContextMenuRequested.connect(self._show_chapter_menu)
        lay.addWidget(self.chapter_viewer, 1)
        row = QHBoxLayout()
        self.edit_chapter = QComboBox()
        self.edit_chapter.currentIndexChanged.connect(lambda *_: self._load_chapter_view())
        row.addWidget(QLabel("章节:"))
        row.addWidget(self.edit_chapter)
        self.btn_undo = QPushButton("撤销上次修改")
        self.btn_redo = QPushButton("重做")
        self.btn_snapshot = QPushButton("保存当前版本")
        row.addWidget(self.btn_undo)
        row.addWidget(self.btn_redo)
        row.addWidget(self.btn_snapshot)
        row.addStretch(1)
        lay.addLayout(row)
        qbox = QGroupBox("批量修改队列（按顺序执行）")
        qlay = QVBoxLayout(qbox)
        self.queue_list = QListWidget()
        qlay.addWidget(self.queue_list)
        qrow = QHBoxLayout()
        self.btn_q_add = QPushButton("添加修改任务")
        self.btn_q_run = QPushButton("执行全部队列")
        self.btn_q_clear = QPushButton("清空队列")
        qrow.addWidget(self.btn_q_add)
        qrow.addWidget(self.btn_q_run)
        qrow.addWidget(self.btn_q_clear)
        qrow.addStretch(1)
        qlay.addLayout(qrow)
        lay.addWidget(qbox)
        self.edit_status = QLabel()
        self.edit_status.setStyleSheet("color: #667085;")
        lay.addWidget(self.edit_status)
        self.btn_undo.clicked.connect(self.on_undo)
        self.btn_redo.clicked.connect(self.on_redo)
        self.btn_snapshot.clicked.connect(self.on_snapshot)
        self.btn_q_add.clicked.connect(self.on_queue_add)
        self.btn_q_run.clicked.connect(self.on_queue_run)
        self.btn_q_clear.clicked.connect(self.on_queue_clear)
        return content

    def _load_chapter_view(self):
        idx = self.edit_chapter.currentIndex() + 1
        text = writer_mod.read_chapter(idx)
        self.chapter_viewer.setPlainText(text if text.strip() else "（本章尚未生成）")

    def _refresh_chapter_combo(self):
        outline = self.mw.project.outline() or {}
        sections = outline.get("sections") or []
        self.edit_chapter.blockSignals(True)
        self.edit_chapter.clear()
        for i, s in enumerate(sections, 1):
            self.edit_chapter.addItem(f"{i:02d} {s.get('title', '')}", i)
        self.edit_chapter.blockSignals(False)
        self._load_chapter_view()

    def _current_chapter_idx(self):
        return self.edit_chapter.currentData() or 1

    def _show_chapter_menu(self, pos):
        menu = QMenu(self)
        act = menu.addAction("AI修改选中文字…")
        chosen = menu.exec(self.chapter_viewer.mapToGlobal(pos))
        if chosen is act:
            sel = self.chapter_viewer.textCursor().selectedText()
            sel = sel.replace("\u2029", "\n").strip()
            if not sel:
                msg_warn(self, "请先在正文中选中要修改的文字。")
                return
            self._open_edit_dialog(sel, is_selection=True)

    def _open_edit_dialog(self, region, is_selection=False):
        from gui.widgets import ask_confirm as _ask
        instruction, ok = QInputDialog.getText(
            self, "修改要求", "请输入修改要求（如：更加正式 / 扩写300字 / 增加案例 / 删除重复表达）:")
        if not ok or not instruction.strip():
            return
        idx = self._current_chapter_idx()
        original = writer_mod.read_chapter(idx)
        if region not in original:
            msg_warn(self, "选中内容与当前章节不一致，请重新选择。")
            return
        self.edit_status.setText("正在生成修改预览……")
        outline = self.mw.project.outline() or {}
        sections = outline.get("sections") or []
        title = sections[idx - 1].get("title", "") if idx <= len(sections) else ""
        self._worker = Worker(self._advanced_run, edit_region,
                              original, region, instruction.strip(),
                              self.mw.project.info(), title)
        self._worker.done.connect(
            lambda new_text: self._preview_result(idx, original, region, new_text,
                                                  instruction.strip()))
        self._worker.failed.connect(lambda m: (self.edit_status.setText("修改失败"),
                                               msg_err(self, m, "修改失败", retry=True)))
        self._worker.start()

    def _preview_result(self, idx, original, region, new_text, instruction):
        box = QMessageBox(self)
        box.setWindowTitle("预览修改")
        box.setText(f"原文：\n{region[:300]}\n\n修改后：\n{new_text[:300]}\n\n"
                    f"（引用编号与数字将被程序强制保护）")
        btn_accept = box.addButton("接受", QMessageBox.ButtonRole.AcceptRole)
        btn_reject = box.addButton("拒绝", QMessageBox.ButtonRole.RejectRole)
        btn_retry = box.addButton("重新修改", QMessageBox.ButtonRole.ActionRole)
        box.exec()
        if box.clickedButton() is btn_reject:
            self.edit_status.setText("已拒绝修改。")
            return
        if box.clickedButton() is btn_retry:
            self._open_edit_dialog(region)
            return
        safe = safe_apply(original, new_text)
        if safe is None:
            self.edit_status.setText("修改被拒绝：引用编号或数字发生变化。")
            msg_warn(self, "修改被程序拒绝：引用编号或数字发生了变化（保护机制，未改变原文）。")
            return
        writer_mod.save_chapter(idx, safe)
        self.state.add_history({
            "chapter": idx, "instruction": instruction,
            "before": region, "after": new_text, "model": self.mw.config.task_model("polish")})
        self._undo_stack.append({"chapter": idx, "before": region, "after": new_text})
        self._redo_stack.clear()
        self._load_chapter_view()
        self.edit_status.setText("✓ 修改已应用（可撤销）。")

    def on_undo(self):
        if not self._undo_stack:
            msg_info(self, "没有可撤销的修改。")
            return
        item = self._undo_stack.pop()
        idx = item["chapter"]
        text = writer_mod.read_chapter(idx)
        if item["after"] not in text:
            msg_warn(self, "章节内容已变化，无法撤销该次修改。")
            return
        writer_mod.save_chapter(idx, text.replace(item["after"], item["before"], 1))
        self._redo_stack.append(item)
        self._load_chapter_view()
        self.edit_status.setText("已撤销上次修改。")

    def on_redo(self):
        if not self._redo_stack:
            msg_info(self, "没有可重做的修改。")
            return
        item = self._redo_stack.pop()
        idx = item["chapter"]
        text = writer_mod.read_chapter(idx)
        if item["before"] not in text:
            msg_warn(self, "章节内容已变化，无法重做。")
            return
        writer_mod.save_chapter(idx, text.replace(item["before"], item["after"], 1))
        self._undo_stack.append(item)
        self._load_chapter_view()
        self.edit_status.setText("已重做。")

    def on_snapshot(self):
        vid = f"V{len(self.state.versions()) + 1}"
        note, ok = QInputDialog.getText(self, "保存版本", "版本说明（如：修改摘要后）:",
                                        text="手动保存")
        if not ok:
            return
        n = self.versions.snapshot_chapters(vid, note)
        self._load_versions()
        msg_info(self, f"版本 {vid} 已保存（{n} 章）。")

    def _load_queue(self):
        self.queue_list.clear()
        for q in self.state.queue():
            mark = {"pending": "待执行", "done": "✓", "failed": "✗"}.get(q.get("status"), "")
            self.queue_list.addItem(QListWidgetItem(
                f"[{q.get('id')}] 第{q.get('chapter', '?')}章：{q.get('instruction', '')[:40]} {mark}"))

    def on_queue_add(self):
        instruction, ok = QInputDialog.getText(
            self, "添加修改任务", "修改要求（如：第二章第二节增加一个实际案例）:")
        if not ok or not instruction.strip():
            return
        m = re.search(r"第([一二三四五六七八九十\d]+)章", instruction)
        chapter = 1
        if m:
            try:
                chapter = int(m.group(1)) if m.group(1).isdigit() else \
                    {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
                     "七": 7, "八": 8, "九": 9, "十": 10}.get(m.group(1), 1)
            except (ValueError, KeyError):
                chapter = 1
        self.state.add_queue_item({"chapter": chapter, "instruction": instruction.strip()})
        self._load_queue()

    def on_queue_run(self):
        queue = [q for q in self.state.queue() if q.get("status") != "done"]
        if not queue:
            msg_info(self, "队列为空或已全部执行。")
            return
        self.edit_status.setText("正在执行批量修改队列……")
        self._worker = Worker(self._advanced_run, self._run_queue, queue)
        self._worker.done.connect(lambda r: self._on_queue_done(queue, r))
        self._worker.failed.connect(lambda m: (self.edit_status.setText("队列执行失败"),
                                               msg_err(self, m, "执行失败", retry=True)))
        self._worker.start()

    def _run_queue(self, queue):
        outline = self.mw.project.outline() or {}
        sections = outline.get("sections") or []
        results = []
        for q in queue:
            idx = int(q.get("chapter", 1))
            if not (1 <= idx <= len(sections)):
                results.append((q["id"], False, "章节不存在"))
                continue
            text = writer_mod.read_chapter(idx)
            if not text.strip():
                results.append((q["id"], False, "章节未生成"))
                continue
            title = sections[idx - 1].get("title", "")
            try:
                new_text = edit_region(text, text, q["instruction"],
                                       self.mw.project.info(), title)
            except Exception as e:
                results.append((q["id"], False, str(e)))
                continue
            safe = safe_apply(text, new_text)
            if safe is None:
                results.append((q["id"], False, "引用/数字保护拒绝"))
                continue
            writer_mod.save_chapter(idx, safe)
            self.state.add_history({"chapter": idx, "instruction": q["instruction"],
                                    "before": text, "after": safe,
                                    "model": self.mw.config.task_model("polish")})
            results.append((q["id"], True, "完成"))
        return results

    def _on_queue_done(self, queue, results):
        for qid, ok, msg in results:
            self.state.set_queue_status(qid, "done" if ok else "failed", msg)
        self.edit_status.setText("；".join(f"{qid}:{msg}" for qid, ok, msg in results))
        self.versions.snapshot_chapters(f"V{len(self.state.versions()) + 1}", "批量修改后")
        self._load_queue()
        self._load_versions()
        msg_info(self, "批量修改执行完成，已自动保存新版本。")

    def on_queue_clear(self):
        self.state.clear_queue()
        self._load_queue()

    # ============ 8. 质量检查 ============

    def _build_quality_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        row = QHBoxLayout()
        self.btn_check = QPushButton("开始质量检查")
        self.btn_check.setObjectName("primary")
        self.btn_naturalize = QPushButton("重新改写（整章润色）")
        self.btn_local = QPushButton("局部修改（跳转定向修改）")
        self.btn_source_hint = QPushButton("补充真实资料（跳转联网检索）")
        row.addWidget(self.btn_check)
        row.addWidget(self.btn_naturalize)
        row.addWidget(self.btn_local)
        row.addWidget(self.btn_source_hint)
        row.addStretch(1)
        lay.addLayout(row)
        self.quality_view = QTextBrowser()
        lay.addWidget(self.quality_view, 1)
        self.btn_check.clicked.connect(self.on_quality_check)
        self.btn_naturalize.clicked.connect(self.on_naturalize)
        self.btn_local.clicked.connect(lambda: self.nav.setCurrentRow(6))
        self.btn_source_hint.clicked.connect(lambda: self.nav.setCurrentRow(2))
        return content

    def on_quality_check(self):
        self.quality_view.setPlainText("正在检查……")
        self._worker = Worker(self._advanced_run, self._run_quality)
        self._worker.done.connect(lambda r: self.quality_view.setPlainText(r))
        self._worker.failed.connect(lambda m: msg_err(self, m))
        self._worker.start()

    def _run_quality(self):
        from core import detector, style_checker
        store = self.mw.evidence
        full = exporter.build_full_text(self.mw.project)
        analysis = fact_checker.analyze(full, store)
        self.mw.project.set("check", analysis)
        stats = style_checker.structure_stats(full, len((self.mw.project.outline() or {}).get("sections", [])),
                                              self.mw.project.get("final_meta") or {})
        style = style_checker.analyze(full)
        det = detector.detect(full, style)
        wordcount = {"required": int(self.mw.project.info().get("word_count") or 3000),
                     "actual": stats.get("words", 0)}
        wordcount["ok"] = wordcount["actual"] >= wordcount["required"] * 0.85
        scores = style_checker.score(style, stats, wordcount["ok"], len(analysis.get("refs", [])))
        lines = ["# 高级模式质量检查", "",
                 "## 基础检查",
                 f"- 论文结构：{stats['sections']} 章、{stats['paragraphs']} 段、{stats['headings']} 个标题",
                 f"- 字数：{wordcount['actual']} / 要求 {wordcount['required']}（{'达标' if wordcount['ok'] else '未达标'}）",
                 f"- 引用检查：正文引用 {analysis['citation_count']} 处；"
                 + ("存在未知编号 " + str(analysis['unresolved']) if analysis['unresolved'] else "全部有效"),
                 f"- 参考文献对应：{'通过' if analysis['bidirectional_ok'] else '未通过（未使用证据: ' + str(analysis['unused']) + '）'}",
                 f"- 证据可追溯：{'✓' if not analysis['unresolved'] else '✗'}",
                 f"- 著录信息：{len(store.pending_count())} 条待完善",
                 "", "## 文本质量与原创性检查（内部分析值，非任何检测平台官方结果）",
                 f"- AI文本风险（内部分析值）：{det['ai_risk']}%",
                 f"- 重复/相似内容风险（内部分析值）：{det['repeat_risk']}%",
                 f"- 模板化表达：{style['template_score']}（{style['template_count']} 处）",
                 f"- 重复句子：{len(style['repeats'])} 组；空洞表达：{len(style['empties'])} 处",
                 f"- 综合质量：{scores.get('综合质量', '—')}/100（程序内部启发式评估）",
                 "", "## 需要核实", ""]
        unverified = []
        for i, p in enumerate(style_checker.split_paragraphs(full), 1):
            if re.search(r"\d", p) and not re.search(r"\[E\d+\]", p):
                unverified.append((i, p[:80]))
        if unverified:
            for i, p in unverified[:15]:
                lines.append(f"- 第{i}段存在数据但没有来源标注：{p}…【需要核实】")
        else:
            lines.append("- 未发现无来源数据。")
        lines += ["", "说明：程序绝不自动编造来源；请通过联网检索补充真实资料后在正文标注 [E编号]。"]
        return "\n".join(lines)

    def on_naturalize(self):
        from core import naturalizer
        idx = 1
        sections = (self.mw.project.outline() or {}).get("sections") or []
        text = writer_mod.read_chapter(idx)
        if not text.strip():
            msg_warn(self, "第 1 章尚未生成。")
            return
        self._worker = Worker(
            self._advanced_run,
            naturalizer.naturalize_chapter,
            text,
            self.mw.project.info(),
            sections[0].get("title", "") if sections else "",
        )
        self._worker.done.connect(lambda new: self._on_naturalized(idx, text, new))
        self._worker.failed.connect(lambda m: msg_err(self, m, "改写失败", retry=True))
        self._worker.start()

    def _on_naturalized(self, idx, original, new_text):
        from core.naturalizer import safe_rewrite
        safe = safe_rewrite(original, new_text)
        if safe is None:
            msg_warn(self, "改写被保护机制拒绝（引用/数字变化），未改变原文。")
            return
        writer_mod.save_chapter(idx, safe)
        msg_info(self, "第 1 章已重新改写（未改变事实与引用），可再次质量检查。")

    # ============ 9. 版本管理 ============

    def _build_versions_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        row = QHBoxLayout()
        self.btn_v_save = QPushButton("保存当前版本")
        self.btn_v_restore = QPushButton("恢复选中版本")
        self.btn_v_view = QPushButton("查看版本内容")
        self.btn_v_del = QPushButton("删除选中版本")
        row.addWidget(self.btn_v_save)
        row.addWidget(self.btn_v_restore)
        row.addWidget(self.btn_v_view)
        row.addWidget(self.btn_v_del)
        row.addStretch(1)
        lay.addLayout(row)
        self.version_list = QListWidget()
        lay.addWidget(self.version_list, 1)
        self.btn_v_save.clicked.connect(self.on_snapshot)
        self.btn_v_restore.clicked.connect(self.on_restore_version)
        self.btn_v_view.clicked.connect(self.on_view_version)
        self.btn_v_del.clicked.connect(self.on_del_version)
        return content

    def _load_versions(self):
        self.version_list.clear()
        for v in self.state.versions():
            self.version_list.addItem(QListWidgetItem(
                f"{v.get('id')}　{v.get('at')}　{v.get('note')}"))
        self.version_list.setCurrentRow(self.version_list.count() - 1)

    def _selected_version(self):
        item = self.version_list.currentItem()
        if not item:
            return None
        return item.text().split("　")[0]

    def on_restore_version(self):
        vid = self._selected_version()
        if not vid:
            msg_warn(self, "请先选择版本。")
            return
        if not ask_confirm(self, f"恢复版本 {vid}？当前章节内容将被该版本覆盖"
                                 "（建议先保存当前版本）。"):
            return
        if self.versions.restore_chapters(vid):
            msg_info(self, f"版本 {vid} 已恢复。")
        else:
            msg_warn(self, "该版本快照不存在。")

    def on_view_version(self):
        vid = self._selected_version()
        if not vid:
            msg_warn(self, "请先选择版本。")
            return
        import glob
        files = sorted(glob.glob(os.path.join(self.versions.versions_dir, vid, "*.md")))
        if not files:
            msg_warn(self, "该版本没有章节快照。")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"查看版本 {vid}")
        dlg.setMinimumSize(560, 480)
        dlay = QVBoxLayout(dlg)
        combo = QComboBox()
        combo.addItems([os.path.basename(f) for f in files])
        view = QPlainTextEdit()
        view.setReadOnly(True)

        def load(fname):
            with open(os.path.join(self.versions.versions_dir, vid, fname),
                      encoding="utf-8") as f:
                view.setPlainText(f.read())

        combo.currentTextChanged.connect(load)
        if files:
            load(os.path.basename(files[0]))
        dlay.addWidget(combo)
        dlay.addWidget(view, 1)
        dlg.exec()

    def on_del_version(self):
        vid = self._selected_version()
        if not vid:
            msg_warn(self, "请先选择版本。")
            return
        if ask_confirm(self, f"删除版本 {vid}？（章节快照将被删除，不可恢复）"):
            self.versions.delete(vid)
            self._load_versions()

    # ============ 10. 导出 ============

    def _build_export_page(self):
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        box = QGroupBox("导出格式（多选，保存到同一目录）")
        brow = QHBoxLayout(box)
        self.exp_checks = {}
        for key, label in FORMAT_LABELS.items():
            cb = QCheckBox(label)
            cb.setChecked(key in ("docx", "pdf"))
            self.exp_checks[key] = cb
            brow.addWidget(cb)
        brow.addStretch(1)
        lay.addWidget(box)
        lbox = QGroupBox("输出位置")
        lform = QFormLayout(lbox)
        self.exp_choice = QComboBox()
        for key, label in output_location.CHOICE_LABELS.items():
            self.exp_choice.addItem(label, key)
        self.exp_path = QLabel()
        self.exp_path.setStyleSheet("color: #175cd3;")
        self.btn_pick_dir = QPushButton("选择文件夹…")
        self.chk_remember = QCheckBox("记住这个位置")
        self.chk_remember.setChecked(True)
        lform.addRow("输出位置", self.exp_choice)
        lform.addRow("当前路径", self.exp_path)
        lform.addRow("", self.btn_pick_dir)
        lform.addRow("", self.chk_remember)
        lay.addWidget(lbox)
        nrow = QHBoxLayout()
        nrow.addWidget(QLabel("文件名："))
        self.exp_name = QLineEdit()
        nrow.addWidget(self.exp_name, 1)
        self.chk_date = QCheckBox("自动添加日期")
        self.chk_name = QCheckBox("自动添加姓名")
        self.chk_date.setChecked(True)
        self.chk_name.setChecked(True)
        nrow.addWidget(self.chk_date)
        nrow.addWidget(self.chk_name)
        lay.addLayout(nrow)
        erow = QHBoxLayout()
        self.btn_export = QPushButton("导出文件")
        self.btn_export.setObjectName("primary")
        self.btn_open_folder = QPushButton("打开文件夹")
        erow.addWidget(self.btn_export)
        erow.addWidget(self.btn_open_folder)
        erow.addStretch(1)
        lay.addLayout(erow)
        self.exp_status = QLabel()
        self.exp_status.setWordWrap(True)
        lay.addWidget(self.exp_status)
        lay.addStretch(1)
        self.btn_export.clicked.connect(self.on_export_advanced)
        self.btn_open_folder.clicked.connect(self._open_export_dir)
        self.btn_pick_dir.clicked.connect(self._pick_dir)
        self.exp_choice.currentIndexChanged.connect(self._update_exp_path)
        return self._build_scroll_page(content)

    def _load_export_defaults(self):
        cfg = self.mw.config
        idx = self.exp_choice.findData(cfg.get("export_choice", "default"))
        self.exp_choice.setCurrentIndex(idx if idx >= 0 else 0)
        self._custom_dir = cfg.get("export_custom_path", "")
        info = self.mw.project.info()
        self.exp_name.setText(sanitize_filename(
            f"{info.get('topic') or '论文'}_{info.get('name') or '作者'}"))
        self._update_exp_path()

    def _update_exp_path(self):
        self.exp_path.setText(output_location.preview_path(
            self.exp_choice.currentData(), getattr(self, "_custom_dir", "")))

    def _pick_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择输出文件夹", self.exp_path.text() or os.path.expanduser("~"))
        if folder:
            self._custom_dir = folder
            idx = self.exp_choice.findData("custom")
            self.exp_choice.setCurrentIndex(max(0, idx))
            self._update_exp_path()

    def _open_export_dir(self):
        d = getattr(self, "_last_dir", "") or output_location.preview_path(
            self.exp_choice.currentData(), getattr(self, "_custom_dir", ""))
        if d and os.path.isdir(d):
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))

    def on_export_advanced(self):
        formats = [k for k, cb in self.exp_checks.items() if cb.isChecked()]
        if not formats:
            msg_warn(self, "请至少选择一种导出格式。")
            return
        sections = (self.mw.project.outline() or {}).get("sections") or []
        if not any(writer_mod.read_chapter(i).strip() for i in range(1, len(sections) + 1)):
            msg_warn(self, "尚无正文，请先在【论文信息】页生成。")
            return
        directory = output_location.resolve_output_dir(
            self.exp_choice.currentData(), getattr(self, "_custom_dir", ""))
        if not os.path.isdir(directory):
            if not ask_confirm(self, f"目标文件夹不存在：\n{directory}\n\n是否创建？", "创建文件夹"):
                return
            ok, err = output_location.ensure_dir(directory)
            if not ok:
                msg_err(self, err)
                return
        writable, werr = output_location.is_writable(directory)
        if not writable:
            msg_err(self, f"无法保存文件。原因：{werr}\n请选择其他文件夹。")
            self._pick_dir()
            return
        base = sanitize_filename(self.exp_name.text().strip())
        info = self.mw.project.info()
        if self.chk_name.isChecked() and info.get("name"):
            if sanitize_filename(info["name"]) not in base:
                base += "_" + sanitize_filename(info["name"])
        if self.chk_date.isChecked():
            import datetime
            base += "_" + datetime.date.today().strftime("%Y%m%d")
        conflicts = [os.path.basename(os.path.join(directory, f"{base}.{f}"))
                     for f in formats
                     if os.path.exists(os.path.join(directory, f"{base}.{f}"))]
        rename_mode = False
        if conflicts:
            box = QMessageBox(self)
            box.setWindowTitle("检测到同名文件")
            box.setText("检测到同名文件：\n" + "\n".join(conflicts))
            btn_ren = box.addButton("自动重命名", QMessageBox.ButtonRole.AcceptRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            if box.clickedButton() is btn_ren:
                rename_mode = True
            else:
                return
        self._last_dir = directory
        if self.chk_remember.isChecked():
            self.mw.config.set("export_choice", self.exp_choice.currentData())
            self.mw.config.set("export_custom_path", getattr(self, "_custom_dir", ""))
        self.exp_status.setText("正在导出……")
        self._worker = Worker(self._advanced_run, self._do_export_advanced,
                              formats, base, directory, rename_mode)
        self._worker.done.connect(lambda r: self._on_export_advanced_done(formats, r))
        self._worker.failed.connect(lambda m: (self.exp_status.setText("导出失败"),
                                               msg_err(self, m, "导出失败", retry=True)))
        self._worker.start()

    def _do_export_advanced(self, formats, base, directory, rename_mode):
        full = exporter.build_full_text(self.mw.project)
        analysis = fact_checker.analyze(full, self.mw.evidence)
        self.mw.project.set("check", analysis)
        doc = exporter.build_document(self.mw.project, self.mw.evidence, analysis)
        doc.meta.update(self.state.info_extra())
        doc.meta["format_dict"] = self.state.format()
        doc.meta["format_note"] = build_format_note(self.state.format())
        mode = self.state.data_source_mode()
        if mode == "auto":
            cited = analysis.get("refs") or []
            self.state.auto_data_sources_from_evidence(self.mw.evidence, cited)
        if mode in ("auto", "manual"):
            doc.data_sources = self.state.data_sources()
        from core.exporters import export as export_format
        results = []
        for fmt in formats:
            path = os.path.join(directory, f"{base}.{fmt}")
            if rename_mode:
                path = output_location.unique_path(path)
            export_format(doc, fmt, path)
            results.append((fmt, path))
        return results

    def _on_export_advanced_done(self, formats, results):
        lines = [f"✓ 导出成功（{len(results)} 个文件，含当前格式设置与数据来源）："]
        for fmt, path in results:
            lines.append(f"  [{FORMAT_LABELS[fmt]}] {os.path.basename(path)}")
        self.exp_status.setText("\n".join(lines))
        self._record_history(results)
        msg_info(self, "\n".join(lines) + f"\n\n保存位置：{self._last_dir}",
                 "导出成功")

    def _record_history(self, results):
        from core.history import HistoryManager, new_task_id
        history = HistoryManager()
        tid = "A" + new_task_id()
        info = self.mw.project.info()
        input_data = {
            "topic": info.get("topic"), "name": info.get("name"),
            "class_name": info.get("class_name"), "course": info.get("course"),
            "school": info.get("school"), "word_count": info.get("word_count"),
            "mode": "advanced", "format": self.state.format().get("name", ""),
        }
        history.create(tid, input_data)
        result = {
            "paths": {},
            "rounds": 0, "ai_risk": None, "repeat_risk": None,
            "scores": {}, "target_met": True,
        }
        for fmt, path in results:
            result["paths"][fmt] = path
        history.add_files(tid, [{"name": os.path.basename(p), "path": p, "format": f}
                                for f, p in results])
        history.finalize(tid, result, {"task_id": tid, "input": input_data})
        rec = history.get(tid)
        if rec:
            rec["sources_count"] = len(self.state.data_sources())
            rec["versions"] = len(self.state.versions())
            history.save()

    def _do_refresh_advanced(self):
        self.refresh()
        self._load_export_defaults()
        self._refresh_chapter_combo()

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
