from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from gui.widgets import LinkBrowser, Worker, msg_err, msg_warn


class FactCheckPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        title = QLabel("第七阶段：事实核查")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        tip = QLabel("全文完成后逐句核查：数据、日期、人物、机构、政策、论文、统计结果、学术观点、"
                     "引用与参考文献。每个事实必须能追溯到 E 编号。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)

        row = QHBoxLayout()
        self.btn_run = QPushButton("开始核查")
        self.btn_run.setObjectName("primary")
        self.chk_ai = QCheckBox("调用 AI 逐项核查（对照证据表）")
        self.chk_ai.setChecked(True)
        self.btn_next = QPushButton("核查通过，进入输出")
        row.addWidget(self.btn_run)
        row.addWidget(self.chk_ai)
        row.addStretch(1)
        row.addWidget(self.btn_next)
        lay.addLayout(row)

        self.view = LinkBrowser()
        self.view.setPlaceholderText("核查报告将在此显示。")
        lay.addWidget(self.view, 1)

        self.btn_run.clicked.connect(self.on_run)
        self.btn_next.clicked.connect(lambda: self.mw.go(8))

    def refresh(self):
        if self.mw.project.get("check"):
            self.view.show_markdown("上次核查结果已保存在项目中。\n"
                                    "点击【开始核查】重新执行，或直接进入输出阶段。")

    def _chapters_done(self):
        from core import writer as writer_mod
        sections = self.mw.project.outline().get("sections") or []
        return [i for i in range(1, len(sections) + 1)
                if writer_mod.read_chapter(i).strip()]

    def on_run(self):
        done = self._chapters_done()
        if not done:
            msg_warn(self, "尚无已写章节，请先完成分章节写作。")
            return
        self.btn_run.setEnabled(False)
        self._worker = Worker(self._run)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _run(self):
        from core import exporter, fact_checker
        store = self.mw.evidence
        full_text = exporter.build_full_text(self.mw.project)
        analysis = fact_checker.analyze(full_text, store)
        issues = fact_checker.ai_fact_check(full_text, store) if self.chk_ai.isChecked() else []
        return analysis, issues

    def _on_done(self, result):
        self.btn_run.setEnabled(True)
        analysis, issues = result
        from core import exporter, fact_checker
        done = self._chapters_done()
        total_words = 0
        from core import writer as writer_mod
        for i in done:
            total_words += writer_mod.cjk_count(writer_mod.read_chapter(i))
        self.mw.project.set("check", analysis)
        self.mw.project.set("check_ai_issues", issues)
        report = fact_checker.build_report(self.mw.project, self.mw.evidence, analysis,
                                           issues, len(done), total_words)
        self.view.show_markdown(report)
        from core import log
        log.get().info("事实核查完成 通过=%s 问题=%d", analysis.get("bidirectional_ok"), len(issues))

    def _on_failed(self, msg):
        self.btn_run.setEnabled(True)
        msg_err(self, msg, "核查失败", retry=True)

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
