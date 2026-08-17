import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_auto_test_")

from PySide6.QtWidgets import QApplication
from main import apply_light_theme

app = QApplication([])
app.setStyle("Fusion")
apply_light_theme(app)

from gui.main_window import MainWindow
from core.checkpoint import AutoCheckpoint

win = MainWindow()

win.project.update_info({"topic": "人工智能对大学生就业的影响", "name": "张三",
                         "class_name": "计科2024级1班", "word_count": 3000,
                         "format_note": "默认格式"})
win.evidence.add({
    "title": "2024年国民经济和社会发展统计公报", "organization": "国家统计局",
    "source_type": "government", "url": "https://www.stats.gov.cn/",
    "published_at": "2025-02-28", "content": "全年国内生产总值同比增长5.0%。",
})
e2 = win.evidence.add({
    "title": "高校毕业生就业研究", "authors": "李明", "journal": "教育研究",
    "year": "2024", "volume_issue_pages": "45(3): 12-20", "doi": "10.1234/jy.2024.001",
    "source_type": "cnki", "content": "人工智能相关岗位需求明显增长。",
})
e1 = "E001"

outline = {"title": "人工智能对大学生就业的影响", "keywords": ["人工智能", "就业"],
           "abstract_plan": "", "sections": [
               {"id": 1, "title": "一、引言", "core_points": "背景与问题", "target_words": 300,
                "evidence_ids": [e1], "subsections": []},
               {"id": 2, "title": "二、结论", "core_points": "总结", "target_words": 300,
                "evidence_ids": [e2], "subsections": []},
           ]}
win.project.set_outline(outline)

from core import paths, writer as writer_mod
with open(os.path.join(paths.chapters_dir(), "01.md"), "w", encoding="utf-8") as f:
    f.write(f"近年来人工智能快速发展，就业市场发生变化。根据国家统计局公布的数据，"
            f"全年国内生产总值同比增长5.0%[{e1}]。这说明经济总体保持增长态势，"
            f"为就业提供基础。从大学生视角来看，需要关注行业变化带来的机会。")
with open(os.path.join(paths.chapters_dir(), "02.md"), "w", encoding="utf-8") as f:
    f.write(f"综合来看，人工智能对就业的影响是复杂的。有研究指出人工智能相关岗位"
            f"需求明显增长[{e2}]，同时经济数据也支持这一判断[{e1}]。"
            f"因此大学生应提升数字技能，适应变化。")

cp = AutoCheckpoint()
cp.create({"topic": "人工智能对大学生就业的影响", "name": "张三",
           "class_name": "计科2024级1班", "word_count": 3000,
           "format_note": "默认格式", "user_outline": "",
           "ai_risk_limit": 20, "repeat_risk_limit": 20, "max_rounds": 3})
for key in ("info", "topic", "outline_read", "queries", "openalex", "crossref",
            "government", "cnki", "evidence", "verify", "structure", "write"):
    cp.mark_done(key, "预置完成（模拟断点恢复场景）")

from core.auto_pipeline import AutoPipelineEngine
from core.auto_pipeline import PipelineError

results = {}
engine = AutoPipelineEngine(win)
engine.finished.connect(lambda r: results.__setitem__("done", r))
engine.aborted.connect(lambda: results.__setitem__("aborted", True))
engine.failed.connect(lambda m: results.__setitem__("failed", m))
engine.run()

assert "done" in results, f"pipeline failed: {results.get('failed')}"
r = results["done"]
print("结果:", {k: r[k] for k in ("evidence_count", "references_ok", "final_status",
                                "ai_risk", "repeat_risk", "target_met", "rounds")})
assert r["evidence_count"] == 2
assert r["references_ok"] is True
assert r["final_status"] == "可以导出", r
assert r["ai_risk"] is not None and r["repeat_risk"] is not None
assert r["ai_limit"] == 20 and r["repeat_limit"] == 20 and r["max_rounds"] == 3
assert r["target_met"] is True, r

out_dir = paths.output_dir()
for f in ("论文.docx", "论文.md", "资料核验报告.md", "证据表.json",
          "论文质量报告.md", "全自动运行日志.md"):
    p = os.path.join(out_dir, f)
    assert os.path.exists(p), f"缺少输出文件: {f}"
print("输出文件检查通过")

report = open(os.path.join(out_dir, "资料核验报告.md"), encoding="utf-8").read()
assert "引用↔参考文献检查" in report
print("核验报告内容检查通过")
log_md = open(os.path.join(out_dir, "全自动运行日志.md"), encoding="utf-8").read()
assert "步骤记录" in log_md
print("运行日志检查通过")

cp2 = AutoCheckpoint()
assert cp2.has_unfinished() is False and cp2.data.get("finished") is True
print("断点状态检查通过")


class EmptyStore:
    def all(self):
        return []


class EmptyCheckpoint:
    def set(self, *_args):
        return None


empty_engine = AutoPipelineEngine.__new__(AutoPipelineEngine)
empty_engine.store = EmptyStore()
empty_engine.checkpoint = EmptyCheckpoint()
empty_engine.log = lambda *_args: None
try:
    empty_engine._step_evidence()
except PipelineError as exc:
    assert "未获得任何资料或文献" in str(exc)
else:
    raise AssertionError("证据库为空时必须停止全自动写作")
print("空资料安全停止检查通过")

print("\n=== 离线端到端全自动流水线测试通过 ===")

# 版本: v2.1.2 (2026-08-18) 更新: 空资料安全停止回归测试
