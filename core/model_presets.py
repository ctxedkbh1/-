ALL_CAPS = ["文本生成", "长文本", "中文能力", "逻辑分析", "润色", "总结", "结构分析"]

LEGACY_PRESETS = {
    "deepseek": {
        "name": "DeepSeek", "type": "openai_compatible",
        "base_url": "https://api.deepseek.com", "env_key": "DEEPSEEK_API_KEY",
        "model_id": "deepseek-chat", "price": 2,
        "capabilities": list(ALL_CAPS),
    },
    "openai": {
        "name": "OpenAI GPT", "type": "openai_compatible",
        "base_url": "https://api.openai.com/v1", "env_key": "OPENAI_API_KEY",
        "model_id": "gpt-4o-mini", "price": 4.4,
        "capabilities": list(ALL_CAPS),
    },
    "claude": {
        "name": "Anthropic Claude", "type": "claude",
        "base_url": "https://api.anthropic.com", "env_key": "ANTHROPIC_API_KEY",
        "model_id": "claude-sonnet-4-20250514", "price": 22,
        "capabilities": ["文本生成", "长文本", "逻辑分析", "润色", "总结", "结构分析"],
    },
    "gemini": {
        "name": "Google Gemini", "type": "gemini",
        "base_url": "https://generativelanguage.googleapis.com", "env_key": "GEMINI_API_KEY",
        "model_id": "gemini-2.0-flash", "price": 0.6,
        "capabilities": ["文本生成", "长文本", "逻辑分析", "总结", "结构分析"],
    },
    "qwen": {
        "name": "阿里通义千问 Qwen", "type": "openai_compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY", "model_id": "qwen-plus", "price": 1.1,
        "capabilities": list(ALL_CAPS),
    },
    "moonshot": {
        "name": "Moonshot Kimi", "type": "openai_compatible",
        "base_url": "https://api.moonshot.cn/v1", "env_key": "MOONSHOT_API_KEY",
        "model_id": "moonshot-v1-8k", "price": 12,
        "capabilities": list(ALL_CAPS),
    },
    "zhipu": {
        "name": "智谱 GLM", "type": "openai_compatible",
        "base_url": "https://open.bigmodel.cn/api/paas/v4", "env_key": "ZHIPU_API_KEY",
        "model_id": "glm-4-flash", "price": 0.1,
        "capabilities": list(ALL_CAPS),
    },
    "openrouter": {
        "name": "OpenRouter", "type": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1", "env_key": "OPENROUTER_API_KEY",
        "model_id": "openai/gpt-4o-mini", "price": 0.4,
        "capabilities": list(ALL_CAPS),
    },
    "ollama": {
        "name": "Ollama 本地模型", "type": "openai_compatible",
        "base_url": "http://localhost:11434/v1", "env_key": "",
        "model_id": "qwen2.5:7b", "price": 0,
        "capabilities": list(ALL_CAPS),
    },
}

# New installations get provider connection presets only. Model IDs come from
# official discovery or an explicit manual model entry.
PROVIDER_PRESETS = {}
for _key, _preset in LEGACY_PRESETS.items():
    _provider = dict(_preset)
    _provider["model_id"] = ""
    _provider["price"] = 0
    _provider["capabilities"] = []
    PROVIDER_PRESETS[_key] = _provider

# Compatibility name for callers that still need to read historical records.
PRESETS = LEGACY_PRESETS

# 版本: v2.0.1 (2026-08-17) 更新: 区分 Provider 预设与 Legacy Model 预设
