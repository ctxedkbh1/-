from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from gui.widgets import LinkBrowser, Worker, msg_err, msg_warn


class ResearchPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self._plan = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)

        title = QLabel("第二步：选题解析 / 检索方案")
        title.setObjectName("pageTitle")
        lay.addWidget(title)

        row = QHBoxLayout()
        self.btn_gen = QPushButton("AI 分析题目并生成研究方案")
        self.btn_gen.setObjectName("primary")
        self.btn_regen = QPushButton("重新分析")
        self.btn_confirm = QPushButton("确认方案，进入资料检索")
        row.addWidget(self.btn_gen)
        row.addWidget(self.btn_regen)
        row.addWidget(self.btn_confirm)
        row.addStretch(1)
        lay.addLayout(row)

        self.view = LinkBrowser()
        self.view.setPlaceholderText("生成的研究方案将在此显示（可点击 [E编号] 查看证据来源）。")
        lay.addWidget(self.view, 1)

        self.btn_gen.clicked.connect(self.on_generate)
        self.btn_regen.clicked.connect(self.on_generate)
        self.btn_confirm.clicked.connect(self.on_confirm)

    def refresh(self):
        if not self.mw.project.info_complete():
            self.view.show_markdown("请先在【1 论文信息】中填写题目、学校、姓名。")
            return
        plan = self.mw.project.get("research_plan")
        if plan:
            from core import research
            self._plan = plan
            self.view.show_markdown(research.plan_markdown(self.mw.project.info(), plan))
        else:
            self.view.show_markdown("尚未生成研究方案。点击上方按钮开始分析。")

    def on_generate(self):
        if not self.mw.project.info_complete():
            msg_warn(self, "请先填写论文信息（至少题目、学校、姓名）。")
            return
        self.btn_gen.setEnabled(False)
        self.btn_regen.setEnabled(False)
        self.view.show_markdown("正在调用 DeepSeek 分析题目……")
        self._worker = Worker(self._generate)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _generate(self):
        from core import research
        return research.generate_plan(self.mw.project.info())

    def _on_done(self, plan):
        self.btn_gen.setEnabled(True)
        self.btn_regen.setEnabled(True)
        self._plan = plan
        from core import research
        self.view.show_markdown(research.plan_markdown(self.mw.project.info(), plan))

    def _on_failed(self, msg):
        self.btn_gen.setEnabled(True)
        self.btn_regen.setEnabled(True)
        self.view.show_markdown("生成失败，请重试。")
        msg_err(self, msg, "分析失败", retry=True)

    def on_confirm(self):
        if not self._plan and not self.mw.project.get("research_plan"):
            msg_warn(self, "请先生成研究方案。")
            return
        plan = self._plan or self.mw.project.get("research_plan")
        self.mw.project.set("research_plan", plan)
        from core import log, paths, research
        with open(paths.research_plan_md(), "w", encoding="utf-8") as f:
            f.write(research.plan_markdown(self.mw.project.info(), plan))
        log.get().info("研究方案已确认并保存 research_plan.md")
        from gui.widgets import msg_info
        msg_info(self, "研究方案已保存到 research_plan.md。\n下一步：资料检索（第三阶段）。")
        self.mw.go(3)

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
