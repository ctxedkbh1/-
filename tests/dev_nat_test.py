import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_nat_test_")

from PySide6.QtWidgets import QApplication
from main import apply_light_theme

app = QApplication([])
app.setStyle("Fusion")
apply_light_theme(app)

from gui.main_window import MainWindow
from core.checkpoint import AutoCheckpoint
from core import paths

win = MainWindow()
win.project.update_info({"topic": "测试", "name": "张三", "word_count": 2000})
e1 = win.evidence.add({"title": "数据来源", "organization": "国家统计局",
                       "source_type": "government", "url": "https://www.stats.gov.cn/",
                       "content": "数据为100。"})
win.project.set_outline({"title": "测试", "sections": [
    {"id": 1, "title": "一、引言", "core_points": "背景", "target_words": 300,
     "evidence_ids": [e1], "subsections": []}]})

template_text = ("综上所述，本研究具有重要意义。首先介绍背景，其次分析现状，最后提出建议。"
                 "随着人工智能不断发展，具有重要意义。综上所述，本研究具有重要意义。"
                 f"数据为100[{e1}]。")
with open(os.path.join(paths.chapters_dir(), "01.md"), "w", encoding="utf-8") as f:
    f.write(template_text)

cp = AutoCheckpoint()
cp.create({"topic": "测试", "name": "张三", "word_count": 2000, "user_outline": "",
           "ai_risk_limit": 20, "repeat_risk_limit": 20, "max_rounds": 2})
for key in ("info", "topic", "outline_read", "queries", "openalex", "crossref",
            "government", "cnki", "evidence", "verify", "structure", "write",
            "citations", "references", "structure_check", "wordcount_check",
            "factcheck"):
    cp.mark_done(key, "预置")

from core.auto_pipeline import AutoPipelineEngine

results = {}
engine = AutoPipelineEngine(win)
engine.finished.connect(lambda r: results.__setitem__("done", r))
engine.failed.connect(lambda m: results.__setitem__("failed", m))
engine.run()

assert "done" in results, f"FAILED: {results.get('failed')}"
r = results["done"]
print(f"优化轮数={r['rounds']} 模板化={r['style_level']} AI风险={r['ai_risk']}%"
      f"（目标≤{r['ai_limit']}%） 重复风险={r['repeat_risk']}% 达标={r['target_met']}")
assert r["rounds"] >= 1
assert r["ai_risk"] > r["ai_limit"], "模板化文本风险应高于阈值"
assert r["target_met"] is False, "无 Key 无法修改，不应谎称达标"
assert r["max_rounds"] == 2
assert os.path.exists(os.path.join(paths.output_dir(), "论文.docx"))
report = open(os.path.join(paths.output_dir(), "论文质量报告.md"), encoding="utf-8").read()
assert "检测目标与结果" in report and "✗" in report and "内部分析" in report
print("阈值门控 + 未达标不谎报 测试通过")

# 版本: v1.4.0 (2026-08-16) 更新: 可自定义检测阈值
