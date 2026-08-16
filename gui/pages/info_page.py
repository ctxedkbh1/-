from PySide6.QtWidgets import (QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from gui.widgets import msg_info, msg_warn


class InfoPage(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(30, 24, 30, 24)

        title = QLabel("第一步：论文信息")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        tip = QLabel("以下 10 项信息会写入 project.json，并用于 AI 选题解析与写作。带 * 为必填。")
        tip.setStyleSheet("color: #667085;")
        lay.addWidget(tip)

        box = QGroupBox("论文信息（10 项）")
        form = QFormLayout(box)
        form.setSpacing(10)
        self.topic = QLineEdit()
        self.major = QLineEdit()
        self.course = QLineEdit()
        self.school = QLineEdit()
        self.class_name = QLineEdit()
        self.student_id = QLineEdit()
        self.name = QLineEdit()
        self.word_count = QSpinBox()
        self.word_count.setRange(500, 100000)
        self.word_count.setSingleStep(100)
        self.word_count.setValue(3000)
        self.word_count.setSuffix(" 字")
        self.format_note = QPlainTextEdit()
        self.format_note.setPlaceholderText("例如：正文宋体小四、1.5 倍行距、参考文献按 GB/T 7714……（可留空）")
        self.format_note.setFixedHeight(64)
        self.deadline = QLineEdit()
        self.deadline.setPlaceholderText("例如：2026-06-30（可留空）")

        form.addRow("1. 论文题目 *", self.topic)
        form.addRow("2. 专业", self.major)
        form.addRow("3. 课程名称", self.course)
        form.addRow("4. 学校 *", self.school)
        form.addRow("5. 班级", self.class_name)
        form.addRow("6. 学号", self.student_id)
        form.addRow("7. 姓名 *", self.name)
        form.addRow("8. 字数要求", self.word_count)
        form.addRow("9. 格式要求", self.format_note)
        form.addRow("10. 截止时间", self.deadline)
        lay.addWidget(box)

        row = QHBoxLayout()
        self.btn_save = QPushButton("保存论文信息")
        self.btn_next = QPushButton("保存并下一步")
        self.btn_next.setObjectName("primary")
        row.addWidget(self.btn_save)
        row.addWidget(self.btn_next)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.btn_save.clicked.connect(lambda: self.save(go_next=False))
        self.btn_next.clicked.connect(lambda: self.save(go_next=True))

    def refresh(self):
        info = self.mw.project.info()
        self.topic.setText(str(info.get("topic") or ""))
        self.major.setText(str(info.get("major") or ""))
        self.course.setText(str(info.get("course") or ""))
        self.school.setText(str(info.get("school") or ""))
        self.class_name.setText(str(info.get("class_name") or ""))
        self.student_id.setText(str(info.get("student_id") or ""))
        self.name.setText(str(info.get("name") or ""))
        self.word_count.setValue(int(info.get("word_count") or 3000))
        self.format_note.setPlainText(str(info.get("format_note") or ""))
        self.deadline.setText(str(info.get("deadline") or ""))

    def save(self, go_next=False):
        values = {
            "topic": self.topic.text().strip(),
            "major": self.major.text().strip(),
            "course": self.course.text().strip(),
            "school": self.school.text().strip(),
            "class_name": self.class_name.text().strip(),
            "student_id": self.student_id.text().strip(),
            "name": self.name.text().strip(),
            "word_count": self.word_count.value(),
            "format_note": self.format_note.toPlainText().strip(),
            "deadline": self.deadline.text().strip(),
        }
        if not values["topic"] or not values["school"] or not values["name"]:
            msg_warn(self, "论文题目、学校、姓名为必填项。")
            return
        self.mw.project.update_info(values)
        from core import log
        log.get().info("论文信息已保存 topic=%s", values["topic"])
        if go_next:
            msg_info(self, "论文信息已保存到 project.json。\n下一步：选题解析与检索方案。")
            self.mw.go(2)
        else:
            msg_info(self, "论文信息已保存。")

# 版本: v1.9.0 (2026-08-16) 更新: 响应式窗口与DPI适配
