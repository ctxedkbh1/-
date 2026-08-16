import datetime
import json
import os

from core import paths


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class AutoCheckpoint:
    """全自动任务断点：每一步完成后立即落盘，崩溃后可恢复。"""

    def __init__(self, data_dir=None):
        self.path = os.path.join(data_dir or paths.data_dir(), "auto_checkpoint.json")
        self.data = self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, dict):
                        return d
            except Exception:
                pass
        return {}

    def exists(self):
        return bool(self.data)

    def has_unfinished(self):
        return self.exists() and not self.data.get("finished", False)

    def create(self, input_data):
        from core.history import new_task_id
        tasks_dir = os.path.join(os.path.dirname(self.path), "tasks")
        task_id = new_task_id()
        while os.path.exists(os.path.join(tasks_dir, f"{task_id}.json")):
            task_id = new_task_id()
        self.data = {
            "task_id": task_id,
            "input": dict(input_data),
            "steps": {},
            "chapters_done": [],
            "started_at": _now(),
            "updated_at": _now(),
            "finished": False,
            "log_entries": [],
            "data": {},
        }
        self.save()

    def clear(self):
        self.data = {}
        if os.path.exists(self.path):
            try:
                os.remove(self.path)
            except OSError:
                pass

    def save(self):
        self.data["updated_at"] = _now()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_log(self, msg, level="INFO"):
        entries = self.data.setdefault("log_entries", [])
        entries.append({"at": _now(), "level": level, "msg": str(msg)})
        self.data["log_entries"] = entries[-500:]
        self.save()

    def status(self, key):
        return (self.data.get("steps", {}).get(key) or {}).get("status", "pending")

    def is_done(self, key):
        return self.status(key) == "done"

    def set_step(self, key, status, detail="", msg=""):
        self.data.setdefault("steps", {})[key] = {
            "status": status, "detail": str(detail), "msg": str(msg), "at": _now()}
        self.save()

    def mark_done(self, key, detail=""):
        self.set_step(key, "done", detail)
        self.add_log(f"步骤完成: {key} {detail}")

    def mark_failed(self, key, msg):
        self.set_step(key, "failed", msg=msg)
        self.add_log(f"步骤失败: {key} - {msg}", "ERROR")

    def mark_skipped(self, key, reason):
        self.set_step(key, "skipped", reason, reason)
        self.add_log(f"步骤跳过: {key} - {reason}", "WARN")

    def reset_steps(self, keys):
        """将指定步骤重置为待执行（用于"继续优化"等续跑场景）。"""
        steps = self.data.setdefault("steps", {})
        for key in keys:
            steps.pop(key, None)
        self.add_log(f"已重置步骤以继续优化: {'、'.join(keys)}")
        self.save()

    def get(self, key, default=None):
        return self.data.get("data", {}).get(key, default)

    def set(self, key, value):
        self.data.setdefault("data", {})[key] = value
        self.save()

    def append(self, key, value):
        lst = self.data.setdefault("data", {}).setdefault(key, [])
        if value not in lst:
            lst.append(value)
            self.save()

    def done_count(self):
        return sum(1 for v in self.data.get("steps", {}).values() if v.get("status") == "done")

    def mark_finished(self):
        self.data["finished"] = True
        self.data["finished_at"] = _now()
        self.save()

    def build_log_markdown(self):
        d = self.data
        if not d:
            return "# 全自动运行日志\n\n（无记录）"
        lines = ["# 全自动运行日志", "",
                 f"- 任务 ID：{d.get('task_id', '')}",
                 f"- 开始时间：{d.get('started_at', '')}",
                 f"- 结束时间：{d.get('finished_at', '未完成')}",
                 f"- 状态：{'已完成' if d.get('finished') else '未完成（可断点恢复）'}",
                 "", "## 步骤记录", "", "| 步骤 | 状态 | 说明 |", "| --- | --- | --- |"]
        for key, v in d.get("steps", {}).items():
            lines.append(f"| {key} | {v.get('status', '')} | "
                         f"{(v.get('detail') or v.get('msg') or '').replace('|', '｜')} |")
        lines += ["", "## 运行日志", ""]
        for e in d.get("log_entries", []):
            lines.append(f"- [{e.get('at')}] [{e.get('level')}] {e.get('msg')}")
        extra = d.get("data", {})
        if extra.get("insufficient_chapters"):
            lines += ["", "## 资料不足章节（正文已按规范标注“暂无足够可靠资料支持该观点”）", ""]
            for item in extra["insufficient_chapters"]:
                lines.append(f"- {item}")
        if extra.get("openalex_added"):
            lines += ["", f"## OpenAlex 新增证据（{len(extra['openalex_added'])} 条）", ""]
            lines += [f"- {x}" for x in extra["openalex_added"]]
        if extra.get("gov_added"):
            lines += ["", f"## 政府官方网页新增证据（{len(extra['gov_added'])} 条）", ""]
            lines += [f"- {x}" for x in extra["gov_added"]]
        return "\n".join(lines)

# 版本: v1.7.0 (2026-08-16) 更新: 历史记录与任务管理
