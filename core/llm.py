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
                   "temperature": temperature, "max_tokens": max_tokens}
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
                   "temperature": temperature, "messages": claude_msgs}
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
        payload = {"contents": contents,
                   "generationConfig": {"temperature": temperature,
                                        "maxOutputTokens": max(64, int(max_tokens))}}
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


class ModelRouter:
    """模型路由：按任务选择模型、失败自动切换备用模型、成本统计。"""

    def __init__(self, config):
        self.cfg = config
        self.task_overrides = {}
        self.usage = {"calls": 0, "tokens": 0, "cost": 0.0}
        self._usage_file = os.path.join(os.path.dirname(config.path), "api_usage.json")
        self.load_usage()

    def load_usage(self):
        try:
            if os.path.exists(self._usage_file):
                with open(self._usage_file, encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, dict):
                        self.usage.update(d)
        except Exception:
            pass

    def save_usage(self):
        try:
            with open(self._usage_file, "w", encoding="utf-8") as f:
                json.dump(self.usage, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def reset_usage(self):
        self.usage = {"calls": 0, "tokens": 0, "cost": 0.0}
        self.save_usage()

    def _refresh(self):
        try:
            self.cfg.data = self.cfg._load()
            self.cfg._migrate()
        except Exception:
            pass

    def limits(self):
        self._refresh()
        lim = self.cfg.data.get("cost_limits") or {}
        return {"max_api_calls": int(lim.get("max_api_calls") or 0),
                "max_tokens": int(lim.get("max_tokens") or 0),
                "max_budget": float(lim.get("max_budget") or 0)}

    def limits_reached(self):
        lim = self.limits()
        if lim["max_api_calls"] > 0 and self.usage["calls"] >= lim["max_api_calls"]:
            return f"已达到单次最大 API 调用次数（{lim['max_api_calls']}）"
        if lim["max_tokens"] > 0 and self.usage["tokens"] >= lim["max_tokens"]:
            return f"已达到单次最大 Token 数（{lim['max_tokens']}）"
        if lim["max_budget"] > 0 and self.usage["cost"] >= lim["max_budget"]:
            return f"已达到单次最大预算（{lim['max_budget']} 元，按估算）"
        return None

    def enabled_models(self):
        self._refresh()
        return [(k, v) for k, v in self.cfg.data.get("models", {}).items()
                if v.get("enabled")]

    def task_model(self, task):
        if self.task_overrides.get(task):
            return self.task_overrides[task]
        return self.cfg.data.get("tasks", {}).get(task) or "auto"

    def _score(self, key, model, task):
        caps = TASK_CAPS.get(task, [])
        model_caps = model.get("capabilities") or []
        score = 0
        for c in caps:
            if c in model_caps:
                score += 2
        if model.get("api_key") or model.get("env_key"):
            score += 1
        if task == "generation" and "中文能力" in model_caps:
            score += 1
        return score

    def _auto_pick(self, task):
        best, best_score = None, -1
        for key, model in self.enabled_models():
            s = self._score(key, model, task)
            if s > best_score:
                best, best_score = key, s
        return best

    def _candidates(self, task):
        assigned = self.task_model(task)
        ordered = []
        if assigned and assigned != "auto":
            ordered.append(assigned)
        elif assigned == "auto":
            auto = self._auto_pick(task)
            if auto:
                ordered.append(auto)
        for key, _ in self.enabled_models():
            if key not in ordered:
                ordered.append(key)
        return ordered

    def chat(self, task, messages, temperature=0.7, json_mode=False,
             max_tokens=8000, timeout=600):
        self._refresh()
        limit_hit = self.limits_reached()
        if limit_hit:
            raise DeepseekError(limit_hit)
        candidates = self._candidates(task)
        if not candidates:
            raise DeepseekError("没有可用的已启用模型，请先在【AI 模型管理】中配置并启用模型。")
        errors = []
        for key in candidates:
            model = self.cfg.data.get("models", {}).get(key)
            if not model:
                continue
            provider = build_provider(model)
            try:
                text = provider.chat(messages, temperature=temperature,
                                     json_mode=json_mode, max_tokens=max_tokens,
                                     timeout=timeout)
                if not text or not text.strip():
                    raise LLMError(f"{model.get('name')}: 返回内容为空")
                self._account(model, text)
                log.get().info("模型调用成功 task=%s model=%s", task, model.get("name"))
                return text, key
            except LLMError as e:
                errors.append(f"{model.get('name')}({key}): {e}")
                log.get().warning("模型调用失败，切换备用模型: %s", e)
                continue
        raise DeepseekError("所有已启用模型均调用失败：" + "；".join(errors))

    def _account(self, model, output_text):
        est_tokens = max(1, int(len(output_text) * 0.7))
        self.usage["calls"] += 1
        self.usage["tokens"] += est_tokens
        price = float(model.get("price") or 0)
        if price > 0:
            self.usage["cost"] += round(est_tokens / 1_000_000 * price, 6)
        self.save_usage()

    def health_check(self, model_key):
        self._refresh()
        model = self.cfg.data.get("models", {}).get(model_key)
        if not model:
            return {"ok": False, "latency": None, "message": "模型不存在"}
        return build_provider(model).health_check()

# 版本: v1.5.2 (2026-08-16) 更新: 401错误信息友好化提示
