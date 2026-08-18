import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_known_issues_runtime_")


class FakeHandler(BaseHTTPRequestHandler):
    claude_payload = None
    claude_headers = None
    gemini_payload = None
    gemini_headers = None

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/releases/latest":
            self._json(200, {
                "tag_name": "v99.0.0",
                "name": "Test Release",
                "html_url": "https://github.com/ctxedkbh1/paper-workbench/releases/tag/v99.0.0",
                "published_at": "2026-08-18T00:00:00Z",
                "assets": [{
                    "name": "paperassistant-v99.0.0-full.zip",
                    "label": "Test full package",
                    "browser_download_url": (
                        "https://github.com/ctxedkbh1/paper-workbench/releases/download/"
                        "v99.0.0/paperassistant-v99.0.0-full.zip"),
                    "size": 123,
                }],
            })
            return
        if self.path == "/releases/error":
            self._json(503, {"message": "temporary unavailable"})
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path == "/v1/messages":
            type(self).claude_payload = payload
            type(self).claude_headers = dict(self.headers)
            self._json(200, {"content": [{"type": "text", "text": "claude-ok"}]})
            return
        if self.path == "/v1beta/models/gemini-test:generateContent":
            type(self).gemini_payload = payload
            type(self).gemini_headers = dict(self.headers)
            self._json(200, {
                "candidates": [{"content": {"parts": [{"text": "gemini-ok"}]}}],
            })
            return
        self.send_error(404)

    def log_message(self, _format, *_args):
        return


