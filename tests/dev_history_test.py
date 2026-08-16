import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_hist_")

from PySide6.QtWidgets import QApplication
from main import apply_light_theme

app = QApplication([])
app.setStyle("Fusion")
apply_light_theme(app)

from gui.main_window import MainWindow
from core.checkpoint import AutoCheckpoint
from core.history import HistoryManager, new_task_id
from core import paths

import gui.auto_mode_page as amp
amp.msg_info = lambda *a, **k: None
amp.msg_err = lambda *a, **k: False
amp.msg_warn = lambda *a, **k: None
amp.ask_confirm = lambda *a, **k: True


class _FakeBox:
    Icon = type("Icon", (), {"Information": 1})
    StandardButton = type("Std", (), {"Close": 1})
    ButtonRole = type("Role", (), {"ActionRole": 1})

    def __init__(self, *a, **k):
        pass

    def setWindowTitle(self, *a):
        pass

    def setIcon(self, *a):
        pass

    def setText(self, *a):
        pass

    def addButton(self, *a, **k):
        self._btn = object()
        return self._btn

    def clickedButton(self):
        return None

    def exec(self):
        return 0


amp.QMessageBox = _FakeBox

win = MainWindow()
page = win.pages[1]
history = HistoryManager()

win.project.update_info({"topic": "历史测试论文", "name": "陈舰辉", "class_name": "25中医4班",
                         "word_count": 2000})
e1 = win.evidence.add({"title": "数据来源", "organization": "国家统计局",
                       "source_type": "government", "url": "https://www.stats.gov.cn/",
                       "content": "数据为100。"})
win.project.set_outline({"title": "历史测试论文", "sections": [
    {"id": 1, "title": "一、引言", "core_points": "背景", "target_words": 300,
     "evidence_ids": [e1], "subsections": []}]})
with open(os.path.join(paths.chapters_dir(), "01.md"), "w", encoding="utf-8") as f:
    f.write(f"正常内容，引用数据为100[{e1}]。")

# 场景1：任务创建 -> 完成 -> 历史记录出现
cp = AutoCheckpoint()
input_data = {"topic": "历史测试论文", "name": "陈舰辉", "class_name": "25中医4班",
              "word_count": 2000, "user_outline": "", "ai_risk_limit": 20,
              "repeat_risk_limit": 20, "max_rounds": 1}
cp.create(input_data)
tid1 = cp.data["task_id"]
history.create(tid1, input_data)
for key in ("info", "topic", "outline_read", "queries", "openalex", "crossref",
            "government", "cnki", "evidence", "verify", "structure", "write",
            "citations", "references", "structure_check", "wordcount_check",
            "factcheck", "quality", "naturalize", "factcheck2", "citations2"):
    cp.mark_done(key, "预置")

from core.auto_pipeline import AutoPipelineEngine
results = {}
engine = AutoPipelineEngine(win)
engine.finished.connect(lambda r: results.__setitem__("done", r))
engine.run()
assert "done" in results
page._on_finished(results["done"])
assert not AutoCheckpoint().exists(), "完成后活动断点应归档清除"
history = HistoryManager()
rec = history.get(tid1)
assert rec and rec["status"] == "completed", rec
assert rec["files"], "历史记录应关联生成文件"
for f in rec["files"]:
    assert os.path.exists(f["path"]), f["path"]
print("场景1 完成+历史记录+文件关联 ✓")

# 场景2：模拟程序重启（历史仍在）
hist2 = HistoryManager()
rec2 = hist2.get(tid1)
assert rec2 and rec2["status"] == "completed"
print("场景2 重启后历史记录仍存在 ✓")

# 场景3：再来一篇 -> 新任务ID，两篇独立
new_input = dict(history.latest()["input"])
cp2 = AutoCheckpoint()
cp2.create(new_input)
tid2 = cp2.data["task_id"]
assert tid2 != tid1
history.create(tid2, new_input)
assert history.get(tid1)["status"] == "completed"
assert history.get(tid2)["status"] == "generating"
cp2.clear()
print("场景3 再来一篇=新任务ID，原记录独立保留 ✓")

# 场景4：删除 -> 记录+关联文件+任务归档全部删除
files_before = [f["path"] for f in rec["files"]]
ok, failed = history.delete(tid1)
assert ok and not failed
assert history.get(tid1) is None
for p in files_before:
    assert not os.path.exists(p), p
assert not os.path.exists(os.path.join(paths.data_dir(), "tasks", f"{tid1}.json"))
print("场景4 删除记录+文件+归档 ✓")

# 场景5：连续点击 10 次 -> 通过 UI 守卫（防重复任务）
for _ in range(10):
    page._creating_again = True
    assert page.on_again() is None  # 创建中守卫
page._creating_again = False


class _FakeThread:
    def isRunning(self):
        return True


page._thread = _FakeThread()
assert page.on_again_from_input(new_input) is None  # 运行中守卫
page._thread = None
print("场景5 防重复任务守卫存在 ✓")

# 场景6：失败 -> 记录保留为失败状态
cp3 = AutoCheckpoint()
cp3.create({"topic": "失败测试", "name": "张三", "word_count": 2000, "user_outline": ""})
tid3 = cp3.data["task_id"]
history.create(tid3, cp3.data["input"])
page._on_failed("模拟API超时错误")
history = HistoryManager()
rec3 = history.get(tid3)
assert rec3 and rec3["status"] == "failed" and "超时" in rec3.get("failure_reason", "")
assert not AutoCheckpoint().exists()
print("场景6 失败记录保留+可重新生成 ✓")

# 场景7：多格式文件关联（docx/pdf/pptx）
out = paths.output_dir()
extra = []
for fmt in ("docx", "pdf", "pptx"):
    p = os.path.join(out, f"多格式_测试.{fmt}")
    with open(p, "w", encoding="utf-8") as f:
        f.write("test")
    extra.append({"name": os.path.basename(p), "path": p, "format": fmt})
history.add_files(tid2, extra)
history = HistoryManager()
assert len(history.get(tid2)["files"]) == 3
history.delete(tid2)
for p, in [(f["path"],) for f in extra]:
    assert not os.path.exists(p)
print("场景7 多格式文件关联+删除 ✓")

print("\n=== 历史记录与任务管理测试全部通过 ===")

# 版本: v1.7.0 (2026-08-16) 更新: 历史记录与任务管理
