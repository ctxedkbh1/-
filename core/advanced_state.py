import datetime
import json
import os

from core import log, paths

FORMAT_PRESET = {
    "name": "中国高校通用论文格式",
    "page": "A4", "orientation": "纵向",
    "font": "宋体", "latin_font": "Times New Roman", "size": 12,
    "line_spacing": 1.5, "first_indent_chars": 2, "align": "justify",
    "title_font": "黑体", "title_size": 22, "title_bold": True, "title_align": "center",
    "h1_font": "黑体", "h1_size": 15, "h1_bold": True,
    "h2_font": "黑体", "h2_size": 14, "h2_bold": True,
    "h3_font": "黑体", "h3_size": 12, "h3_bold": True,
    "page_number": "bottom_center", "header": "", "footer": "",
    "margin_top": 2.54, "margin_bottom": 2.54,
    "margin_left": 3.17, "margin_right": 3.17,
}

ALIGN_LABELS = {"justify": "两端对齐", "left": "左对齐", "center": "居中", "right": "右对齐"}


class AdvancedStateManager:
    """高级模式统一项目状态（paper_project/advanced.json）。

    各功能模块（论文信息/AI模型/检索/格式/来源/修改/质量/版本/导出）
    共享这一份状态，修改立即影响导出与生成。"""

    def __init__(self, data_dir=None):
        self.path = os.path.join(data_dir or paths.data_dir(), "advanced.json")
        self.data = self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    d = json.load(f)
                    if isinstance(d, dict):
                        return d
            except Exception as e:
                log.get().warning("高级模式状态读取失败: %s", e)
        return self._defaults()

    def _defaults(self):
        return {
            "info_extra": {"college": "", "teacher": "", "paper_type": "",
                           "custom_requirements": ""},
            "format": dict(FORMAT_PRESET),
            "data_source_mode": "none",
            "data_sources": [],
            "web_enabled": True,
            "search_cache": {},
            "modification_queue": [],
            "modification_history": [],
            "versions": [],
            "created_at": datetime.datetime.now().isoformat(),
        }

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    # 论文信息扩展字段
    def info_extra(self):
        return self.data.setdefault("info_extra", {})

    def update_info_extra(self, values):
        self.data.setdefault("info_extra", {}).update(values)
        self.save()

    # 格式
    def format(self):
        return self.data.setdefault("format", dict(FORMAT_PRESET))

    def update_format(self, values):
        self.data.setdefault("format", {}).update(values)
        self.save()

    def reset_format_to_preset(self):
        self.data["format"] = dict(FORMAT_PRESET)
        self.save()

    # 数据来源
    def data_source_mode(self):
        return self.data.get("data_source_mode", "none")

    def data_sources(self):
        return self.data.get("data_sources", [])

    def add_data_source(self, name, url="", note="", verified=True):
        item = {"name": name, "url": url, "note": note,
                "verified": bool(verified),
                "added_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
        self.data.setdefault("data_sources", []).append(item)
        self.save()
        return item

    def remove_data_source(self, index):
        lst = self.data.get("data_sources", [])
        if 0 <= index < len(lst):
            lst.pop(index)
            self.save()

    def clear_data_sources(self):
        self.data["data_sources"] = []
        self.save()

    def auto_data_sources_from_evidence(self, store, cited_ids):
        """自动添加：仅使用正文实际引用的真实证据，绝不虚构来源。"""
        self.data["data_sources"] = []
        for eid in cited_ids:
            e = store.get(eid)
            if not e:
                continue
            src = e.get("organization") or e.get("journal") or e.get("source") or "未标注来源"
            url = e.get("url") or ("https://doi.org/" + e["doi"] if e.get("doi") else "")
            self.data["data_sources"].append({
                "name": f"{src}：《{(e.get('title') or '')[:60]}》",
                "url": url,
                "note": "来自证据库 " + str(eid),
                "verified": bool(e.get("verified")),
                "added_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        self.save()
        return len(self.data["data_sources"])

    # 修改队列
    def queue(self):
        return self.data.setdefault("modification_queue", [])

    def add_queue_item(self, item):
        item.setdefault("id", "Q%d" % (len(self.queue()) + 1))
        item.setdefault("status", "pending")
        self.queue().append(item)
        self.save()
        return item

    def set_queue_status(self, qid, status, result=""):
        for q in self.queue():
            if q.get("id") == qid:
                q["status"] = status
                q["result"] = result
        self.save()

    def clear_queue(self):
        self.data["modification_queue"] = []
        self.save()

    # 修改历史（撤销/重做）
    def history(self):
        return self.data.setdefault("modification_history", [])

    def add_history(self, entry):
        entry.setdefault("at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.history().append(entry)
        self.save()

    def clear_history(self):
        self.data["modification_history"] = []
        self.save()

    # 版本
    def versions(self):
        return self.data.setdefault("versions", [])

    def add_version(self, vid, note):
        self.versions().append({
            "id": vid, "note": note,
            "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        self.save()

    def remove_version(self, vid):
        self.data["versions"] = [v for v in self.versions() if v.get("id") != vid]
        self.save()

    # 搜索缓存
    def cache_get(self, query):
        return self.data.setdefault("search_cache", {}).get(query)

    def cache_set(self, query, results):
        self.data.setdefault("search_cache", {})[query] = {
            "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": results}
        self.save()

    def cache_clear(self, query=None):
        if query:
            self.data.setdefault("search_cache", {}).pop(query, None)
        else:
            self.data["search_cache"] = {}
        self.save()


class VersionManager:
    """版本管理：把 chapters 快照保存到 paper_project/versions/<id>/，支持查看/恢复/删除。"""

    def __init__(self, state=None, data_dir=None):
        self.state = state
        self.versions_dir = os.path.join(data_dir or paths.data_dir(), "versions")

    def _vdir(self, vid):
        return os.path.join(self.versions_dir, vid)

    def snapshot_chapters(self, vid, note=""):
        chapters_dir = paths.chapters_dir()
        vdir = self._vdir(vid)
        os.makedirs(vdir, exist_ok=True)
        count = 0
        for name in os.listdir(chapters_dir):
            if name.endswith(".md"):
                with open(os.path.join(chapters_dir, name), encoding="utf-8") as src, \
                        open(os.path.join(vdir, name), "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                count += 1
        if self.state is not None:
            self.state.add_version(vid, note)
        log.get().info("版本已保存 vid=%s chapters=%d", vid, count)
        return count

    def restore_chapters(self, vid):
        vdir = self._vdir(vid)
        if not os.path.isdir(vdir):
            return False
        chapters_dir = paths.chapters_dir()
        restored = 0
        for name in os.listdir(vdir):
            if name.endswith(".md"):
                with open(os.path.join(vdir, name), encoding="utf-8") as src, \
                        open(os.path.join(chapters_dir, name), "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                restored += 1
        log.get().info("版本已恢复 vid=%s chapters=%d", vid, restored)
        return True

    def list_snapshots(self):
        if not os.path.isdir(self.versions_dir):
            return []
        return sorted(os.listdir(self.versions_dir))

    def delete(self, vid):
        import shutil
        vdir = self._vdir(vid)
        if os.path.isdir(vdir):
            shutil.rmtree(vdir, ignore_errors=True)
        if self.state is not None:
            self.state.remove_version(vid)
        log.get().info("版本已删除 vid=%s", vid)

# 版本: v2.0.0 (2026-08-16) 更新: 高级模式工作台
