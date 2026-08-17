from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QPushButton, QTextBrowser,
                               QVBoxLayout, QWidget)


TASK_LABELS = {
    "generation": "论文生成",
    "polish": "论文润色",
    "search": "联网检索",
    "summary": "资料摘要",
    "quick_edit": "快速修改",
    "advanced": "高级模式",
    "analysis": "结构分析",
    "check": "最终检查",
}


class ModelCenterViewMixin:
    def _provider_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.addWidget(QLabel("🔌 AI Providers（勾选 = 启用）"))
        self.provider_list = QListWidget()
        self.provider_list.currentItemChanged.connect(self._provider_changed)
        self.provider_list.itemChanged.connect(self._provider_item_toggled)
        layout.addWidget(self.provider_list, 1)
        row = QHBoxLayout()
        for text, slot in (("➕ 添加", self._add_provider), ("✏️ 编辑", self._edit_provider),
                           ("🗑️ 删除", self._delete_provider)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        self.migrate_button = QPushButton("🔐 迁移旧 API Key 到系统凭据")
        self.migrate_button.clicked.connect(self._migrate_credentials)
        layout.addWidget(self.migrate_button)
        return panel

    def _model_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 0, 0, 0)
        top = QHBoxLayout()
        self.provider_title = QLabel("请选择 Provider")
        self.provider_title.setObjectName("sectionTitle")
        self.provider_status = QLabel("未检测")
        top.addWidget(self.provider_title)
        top.addWidget(self.provider_status)
        top.addStretch(1)
        self.test_button = QPushButton("🧪 测试模型")
        self.provider_test_button = QPushButton("🧪 测试 Provider")
        self.refresh_button = QPushButton("🔄 刷新模型")
        self.add_model_button = QPushButton("➕ 添加模型")
        self.preset_button = QPushButton("📚 预设库")
        self.test_button.clicked.connect(self._test_model)
        self.provider_test_button.clicked.connect(self._test_provider)
        self.refresh_button.clicked.connect(self._refresh_models_online)
        self.add_model_button.clicked.connect(self._add_model)
        self.preset_button.clicked.connect(self._open_preset_library)
        top.addWidget(self.test_button)
        top.addWidget(self.provider_test_button)
        top.addWidget(self.refresh_button)
        top.addWidget(self.add_model_button)
        top.addWidget(self.preset_button)
        layout.addLayout(top)
        self.last_refresh = QLabel("最后刷新：—")
        self.last_refresh.setObjectName("muted")
        layout.addWidget(self.last_refresh)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索名称、Model ID、Provider 或能力")
        self.filter = QComboBox()
        for label, value in (("全部", ""), ("可用", "available"), ("推理", "reasoning"),
                             ("视觉", "vision"), ("长上下文", "long_context"),
                             ("收藏", "favorite")):
            self.filter.addItem(label, value)
        self.sort = QComboBox()
        self.sort.addItem("收藏优先", "favorite")
        self.sort.addItem("名称", "name")
        self.sort.addItem("上下文", "context")
        self.sort.addItem("更新时间", "updated")
        filters.addWidget(self.search, 1)
        filters.addWidget(self.filter)
        filters.addWidget(self.sort)
        layout.addLayout(filters)
        self.search.textChanged.connect(self._load_models)
        self.filter.currentIndexChanged.connect(self._load_models)
        self.sort.currentIndexChanged.connect(self._load_models)
        self.model_list = QListWidget()
        self.model_list.currentItemChanged.connect(self._show_model)
        self.model_list.itemChanged.connect(self._model_item_toggled)
        self.model_list.itemDoubleClicked.connect(lambda _item: self._toggle_favorite())
        layout.addWidget(self.model_list, 1)
        actions = QHBoxLayout()
        self.favorite_button = QPushButton("⭐ 收藏 / 取消收藏")
        self.toggle_model_button = QPushButton("⏸️ 停用模型")
        self.delete_model_button = QPushButton("🗑️ 删除模型配置")
        self.favorite_button.clicked.connect(self._toggle_favorite)
        self.toggle_model_button.clicked.connect(self._toggle_model_enabled)
        self.delete_model_button.clicked.connect(self._delete_model)
        self.task = QComboBox()
        for key, label in TASK_LABELS.items():
            self.task.addItem(label, key)
        self.task_policy = QComboBox()
        self.task_policy.addItem("指定模型", "selected")
        self.task_policy.addItem("官方最新", "latest")
        self.set_default_button = QPushButton("🎯 设为任务默认模型")
        self.set_default_button.clicked.connect(self._set_default)
        actions.addWidget(self.favorite_button)
        actions.addWidget(self.toggle_model_button)
        actions.addWidget(self.delete_model_button)
        actions.addStretch(1)
        actions.addWidget(self.task)
        actions.addWidget(self.task_policy)
        actions.addWidget(self.set_default_button)
        layout.addLayout(actions)
        self.details = QTextBrowser()
        self.details.setMaximumHeight(150)
        layout.addWidget(self.details)
        return panel

# 版本: v2.0.1 (2026-08-17) 更新: AI 模型中心视图构建
