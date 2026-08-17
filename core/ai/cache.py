import datetime
import json
import os

from core.ai.domain import AIModel


class ModelCache:
    def __init__(self, path: str):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict[str, object]:
        if not os.path.exists(self.path):
            return {"providers": {}}
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("providers"), dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return {"providers": {}}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def update(self, provider_id: str, models: list[AIModel], fetched_at: str = "") -> None:
        providers = self.data.setdefault("providers", {})
        providers[provider_id] = {
            "fetched_at": fetched_at or datetime.datetime.now().isoformat(timespec="seconds"),
            "models": [model.to_dict() for model in models],
        }
        self._save()

    def models(self, provider_id: str) -> list[AIModel]:
        providers = self.data.get("providers", {})
        record = providers.get(provider_id, {}) if isinstance(providers, dict) else {}
        raw_models = record.get("models", []) if isinstance(record, dict) else []
        return [AIModel.from_dict(item) for item in raw_models if isinstance(item, dict)]

    def fetched_at(self, provider_id: str) -> str:
        providers = self.data.get("providers", {})
        record = providers.get(provider_id, {}) if isinstance(providers, dict) else {}
        return str(record.get("fetched_at") or "") if isinstance(record, dict) else ""

    def clear(self, provider_id: str) -> None:
        providers = self.data.get("providers", {})
        if isinstance(providers, dict) and provider_id in providers:
            providers.pop(provider_id)
            self._save()

# 版本: v2.0.1 (2026-08-17) 更新: AI 模型发现缓存
