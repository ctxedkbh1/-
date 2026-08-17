from core import deepseek, log
from core.prompts import RESEARCH_JSON_SPEC, WRITER_SYSTEM


def generate_plan(info):
    user_msg = (
        f"论文题目：{info.get('topic')}\n"
        f"专业：{info.get('major') or '未标注'}\n"
        f"课程名称：{info.get('course') or '未标注'}\n"
        f"学校：{info.get('school') or '未标注'}\n"
        f"字数要求：{info.get('word_count') or 3000} 字\n"
        "请解析题目（研究对象、核心问题、关键词、研究范围、时间范围），"
        "并给出可能使用的权威资料来源、需要检索的数据与学术论文方向。")
    resp = deepseek.chat([{"role": "system", "content": WRITER_SYSTEM},
                          {"role": "user", "content": user_msg + RESEARCH_JSON_SPEC}],
                         temperature=0.3, json_mode=True, task="search")
    data = deepseek.extract_json(resp)
    if not data or not isinstance(data.get("keywords"), list) or not data["keywords"]:
        raise deepseek.DeepseekError("AI 返回格式异常，请重试。")
    log.get().info("研究方案生成成功 关键词=%s", "、".join(data["keywords"]))
    return data


def plan_markdown(info, plan):
    lines = [
        "# 论文研究方案", "",
        f"论文题目：{info.get('topic')}",
        f"专业：{info.get('major') or '未标注'}　课程：{info.get('course') or '未标注'}",
        f"字数要求：{info.get('word_count') or 3000} 字", "",
        "## 一、研究对象", plan.get("subject", ""), "",
        "## 二、核心问题", plan.get("core_question", ""), "",
        "## 三、关键词", "、".join(plan.get("keywords", [])), "",
        "## 四、研究范围", plan.get("scope", ""), "",
        "## 五、时间范围", plan.get("time_range", ""), "",
        "## 六、可能使用的权威资料来源",
    ]
    lines += [f"- {x}" for x in plan.get("authoritative_sources", [])] or ["- （未列出）"]
    lines += ["", "## 七、需要检索的数据"]
    lines += [f"- {x}" for x in plan.get("data_needs", [])] or ["- （未列出）"]
    lines += ["", "## 八、需要检索的学术论文方向"]
    lines += [f"- {x}" for x in plan.get("paper_needs", [])] or ["- （未列出）"]
    return "\n".join(lines)

# 版本: v2.0.1 (2026-08-17) 更新: 联网检索模型任务路由
