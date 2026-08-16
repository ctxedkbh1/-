import json
import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from gui.widgets import LinkBrowser, Worker, msg_err, msg_info, msg_warn


class OutlinePage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        title = QLabel("第五阶段：AI 大纲")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        row = QHBoxLayout()
        self.btn_gen = QPushButton("生成大纲")
        self.btn_gen.setObjectName("primary")
        self.btn_regen = QPushButton("重新生成")
        self.btn_edit = QPushButton("编辑大纲 JSON")
        self.btn_reload = QPushButton("重新载入")
        self.btn_confirm = QPushButton("确认大纲，进入写作")
        row.addWidget(self.btn_gen)
        row.addWidget(self.btn_regen)
        row.addWidget(self.btn_edit)
        row.addWidget(self.btn_reload)
        row.addStretch(1)
        row.addWidget(self.btn_confirm)
        lay.addLayout(row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["章节 / 小节", "核心观点", "证据", "目标字数"])
        self.tree.setColumnWidth(0, 280)
        self.tree.setColumnWidth(1, 420)
        self.tree.setColumnWidth(2, 220)
        self.tree.setAlternatingRowColors(True)
        lay.addWidget(self.tree, 1)

        self.view = LinkBrowser()
        self.view.setMinimumHeight(60)
        self.view.show_markdown("大纲将在此显示与确认。证据不足的部分不会安排事实性论述。")
        lay.addWidget(self.view)

        self.btn_gen.clicked.connect(self.on_generate)
        self.btn_regen.clicked.connect(self.on_generate)
        self.btn_edit.clicked.connect(self.on_edit_json)
        self.btn_reload.clicked.connect(self.on_reload_json)
        self.btn_confirm.clicked.connect(self.on_confirm)

    def refresh(self):
        outline = self.mw.project.outline()
        self.tree.clear()
        if not outline.get("sections"):
            return
        self.view.show_markdown(
            f"论文标题：{outline.get('title', '')}\n\n"
            f"共 {len(outline.get('sections', []))} 章，总目标字数 "
            f"{sum(s.get('target_words', 0) for s in outline.get('sections', []))} 字。")
        for sec in outline.get("sections", []):
            item = QTreeWidgetItem([sec.get("title", ""),
                                    sec.get("core_points", ""),
                                    " ".join(sec.get("evidence_ids", [])),
                                    str(sec.get("target_words", 0))])
            item.setForeground(0, Qt.GlobalColor.darkBlue)
            self.tree.addTopLevelItem(item)
            for sub in sec.get("subsections", []):
                sub_item = QTreeWidgetItem([sub.get("title", ""),
                                            sub.get("core_points", ""),
                                            " ".join(sub.get("evidence_ids", [])), ""])
                item.addChild(sub_item)
            item.setExpanded(True)
        self.tree.expandAll()

    def on_generate(self):
        if not self.mw.evidence.all():
            msg_warn(self, "证据库为空。请先完成资料检索（第三阶段）并建立证据表。")
            return
        self.btn_gen.setEnabled(False)
        self.btn_regen.setEnabled(False)
        self._worker = Worker(self._generate)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _generate(self):
        from core import outline
        return outline.generate_outline(self.mw.project.info(), self.mw.evidence)

    def _on_done(self, outline):
        self.btn_gen.setEnabled(True)
        self.btn_regen.setEnabled(True)
        self.mw.project.set_outline(outline)
        from core import log
        log.get().info("大纲生成成功并保存")
        self.refresh()

    def _on_failed(self, msg):
        self.btn_gen.setEnabled(True)
        self.btn_regen.setEnabled(True)
        msg_err(self, msg, "大纲生成失败", retry=True)

    def on_edit_json(self):
        outline = self.mw.project.outline()
        if not outline.get("sections"):
            msg_warn(self, "请先生成大纲。")
            return
        fname = os.path.join(self.mw.data_dir, "outline_edit.json")
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(outline, f, ensure_ascii=False, indent=2)
        try:
            if os.name == "nt":
                subprocess.Popen(["notepad", fname])
        except Exception:
            pass
        msg_info(self, f"已导出大纲 JSON 到:\n{fname}\n修改保存后点击【重新载入】。")

    def on_reload_json(self):
        fname = os.path.join(self.mw.data_dir, "outline_edit.json")
        if not os.path.exists(fname):
            msg_warn(self, "未找到 outline_edit.json，请先点击【编辑大纲 JSON】。")
            return
        try:
            with open(fname, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data.get("sections"), list) or not data["sections"]:
                raise ValueError("sections 格式无效")
            self.mw.project.set_outline(data)
            from core import log
            log.get().info("大纲 JSON 已重新载入")
            self.refresh()
        except Exception as e:
            msg_err(self, f"载入失败: {e}")

    def on_confirm(self):
        outline = self.mw.project.outline()
        if not outline.get("sections"):
            msg_warn(self, "请先生成大纲。")
            return
        from core import log, outline as outline_mod, paths
        with open(paths.outline_md(), "w", encoding="utf-8") as f:
            f.write(outline_mod.outline_markdown(outline, self.mw.evidence))
        self.mw.project.set_outline(outline)
        log.get().info("大纲已确认并保存 outline.md")
        msg_info(self, "大纲已保存到 outline.md。\n下一步：分章节写作（第六阶段）。")
        self.mw.go(6)

# 版本: v1.9.0 (2026-08-16) 更新: 响应式窗口与DPI适配
