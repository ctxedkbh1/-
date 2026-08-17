import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeAIHandler(BaseHTTPRequestHandler):
    models_requested = 0
    requested_models = []

    def do_GET(self):
        if self.path == "/v1/models":
            type(self).models_requested += 1
            body = json.dumps({
                "object": "list",
                "data": [{
                    "id": "future-model-x",
                    "object": "model",
                    "owned_by": "test-provider",
                    "created": 2000000000,
                }],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).requested_models.append(payload.get("model"))
        body = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def main():
    data_dir = tempfile.mkdtemp(prefix="pa_ai_center_")
    os.environ["PAPER_PROJECT_DIR"] = data_dir
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/v1"

    try:
        config_path = os.path.join(data_dir, "config.json")
        legacy = {
            "deepseek_api_key": "different-legacy-key",
            "models": {
                "custom": {
                    "name": "Custom Provider",
                    "type": "openai_compatible",
                    "base_url": base_url,
                    "api_key": "legacy-secret",
                    "env_key": "",
                    "model_id": "old-model",
                    "price": 0,
                    "capabilities": ["文本生成"],
                    "enabled": True,
                }
            },
            "tasks": {"generation": "custom"},
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(legacy, f, ensure_ascii=False, indent=2)

        from config.manager import ConfigManager
        from core.ai.cache import ModelCache
        from core.ai.credentials import (MemoryCredentialStore,
                                         migrate_legacy_credentials,
                                         resolve_api_key)
        from core.ai.discovery import ModelDiscovery, normalize_models_url
        from core.ai.domain import AIProvider, ModelRef, ModelSource, ModelStatus
        from core.ai.registry import ModelRegistry
        from core.ai.service import AIService

        ref = ModelRef(provider_id="custom", model_id="future-model-x")
        assert ModelRef.parse(ref.value) == ref
        assert normalize_models_url("https://api.deepseek.com") == "https://api.deepseek.com/models"
        assert normalize_models_url("https://api.example.com/v1") == "https://api.example.com/v1/models"

        cfg = ConfigManager(config_path)
        center = cfg.ai_center()
        assert center["schema_version"] == 1
        assert center["legacy_model_keys"]["custom"] == "custom::old-model"
        assert cfg.models()["custom"]["api_key"] == "legacy-secret"
        assert cfg.save_ai_model("custom::old-model", {"model_id": "replacement"}) is False
        assert cfg.ai_manual_models()["custom::old-model"]["model_id"] == "old-model"

        secrets = MemoryCredentialStore()
        report = migrate_legacy_credentials(cfg, secrets)
        assert report.migrated == 2
        assert cfg.models()["custom"]["api_key"] == ""
        assert cfg.get("deepseek_api_key") == ""
        assert secrets.get("provider:custom") == "legacy-secret"
        deepseek_provider = AIProvider.from_dict(
            "deepseek",
            {"credential_ref": "provider:deepseek", "base_url": "https://api.deepseek.com"},
        )
        secrets.set("legacy:deepseek:top-level", "top-level-secret")
        assert resolve_api_key(deepseek_provider, secrets) == "top-level-secret"

        cache = ModelCache(os.path.join(data_dir, "models_cache.json"))
        registry = ModelRegistry(cfg, cache)
        provider = registry.provider("custom")
        discovered = ModelDiscovery().discover(provider, secrets.get("provider:custom"))
        assert len(discovered) == 1
        model = discovered[0]
        assert model.model_id == "future-model-x"
        assert model.source is ModelSource.OFFICIAL_API
        assert model.status is ModelStatus.AVAILABLE
        assert model.capabilities.context_window is None
        registry.update_discovered("custom", discovered)
        assert cache.models("custom")[0].model_id == "future-model-x"
        registry.set_model_enabled(ref.value, False)
        assert registry.model(ref).enabled is False
        registry.set_model_enabled(ref.value, True)
        assert registry.model(ref).enabled is True

        cfg.set_ai_task_model("generation", ref.value)
        service = AIService(cfg, registry, secrets)
        text, used = service.chat(
            "generation", [{"role": "user", "content": "hello"}], max_tokens=8
        )
        assert text == "ok"
        assert used == ref
        assert FakeAIHandler.requested_models[-1] == "future-model-x"

        old_ref = ModelRef(provider_id="custom", model_id="old-model")
        with service.override_models({"generation": old_ref.value}):
            service.chat("generation", [{"role": "user", "content": "override"}], max_tokens=8)
        service.chat("generation", [{"role": "user", "content": "again"}], max_tokens=8)
        assert FakeAIHandler.requested_models[-2:] == ["old-model", "future-model-x"]
        cfg.set_ai_task_model("generation", "latest")
        service.chat("generation", [{"role": "user", "content": "latest"}], max_tokens=8)
        assert FakeAIHandler.requested_models[-1] == "future-model-x"
        assert FakeAIHandler.models_requested == 1
        registry.delete_model(ref.value)
        assert all(model.ref.value != ref.value for model in registry.models("custom"))
        print("AI CENTER TEST OK")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

# 版本: v2.0.1 (2026-08-17) 更新: AI 模型中心回归测试
