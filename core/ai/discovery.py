import datetime
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests

from core.ai.domain import (AIModel, AIProvider, AdapterType, DiscoveryMode,
                            ModelCapabilities, ModelSource, ModelStatus)


@dataclass(frozen=True, slots=True)
class DiscoveryError(RuntimeError):
    provider_id: str
    message: str
    http_status: int | None = None

    def __str__(self) -> str:
        status = f"HTTP {self.http_status} " if self.http_status else ""
        return f"{self.provider_id}: {status}{self.message}"


class ModelDiscovery:
    def discover(self, provider: AIProvider, api_key: str = "") -> list[AIModel]:
        if provider.discovery_mode is DiscoveryMode.MANUAL:
            raise DiscoveryError(provider.provider_id, "Provider 未提供已确认的官方模型列表接口")
        match provider.adapter_type:
            case AdapterType.ANTHROPIC:
                return self._anthropic(provider, api_key)
            case AdapterType.GEMINI:
                return self._gemini(provider, api_key)
            case AdapterType.OLLAMA:
                return self._ollama(provider)
            case AdapterType.OPENAI | AdapterType.OPENAI_COMPATIBLE:
                return self._openai_compatible(provider, api_key)

    def _request(self, provider: AIProvider, url: str, headers: dict[str, str]) -> dict:
        try:
            response = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as exc:
            raise DiscoveryError(provider.provider_id, f"网络错误: {exc}") from exc
        if response.status_code != 200:
            message = _safe_error(response)
            raise DiscoveryError(provider.provider_id, message, response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise DiscoveryError(provider.provider_id, "模型列表响应不是有效 JSON") from exc
        if not isinstance(data, dict):
            raise DiscoveryError(provider.provider_id, "模型列表响应结构无效")
        return data

    def _openai_compatible(self, provider: AIProvider, api_key: str) -> list[AIModel]:
        url = normalize_models_url(provider.discovery_url or provider.base_url)
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = self._request(provider, url, headers)
        records = payload.get("data", [])
        return [self._openai_model(provider, item) for item in records if isinstance(item, dict)]

    def _openai_model(self, provider: AIProvider, item: dict) -> AIModel:
        model_id = str(item.get("id") or "")
        architecture = item.get("architecture") if isinstance(item.get("architecture"), dict) else {}
        input_modalities = tuple(str(x) for x in architecture.get("input_modalities", ["text"]))
        output_modalities = tuple(str(x) for x in architecture.get("output_modalities", ["text"]))
        supported = tuple(str(x) for x in item.get("supported_parameters", []))
        reasoning = item.get("reasoning")
        context_window = _int_or_none(item.get("context_length"))
        top_provider = item.get("top_provider") if isinstance(item.get("top_provider"), dict) else {}
        max_output = _int_or_none(top_provider.get("max_completion_tokens"))
        created_at = _timestamp(item.get("created"))
        return AIModel(
            provider_id=provider.provider_id,
            model_id=model_id,
            display_name=str(item.get("name") or model_id),
            status=ModelStatus.AVAILABLE,
            source=ModelSource.OFFICIAL_API,
            capabilities=ModelCapabilities(
                context_window=context_window,
                max_output_tokens=max_output,
                supports_reasoning=True if reasoning else (True if "reasoning" in supported else None),
                supports_vision=True if "image" in input_modalities else None,
                supports_tools=True if "tools" in supported else None,
                supports_streaming=True if "stream" in supported else None,
                supports_text=True if "text" in input_modalities else None,
                supports_image=True if "image" in output_modalities else None,
                input_modalities=input_modalities,
                output_modalities=output_modalities,
                supported_parameters=supported,
            ),
            created_at=created_at,
            updated_at=str(item.get("expiration_date") or item.get("shutdown_date") or ""),
            notes=str(item.get("description") or ""),
        )

    def _anthropic(self, provider: AIProvider, api_key: str) -> list[AIModel]:
        url = provider.discovery_url or provider.base_url.rstrip("/") + "/v1/models"
        headers = {"anthropic-version": "2023-06-01", "x-api-key": api_key}
        models = []
        after_id = ""
        while True:
            page_url = url + ("?" + urlencode({"after_id": after_id, "limit": 100}) if after_id else "?limit=100")
            payload = self._request(provider, page_url, headers)
            for item in payload.get("data", []):
                if isinstance(item, dict):
                    models.append(self._anthropic_model(provider, item))
            if not payload.get("has_more") or not payload.get("last_id"):
                return models
            after_id = str(payload["last_id"])

    def _anthropic_model(self, provider: AIProvider, item: dict) -> AIModel:
        caps = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
        thinking = caps.get("thinking") if isinstance(caps.get("thinking"), dict) else {}
        return AIModel(
            provider_id=provider.provider_id,
            model_id=str(item.get("id") or ""),
            display_name=str(item.get("display_name") or item.get("id") or ""),
            status=ModelStatus.AVAILABLE,
            source=ModelSource.OFFICIAL_API,
            capabilities=ModelCapabilities(
                context_window=_int_or_none(item.get("max_input_tokens")),
                max_output_tokens=_int_or_none(item.get("max_tokens")),
                supports_reasoning=_supported(thinking),
                supports_vision=_supported(caps.get("image_input")),
                supports_tools=_supported(caps.get("code_execution")),
                supports_streaming=None,
                supports_text=True,
                supports_image=False,
                input_modalities=("text", "image") if _supported(caps.get("image_input")) else ("text",),
                supported_parameters=(),
            ),
            created_at=str(item.get("created_at") or ""),
        )

    def _gemini(self, provider: AIProvider, api_key: str) -> list[AIModel]:
        url = provider.discovery_url or provider.base_url.rstrip("/") + "/v1beta/models"
        headers = {"x-goog-api-key": api_key}
        models = []
        token = ""
        while True:
            page_url = url + ("?" + urlencode({"pageToken": token}) if token else "")
            payload = self._request(provider, page_url, headers)
            for item in payload.get("models", []):
                if isinstance(item, dict):
                    models.append(self._gemini_model(provider, item))
            token = str(payload.get("nextPageToken") or "")
            if not token:
                return models

    def _gemini_model(self, provider: AIProvider, item: dict) -> AIModel:
        model_id = str(item.get("name") or "").removeprefix("models/")
        methods = tuple(str(x) for x in item.get("supportedGenerationMethods", []))
        return AIModel(
            provider_id=provider.provider_id,
            model_id=model_id,
            display_name=str(item.get("displayName") or model_id),
            status=ModelStatus.AVAILABLE,
            source=ModelSource.OFFICIAL_API,
            capabilities=ModelCapabilities(
                context_window=_int_or_none(item.get("inputTokenLimit")),
                max_output_tokens=_int_or_none(item.get("outputTokenLimit")),
                supports_reasoning=_bool_or_none(item.get("thinking")),
                supports_streaming=True if "streamGenerateContent" in methods else None,
                supports_text=True,
                supported_parameters=methods,
            ),
            notes=str(item.get("description") or ""),
        )

    def _ollama(self, provider: AIProvider) -> list[AIModel]:
        root = provider.base_url.rstrip("/").removesuffix("/v1")
        payload = self._request(provider, provider.discovery_url or root + "/api/tags", {})
        models = []
        for item in payload.get("models", []):
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("model") or item.get("name") or "")
            details = item.get("details") if isinstance(item.get("details"), dict) else {}
            note = " / ".join(str(details.get(k)) for k in ("family", "parameter_size", "quantization_level") if details.get(k))
            models.append(AIModel(
                provider_id=provider.provider_id,
                model_id=model_id,
                display_name=model_id,
                status=ModelStatus.AVAILABLE,
                source=ModelSource.OFFICIAL_API,
                capabilities=ModelCapabilities(),
                updated_at=str(item.get("modified_at") or ""),
                notes=note,
            ))
        return models


def _safe_error(response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("type") or "请求失败")[:300]
    except ValueError:
        pass
    return str(response.text or "请求失败")[:300]


def normalize_models_url(value: str) -> str:
    """Treat a provider base URL as a base, not as the completed list endpoint."""
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return ""
    parts = urlsplit(raw)
    path = parts.path.rstrip("/")
    if path.lower().endswith("/models"):
        return raw
    if path in {"", "/"} or path.lower().endswith("/v1"):
        return urlunsplit((parts.scheme, parts.netloc, path + "/models", parts.query, ""))
    return raw


def _timestamp(value) -> str:
    try:
        return datetime.datetime.fromtimestamp(int(value), datetime.timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _int_or_none(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _supported(value) -> bool | None:
    return bool(value.get("supported")) if isinstance(value, dict) and "supported" in value else None


def _bool_or_none(value) -> bool | None:
    return value if isinstance(value, bool) else None

# 版本: v2.0.1 (2026-08-17) 更新: Provider 官方模型动态发现
