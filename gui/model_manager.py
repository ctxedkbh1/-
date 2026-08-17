from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox,
                               QPushButton, QScrollArea, QSpinBox,
                               QVBoxLayout, QWidget)

from core.llm import CAPABILITY_LABELS, TASK_LABELS
from gui.widgets import Worker, msg_err, msg_info, msg_warn


class ModelEditDialog(QDialog):
    def __init__(self, parent=None, record=None, key=None):
        super().__init__(parent)
        self.setWindowTitle("编辑模型" if record else "添加自定义模型")
        self.setMinimumSize(460, 440)
        self.resize(520, 560)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)
        form = QFormLayout()
        self.f_name = QLineEdit()
        self.f_type = QComboBox()
        self.f_type.addItem("OpenAI Compatible API", "openai_compatible")
        self.f_type.addItem("Anthropic Claude API", "claude")
        self.f_type.addItem("Google Gemini API", "gemini")
        self.f_type.addItem("本地模型（Ollama 等）", "local")
        self.f_base = QLineEdit()
        self.f_base.setPlaceholderText("例如 https://api.example.com（不要写死，可随时修改）")
        self.f_key = QLineEdit()
        self.f_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_key.setPlaceholderText("留空则读取环境变量")
        self.f_model_id = QLineEdit()
        self.f_price = QDoubleSpinBox()
        self.f_price.setRange(0, 10000)
        self.f_price.setDecimals(2)
        self.f_price.setSuffix(" 元/百万token")
        form.addRow("模型名称", self.f_name)
        form.addRow("API 类型", self.f_type)
        form.addRow("API Base URL", self.f_base)
        form.addRow("API Key", self.f_key)
        form.addRow("Model ID", self.f_model_id)
        form.addRow("参考价格", self.f_price)
        lay.addLayout(form)
        cap_box = QGroupBox("能力标签（用于自动选择模型）")
        cap_lay = QVBoxLayout(cap_box)
        self.caps = {}
        for c in CAPABILITY_LABELS:
            cb = QCheckBox(c)
            cap_lay.addWidget(cb)
            self.caps[c] = cb
        lay.addWidget(cap_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.record = None
        if record:
            self.f_name.setText(str(record.get("name") or ""))
            idx = self.f_type.findData(record.get("type") or "openai_compatible")
            if idx >= 0 and record.get("type") != "local":
                self.f_type.setCurrentIndex(idx)
            elif record.get("type") == "local":
                self.f_type.setCurrentIndex(0)
            self.f_base.setText(str(record.get("base_url") or ""))
            self.f_key.setText(str(record.get("api_key") or ""))
            self.f_key.setPlaceholderText(f"环境变量: {record.get('env_key') or '无'}（留空使用环境变量）")
            self.f_model_id.setText(str(record.get("model_id") or ""))
            self.f_price.setValue(float(record.get("price") or 0))
            for c, cb in self.caps.items():
                cb.setChecked(c in (record.get("capabilities") or []))

    def _on_accept(self):
        if not self.f_name.text().strip():
            msg_warn(self, "模型名称不能为空。")
            return
        if not self.f_base.text().strip():
            msg_warn(self, "API Base URL 不能为空。")
            return
        if not self.f_model_id.text().strip():
            msg_warn(self, "Model ID 不能为空。")
            return
        ptype = self.f_type.currentData()
        self.record = {
            "name": self.f_name.text().strip(),
            "type": "openai_compatible" if ptype == "local" else ptype,
            "base_url": self.f_base.text().strip(),
            "api_key": self.f_key.text().strip(),
            "env_key": "",
            "model_id": self.f_model_id.text().strip(),
            "price": round(self.f_price.value(), 2),
            "capabilities": [c for c, cb in self.caps.items() if cb.isChecked()],
            "enabled": True,
        }
        self.accept()


class ModelManagerDialog(QDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("AI 模型中心（旧配置兼容入口）")
        self.setMinimumSize(640, 520)
        self.resize(760, 680)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        lay = QVBoxLayout(content)

        top = QHBoxLayout()
        top.addWidget(QLabel("已配置模型（勾选 = 启用，备用模型按列表顺序自动切换）："))
        top.addStretch(1)
        self.btn_add = QPushButton("添加自定义模型")
        self.btn_edit = QPushButton("编辑")
        self.btn_del = QPushButton("删除")
        self.btn_test = QPushButton("测试模型")
        for b in (self.btn_add, self.btn_edit, self.btn_del, self.btn_test):
            top.addWidget(b)
        lay.addLayout(top)

        self.model_list = QListWidget()
        self.model_list.itemChanged.connect(self._on_toggle)
        self.model_list.itemDoubleClicked.connect(lambda _: self.on_edit())
        lay.addWidget(self.model_list, 1)

        task_box = QGroupBox("任务级模型选择（【自动选择】= 由系统按能力自动路由）")
        tform = QFormLayout(task_box)
        self.task_combos = {}
        for key, label in TASK_LABELS.items():
            combo = QComboBox()
            combo.addItem("自动选择", "auto")
            self.task_combos[key] = combo
            tform.addRow(label, combo)
        lay.addWidget(task_box)

        plan_row = QHBoxLayout()
        plan_row.addWidget(QLabel("模型方案:"))
        self.plan_combo = QComboBox()
        self.btn_save_plan = QPushButton("保存当前任务配置为方案")
        self.btn_del_plan = QPushButton("删除方案")
        plan_row.addWidget(self.plan_combo, 1)
        plan_row.addWidget(self.btn_save_plan)
        plan_row.addWidget(self.btn_del_plan)
        lay.addLayout(plan_row)

        cost_box = QGroupBox("成本控制（达到限制将暂停自动优化）")
        cform = QFormLayout(cost_box)
        self.f_max_calls = QSpinBox()
        self.f_max_calls.setRange(0, 100000)
        self.f_max_calls.setSpecialValueText("不限")
        self.f_max_calls.setValue(int(self.cfg.cost_limits().get("max_api_calls") or 0))
        self.f_max_tokens = QSpinBox()
        self.f_max_tokens.setRange(0, 10000000)
        self.f_max_tokens.setSingleStep(10000)
        self.f_max_tokens.setSpecialValueText("不限")
        self.f_max_tokens.setValue(int(self.cfg.cost_limits().get("max_tokens") or 0))
        self.f_max_budget = QDoubleSpinBox()
        self.f_max_budget.setRange(0, 100000)
        self.f_max_budget.setDecimals(2)
        self.f_max_budget.setSpecialValueText("不限")
        self.f_max_budget.setSuffix(" 元")
        self.f_max_budget.setValue(float(self.cfg.cost_limits().get("max_budget") or 0))
        cform.addRow("单次论文最大 API 调用次数", self.f_max_calls)
        cform.addRow("单次论文最大 Token 数（估算）", self.f_max_tokens)
        cform.addRow("单次论文最大预算（按参考价估算）", self.f_max_budget)
        self.usage_label = QLabel()
        cform.addRow("当前累计用量", self.usage_label)
        usage_row = QHBoxLayout()
        self.btn_reset_usage = QPushButton("重置用量统计")
        usage_row.addWidget(self.btn_reset_usage)
        usage_row.addStretch(1)
        cform.addRow("", usage_row)
        lay.addWidget(cost_box)

        det_box = QGroupBox("检测服务（未接入正规第三方检测 API 时使用内部分析）")
        dform = QFormLayout(det_box)
        self.det_combo = QComboBox()
        self.det_combo.addItem("内部分析（内置，非任何检测平台结果）", "internal")
        self.det_combo.addItem("自定义检测 API（自行提供的正规服务）", "custom")
        self.det_name = QLineEdit()
        self.det_name.setPlaceholderText("服务名称（显示在报告中）")
        self.det_url = QLineEdit()
        self.det_url.setPlaceholderText("https://你的服务/api/detect（POST，期望返回 {\"ai_risk\":n,\"repeat_risk\":n}）")
        self.det_key = QLineEdit()
        self.det_key.setEchoMode(QLineEdit.EchoMode.Password)
        dform.addRow("检测服务", self.det_combo)
        dform.addRow("服务名称", self.det_name)
        dform.addRow("服务 URL", self.det_url)
        dform.addRow("API Key", self.det_key)
        lay.addWidget(det_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_del.clicked.connect(self.on_delete)
        self.btn_test.clicked.connect(self.on_test)
        self.btn_save_plan.clicked.connect(self.on_save_plan)
        self.btn_del_plan.clicked.connect(self.on_del_plan)
        self.btn_reset_usage.clicked.connect(self.on_reset_usage)
        self.plan_combo.currentIndexChanged.connect(self._on_plan)
        self._load()
        self.refresh_all()

    # ---------- 数据加载 ----------

    def _load(self):
        models = self.cfg.models()
        for key, m in models.items():
            item = QListWidgetItem(self._row_text(key, m))
            item.setData(0x0100, key)
            item.setCheckState(Qt.CheckState.Checked if m.get("enabled") else Qt.CheckState.Unchecked)
            self.model_list.addItem(item)
        for key, combo in self.task_combos.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("自动选择", "auto")
            for k, m in models.items():
                combo.addItem(m.get("name", k), k)
            cur = self.cfg.task_model(key)
            idx = combo.findData(cur)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
        self.plan_combo.blockSignals(True)
        self.plan_combo.clear()
        self.plan_combo.addItem("（不使用方案）", None)
        for name in self.cfg.plans():
            self.plan_combo.addItem(name, name)
        self.plan_combo.blockSignals(False)
        det = self.cfg.quality_provider() or {}
        idx = self.det_combo.findData(det.get("type") or "internal")
        self.det_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.det_name.setText(str(det.get("name") or ""))
        self.det_url.setText(str(det.get("url") or ""))
        self.det_key.setText(str(det.get("api_key") or ""))

    @staticmethod
    def _row_text(key, m):
        key_state = "Key: " + ConfigManager_mask(m)
        enabled = "✓" if m.get("enabled") else "○"
        return (f"{enabled} {m.get('name', key)} | {m.get('model_id', '')} | "
                f"{m.get('base_url', '')} | {key_state}")

    # ---------- 模型操作 ----------

    def _selected_key(self):
        item = self.model_list.currentItem()
        return item.data(0x0100) if item else None

    def on_add(self):
        dlg = ModelEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.record:
            name, _ = QInputDialog.getText(self, "模型标识", "唯一标识（英文小写，如 mymodel）:")
            key = name.strip().lower()
            if not key:
                return
            if key in self.cfg.models():
                msg_warn(self, f"标识 {key} 已存在，请换一个。")
                return
            self.cfg.add_model(key, dlg.record)
            self.reload_lists()

    def on_edit(self):
        key = self._selected_key()
        if not key:
            msg_warn(self, "请先选择模型。")
            return
        record = self.cfg.models().get(key)
        dlg = ModelEditDialog(self, record=record)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.record:
            rec = dlg.record
            rec["env_key"] = record.get("env_key", "")
            rec["enabled"] = record.get("enabled", True)
            self.cfg.add_model(key, rec)
            self.reload_lists()

    def on_delete(self):
        key = self._selected_key()
        if not key:
            msg_warn(self, "请先选择模型。")
            return
        if QMessageBox.question(self, "确认", f"确定删除模型 {key}？") != QMessageBox.StandardButton.Yes:
            return
        self.cfg.remove_model(key)
        self.reload_lists()

    def on_test(self):
        key = self._selected_key()
        if not key:
            msg_warn(self, "请先选择模型。")
            return
        from core.llm import ModelRouter
        self.btn_test.setEnabled(False)
        self._worker = Worker(ModelRouter(self.cfg).health_check, key)
        self._worker.done.connect(self._on_test_done)
        self._worker.failed.connect(lambda m: (self.btn_test.setEnabled(True), msg_err(self, m)))
        self._worker.start()

    def _on_test_done(self, result):
        self.btn_test.setEnabled(True)
        if result.get("ok"):
            msg_info(self, f"✓ {result.get('message')}", "模型测试")
        else:
            msg_err(self, f"✗ {result.get('message')}", "模型测试")

    def _on_toggle(self, item):
        key = item.data(0x0100)
        model = self.cfg.models().get(key)
        if model:
            model["enabled"] = item.checkState() == Qt.CheckState.Checked
            self.cfg.save()
            self._refresh_item_text(item, key, model)

    def _refresh_item_text(self, item, key, model):
        item.blockSignals(True)
        item.setText(self._row_text(key, model))
        item.blockSignals(False)

    def reload_lists(self):
        self.model_list.blockSignals(True)
        self.model_list.clear()
        self.model_list.blockSignals(False)
        self._load()

    # ---------- 方案 ----------

    def _current_assignment(self):
        return {k: c.currentData() for k, c in self.task_combos.items()}

    def _on_plan(self):
        name = self.plan_combo.currentData()
        if not name:
            return
        plan = self.cfg.plans().get(name) or {}
        for key, combo in self.task_combos.items():
            idx = combo.findData(plan.get(key) or "auto")
            combo.setCurrentIndex(idx if idx >= 0 else 0)

    def on_save_plan(self):
        name, ok = QInputDialog.getText(self, "保存方案", "方案名称（如：方案A 中文论文）:")
        name = name.strip()
        if not ok or not name:
            return
        self.cfg.save_plan(name, self._current_assignment())
        self.plan_combo.blockSignals(True)
        self.plan_combo.addItem(name, name)
        self.plan_combo.blockSignals(False)
        msg_info(self, f"方案「{name}」已保存，可一键切换。")

    def on_del_plan(self):
        name = self.plan_combo.currentData()
        if not name:
            msg_warn(self, "请先选择要删除的方案。")
            return
        self.cfg.remove_plan(name)
        idx = self.plan_combo.currentIndex()
        self.plan_combo.blockSignals(True)
        self.plan_combo.removeItem(idx)
        self.plan_combo.blockSignals(False)

    # ---------- 成本 ----------

    def on_reset_usage(self):
        from core import deepseek
        deepseek.reset_usage()
        self.refresh_usage()

    def refresh_usage(self):
        from core import deepseek
        u = deepseek.usage()
        self.usage_label.setText(
            f"调用 {u['calls']} 次 | Token（估算）{u['tokens']} | 估算费用 {u['cost']:.4f} 元")

    # ---------- 保存 ----------

    def refresh_all(self):
        self.refresh_usage()

    def _save(self):
        for key, combo in self.task_combos.items():
            self.cfg.set_task_model(key, combo.currentData() or "auto")
        self.cfg.set("cost_limits", {
            "max_api_calls": self.f_max_calls.value(),
            "max_tokens": self.f_max_tokens.value(),
            "max_budget": round(self.f_max_budget.value(), 2),
        })
        self.cfg.set("quality_provider", {
            "type": self.det_combo.currentData(),
            "name": self.det_name.text().strip(),
            "url": self.det_url.text().strip(),
            "api_key": self.det_key.text().strip(),
        })
        self.cfg.save()
        self.accept()


def ConfigManager_mask(m):
    from config.manager import ConfigManager
    key = m.get("api_key") or ""
    env = m.get("env_key") or ""
    if env:
        import os
        if os.environ.get(env, "").strip():
            return f"环境变量 {env}（已设置）"
    return ConfigManager.mask_key(key)

# 版本: v1.9.0 (2026-08-16) 更新: 响应式窗口与DPI适配
