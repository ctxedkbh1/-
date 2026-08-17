def ensure_ai_center(data):
    center = data.get("ai_center")
    if isinstance(center, dict):
        center.setdefault("schema_version", 1)
        center.setdefault("providers", {})
        center.setdefault("manual_models", {})
        center.setdefault("legacy_model_keys", {})
        defaults = center.setdefault("task_defaults", {})
        _expand_task_defaults(defaults)
        center.setdefault("mode_defaults", {})
        center.setdefault("favorites", [])
        center.setdefault("migration", {})
        return False

    providers = {}
    manual_models = {}
    legacy_model_keys = {}
    for key, model in data.get("models", {}).items():
        provider, manual, reference = legacy_records(key, model)
        providers[key] = provider
        if reference:
            legacy_model_keys[key] = reference
            manual_models[reference] = manual

    task_defaults = {}
    for task, value in data.get("tasks", {}).items():
        task_defaults[task] = legacy_model_keys.get(value, value or "auto")
    _expand_task_defaults(task_defaults)
    data["ai_center"] = {
        "schema_version": 1,
        "providers": providers,
        "manual_models": manual_models,
        "legacy_model_keys": legacy_model_keys,
        "task_defaults": task_defaults,
        "mode_defaults": {"advanced": "auto"},
        "favorites": [],
        "migration": {
            "legacy_detected": bool(data.get("models")),
            "credentials_migrated": False,
        },
    }
    return True


def sync_legacy_model(center, key, model):
    provider, manual, reference = legacy_records(key, model)
    center.setdefault("providers", {})[key] = provider
    if reference:
        center.setdefault("legacy_model_keys", {})[key] = reference
        center.setdefault("manual_models", {})[reference] = manual


def remove_legacy_model(center, key):
    center.get("providers", {}).pop(key, None)
    reference = center.get("legacy_model_keys", {}).pop(key, "")
    if reference:
        center.get("manual_models", {}).pop(reference, None)


def mapped_task_value(center, value):
    return center.get("legacy_model_keys", {}).get(value, value or "auto")


def _expand_task_defaults(defaults):
    defaults.setdefault("generation", "auto")
    defaults.setdefault("analysis", "auto")
    defaults.setdefault("polish", "auto")
    defaults.setdefault("check", "auto")
    defaults.setdefault("search", defaults.get("analysis", "auto"))
    defaults.setdefault("summary", defaults.get("analysis", "auto"))
    defaults.setdefault("quick_edit", defaults.get("polish", "auto"))
    defaults.setdefault("advanced", "auto")


def legacy_records(key, model):
    provider = {
        "name": str(model.get("name") or key),
        "display_name": str(model.get("name") or key),
        "adapter_type": adapter_type(key, model),
        "base_url": str(model.get("base_url") or ""),
        "env_key": str(model.get("env_key") or ""),
        "enabled": bool(model.get("enabled")),
        "discovery_mode": "manual" if key == "zhipu" else "standard",
        "discovery_url": "",
        "credential_ref": f"provider:{key}",
        "status": "not_checked",
        "last_checked": "",
        "last_error": "",
    }
    model_id = str(model.get("model_id") or "").strip()
    if not model_id:
        return provider, {}, ""
    reference = f"{key}::{model_id}"
    labels = list(model.get("capabilities") or [])
    manual = {
        "provider_id": key,
        "model_id": model_id,
        "display_name": str(model.get("name") or model_id),
        "status": "unknown",
        "source": "legacy",
        "capabilities": {
            "context_window": None,
            "max_output_tokens": None,
            "supports_reasoning": True if "逻辑分析" in labels else None,
            "supports_vision": None,
            "supports_tools": None,
            "supports_streaming": None,
            "supports_text": True,
            "supports_image": None,
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "supported_parameters": [],
        },
        "created_at": "",
        "updated_at": "",
        "favorite": False,
        "last_checked": "",
        "latency_ms": None,
        "error_count": 0,
        "last_error": "",
        "notes": "由旧模型配置迁移，能力状态未经官方模型接口确认。",
    }
    return provider, manual, reference


def adapter_type(key, model):
    model_type = str(model.get("type") or "openai_compatible")
    if model_type == "claude":
        return "anthropic"
    if model_type == "gemini":
        return "gemini"
    if key == "ollama":
        return "ollama"
    if key == "openai":
        return "openai"
    return "openai_compatible"

# 版本: v2.0.1 (2026-08-17) 更新: AI 模型中心配置 schema 与旧模型映射
