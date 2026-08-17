from core.ai.runtime import model_registry


def enabled_model_options(config):
    registry = model_registry(config)
    options = []
    for provider in registry.providers(enabled_only=True):
        for model in registry.models(provider.provider_id):
            label = f"{provider.display_name} / {model.display_name}"
            options.append((model.ref.value, label))
    return options


def populate_model_combo(combo, config, task: str, auto_label: str = "跟随默认设置"):
    current = str(config.ai_task_model(task) or "auto")
    combo.blockSignals(True)
    combo.clear()
    combo.addItem(auto_label, "auto")
    combo.addItem("官方最新（仅使用官方时间信息）", "latest")
    for reference, label in enabled_model_options(config):
        combo.addItem(label, reference)
    index = combo.findData(current)
    combo.setCurrentIndex(index if index >= 0 else 0)
    combo.blockSignals(False)


def normalize_model_choice(config, value: str) -> str:
    if not value or value == "auto":
        return "auto"
    legacy = config.ai_center().get("legacy_model_keys", {})
    return str(legacy.get(value) or value)

# 版本: v2.0.1 (2026-08-17) 更新: 新旧模型选择选项兼容
