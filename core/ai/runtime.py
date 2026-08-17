import os

from core.ai.cache import ModelCache
from core.ai.credentials import (CredentialError, NullCredentialStore,
                                 WindowsCredentialStore)
from core.ai.registry import ModelRegistry
from core.ai.service import AIService


def credential_store():
    try:
        return WindowsCredentialStore()
    except CredentialError:
        return NullCredentialStore()


def model_registry(config) -> ModelRegistry:
    cache_path = os.path.join(os.path.dirname(config.path), "models_cache.json")
    return ModelRegistry(config, ModelCache(cache_path))


def ai_service(config) -> AIService:
    registry = model_registry(config)
    return AIService(config, registry, credential_store())

# 版本: v2.0.1 (2026-08-17) 更新: AI 模型中心运行时工厂
