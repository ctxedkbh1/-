import json
import os

from config.ai_schema import (ensure_ai_center, mapped_task_value,
                              remove_legacy_model, sync_legacy_model)
from core import paths
from core.model_presets import PRESETS


class ConfigManager:
    def __init__(self, path=None):
        self.path = path or paths.config_file()
        self.data = self._load()
        self._migrate()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, dict):
                        return d
            except Exception:
                pass
        return {}

    def _migrate(self):
        if "models" not in self.data:
            models = {}
            legacy_key = str(self.data.get("deepseek_api_key") or "")
            legacy_base = str(self.data.get("deepseek_base_url") or "")
            legacy_model = str(self.data.get("deepseek_model") or "")
            for key, preset in PRESETS.items():
                m = dict(preset)
                m["enabled"] = key == "deepseek"
                m["api_key"] = ""
                if key == "deepseek":
                    m["api_key"] = legacy_key
                    if legacy_base:
                        m["base_url"] = legacy_base
                    if legacy_model:
                        m["model_id"] = legacy_model
                models[key] = m
            self.data["models"] = models
            self.data.setdefault("tasks", {"generation": "auto", "analysis": "auto",
                                           "polish": "auto", "check": "auto"})
            self.data.setdefault("plans", {})
            self.data.setdefault("cost_limits",
                                 {"max_api_calls": 0, "max_tokens": 0, "max_budget": 0})
            self.data.setdefault("quality_provider",
                                 {"type": "internal", "name": "", "url": "", "api_key": ""})
            self.save()
        for key, preset in PRESETS.items():
            self.data["models"].setdefault(key, {**preset, "enabled": False, "api_key": ""})
        if ensure_ai_center(self.data):
            self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def reload(self):
        self.data = self._load()
        self._migrate()
        return self.data

    def get(self, key, default=""):
        return self.data.get(key, default)

    def get_int(self, key, default=0):
        try:
            return int(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def models(self):
        return self.data["models"]

    def enabled_model_keys(self):
        return [k for k, v in self.data["models"].items() if v.get("enabled")]

    def add_model(self, key, cfg):
        self.data["models"][key] = cfg
        sync_legacy_model(self.ai_center(), key, cfg)
        self.save()

    def remove_model(self, key):
        if key in self.data["models"]:
            del self.data["models"][key]
            remove_legacy_model(self.ai_center(), key)
            self.save()

    def task_model(self, task):
        return self.data.get("tasks", {}).get(task) or "auto"

    def set_task_model(self, task, model_key):
        self.data.setdefault("tasks", {})[task] = model_key
        mapped = mapped_task_value(self.ai_center(), model_key)
        self.ai_center().setdefault("task_defaults", {})[task] = mapped or "auto"
        self.save()

    def plans(self):
        return self.data.get("plans", {})

    def save_plan(self, name, assignment):
        self.data.setdefault("plans", {})[name] = assignment
        self.save()

    def remove_plan(self, name):
        self.data.get("plans", {}).pop(name, None)
        self.save()

    def cost_limits(self):
        return self.data.get("cost_limits") or {}

    def quality_provider(self):
        return self.data.get("quality_provider") or {}

    def ai_center(self):
        return self.data["ai_center"]

    def ai_providers(self):
        return self.ai_center().get("providers", {})

    def ai_manual_models(self):
        return self.ai_center().get("manual_models", {})

    def ai_task_model(self, task):
        value = self.ai_center().get("task_defaults", {}).get(task)
        return value or self.task_model(task)

    def set_ai_task_model(self, task, model_ref):
        self.ai_center().setdefault("task_defaults", {})[task] = model_ref or "auto"
        self.save()

    def save_ai_provider(self, provider_id, record):
        self.ai_center().setdefault("providers", {})[provider_id] = dict(record)
        self.save()

    def remove_ai_provider(self, provider_id):
        self.ai_center().setdefault("providers", {}).pop(provider_id, None)
        self.save()

    def save_ai_model(self, reference, record):
        self.ai_center().setdefault("manual_models", {})[reference] = dict(record)
        self.save()

    def remove_ai_model(self, reference):
        self.ai_center().setdefault("manual_models", {}).pop(reference, None)
        self.save()

    def api_key(self):
        m = self.data.get("models", {}).get("deepseek", {})
        env = os.environ.get(m.get("env_key", "DEEPSEEK_API_KEY"), "").strip()
        return env or str(m.get("api_key") or "").strip()

    def base_url(self):
        m = self.data.get("models", {}).get("deepseek", {})
        return str(m.get("base_url") or "https://api.deepseek.com")

    def model(self):
        m = self.data.get("models", {}).get("deepseek", {})
        return str(m.get("model_id") or "deepseek-chat")

    @staticmethod
    def mask_key(key):
        key = str(key or "").strip()
        if not key:
            return "（未设置）"
        if len(key) <= 8:
            return "*" * len(key)
        return key[:3] + "*" * (len(key) - 7) + key[-4:]

# 版本: v2.0.1 (2026-08-17) 更新: 动态 AI 模型中心兼容迁移
