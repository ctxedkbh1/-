import json
import os

from core.ai.cache import ModelCache
from core.ai.credentials import (CredentialError, NullCredentialStore,
                                 WindowsCredentialStore)
from core.ai.registry import ModelRegistry
from core.ai.service import AIService


class ModelRouter:
    """Backward-compatible router backed by the dynamic AIService."""

    def __init__(self, config):
        self.cfg = config
        self.task_overrides = {}
        self.usage = {"calls": 0, "tokens": 0, "cost": 0.0}
        data_dir = os.path.dirname(config.path)
        self._usage_file = os.path.join(data_dir, "api_usage.json")
        self.registry = ModelRegistry(config, ModelCache(os.path.join(data_dir, "models_cache.json")))
        try:
            credentials = WindowsCredentialStore()
        except CredentialError:
            credentials = NullCredentialStore()
        self.service = AIService(config, self.registry, credentials)
        self.load_usage()

    def load_usage(self):
        try:
            if os.path.exists(self._usage_file):
                with open(self._usage_file, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.usage.update(data)
        except (OSError, json.JSONDecodeError):
            return

    def save_usage(self):
        try:
            with open(self._usage_file, "w", encoding="utf-8") as f:
                json.dump(self.usage, f, ensure_ascii=False, indent=2)
        except OSError:
            return

    def reset_usage(self):
        self.usage = {"calls": 0, "tokens": 0, "cost": 0.0}
        self.save_usage()

    def _refresh(self):
        self.cfg.reload()

    def limits(self):
        self._refresh()
        limits = self.cfg.data.get("cost_limits") or {}
        return {
            "max_api_calls": int(limits.get("max_api_calls") or 0),
            "max_tokens": int(limits.get("max_tokens") or 0),
            "max_budget": float(limits.get("max_budget") or 0),
        }

    def limits_reached(self):
        limits = self.limits()
        if limits["max_api_calls"] > 0 and self.usage["calls"] >= limits["max_api_calls"]:
            return f"已达到单次最大 API 调用次数（{limits['max_api_calls']}）"
        if limits["max_tokens"] > 0 and self.usage["tokens"] >= limits["max_tokens"]:
            return f"已达到单次最大 Token 数（{limits['max_tokens']}）"
        if limits["max_budget"] > 0 and self.usage["cost"] >= limits["max_budget"]:
            return f"已达到单次最大预算（{limits['max_budget']} 元，按估算）"
        return None

    def enabled_models(self):
        self._refresh()
        return [
            (key, value)
            for key, value in self.cfg.data.get("models", {}).items()
            if value.get("enabled")
        ]

    def task_model(self, task):
        return self.task_overrides.get(task) or self.cfg.ai_task_model(task) or "auto"

    def chat(self, task, messages, temperature=0.7, json_mode=False,
             max_tokens=8000, timeout=600):
        from core.llm import DeepseekError

        self._refresh()
        limit_hit = self.limits_reached()
        if limit_hit:
            raise DeepseekError(limit_hit)
        with self.service.override_models(self.task_overrides):
            text, reference = self.service.chat(
                task,
                messages,
                temperature=temperature,
                json_mode=json_mode,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        legacy_key = self._legacy_key(reference.value)
        model = self.cfg.models().get(legacy_key or reference.provider_id, {})
        self._account(model, text)
        return text, legacy_key or reference.value

    def _legacy_key(self, reference: str) -> str:
        for key, value in self.cfg.ai_center().get("legacy_model_keys", {}).items():
            if value == reference:
                return key
        return ""

    def _account(self, model, output_text):
        estimated_tokens = max(1, int(len(output_text) * 0.7))
        self.usage["calls"] += 1
        self.usage["tokens"] += estimated_tokens
        price = float(model.get("price") or 0)
        if price > 0:
            self.usage["cost"] += round(estimated_tokens / 1_000_000 * price, 6)
        self.save_usage()

    def health_check(self, model_reference):
        try:
            result = self.service.health_check(model_reference)
        except (KeyError, RuntimeError) as exc:
            return {"ok": False, "latency": None, "message": str(exc)}
        return {
            "ok": result.ok,
            "latency": (result.latency_ms or 0) / 1000,
            "message": result.message,
            "provider": result.provider_id,
            "model": result.model_id,
            "http_status": result.http_status,
        }

# 版本: v2.0.1 (2026-08-17) 更新: AIService 兼容路由与成本统计
