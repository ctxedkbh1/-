from dataclasses import replace

from core.ai.cache import ModelCache
from core.ai.domain import AIModel, AIProvider, ModelRef, ModelRefError


class ModelRegistry:
    def __init__(self, config, cache: ModelCache):
        self.config = config
        self.cache = cache

    def providers(self, enabled_only: bool = False) -> list[AIProvider]:
        records = self.config.ai_center().get("providers", {})
        providers = [
            AIProvider.from_dict(provider_id, data)
            for provider_id, data in records.items()
            if isinstance(data, dict)
        ]
        if enabled_only:
            providers = [provider for provider in providers if provider.enabled]
        return sorted(providers, key=lambda provider: provider.display_name.lower())

    def provider(self, provider_id: str) -> AIProvider:
        for provider in self.providers():
            if provider.provider_id == provider_id:
                return provider
        raise ProviderNotFoundError(provider_id=provider_id)

    def models(self, provider_id: str = "") -> list[AIModel]:
        merged: dict[str, AIModel] = {}
        provider_ids = [provider_id] if provider_id else [p.provider_id for p in self.providers()]
        for current_provider in provider_ids:
            for model in self.cache.models(current_provider):
                merged[model.ref.value] = model
        manual = self.config.ai_center().get("manual_models", {})
        for record in manual.values():
            if not isinstance(record, dict):
                continue
            model = AIModel.from_dict(record)
            if provider_id and model.provider_id != provider_id:
                continue
            existing = merged.get(model.ref.value)
            merged[model.ref.value] = self._merge(existing, model)
        favorites = set(self.config.ai_center().get("favorites", []))
        return sorted(
            [replace(model, favorite=model.ref.value in favorites) for model in merged.values()],
            key=lambda model: (not model.favorite, model.display_name.lower(), model.model_id),
        )

    def model(self, reference: str | ModelRef) -> AIModel:
        ref = reference if isinstance(reference, ModelRef) else self.resolve_ref(reference)
        for model in self.models(ref.provider_id):
            if model.model_id == ref.model_id:
                return model
        raise ModelNotFoundError(reference=ref.value)

    def resolve_ref(self, value: str) -> ModelRef:
        try:
            return ModelRef.parse(value)
        except ModelRefError:
            legacy = self.config.ai_center().get("legacy_model_keys", {})
            mapped = str(legacy.get(value) or "")
            if mapped:
                return ModelRef.parse(mapped)
            raise ModelNotFoundError(reference=value) from None

    def update_discovered(self, provider_id: str, models: list[AIModel]) -> None:
        self.provider(provider_id)
        self.cache.update(provider_id, models)

    def update_health(self, reference: str, result) -> None:
        ref = self.resolve_ref(reference)
        status = "available" if result.ok else "unavailable"
        cached = []
        for model in self.cache.models(ref.provider_id):
            if model.ref == ref:
                model = replace(
                    model,
                    status=type(model.status)(status),
                    last_checked=result.checked_at,
                    latency_ms=result.latency_ms,
                    error_count=0 if result.ok else model.error_count + 1,
                    last_error="" if result.ok else result.message,
                )
            cached.append(model)
        if cached:
            self.cache.update(ref.provider_id, cached, self.cache.fetched_at(ref.provider_id))
        manual = self.config.ai_center().get("manual_models", {})
        if ref.value in manual:
            record = manual[ref.value]
            record.update({
                "status": status,
                "last_checked": result.checked_at,
                "latency_ms": result.latency_ms,
                "error_count": 0 if result.ok else int(record.get("error_count") or 0) + 1,
                "last_error": "" if result.ok else result.message,
            })
            self.config.save()

    def set_favorite(self, reference: str, favorite: bool) -> None:
        ref = self.resolve_ref(reference).value
        center = self.config.ai_center()
        favorites = list(dict.fromkeys(str(x) for x in center.get("favorites", [])))
        if favorite and ref not in favorites:
            favorites.append(ref)
        if not favorite and ref in favorites:
            favorites.remove(ref)
        center["favorites"] = favorites
        self.config.save()

    def search(self, query: str = "", provider_id: str = "", capability: str = "") -> list[AIModel]:
        models = self.models(provider_id)
        needle = str(query or "").strip().lower()
        if needle:
            models = [model for model in models if needle in self._search_blob(model)]
        if capability:
            models = [model for model in models if self._supports(model, capability)]
        return models

    def task_reference(self, task: str, override: str = "") -> ModelRef | None:
        selected = override or str(self.config.ai_task_model(task) or "auto")
        if not selected or selected == "auto":
            return None
        return self.resolve_ref(selected)

    def latest_models(self, provider_id: str = "") -> list[AIModel]:
        models = self.models(provider_id)
        dated = [
            model for model in models
            if model.created_at and model.source.value == "official_api"
            and model.status.value == "available"
        ]
        return sorted(dated, key=lambda model: model.created_at, reverse=True)

    @staticmethod
    def _merge(discovered: AIModel | None, manual: AIModel) -> AIModel:
        if discovered is None:
            return manual
        return replace(
            discovered,
            display_name=manual.display_name or discovered.display_name,
            capabilities=manual.capabilities,
            favorite=manual.favorite,
            notes=manual.notes or discovered.notes,
        )

    @staticmethod
    def _search_blob(model: AIModel) -> str:
        caps = model.capabilities
        values = [
            model.display_name,
            model.model_id,
            model.provider_id,
            model.status.value,
            model.source.value,
            model.notes,
            "reasoning" if caps.supports_reasoning else "",
            "vision" if caps.supports_vision else "",
            "tools" if caps.supports_tools else "",
        ]
        return " ".join(values).lower()

    @staticmethod
    def _supports(model: AIModel, capability: str) -> bool:
        caps = model.capabilities
        mapping = {
            "reasoning": caps.supports_reasoning,
            "vision": caps.supports_vision,
            "tools": caps.supports_tools,
            "streaming": caps.supports_streaming,
            "text": caps.supports_text,
            "image": caps.supports_image,
            "long_context": bool(caps.context_window and caps.context_window >= 100_000),
            "favorite": model.favorite,
            "available": model.status.value == "available",
        }
        return mapping.get(capability, False) is True


class ProviderNotFoundError(KeyError):
    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        super().__init__(provider_id)


class ModelNotFoundError(KeyError):
    def __init__(self, reference: str):
        self.reference = reference
        super().__init__(reference)

# 版本: v2.0.1 (2026-08-17) 更新: AI 模型注册、搜索与任务选择
