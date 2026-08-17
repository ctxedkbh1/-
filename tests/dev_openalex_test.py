import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = "rate limited" if status_code == 429 else ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def main():
    from sources import openalex

    calls = []
    responses = [
        FakeResponse(429, headers={"Retry-After": "0"}),
        FakeResponse(429, headers={"Retry-After": "0"}),
        FakeResponse(200, {"results": [{"display_name": "Recovered paper"}]}),
    ]

    def fake_get(url, params, headers, timeout):
        calls.append((url, params, headers, timeout))
        return responses.pop(0)

    original_get = openalex.requests.get
    original_interval = openalex.MIN_REQUEST_INTERVAL
    old_mailto = os.environ.get("OPENALEX_MAILTO")
    try:
        openalex.requests.get = fake_get
        openalex.MIN_REQUEST_INTERVAL = 0
        os.environ["OPENALEX_MAILTO"] = "research@example.com"
        records = openalex.search("恢复测试", per_page=5)
        assert len(records) == 1
        assert records[0]["title"] == "Recovered paper"
        assert len(calls) == 3
        assert calls[0][1]["mailto"] == "research@example.com"
        assert calls[0][2]["User-Agent"].startswith("PaperAssistant/")

        responses.extend([FakeResponse(429, headers={"Retry-After": "0"}) for _ in range(4)])
        try:
            openalex.search("持续限流", per_page=5)
        except openalex.SourceError as exc:
            assert "429" in str(exc)
        else:
            raise AssertionError("持续 429 应转换为可操作的 SourceError")
        assert len(calls) == 7
        print("OPENALEX TEST OK")
    finally:
        openalex.requests.get = original_get
        openalex.MIN_REQUEST_INTERVAL = original_interval
        if old_mailto is None:
            os.environ.pop("OPENALEX_MAILTO", None)
        else:
            os.environ["OPENALEX_MAILTO"] = old_mailto


if __name__ == "__main__":
    main()

# 版本: v2.1.2 (2026-08-18) 更新: OpenAlex 429 限流恢复测试
