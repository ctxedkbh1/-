import contextlib
import contextvars
import datetime
import re
import time

from core import log
from core.ai.credentials import CredentialStore, resolve_api_key
from core.ai.domain import (AIModel, AdapterType, HealthResult, ModelRef,
                            ModelStatus)
from core.ai.registry import ModelNotFoundError, ModelRegistry


_MODEL_OVERRIDES = contextvars.ContextVar("paper_assistant_model_overrides", default={})


class AIService:
    def __init__(self, config, registry: ModelRegistry, credentials: CredentialStore):
        self.config = config
        self.registry = registry
        self.credentials = credentials

    @contextlib.contextmanager
    def override_models(self, overrides: dict[str, str]):
        current = dict(_MODEL_OVERRIDES.get())
        current.update({key: value for key, value in (overrides or {}).items() if value})
        token = _MODEL_OVERRIDES.set(current)
        try:
            yield self
        finally:
            _MODEL_OVERRIDES.reset(token)

    def chat(self, task: str, messages: list[dict], temperature=0.7,
             json_mode=False, max_tokens=8000, timeout=600):
        from core.llm import DeepseekError, LLMError, build_provider

        errors = []
        for model in self._candidates(task):
            provider = self.registry.provider(model.provider_id)
            legacy_model = self.config.models().get(model.provider_id, {})
            api_key = resolve_api_key(
                provider, self.credentials, str(legacy_model.get("api_key") or "")
            )
            adapter = build_provider(self._adapter_config(provider, model, api_key))
            try:
                text = adapter.chat(
                    messages,
                    temperature=self._temperature(model, temperature),
                    json_mode=json_mode,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                if not text or not text.strip():
                    raise LLMError(f"{model.display_name}: 返回内容为空")
                log.get().info(
                    "模型调用成功 task=%s provider=%s model=%s",
                    task,
                    provider.provider_id,
                    model.model_id,
                )
                return text, model.ref
            except LLMError as exc:
                errors.append(f"{model.display_name}: {exc}")
                log.get().warning(
                    "模型调用失败，切换备用模型 task=%s provider=%s model=%s error=%s",
                    task,
                    provider.provider_id,
                    model.model_id,
                    exc,
                )
        if not errors:
            raise DeepseekError("没有可用模型，请先在【AI 模型中心】刷新或添加模型。")
        raise DeepseekError("所有候选模型均调用失败：" + "；".join(errors))

    def health_check(self, reference: str) -> HealthResult:
        from core.llm import build_provider

        model = self.registry.model(reference)
        provider = self.registry.provider(model.provider_id)
        legacy = self.config.models().get(model.provider_id, {})
        api_key = resolve_api_key(provider, self.credentials, str(legacy.get("api_key") or ""))
        adapter = build_provider(self._adapter_config(provider, model, api_key))
        started = time.perf_counter()
        result = adapter.health_check()
        latency = int((time.perf_counter() - started) * 1000)
        message = str(result.get("message") or "")
        match = re.search(r"HTTP\s+(\d{3})", message)
        return HealthResult(
            ok=bool(result.get("ok")),
            provider_id=provider.provider_id,
            model_id=model.model_id,
            latency_ms=latency,
            http_status=int(match.group(1)) if match else None,
            message=message,
            checked_at=datetime.datetime.now().isoformat(timespec="seconds"),
        )

    def _candidates(self, task: str) -> list[AIModel]:
        selected = str(_MODEL_OVERRIDES.get().get(task) or self.config.ai_task_model(task) or "auto")
        ordered = []
        if selected == "latest":
            ordered.extend(self.registry.latest_models())
        elif selected != "auto":
            try:
                ordered.append(self.registry.model(selected))
            except ModelNotFoundError:
                log.get().warning("任务指定模型不存在 task=%s reference=%s", task, selected)
        for provider in self.registry.providers(enabled_only=True):
            for model in self.registry.models(provider.provider_id):
                if model.ref.value not in {item.ref.value for item in ordered}:
                    ordered.append(model)
        return sorted(
            ordered,
            key=lambda model: (
                0 if selected == "latest" or model.ref.value == selected else 1,
                0 if model.favorite else 1,
                0 if model.status is ModelStatus.AVAILABLE else 1,
            ),
        )

    @staticmethod
    def _adapter_config(provider, model: AIModel, api_key: str) -> dict:
        match provider.adapter_type:
            case AdapterType.ANTHROPIC:
                provider_type = "claude"
            case AdapterType.GEMINI:
                provider_type = "gemini"
            case AdapterType.OPENAI | AdapterType.OPENAI_COMPATIBLE | AdapterType.OLLAMA:
                provider_type = "openai_compatible"
        return {
            "name": provider.display_name,
            "type": provider_type,
            "base_url": provider.base_url,
            "api_key": api_key,
            "env_key": "",
            "model_id": model.model_id,
            "capabilities": model.capabilities.to_dict(),
        }

    @staticmethod
    def _temperature(model: AIModel, value):
        supported = model.capabilities.supported_parameters
        if supported and "temperature" not in supported:
            return None
        return value

# 版本: v2.0.1 (2026-08-17) 更新: 统一 AIService 与模型上下文覆盖
