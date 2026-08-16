import datetime
import json
import os
import random

from core import log, paths

STATUS_LABELS = {
    "waiting": "等待中",
    "generating": "生成中",
    "optimizing": "优化中",
    "checking": "检测中",
    "completed": "已完成",
    "failed": "失败",
    "deleted": "已删除",
}

ACTIVE_STATUSES = ("waiting", "generating", "optimizing", "checking")


def new_task_id():
    return "T" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + \
        "".join(random.choices("0123456789abcdef", k=4))


class HistoryManager:
    """全自动任务历史记录：JSON 持久化（paper_project/history.json），
    任务断点归档到 paper_project/tasks/Txxxx.json，与生成文件建立关联。"""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or paths.data_dir()
        self.path = os.path.join(self.data_dir, "history.json")
        self.tasks_dir = os.path.join(self.data_dir, "tasks")
        os.makedirs(self.tasks_dir, exist_ok=True)
        self.data = self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, list):
                        return d
            except Exception as e:
                log.get().warning("历史记录读取失败: %s", e)
        return []

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    # ---------- 查询 ----------

    def all(self):
        self.data = self.load()
        return list(self.data)

    def get(self, task_id):
        self.data = self.load()
        for r in self.data:
            if r.get("task_id") == task_id:
                return r
        return None

    def latest(self):
        self.data = self.load()
        for r in self.data:
            if r.get("status") != "deleted":
                return r
        return None

    def search(self, text="", status_filter="全部", order="最新"):
        self.data = self.load()
        out = [r for r in self.data if r.get("status") != "deleted"]
        if status_filter == "已完成":
            out = [r for r in out if r.get("status") == "completed"]
        elif status_filter == "生成中":
            out = [r for r in out if r.get("status") in ACTIVE_STATUSES]
        elif status_filter == "失败":
            out = [r for r in out if r.get("status") == "failed"]
        if text:
            t = text.strip().lower()
            out = [r for r in out if t in " ".join(str(r.get(k) or "") for k in
                    ("title", "name", "class_name", "course", "created_at")).lower()]
        out.sort(key=lambda r: r.get("created_at") or "", reverse=(order == "最新"))
        return out

    # ---------- 生命周期 ----------

    def create(self, task_id, input_data):
        self.data = self.load()
        rec = {
            "id": "H" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:19],
            "task_id": task_id,
            "mode": str(input_data.get("mode") or "auto"),
            "title": (input_data.get("topic") or "").strip(),
            "name": (input_data.get("name") or "").strip(),
            "class_name": (input_data.get("class_name") or "").strip(),
            "course": (input_data.get("course") or "").strip(),
            "school": (input_data.get("school") or "").strip(),
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": "",
            "status": "generating",
            "status_text": "生成中",
            "stage": "",
            "models": input_data.get("task_models") or {},
            "rounds": 0,
            "ai_risk": None,
            "repeat_risk": None,
            "scores": {},
            "files": [],
            "duration_sec": 0,
            "failure_reason": "",
            "input": dict(input_data),
            "step_log": {},
        }
        existing = self.get(task_id)
        if existing:
            for k, v in rec.items():
                existing.setdefault(k, v)
            existing["status"] = "generating"
            existing["status_text"] = "生成中"
            rec = existing
        else:
            self.data.insert(0, rec)
        self.save()
        log.get().info("历史记录已创建 task_id=%s", task_id)
        return rec

    def update_stage(self, task_id, stage_key, status_text):
        self.data = self.load()
        rec = self.get(task_id)
        if not rec:
            return
        rec["stage"] = stage_key
        rec["step_log"][stage_key] = {
            "at": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": status_text,
        }
        self.save()

    def update_status(self, task_id, status, reason=""):
        self.data = self.load()
        rec = self.get(task_id)
        if not rec:
            return
        rec["status"] = status
        rec["status_text"] = STATUS_LABELS.get(status, status)
        if reason:
            rec["failure_reason"] = reason
        self.save()

    def archive_checkpoint(self, task_id, checkpoint_data):
        if not checkpoint_data:
            return None
        fname = os.path.join(self.tasks_dir, f"{task_id}.json")
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        return fname

    def remove_archive(self, task_id):
        fname = os.path.join(self.tasks_dir, f"{task_id}.json")
        if os.path.exists(fname):
            try:
                os.remove(fname)
                return True
            except OSError:
                return False
        return True

    def load_archive(self, task_id):
        fname = os.path.join(self.tasks_dir, f"{task_id}.json")
        if os.path.exists(fname):
            try:
                with open(fname, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def finalize(self, task_id, result, checkpoint_data):
        self.data = self.load()
        rec = self.get(task_id)
        if not rec:
            return None
        rec["finished_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rec["status"] = "completed"
        rec["status_text"] = "已完成"
        rec["rounds"] = result.get("rounds") or 0
        rec["ai_risk"] = result.get("ai_risk")
        rec["repeat_risk"] = result.get("repeat_risk")
        rec["scores"] = result.get("scores") or {}
        rec["models"] = (self._input_of(checkpoint_data) or {}).get("task_models") or rec.get("models") or {}
        rec["target_met"] = bool(result.get("target_met"))
        try:
            start = datetime.datetime.strptime(rec["created_at"], "%Y-%m-%d %H:%M:%S")
            end = datetime.datetime.strptime(rec["finished_at"], "%Y-%m-%d %H:%M:%S")
            rec["duration_sec"] = max(0, int((end - start).total_seconds()))
        except Exception:
            rec["duration_sec"] = 0
        files = list(rec.get("files") or [])
        known = {f.get("name") for f in files}
        for key in ("docx", "md", "report"):
            p = (result.get("paths") or {}).get(key)
            if p and os.path.exists(p) and os.path.basename(p) not in known:
                files.append({"name": os.path.basename(p), "path": p, "format": key})
                known.add(os.path.basename(p))
        from core import paths as _paths
        for name in ("论文质量报告.md", "证据表.json", "全自动运行日志.md"):
            p = os.path.join(_paths.output_dir(), name)
            if os.path.exists(p) and name not in known:
                files.append({"name": name, "path": p, "format": name.rsplit(".", 1)[-1]})
                known.add(name)
        rec["files"] = files
        if files:
            rec["export_dir"] = os.path.dirname(files[0].get("path", ""))
        else:
            rec["export_dir"] = ""
        self.archive_checkpoint(task_id, checkpoint_data)
        self.save()
        log.get().info("历史记录已完成 task_id=%s files=%d", task_id, len(files))
        return rec

    def finalize_failed(self, task_id, reason, checkpoint_data):
        self.data = self.load()
        rec = self.get(task_id)
        if not rec:
            return None
        rec["finished_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rec["status"] = "failed"
        rec["status_text"] = "失败"
        rec["failure_reason"] = reason
        self.archive_checkpoint(task_id, checkpoint_data)
        self.save()
        log.get().info("历史记录已标记失败 task_id=%s reason=%s", task_id, reason)
        return rec

    @staticmethod
    def _input_of(checkpoint_data):
        return (checkpoint_data or {}).get("input") or {}

    # ---------- 文件关联 ----------

    def add_files(self, task_id, files):
        self.data = self.load()
        rec = self.get(task_id)
        if not rec:
            return
        names = {f.get("name") for f in rec.get("files", [])}
        for f in files:
            if f.get("name") not in names:
                rec.setdefault("files", []).append(f)
        self.save()

    # ---------- 删除 ----------

    def delete(self, task_id):
        self.data = self.load()
        """删除记录+归档任务+关联文件；返回 (ok, failed_files)。"""
        rec = self.get(task_id)
        if not rec:
            return True, []
        failed = []
        for f in rec.get("files", []):
            p = f.get("path")
            if not p or not os.path.exists(p):
                continue
            try:
                os.remove(p)
            except OSError as e:
                failed.append({"name": f.get("name"), "reason": str(e)})
        if not self.remove_archive(task_id):
            failed.append({"name": f"任务归档 {task_id}.json", "reason": "文件被占用"})
        self.data = [r for r in self.data if r.get("task_id") != task_id]
        self.save()
        log.get().info("历史记录已删除 task_id=%s 失败文件=%d", task_id, len(failed))
        return True, failed

    def delete_many(self, task_ids):
        self.data = self.load()
        total_failed = []
        for tid in task_ids:
            _, failed = self.delete(tid)
            total_failed.extend(failed)
        return total_failed

    # ---------- 迁移/一致性 ----------

    def sync_with_active_checkpoint(self, checkpoint_data):
        self.data = self.load()
        """把旧版本遗留的已完成断点归档为历史记录（数据迁移）。"""
        if not checkpoint_data:
            return None
        task_id = checkpoint_data.get("task_id")
        if not task_id:
            return None
        if self.get(task_id):
            return None
        if not checkpoint_data.get("finished"):
            rec = self.create(task_id, checkpoint_data.get("input") or {})
            rec["status"] = "waiting"
            rec["status_text"] = "等待中"
            self.save()
            return rec
        result = checkpoint_data.get("result") or {}
        rec = self.create(task_id, checkpoint_data.get("input") or {})
        rec["status"] = "completed"
        rec["status_text"] = "已完成"
        rec["finished_at"] = checkpoint_data.get("finished_at") or ""
        rec["rounds"] = result.get("rounds") or 0
        rec["scores"] = result.get("scores") or {}
        rec["ai_risk"] = result.get("ai_risk")
        rec["repeat_risk"] = result.get("repeat_risk")
        rec["target_met"] = bool(result.get("target_met"))
        files = []
        for key in ("docx", "md", "report"):
            p = (result.get("paths") or {}).get(key)
            if p and os.path.exists(p):
                files.append({"name": os.path.basename(p), "path": p, "format": key})
        rec["files"] = files
        self.archive_checkpoint(task_id, checkpoint_data)
        self.save()
        log.get().info("旧任务已迁移为历史记录 task_id=%s", task_id)
        return rec

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
