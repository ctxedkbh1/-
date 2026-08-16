from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from gui.widgets import msg_info, msg_warn


class HomePage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(60, 40, 60, 40)
        lay.setSpacing(16)

        title = QLabel("论文智能研究与写作助手")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        from core import paths
        version_label = QLabel(f"v{paths.VERSION}（{paths.RELEASE_DATE}）")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #98a2b3; font-size: 11px;")
        lay.addWidget(version_label)

        sub = QLabel("选题 → 权威资料检索 → 证据表 → 大纲 → 分章节写作 → 事实核查 → 输出")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #667085; font-size: 13px;")
        lay.addWidget(sub)
        lay.addSpacing(16)

        mode_label = QLabel("请选择工作模式")
        mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_label.setStyleSheet("font-size: 15px; color: #475467;")
        lay.addWidget(mode_label)

        mode_row = QHBoxLayout()
        self.btn_manual = QPushButton("普通模式\n按 1 → 8 步执行")
        self.btn_auto = QPushButton("全自动研究模式\n一键完成全部流程")
        self.btn_advanced = QPushButton("高级模式\n专业论文生成与编辑控制中心")
        for b in (self.btn_manual, self.btn_auto, self.btn_advanced):
            b.setObjectName("modeButton")
            b.setMinimumHeight(92)
            mode_row.addWidget(b)
        lay.addLayout(mode_row)
        lay.addSpacing(14)

        self.proj_label = QLabel()
        self.proj_label.setWordWrap(True)
        self.proj_label.setStyleSheet("font-size: 14px;")
        lay.addWidget(self.proj_label)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setStyleSheet("color: #667085; font-size: 12px;")
        lay.addWidget(self.path_label)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 13px; color: #344054;")
        lay.addWidget(self.summary_label)

        lay.addSpacing(20)
        row = QHBoxLayout()
        self.btn_new = QPushButton("开始新论文")
        self.btn_new.setObjectName("primary")
        self.btn_open = QPushButton("打开已有项目")
        self.btn_settings = QPushButton("设置")
        for b in (self.btn_new, self.btn_open, self.btn_settings):
            b.setMinimumHeight(36)
            b.setMinimumWidth(140)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)

        self.btn_new.clicked.connect(self.on_new)
        self.btn_open.clicked.connect(self.on_open)
        self.btn_settings.clicked.connect(self.mw.show_settings_dialog)
        self.btn_manual.clicked.connect(self.on_manual_mode)
        self.btn_auto.clicked.connect(lambda: self.mw.go(1))
        self.btn_advanced.clicked.connect(lambda: self.mw.go(2))

    def on_manual_mode(self):
        if self.mw.project.info_complete():
            self.mw.go(self.mw.recommended_stage())
        else:
            self.mw.go(4)

    def on_new(self):
        from gui.widgets import ask_confirm
        if ask_confirm(self, "开始新论文将清空当前项目的论文信息、证据表和大纲。\n"
                             "输出文件与章节文件也将被清除。确定继续？", "开始新论文"):
            self.mw.reset_project()
            self.mw.go(4)

    def on_open(self):
        if not self.mw.project.info_complete():
            msg_warn(self, "还没有已保存的论文项目，请先点击【手动研究模式】或【全自动研究模式】开始。")
            return
        msg_info(self, "已载入当前项目，正在跳转到建议的进度。")
        self.mw.go(self.mw.recommended_stage())

    def refresh(self):
        from core import paths
        proj = self.mw.project
        info = proj.info()
        self.proj_label.setText(
            f"<b>当前项目：</b>{info.get('topic') or '（尚未开始）'}<br>"
            f"<b>作者：</b>{info.get('name') or '—'}　"
            f"<b>学校：</b>{info.get('school') or '—'}　"
            f"<b>专业：</b>{info.get('major') or '—'}")
        self.path_label.setText(f"项目路径：{paths.data_dir()}")
        store = self.mw.evidence
        sections = proj.outline().get("sections") or []
        from core import writer as writer_mod
        written = sum(1 for i in range(1, len(sections) + 1)
                      if writer_mod.read_chapter(i).strip())
        exported = proj.get("exported")
        parts = [f"证据库：{len(store.all())} 条",
                 f"大纲章节：{len(sections)} 节",
                 f"已写章节：{written}/{len(sections) or '-'}"]
        if exported:
            parts.append("输出文件：已生成")
        self.summary_label.setText("　|　".join(parts))

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
