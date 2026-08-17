from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Mapping


class AdapterType(StrEnum):
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class DiscoveryMode(StrEnum):
    OFFICIAL = "official"
    STANDARD = "standard"
    MANUAL = "manual"


class ModelStatus(StrEnum):
    AVAILABLE = "available"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    NOT_CHECKED = "not_checked"
    PREVIEW = "preview"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class ModelSource(StrEnum):
    OFFICIAL_API = "official_api"
    MANUAL = "manual"
    LEGACY = "legacy"
    PRESET = "preset"
    CACHE = "cache"


@dataclass(frozen=True, slots=True)
class ModelRef:
    provider_id: str
    model_id: str

    @property
    def value(self) -> str:
        return f"{self.provider_id}::{self.model_id}"

    @classmethod
    def parse(cls, value: str) -> "ModelRef":
        provider_id, separator, model_id = str(value or "").partition("::")
        if not separator or not provider_id or not model_id:
            raise ModelRefError(value=str(value or ""))
        return cls(provider_id=provider_id, model_id=model_id)


@dataclass(frozen=True, slots=True)
class ModelRefError(ValueError):
    value: str

    def __str__(self) -> str:
        return f"Invalid model reference: {self.value}"


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    context_window: int | None = None
    max_output_tokens: int | None = None
    supports_reasoning: bool | None = None
    supports_vision: bool | None = None
    supports_tools: bool | None = None
    supports_streaming: bool | None = None
    supports_text: bool | None = True
    supports_image: bool | None = None
    input_modalities: tuple[str, ...] = ("text",)
    output_modalities: tuple[str, ...] = ("text",)
    supported_parameters: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, object] | None) -> "ModelCapabilities":
        values = data or {}
        return cls(
            context_window=_optional_int(values.get("context_window")),
            max_output_tokens=_optional_int(values.get("max_output_tokens")),
            supports_reasoning=_optional_bool(values.get("supports_reasoning")),
            supports_vision=_optional_bool(values.get("supports_vision")),
            supports_tools=_optional_bool(values.get("supports_tools")),
            supports_streaming=_optional_bool(values.get("supports_streaming")),
            supports_text=_optional_bool(values.get("supports_text"), default=True),
            supports_image=_optional_bool(values.get("supports_image")),
            input_modalities=tuple(str(x) for x in values.get("input_modalities", ("text",))),
            output_modalities=tuple(str(x) for x in values.get("output_modalities", ("text",))),
            supported_parameters=tuple(str(x) for x in values.get("supported_parameters", ())),
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["input_modalities"] = list(self.input_modalities)
        data["output_modalities"] = list(self.output_modalities)
        data["supported_parameters"] = list(self.supported_parameters)
        return data


@dataclass(frozen=True, slots=True)
class AIProvider:
    provider_id: str
    name: str
    display_name: str
    adapter_type: AdapterType
    base_url: str
    env_key: str = ""
    enabled: bool = True
    discovery_mode: DiscoveryMode = DiscoveryMode.STANDARD
    discovery_url: str = ""
    credential_ref: str = ""
    status: ModelStatus = ModelStatus.NOT_CHECKED
    last_checked: str = ""
    last_error: str = ""

    @classmethod
    def from_dict(cls, provider_id: str, data: Mapping[str, object]) -> "AIProvider":
        return cls(
            provider_id=provider_id,
            name=str(data.get("name") or provider_id),
            display_name=str(data.get("display_name") or data.get("name") or provider_id),
            adapter_type=AdapterType(str(data.get("adapter_type") or "openai_compatible")),
            base_url=str(data.get("base_url") or "").rstrip("/"),
            env_key=str(data.get("env_key") or ""),
            enabled=bool(data.get("enabled", True)),
            discovery_mode=DiscoveryMode(str(data.get("discovery_mode") or "standard")),
            discovery_url=str(data.get("discovery_url") or ""),
            credential_ref=str(data.get("credential_ref") or f"provider:{provider_id}"),
            status=ModelStatus(str(data.get("status") or "not_checked")),
            last_checked=str(data.get("last_checked") or ""),
            last_error=str(data.get("last_error") or ""),
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["adapter_type"] = self.adapter_type.value
        data["discovery_mode"] = self.discovery_mode.value
        data["status"] = self.status.value
        data.pop("provider_id")
        return data


@dataclass(frozen=True, slots=True)
class AIModel:
    provider_id: str
    model_id: str
    display_name: str
    status: ModelStatus = ModelStatus.UNKNOWN
    source: ModelSource = ModelSource.MANUAL
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    created_at: str = ""
    updated_at: str = ""
    enabled: bool = True
    favorite: bool = False
    last_checked: str = ""
    latency_ms: int | None = None
    error_count: int = 0
    last_error: str = ""
    notes: str = ""

    @property
    def ref(self) -> ModelRef:
        return ModelRef(self.provider_id, self.model_id)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AIModel":
        return cls(
            provider_id=str(data.get("provider_id") or ""),
            model_id=str(data.get("model_id") or ""),
            display_name=str(data.get("display_name") or data.get("model_id") or ""),
            status=ModelStatus(str(data.get("status") or "unknown")),
            source=ModelSource(str(data.get("source") or "manual")),
            capabilities=ModelCapabilities.from_dict(data.get("capabilities")),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            enabled=bool(data.get("enabled", True)),
            favorite=bool(data.get("favorite", False)),
            last_checked=str(data.get("last_checked") or ""),
            latency_ms=_optional_int(data.get("latency_ms")),
            error_count=int(data.get("error_count") or 0),
            last_error=str(data.get("last_error") or ""),
            notes=str(data.get("notes") or ""),
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        data["source"] = self.source.value
        data["capabilities"] = self.capabilities.to_dict()
        return data


@dataclass(frozen=True, slots=True)
class HealthResult:
    ok: bool
    provider_id: str
    model_id: str
    latency_ms: int | None
    http_status: int | None
    message: str
    checked_at: str


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: object, default: bool | None = None) -> bool | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "supported"}

# 版本: v2.0.1 (2026-08-17) 更新: 动态 AI 模型域定义
