"""AI 调用入口：通过 ModelRouter 按任务路由到配置的模型。

论文生成逻辑与具体模型供应商彻底解耦：
- 所有模块调用 deepseek.chat(..., task="generation|analysis|polish|check")
- 模型选择、故障切换、成本统计由 core.llm.ModelRouter 完成
- 增加新模型只需在【AI 模型管理】中配置，无需修改论文生成逻辑
"""

from config.manager import ConfigManager
from core import log
from core.llm import LLMError, DeepseekError, ModelRouter

_router = None


def get_router():
    global _router
    if _router is None:
        _router = ModelRouter(ConfigManager())
    return _router


def chat(messages, temperature=0.7, json_mode=False, max_tokens=8000, timeout=600,
         task="generation"):
    r = get_router()
    text, model_key = r.chat(task, messages, temperature=temperature,
                             json_mode=json_mode, max_tokens=max_tokens,
                             timeout=timeout)
    return text


def set_task_models(overrides):
    """设置任务级模型覆盖（自动任务使用，覆盖配置中的默认任务模型）。"""
    get_router().task_overrides = dict(overrides or {})


def limits_reached():
    return get_router().limits_reached()


def usage():
    return dict(get_router().usage)


def reset_usage():
    get_router().reset_usage()


def extract_json(text):
    import json
    import re
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None

# 版本: v1.5.0 (2026-08-16) 更新: 多模型供应商系统
