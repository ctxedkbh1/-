import datetime
import json
import os

from core import paths

INFO_FIELDS = [
    ("topic", "论文题目"),
    ("major", "专业"),
    ("course", "课程名称"),
    ("school", "学校"),
    ("class_name", "班级"),
    ("student_id", "学号"),
    ("name", "姓名"),
    ("word_count", "字数要求"),
    ("format_note", "格式要求"),
    ("deadline", "截止时间"),
]


class Project:
    def __init__(self):
        self.path = paths.project_file()
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
        return {"info": {}, "created_at": datetime.datetime.now().isoformat()}

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def reset(self):
        self.data = {"info": {}, "created_at": datetime.datetime.now().isoformat()}
        self.save()

    def info(self):
        info = self.data.setdefault("info", {})
        out = {}
        for key, _ in INFO_FIELDS:
            v = info.get(key, "")
            if key == "word_count":
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    v = 3000
            out[key] = v
        return out

    def update_info(self, values):
        self.data.setdefault("info", {}).update(values)
        self.save()

    def info_complete(self):
        info = self.info()
        return bool(info.get("topic") and info.get("name") and info.get("school"))

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def outline(self):
        out = self.data.get("outline") or {}
        return out if isinstance(out, dict) else {}

    def set_outline(self, outline):
        self.data["outline"] = outline
        self.save()

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