class FakeCheckpoint:
    def __init__(self, data=None, steps=None):
        self.values = dict(data or {})
        self.steps = dict(steps or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def status(self, key):
        return self.steps.get(key, "pending")

    def build_log_markdown(self):
        return "# Test log"


class FakeStore:
    def all(self):
        return []

    def verified_count(self):
        return 0

    def pending_count(self):
        return []

    def export_json(self):
        return "[]"


class FakeProject:
    def info(self):
        return {"topic": "Regression test"}

    def outline(self):
        return {"sections": []}


def test_data_migration():
    from core.data_migration import BACKUP_DIR, merge_legacy_data

    root = tempfile.mkdtemp(prefix="pa_data_migration_")
    first = os.path.join(root, "single", "paper_project")
    second = os.path.join(root, "full", "paper_project")
    target = os.path.join(root, "stable")
    os.makedirs(os.path.join(first, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(second, "chapters"), exist_ok=True)
    first_config = {"models": {"openai": {"api_key": "first-test-key"}}, "theme": "light"}
    second_config = {"models": {"claude": {"api_key": "second-test-key"}}, "theme": "dark"}
    with open(os.path.join(first, "config.json"), "w", encoding="utf-8") as handle:
        json.dump(first_config, handle)
    with open(os.path.join(second, "config.json"), "w", encoding="utf-8") as handle:
        json.dump(second_config, handle)
    with open(os.path.join(first, "chapters", "01.md"), "w", encoding="utf-8") as handle:
        handle.write("single version")
    with open(os.path.join(second, "chapters", "01.md"), "w", encoding="utf-8") as handle:
        handle.write("full version")

    report = merge_legacy_data(target, [first, second])
    with open(os.path.join(target, "config.json"), encoding="utf-8") as handle:
        merged = json.load(handle)
    assert merged["theme"] == "light"
    assert merged["models"]["openai"]["api_key"] == "first-test-key"
    assert merged["models"]["claude"]["api_key"] == "second-test-key"
    assert report["conflicts_backed_up"] >= 2
    backups = []
    for directory, _subdirs, files in os.walk(os.path.join(target, BACKUP_DIR)):
        backups.extend(os.path.join(directory, name) for name in files)
    assert any(path.endswith("config.json") for path in backups)
    assert any(path.endswith(os.path.join("chapters", "01.md")) for path in backups)
    assert os.path.exists(os.path.join(first, "config.json"))
    assert os.path.exists(os.path.join(second, "config.json"))


def test_providers_and_update_check(base_url):
    from core.llm import ClaudeProvider, GeminiProvider
    from core.updater import UpdateCheckError, check_for_update

    messages = [
        {"role": "system", "content": "Use evidence only."},
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Draft"},
    ]
    claude = ClaudeProvider({
        "name": "Claude test", "base_url": base_url, "api_key": "claude-test-key",
        "model_id": "claude-test",
    })
    assert claude.chat(messages, max_tokens=32) == "claude-ok"
    assert FakeHandler.claude_payload["model"] == "claude-test"
    assert FakeHandler.claude_payload["system"] == "Use evidence only."
    assert FakeHandler.claude_payload["messages"][1]["role"] == "assistant"
    assert FakeHandler.claude_headers["x-api-key"] == "claude-test-key"

    gemini = GeminiProvider({
        "name": "Gemini test", "base_url": base_url, "api_key": "gemini-test-key",
        "model_id": "gemini-test",
    })
    assert gemini.chat(messages, max_tokens=32) == "gemini-ok"
    assert FakeHandler.gemini_payload["systemInstruction"]["parts"][0]["text"] == "Use evidence only."
    assert FakeHandler.gemini_payload["contents"][1]["role"] == "model"
    assert FakeHandler.gemini_headers["x-goog-api-key"] == "gemini-test-key"

    result = check_for_update("2.2.0", base_url + "/releases/latest")
    assert result["update_available"] is True
    assert result["latest_version"] == "99.0.0"
    assert result["assets"][0]["name"] == "Test full package"
    try:
        check_for_update("2.2.0", base_url + "/releases/error")
    except UpdateCheckError as exc:
        assert "HTTP 503" in str(exc) and "temporary unavailable" in str(exc)
    else:
        raise AssertionError("HTTP errors must be shown to the user")


def test_factcheck_status_and_export_fallback():
    from core import auto_pipeline, paths, quality_report
    from core.auto_pipeline import AutoPipelineEngine

    checkpoint = FakeCheckpoint(
        data={
            "analysis2": {"unresolved": [], "bidirectional_ok": True, "annotation_ok": True},
            "style": {"template_score": "低"},
            "detection_final": {"ai_risk": 1, "repeat_risk": 1},
        },
        steps={"factcheck2": "skipped"},
    )
    engine = AutoPipelineEngine.__new__(AutoPipelineEngine)
    engine.checkpoint = checkpoint
    engine.store = FakeStore()
    engine.project = FakeProject()
    engine.input = {}
    engine.ai_limit = 20
    engine.repeat_limit = 20
    engine.max_rounds = 3
    engine.log = lambda *_args: None
    result = engine._result()
    assert result["factcheck_ok"] is False
    assert result["factcheck_status"] == "skipped"
    assert result["final_status"] == "自动判定未达标"

    report = quality_report.build(
        engine.project, engine.store, checkpoint.get("analysis2"), checkpoint.get("style"),
        0, [], 0, [], factcheck_status="skipped")
    assert "事实核查：未完成" in report
    assert "最终状态：自动判定未达标" in report
    assert "事实核查：✓ 通过" not in report

    blocked_parent = tempfile.mkdtemp(prefix="pa_output_blocked_")
    blocked = os.path.join(blocked_parent, "file")
    with open(blocked, "w", encoding="utf-8") as handle:
        handle.write("not a directory")
    engine.input = {"export_choice": "custom", "export_custom_path": os.path.join(blocked, "child")}
    original_export = auto_pipeline.exporter.export_files
    original_report = auto_pipeline.quality_report.build

    def fake_export(_project, _store, _analysis, _issues, _done, _total, _checks, out_dir):
        md_path = os.path.join(out_dir, "论文.md")
        report_path = os.path.join(out_dir, "资料核验报告.md")
        with open(md_path, "w", encoding="utf-8") as handle:
            handle.write("test")
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write("test")
        return {"md": md_path, "report": report_path}

    try:
        auto_pipeline.exporter.export_files = fake_export
        auto_pipeline.quality_report.build = lambda *_args, **_kwargs: "# Quality"
        engine._step_export()
    finally:
        auto_pipeline.exporter.export_files = original_export
        auto_pipeline.quality_report.build = original_report
    assert os.path.dirname(checkpoint.get("export_paths")["md"]) == paths.output_dir()


def main():
    test_data_migration()
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        test_providers_and_update_check(base_url)
        test_factcheck_status_and_export_fallback()
    finally:
        server.shutdown()
        server.server_close()
    print("KNOWN ISSUES REGRESSION TEST OK")


if __name__ == "__main__":
    main()

# 版本: v2.3.0 (2026-08-19) 更新: 已知问题离线回归测试
