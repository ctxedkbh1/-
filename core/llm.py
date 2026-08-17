import json
import os
import time

import requests

from core import log

TASK_LABELS = {
    "generation": "论文生成",
    "analysis": "结构分析",
    "polish": "文本优化",
    "check": "最终检查",
}

CAPABILITY_LABELS = ["文本生成", "长文本", "中文能力", "逻辑分析", "润色", "总结", "结构分析"]

TASK_CAPS = {
    "generation": ["文本生成", "中文能力", "长文本"],
    "analysis": ["结构分析", "逻辑分析", "中文能力"],
    "polish": ["润色", "中文能力"],
    "check": ["逻辑分析", "总结", "中文能力"],
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class LLMError(Exception):
    pass


class DeepseekError(LLMError):
    pass


class LLMProvider:
    def __init__(self, cfg_dict):
        self.cfg = cfg_dict or {}
        self.name = self.cfg.get("name", "未命名模型")
        self.model_id = self.cfg.get("model_id", "")
        self.base_url = (self.cfg.get("base_url") or "").rstrip("/")
        self.api_key = self._resolve_key()

    def _resolve_key(self):
        env_name = self.cfg.get("env_key", "")
        if env_name:
            v = os.environ.get(env_name, "").strip()
            if v:
                return v
        return str(self.cfg.get("api_key") or "").strip()

    def chat(self, messages, temperature=0.7, json_mode=False, max_tokens=8000,
             timeout=600):
        raise NotImplementedError

    def health_check(self):
        start = time.time()
        try:
            self.chat([{"role": "user", "content": "请回复：ok"}],
                      temperature=0, max_tokens=8, timeout=25)
            latency = round(time.time() - start, 1)
            return {"ok": True, "latency": latency,
                    "message": f"API 连接正常，模型可用，响应时间 {latency}s"}
        except LLMError as e:
            return {"ok": False, "latency": None, "message": f"API 调用失败：{e}"}
        except Exception as e:
            return {"ok": False, "latency": None, "message": f"API 调用失败：{e}"}


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI 兼容 API：DeepSeek / OpenAI / Qwen / Moonshot / 智谱 / OpenRouter / Ollama / 自定义。"""

    def chat(self, messages, temperature=0.7, json_mode=False, max_tokens=8000,
             timeout=600):
        if not self.base_url:
            raise LLMError(f"{self.name}: 未配置 Base URL")
        url = self.base_url + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model_id, "messages": messages,
                   "max_tokens": max_tokens}
        if temperature is not None:
            payload["temperature"] = temperature
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            raise LLMError(f"{self.name}: 网络错误: {e}")
        if r.status_code == 200:
            try:
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                raise LLMError(f"{self.name}: 响应解析失败: {e}")
        if r.status_code in (401, 403):
            hint = ""
            env_name = self.cfg.get("env_key") or ""
            if env_name and os.environ.get(env_name, "").strip():
                hint = (f"（注意：环境变量 {env_name} 已设置，会优先于界面填写的 Key）")
            raise LLMError(f"{self.name}: HTTP {r.status_code} 认证失败，API Key 无效或已过期。"
                           f"请到【AI 模型管理】编辑该模型，确认 Key 完整（无空格、无多余字符），"
                           f"并核对账户余额与权限。{hint}")
        raise LLMError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}")


class ClaudeProvider(LLMProvider):
    """Anthropic Messages API。"""

    def chat(self, messages, temperature=0.7, json_mode=False, max_tokens=8000,
             timeout=600):
        if not self.base_url:
            raise LLMError(f"{self.name}: 未配置 Base URL")
        if not self.api_key:
            raise LLMError(f"{self.name}: 未配置 API Key")
        url = self.base_url + "/v1/messages"
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        system = ""
        claude_msgs = []
        for m in messages:
            role = "assistant" if m.get("role") == "assistant" else "user"
            content = str(m.get("content") or "")
            if m.get("role") == "system":
                system += content + "\n"
            else:
                claude_msgs.append({"role": role, "content": content})
        payload = {"model": self.model_id, "max_tokens": max(64, int(max_tokens)),
                   "messages": claude_msgs}
        if temperature is not None:
            payload["temperature"] = temperature
        if system.strip():
            payload["system"] = system.strip()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            raise LLMError(f"{self.name}: 网络错误: {e}")
        if r.status_code == 200:
            try:
                blocks = r.json().get("content", [])
                return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            except Exception as e:
                raise LLMError(f"{self.name}: 响应解析失败: {e}")
        if r.status_code in (401, 403):
            raise LLMError(f"{self.name}: HTTP {r.status_code} 认证失败，API Key 无效或已过期。"
                           "请到【AI 模型管理】编辑该模型，检查 Key 是否完整并核对账户权限。")
        raise LLMError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}")


class GeminiProvider(LLMProvider):
    """Google Gemini API。"""

    def chat(self, messages, temperature=0.7, json_mode=False, max_tokens=8000,
             timeout=600):
        if not self.base_url:
            raise LLMError(f"{self.name}: 未配置 Base URL")
        if not self.api_key:
            raise LLMError(f"{self.name}: 未配置 API Key")
        url = (f"{self.base_url}/v1beta/models/{self.model_id}:generateContent")
        system = ""
        contents = []
        for m in messages:
            text = str(m.get("content") or "")
            if m.get("role") == "system":
                system += text + "\n"
            else:
                role = "model" if m.get("role") == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": text}]})
        generation_config = {"maxOutputTokens": max(64, int(max_tokens))}
        if temperature is not None:
            generation_config["temperature"] = temperature
        payload = {"contents": contents, "generationConfig": generation_config}
        if system.strip():
            payload["systemInstruction"] = {"parts": [{"text": system.strip()}]}
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            raise LLMError(f"{self.name}: 网络错误: {e}")
        if r.status_code == 200:
            try:
                cands = r.json().get("candidates", [])
                parts = cands[0]["content"]["parts"] if cands else []
                return "".join(p.get("text", "") for p in parts)
            except Exception as e:
                raise LLMError(f"{self.name}: 响应解析失败: {e}")
        if r.status_code in (401, 403):
            raise LLMError(f"{self.name}: HTTP {r.status_code} 认证失败，API Key 无效或已过期。"
                           "请到【AI 模型管理】编辑该模型，检查 Key 是否完整并核对账户权限。")
        raise LLMError(f"{self.name}: HTTP {r.status_code} {r.text[:200]}")


def build_provider(model_cfg):
    ptype = model_cfg.get("type") or "openai_compatible"
    if ptype == "claude":
        return ClaudeProvider(model_cfg)
    if ptype == "gemini":
        return GeminiProvider(model_cfg)
    return OpenAICompatibleProvider(model_cfg)


from core.ai.router import ModelRouter

# 版本: v2.0.1 (2026-08-17) 更新: Provider Adapter 与动态路由兼容入口
