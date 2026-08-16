import datetime

import requests

from core import log, style_checker


class TextQualityProvider:
    """AI 文本风险分析统一接口（第三方服务接入点）。"""

    def analyze(self, full_text, style=None):
        raise NotImplementedError


class SimilarityProvider:
    """重复/相似内容检测统一接口（第三方服务接入点）。"""

    def analyze(self, full_text, style=None):
        raise NotImplementedError


class InternalQualityProvider(TextQualityProvider, SimilarityProvider):
    """内置启发式分析（非任何第三方检测平台结果）。"""

    name = "内部分析"

    def analyze(self, full_text, style=None):
        style = style or style_checker.analyze(full_text)
        return style_checker.risk_percent(style)


class CustomHttpProvider(TextQualityProvider, SimilarityProvider):
    """自定义检测 API：POST 文本，期望返回 {"ai_risk": n, "repeat_risk": n}（0-100）。

    仅用于用户自行提供的正规 API。程序不会模拟任何无公开 API 的第三方网站接口。
    """

    def __init__(self, cfg):
        self.cfg = cfg or {}
        self.name = self.cfg.get("name") or "自定义检测服务"

    def analyze(self, full_text, style=None):
        url = (self.cfg.get("url") or "").strip()
        if not url:
            raise DetectionError("自定义检测服务未配置 URL")
        headers = {"Content-Type": "application/json"}
        key = (self.cfg.get("api_key") or "").strip()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        try:
            r = requests.post(url, headers=headers,
                              json={"text": full_text}, timeout=60)
            r.raise_for_status()
            data = r.json()
            return {
                "ai_risk": int(data.get("ai_risk", 0)),
                "repeat_risk": int(data.get("repeat_risk", 0)),
            }
        except requests.RequestException as e:
            raise DetectionError(f"检测服务网络错误: {e}")
        except (ValueError, KeyError, TypeError) as e:
            raise DetectionError(f"检测服务响应格式异常: {e}")


class DetectionError(Exception):
    pass


def get_provider(config=None):
    from config.manager import ConfigManager
    cfg = (config or ConfigManager()).quality_provider() or {}
    if cfg.get("type") == "custom":
        return CustomHttpProvider(cfg)
    return InternalQualityProvider()


def detect(full_text, style=None, config=None):
    """统一检测入口：根据配置选择检测 Provider。

    未接入真实第三方检测 API 时，结果明确标注为"内部分析值"，
    绝不把内部估算伪装成任何检测平台的官方结果。
    """
    style = style or style_checker.analyze(full_text)
    provider = get_provider(config)
    external = not isinstance(provider, InternalQualityProvider)
    try:
        risks = provider.analyze(full_text, style)
    except DetectionError as e:
        log.get().warning("外部检测服务失败，回退到内部分析: %s", e)
        risks = InternalQualityProvider().analyze(full_text, style)
        external = False
    ai_risk = max(0, min(100, int(risks.get("ai_risk", 0))))
    repeat_risk = max(0, min(100, int(risks.get("repeat_risk", 0))))
    result = {
        "source": "external" if external else "internal",
        "service": provider.name,
        "detected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ai_risk": ai_risk,
        "repeat_risk": repeat_risk,
    }
    log.get().info("风险检测完成 source=%s service=%s ai=%s repeat=%s",
                   result["source"], result["service"], ai_risk, repeat_risk)
    return result


def source_label(detection):
    if detection.get("source") == "external":
        return f"{detection.get('service', '外部检测服务')}（{detection.get('detected_at', '')}）"
    return "内部分析值（非第三方检测平台结果）"

# 版本: v1.5.0 (2026-08-16) 更新: 多模型供应商系统
