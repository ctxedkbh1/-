import os

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QMainWindow, QMessageBox, QPushButton,
                               QScrollArea, QSpinBox, QSplitter,
                               QStackedWidget, QVBoxLayout, QWidget)

from config.manager import ConfigManager
from core import log, paths
from core.checkpoint import AutoCheckpoint
from core.annotations import AnnotationStore
from core.evidence import EvidenceStore
from core.project import Project
from gui.about_dialog import AboutDialog
from gui.advanced_workspace import AdvancedWorkspacePage
from gui.auto_mode_page import AutoModePage
from gui.pages.export_page import ExportPage
from gui.pages.evidence_page import EvidencePage
from gui.pages.factcheck_page import FactCheckPage
from gui.pages.history_page import HistoryPage
from gui.pages.home_page import HomePage
from gui.pages.info_page import InfoPage
from gui.pages.outline_page import OutlinePage
from gui.pages.annotation_page import AnnotationPage
from gui.pages.research_page import ResearchPage
from gui.pages.search_page import SearchPage
from gui.pages.writing_page import WritingPage
from gui.reference_center import ReferenceCenterPage
from gui.theme import APP_QSS


class SettingsDialog(QDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("设置 - AI 模型与自动质量控制")
        self.setMinimumSize(500, 440)
        self.resize(540, 520)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)

        api_box = QGroupBox("AI 模型（多供应商，可自由添加/切换）")
        api_lay = QVBoxLayout(api_box)
        self.model_status = QLabel()
        self.model_status.setWordWrap(True)
        api_lay.addWidget(self.model_status)
        btn_row = QHBoxLayout()
        self.btn_manage = QPushButton("进入 AI 模型中心")
        self.btn_manage.setMinimumHeight(34)
        btn_row.addWidget(self.btn_manage)
        api_lay.addLayout(btn_row)
        note = QLabel("支持 OpenAI 兼容 API、Claude、Gemini、Ollama 本地模型与自定义模型；\n"
                      "任务失败时自动切换备用模型；API Key 仅存本地配置或环境变量，不进日志。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #667085;")
        api_lay.addWidget(note)
        lay.addWidget(api_box)

        from gui.widgets import ThresholdPicker
        qg = QGroupBox("自动质量控制（检测阈值与优化次数）")
        qform = QFormLayout(qg)
        self.f_ai_limit = ThresholdPicker(cfg.get_int("ai_risk_limit", 20))
        self.f_repeat_limit = ThresholdPicker(cfg.get_int("repeat_risk_limit", 20))
        self.f_max_rounds = QSpinBox()
        self.f_max_rounds.setRange(1, 10)
        self.f_max_rounds.setValue(max(1, min(10, cfg.get_int("max_optimization_rounds", 5))))
        self.f_max_rounds.setSuffix(" 轮")
        qform.addRow("AI文本风险上限", self.f_ai_limit)
        qform.addRow("重复/相似内容风险上限", self.f_repeat_limit)
        qform.addRow("最大自动优化次数", self.f_max_rounds)
        qtip = QLabel("风险数值为程序内部分析估算值，非任何第三方检测平台结果。\n"
                      "两个风险指标均需不高于设定阈值才判定为达到输出条件。")
        qtip.setWordWrap(True)
        qtip.setStyleSheet("color: #667085;")
        qform.addRow("", qtip)
        lay.addWidget(qg)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

        exp_box = QGroupBox("默认导出设置（全自动模式与导出页的初始值）")
        eform = QFormLayout(exp_box)
        self.f_exp_choice = QComboBox()
        from core import output_location
        for key, label in output_location.CHOICE_LABELS.items():
            self.f_exp_choice.addItem(label, key)
        self.f_exp_path = QLabel()
        self.f_exp_path.setStyleSheet("color: #175cd3;")
        self.btn_pick = QPushButton("选择自定义文件夹…")
        self.f_exp_fmt = QComboBox()
        from core.exporters import FORMAT_LABELS
        for key, label in FORMAT_LABELS.items():
            self.f_exp_fmt.addItem(label, key)
        eform.addRow("默认导出位置", self.f_exp_choice)
        eform.addRow("自定义路径", self.f_exp_path)
        eform.addRow("", self.btn_pick)
        eform.addRow("默认导出格式", self.f_exp_fmt)
        lay.addWidget(exp_box)

        self.btn_manage.clicked.connect(self._open_manager)
        self._refresh_status()
        self._exp_custom = cfg.get("export_custom_path", "")
        idx = self.f_exp_choice.findData(cfg.get("export_choice", "default"))
        self.f_exp_choice.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.f_exp_fmt.findData(cfg.get("export_format", "docx"))
        self.f_exp_fmt.setCurrentIndex(idx if idx >= 0 else 0)
        self.f_exp_choice.currentIndexChanged.connect(self._update_exp_path)
        self.btn_pick.clicked.connect(self._pick_exp_dir)
        self._update_exp_path()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _update_exp_path(self):
        from core import output_location
        self.f_exp_path.setText(output_location.preview_path(
            self.f_exp_choice.currentData(), self._exp_custom))

    def _pick_exp_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择默认输出文件夹",
            self.f_exp_path.text() or os.path.expanduser("~"))
        if folder:
            self._exp_custom = folder
            idx = self.f_exp_choice.findData("custom")
            self.f_exp_choice.setCurrentIndex(max(0, idx))
            self._update_exp_path()

    def _refresh_status(self):
        from gui.model_options import enabled_model_options

        options = enabled_model_options(self.cfg)
        names = [label for _reference, label in options]
        provider_count = sum(1 for item in self.cfg.ai_providers().values() if item.get("enabled"))
        self.model_status.setText(
            "已启用模型：" + ("、".join(names[:5]) if names else "（无）") +
            ("…" if len(names) > 5 else "") +
            f"　|　Provider {provider_count} 个，模型 {len(names)} 个"
        )

    def _open_manager(self):
        from gui.model_center import AIModelCenterDialog
        AIModelCenterDialog(self, self.cfg).exec()
        self._refresh_status()

    def _save(self):
        self.cfg.set("ai_risk_limit", self.f_ai_limit.value())
        self.cfg.set("repeat_risk_limit", self.f_repeat_limit.value())
        self.cfg.set("max_optimization_rounds", self.f_max_rounds.value())
        self.cfg.set("export_choice", self.f_exp_choice.currentData())
        self.cfg.set("export_custom_path", self._exp_custom
                     if self.f_exp_choice.currentData() == "custom" else "")
        self.cfg.set("export_format", self.f_exp_fmt.currentData())
        log.get().info("设置已更新（含默认导出位置）")
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("论文智能研究与写作助手")
        self.setMinimumSize(900, 650)
        self.setStyleSheet(APP_QSS)

        self.config = ConfigManager()
        self.project = Project()
        self.evidence = EvidenceStore()
        self.annotations = AnnotationStore()
        self.data_dir = paths.data_dir()

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(150)
        self.sidebar.setMaximumWidth(300)
        self.sidebar.addItems(["首页", "全自动模式", "高级模式", "论文历史",
                               "1 论文信息", "2 选题解析 / 检索方案", "3 资料检索",
                               "4 证据库", "5 AI 大纲", "6 分章节写作",
                               "7 事实核查", "8 最终输出", "参考文献中心", "批注管理"])

        self.stack = QStackedWidget()
        self.pages = [
            HomePage(self), AutoModePage(self), AdvancedWorkspacePage(self),
            HistoryPage(self), InfoPage(self), ResearchPage(self), SearchPage(self),
            EvidencePage(self), OutlinePage(self), WritingPage(self),
            FactCheckPage(self), ExportPage(self), ReferenceCenterPage(self),
            AnnotationPage(self),
        ]
        for p in self.pages:
            self.stack.addWidget(p)

        self.splitter = QSplitter()
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([190, 990])
        root.addWidget(self.splitter, 1)
        self.setCentralWidget(central)

        self.sidebar.currentRowChanged.connect(self._on_sidebar)
        self.statusBar().showMessage(f"项目目录: {self.data_dir}")

        view_menu = self.menuBar().addMenu("视图")
        self.toggle_sidebar_action = QAction("显示/隐藏侧边栏", self)
        self.toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        self.toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(self.toggle_sidebar_action)

        help_menu = self.menuBar().addMenu("帮助")
        update_action = QAction("检查更新…", self)
        update_action.triggered.connect(self._open_update_check)
        help_menu.addAction(update_action)
        about_action = QAction("关于论文助手", self)
        about_action.triggered.connect(lambda: AboutDialog(self).exec())
        help_menu.addAction(about_action)

        self._user_sidebar_pref = None
        self._auto_hidden = False
        self.refresh()
        self._sync_history_on_startup()
        QTimer.singleShot(400, self._maybe_resume_auto)
        QTimer.singleShot(2500, self._check_updates_silently)
        self._load_geometry()

    def _open_update_check(self):
        AboutDialog(self, auto_check=True).exec()

    def _check_updates_silently(self):
        from gui.update_check import UpdateCheckThread

        self._update_worker = UpdateCheckThread(self)
        self._update_worker.result_ready.connect(self._on_background_update_result)
        self._update_worker.error.connect(
            lambda message: log.get().warning("后台检查更新失败: %s", message))
        self._update_worker.start()

    def _on_background_update_result(self, result):
        if result.get("update_available"):
            self.statusBar().showMessage(
                f"发现新版本 v{result['latest_version']}，可在“帮助 → 检查更新”中下载。",
                15000)

    def _sync_history_on_startup(self):
        from core.checkpoint import AutoCheckpoint
        from core.history import HistoryManager
        cp = AutoCheckpoint()
        if not cp.exists():
            return
        HistoryManager().sync_with_active_checkpoint(dict(cp.data))
        if cp.data.get("finished"):
            cp.clear()
            log.get().info("已完成任务的旧断点已归档到历史记录")

    def _on_sidebar(self, row):
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)
            self.pages[row].refresh()
            self.refresh()

    def go(self, index):
        self.sidebar.setCurrentRow(index)

    # ---------- 响应式窗口 ----------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._user_sidebar_pref is not None:
            return
        if self.width() < 1100 and self.sidebar.isVisible():
            self.sidebar.hide()
            self._auto_hidden = True
        elif self.width() >= 1100 and self._auto_hidden:
            self.sidebar.show()
            self._auto_hidden = False

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
            self._user_sidebar_pref = False
            self._auto_hidden = False
        else:
            self.sidebar.show()
            self._user_sidebar_pref = True
            self._auto_hidden = False

    def _load_geometry(self):
        try:
            g = self.config.get("window_geometry") or {}
            w, h = int(g.get("w") or 1180), int(g.get("h") or 760)
            x, y = int(g.get("x") or 100), int(g.get("y") or 100)
            self.resize(max(900, w), max(650, h))
            self.move(max(0, x), max(0, y))
            if self.config.get("window_maximized"):
                self.showMaximized()
        except (TypeError, ValueError):
            self.resize(1180, 760)

    def closeEvent(self, event):
        try:
            if self.isMaximized():
                g = self.normalGeometry()
            else:
                g = self.geometry()
            self.config.set("window_geometry", {"x": g.x(), "y": g.y(),
                                                "w": g.width(), "h": g.height()})
            self.config.set("window_maximized", self.isMaximized())
        except Exception as e:
            log.get().warning("窗口状态保存失败: %s", e)
        super().closeEvent(event)

    def reset_project(self):
        self.project.reset()
        for f in ("evidence.json", "research_plan.md", "outline.md", "outline_edit.json"):
            p = os.path.join(self.data_dir, f)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        chapters_dir = paths.chapters_dir()
        for f in os.listdir(chapters_dir):
            if f.endswith(".md"):
                try:
                    os.remove(os.path.join(chapters_dir, f))
                except OSError:
                    pass
        self.evidence.data = []
        self.evidence.save()
        for f in ("annotations.json", "annotation_styles.json"):
            p = os.path.join(self.data_dir, f)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        log.get().info("已开始新论文项目")
        self.refresh()

    def recommended_stage(self):
        from core import writer as writer_mod
        if not self.project.info_complete():
            return 4
        if not self.project.get("research_plan"):
            return 5
        if not self.evidence.all():
            return 6
        sections = self.project.outline().get("sections") or []
        if not sections:
            return 8
        if any(not writer_mod.read_chapter(i).strip()
               for i in range(1, len(sections) + 1)):
            return 9
        if not self.project.get("check"):
            return 10
        return 11

    def _maybe_resume_auto(self):
        cp = AutoCheckpoint()
        if not cp.has_unfinished():
            return
        input_data = cp.data.get("input") or {}
        topic = input_data.get("topic") or "未命名"
        done = cp.done_count()
        box = QMessageBox(self)
        box.setWindowTitle("检测到未完成的全自动项目")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"检测到未完成的全自动项目：\n\n论文：{topic}\n已完成步骤：{done} 个\n\n是否继续？")
        btn_cont = box.addButton("继续执行", QMessageBox.ButtonRole.AcceptRole)
        btn_restart = box.addButton("重新开始", QMessageBox.ButtonRole.DestructiveRole)
        box.exec()
        self.go(1)
        if box.clickedButton() is btn_cont:
            self.pages[1].start_resume()
        else:
            cp.clear()
            log.get().info("用户选择重新开始，自动任务断点已清除")
            self.refresh()

    def refresh(self):
        store = self.evidence
        done_flags = [
            self.project.info_complete(),
            bool(self.project.get("research_plan")),
            bool(store.all()),
            bool(store.all()),
            bool(self.project.outline().get("sections")),
        ]
        from core import writer as writer_mod
        sections = self.project.outline().get("sections") or []
        done_flags.append(bool(sections) and all(
            writer_mod.read_chapter(i).strip() for i in range(1, len(sections) + 1)))
        done_flags.append(bool(self.project.get("check")))
        done_flags.append(bool(self.project.get("exported")))
        for i in range(8):
            mark = "✓ " if done_flags[i] else ""
            text = ["1 论文信息", "2 选题解析 / 检索方案", "3 资料检索", "4 证据库",
                    "5 AI 大纲", "6 分章节写作", "7 事实核查", "8 最终输出"][i]
            self.sidebar.item(i + 4).setText(mark + text)
        self.sidebar.item(0).setText("首页")

    def show_settings_dialog(self):
        SettingsDialog(self, self.config).exec()
        self.refresh()

# 版本: v2.3.0 (2026-08-19) 更新: GitHub Release 更新检查入口
