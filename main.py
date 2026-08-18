import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def run_selfcheck():
    import tempfile

    tmp = tempfile.mkdtemp(prefix="pa_selfcheck_")
    os.environ["PAPER_PROJECT_DIR"] = tmp
    from core import log, paths
    log.setup_logging()
    log.get().info("自检开始 data_dir=%s", tmp)

    from core.evidence import EvidenceStore
    from core.project import Project

    store = EvidenceStore()
    e1 = store.add({"title": "示例政府数据", "organization": "国家统计局",
                    "source_type": "government", "url": "https://www.stats.gov.cn/",
                    "published_at": "2025-01-01", "content": "2025年某指标为100。"})
    e2 = store.add({"title": "示例文献", "authors": "张三; 李四", "journal": "示例学报",
                    "year": "2024", "volume_issue_pages": "12(3): 45-52",
                    "doi": "10.1234/abcd", "source_type": "cnki",
                    "content": "某研究表明相关结论。"})
    ref1 = store.to_reference(store.get(e1))
    ref2 = store.to_reference(store.get(e2))
    assert "EB/OL" in ref1, ref1
    assert "10.1234/abcd" in ref2, ref2
    assert store.missing_fields(store.get(e2)) == [], store.missing_fields(store.get(e2))

    proj = Project()
    proj.update_info({"topic": "自检测试论文", "name": "测试", "school": "测试大学",
                      "major": "测试专业", "word_count": 2000})
    proj.set_outline({"title": "自检测试论文", "keywords": ["测试"],
                      "abstract_plan": "",
                      "sections": [
                          {"id": 1, "title": "一、引言", "core_points": "背景",
                           "target_words": 300, "evidence_ids": [e1], "subsections": []},
                          {"id": 2, "title": "二、结论", "core_points": "总结",
                           "target_words": 300, "evidence_ids": [e2], "subsections": []},
                      ]})
    chapters_dir = paths.chapters_dir()
    with open(os.path.join(chapters_dir, "01.md"), "w", encoding="utf-8") as f:
        f.write(f"引言引用[{e1}]的数据。")
    with open(os.path.join(chapters_dir, "02.md"), "w", encoding="utf-8") as f:
        f.write(f"结论引用[{e2}]与[{e1}]。")

    from core import exporter, fact_checker
    full_text = exporter.build_full_text(proj)
    analysis = fact_checker.analyze(full_text, store)
    assert analysis["refs"] == [e1, e2], analysis
    assert analysis["unresolved"] == []
    assert analysis["bidirectional_ok"] is True
    final_text = exporter.assemble_markdown(proj, store, analysis, skip_abstract=True)
    assert "[1]" in final_text and "[2]" in final_text
    paths_out = exporter.export_files(proj, store, analysis, [], 2, 150,
                                      skip_abstract=True)
    assert os.path.exists(paths_out["docx"]) and os.path.getsize(paths_out["docx"]) > 1000
    assert os.path.exists(paths_out["md"])
    assert os.path.exists(paths_out["report"])
    report_text = open(paths_out["report"], encoding="utf-8").read()
    assert "国家统计局" in report_text and "引用↔参考文献检查" in report_text

    from core.document import document_from_text
    from core.exporters import export as export_format, verify as verify_format, \
        sanitize_filename
    from core.exporters.style_parser import parse_format_note
    from core import output_location
    doc = document_from_text(final_text, meta={"title": "测试", "name": "张三",
                                               "format_note": "正文宋体小四，1.5倍行距，首行缩进2字符"})
    st = parse_format_note("正文宋体小四，1.5倍行距，首行缩进2字符")
    assert st["font"] == "宋体" and st["size"] == 12 and st["line_spacing"] == 1.5
    assert sanitize_filename('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"
    d1 = output_location.resolve_output_dir("desktop")
    d2 = output_location.resolve_output_dir("documents")
    d3 = output_location.resolve_output_dir("downloads")
    assert isinstance(d1, str) and d1 and d2 and d3
    custom_dir = os.path.join(tmp, "自定义导出目录")
    assert output_location.resolve_output_dir("custom", custom_dir) == custom_dir
    ok, err = output_location.ensure_dir(custom_dir)
    assert ok and os.path.isdir(custom_dir)
    wok, werr = output_location.is_writable(custom_dir)
    assert wok, werr
    with open(os.path.join(custom_dir, "t.docx"), "w", encoding="utf-8") as f:
        f.write("x")
    up = output_location.unique_path(os.path.join(custom_dir, "t.docx"))
    assert up.endswith("(1).docx")
    log.get().info("输出位置解析测试通过（桌面/文档/下载/自定义/重命名）")
    for fmt in ("docx", "pptx", "pdf", "txt", "md", "html"):
        p = os.path.join(tmp, "multi." + fmt)
        export_format(doc, fmt, p)
        assert os.path.getsize(p) > 0, fmt
        v = verify_format(p, fmt)
        assert v["ok"], (fmt, v)
    log.get().info("多格式导出与验证测试通过（docx/pptx/pdf/txt/md/html）")

    from sources import cnki
    ris = "TY  - JOUR\nTI  - 测试文献\nAU  - 王五\nJO  - 测试期刊\nPY  - 2023\nVL  - 1\nIS  - 2\nSP  - 10\nEP  - 20\nDO  - 10.1/xx\nER  - "
    records = cnki.parse_text(ris)
    assert len(records) == 1 and records[0]["title"] == "测试文献"

    from core.checkpoint import AutoCheckpoint
    cp = AutoCheckpoint()
    cp.create({"topic": "测试", "name": "测试", "user_outline": ""})
    assert cp.exists() and cp.has_unfinished()
    cp.mark_done("info", "ok")
    cp.add_log("测试日志")
    assert cp.is_done("info") and cp.done_count() == 1
    assert "测试日志" in cp.build_log_markdown()
    cp.clear()
    assert not cp.exists()

    from core import style_checker
    style = style_checker.analyze("综上所述，本研究具有重要意义。首先介绍背景，其次分析现状，"
                                  "最后提出建议。随着人工智能不断发展，具有重要意义。"
                                  "综上所述，本研究具有重要意义。")
    assert style["template_hits"] and style["template_score"] in ("中", "高"), style
    paras, flagged = style_checker.analyze_paragraphs(
        "第一段正常内容介绍研究背景与问题，数据来源见正文[E001]。\n\n"
        "综上所述，具有重要意义。首先介绍，其次分析，最后总结。\n\n"
        "第三段展开具体分析，结合数据讨论影响与机制。")
    assert flagged, flagged
    stats = style_checker.structure_stats("## 标题\n\n摘要段落", 3,
                                           {"abstract": "x", "keywords": ["a"]})
    assert stats["sections"] == 3 and stats["headings"] == 1
    scores = style_checker.score(style, stats, True, 3)
    assert 0 <= scores["综合质量"] <= 100 and scores["格式完整度"] >= 0, scores
    risks = style_checker.risk_percent(style)
    assert 0 <= risks["ai_risk"] <= 100 and 0 <= risks["repeat_risk"] <= 100, risks
    from core import detector
    det = detector.detect("正常的一段论述文字，结合具体数据进行分析。", style_checker.analyze("正常的一段论述文字，结合具体数据进行分析。"))
    assert det["source"] == "internal" and 0 <= det["ai_risk"] <= 100, det
    assert "内部分析" in detector.source_label(det)

    from core import llm
    assert hasattr(llm, "OpenAICompatibleProvider") and hasattr(llm, "ClaudeProvider") \
        and hasattr(llm, "GeminiProvider")
    from config.manager import ConfigManager
    cfg2 = ConfigManager()
    assert "models" in cfg2.data and cfg2.models()["deepseek"].get("enabled")
    cfg2.add_model("testlocal", {"name": "本地测试模型", "type": "openai_compatible",
                                 "base_url": "http://127.0.0.1:0/v1", "api_key": "",
                                 "env_key": "", "model_id": "test", "price": 0,
                                 "capabilities": ["文本生成"], "enabled": True})
    assert ConfigManager.mask_key("sk-abcdefgh123456").startswith("sk-*")

    import http.server
    import threading
    import json as _json

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            body = _json.dumps({"choices": [{"message": {"role": "assistant",
                                                         "content": "OK"}}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cfg2.add_model("testlocal", {"name": "本地测试模型", "type": "openai_compatible",
                                 "base_url": f"http://127.0.0.1:{port}/v1", "api_key": "",
                                 "env_key": "", "model_id": "test", "price": 0,
                                 "capabilities": ["文本生成"], "enabled": True})
    cfg2.add_model("testdead", {"name": "失效模型", "type": "openai_compatible",
                                "base_url": "http://127.0.0.1:1/v1", "api_key": "",
                                "env_key": "", "model_id": "x", "price": 0,
                                "capabilities": [], "enabled": True})
    cfg2.set_task_model("generation", "testdead")
    router = llm.ModelRouter(cfg2)
    text, used = router.chat("generation", [{"role": "user", "content": "hi"}], max_tokens=8)
    assert text == "OK" and used == "testlocal", (text, used)
    assert router.health_check("testlocal")["ok"] is True
    assert router.health_check("testdead")["ok"] is False
    srv.shutdown()
    log.get().info("模型路由与故障切换测试通过")

    from core import naturalizer
    orig = "2024年某指标为100，[E001]。暂无足够可靠资料支持该观点。"
    assert naturalizer.safe_rewrite(orig, "根据2024年数据，该指标为100，[E001]。暂无足够可靠资料支持该观点。")
    assert naturalizer.safe_rewrite(orig, "根据2024年数据，该指标为100。") is None
    assert naturalizer.safe_rewrite(orig, "2024年某指标为105，[E001]。") is None
    assert naturalizer.safe_rewrite("x", "[E002]") is None

    from core import quality_report
    qr = quality_report.build(proj, store, analysis, style, 1, [], 0, [],
                              structure_stats=stats, wordcount={"required": 2000, "actual": 100, "ok": False},
                              scores=scores, modification_log=[
                                  {"round": 1, "paragraphs_modified": 3, "chapters": [1], "expand": False}],
                              factcheck_status="passed", requirement_failures=[])
    assert "最终状态" in qr and "可以导出" in qr
    assert "综合质量" in qr and "第 1 轮：修改 3 个段落" in qr

    from core.advanced_state import AdvancedStateManager, VersionManager, FORMAT_PRESET
    ast = AdvancedStateManager()
    assert ast.format()["font"] == "宋体" and FORMAT_PRESET["size"] == 12
    ast.update_info_extra({"college": "测试学院", "teacher": "王老师",
                           "custom_requirements": "必须结合中医学专业"})
    assert ast.info_extra()["teacher"] == "王老师"
    ast.add_data_source("国家统计局", "https://www.stats.gov.cn/", verified=True)
    ast.add_data_source("来源待核", "", verified=False)
    assert len(ast.data_sources()) == 2 and ast.data_sources()[1]["verified"] is False
    ast.cache_set("测试查询", [{"title": "x"}])
    assert ast.cache_get("测试查询")["results"][0]["title"] == "x"
    vm = VersionManager(ast)
    n = vm.snapshot_chapters("V1", "测试版本")
    assert n >= 1 and vm.list_snapshots() == ["V1"]
    assert ast.versions()[0]["id"] == "V1"
    from core.targeted_edit import build_format_note, preview_html, safe_apply, edit_region
    fmt = ast.format()
    assert "宋体" in build_format_note(fmt)
    assert "<html" in preview_html(fmt)
    assert safe_apply("2025年数据为100，[E001]。", "2025年数据为100，[E001]。")
    assert safe_apply("2025年数据为100，[E001]。", "2025年数据为105，[E001]。") is None
    assert safe_apply("2025年数据为100，[E001]。", "2025年数据为100。") is None
    vm.restore_chapters("V1")
    vm.delete("V1")
    assert vm.list_snapshots() == []
    log.get().info("高级模式状态/版本/格式/修改安全测试通过")

    from core.auto_pipeline import STAGE_LABELS, AutoPipelineEngine, Controller
    assert len(STAGE_LABELS) >= 15
    ctrl = Controller()
    ctrl.cancel()
    assert ctrl.cancel_event.is_set()

    from core.history import HistoryManager, new_task_id
    hist = HistoryManager()
    tid1 = new_task_id()
    tid2 = new_task_id()
    assert tid1 != tid2
    hist.create(tid1, {"topic": "测试论文A", "name": "张三", "class_name": "一班"})
    hist.create(tid2, {"topic": "测试论文B", "name": "李四"})
    hist.update_status(tid1, "optimizing")
    assert hist.get(tid1)["status"] == "optimizing"
    fake_docx = os.path.join(tmp, "t.docx")
    with open(fake_docx, "w", encoding="utf-8") as f:
        f.write("test")
    fake_docx2 = os.path.join(tmp, "t2.docx")
    with open(fake_docx2, "w", encoding="utf-8") as f:
        f.write("test2")
    hist.add_files(tid1, [{"name": "t.docx", "path": fake_docx, "format": "docx"}])
    hist.finalize(tid1, {"rounds": 2, "ai_risk": 10, "repeat_risk": 5,
                         "scores": {"综合质量": 90}, "paths": {"docx": fake_docx2},
                         "target_met": True},
                  {"task_id": tid1, "input": {"topic": "测试论文A"}})
    rec1 = hist.get(tid1)
    assert rec1["status"] == "completed" and rec1["rounds"] == 2
    assert os.path.exists(os.path.join(tmp, "tasks", f"{tid1}.json"))
    hist.finalize_failed(tid2, "API 请求超时", {"task_id": tid2, "input": {}})
    assert hist.get(tid2)["status"] == "failed"
    found = hist.search("张三")
    assert len(found) == 1 and found[0]["task_id"] == tid1
    assert len(hist.search("", "失败", "最新")) == 1
    ok, failed = hist.delete(tid1)
    assert ok and not failed
    assert hist.get(tid1) is None
    assert not os.path.exists(fake_docx) and not os.path.exists(fake_docx2)
    assert not os.path.exists(os.path.join(tmp, "tasks", f"{tid1}.json"))
    assert hist.delete_many([tid2]) == []
    log.get().info("历史记录测试通过（创建/状态/归档/搜索/删除/文件关联）")

    from sources import websearch
    assert hasattr(websearch, "search_links")

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    app.setStyle("Fusion")
    apply_light_theme(app)
    from gui.main_window import MainWindow
    win = MainWindow()
    for i in range(win.stack.count()):
        win.stack.setCurrentIndex(i)
        win.pages[i].refresh()
    from gui.main_window import SettingsDialog
    from gui.model_manager import ModelManagerDialog
    SettingsDialog(win, win.config)
    ModelManagerDialog(win, win.config)
    log.get().info("设置与模型管理对话框构造检查通过")
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QLineEdit, QPlainTextEdit
    for w in win.findChildren(QLineEdit) + win.findChildren(QPlainTextEdit):
        c = w.palette().color(QPalette.ColorRole.Text)
        assert c.name() not in ("#ffffff", "#fefefe"), f"文字颜色异常: {c.name()}"
    win.project.update_info({"topic": "输入框文字渲染检查", "school": "测试大学",
                             "name": "测试", "word_count": 3000})
    win.sidebar.setCurrentRow(4)
    win.pages[4].refresh()
    win.show()
    app.processEvents()
    img = win.pages[4].topic.grab().toImage()
    dark = sum(1 for y in range(img.height()) for x in range(img.width())
               if (0.299 * img.pixelColor(x, y).red() + 0.587 * img.pixelColor(x, y).green()
                   + 0.114 * img.pixelColor(x, y).blue()) < 100)
    assert dark > 10, "输入框文字渲染失败（白字白底）"
    log.get().info("界面文字颜色与渲染检查通过")
    result_path = os.path.join(tempfile.gettempdir(), "paper_assistant_selfcheck.txt")
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(f"SELFCHECK OK v{paths.VERSION}")
    log.get().info("自检通过 version=%s", paths.VERSION)
    print(f"SELFCHECK OK v{paths.VERSION}")


def apply_light_theme(app):
    from PySide6.QtGui import QColor, QPalette
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#f5f6f8"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#1d2939"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f2f4f7"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#1d2939"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#98a2b3"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1d2939"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#356fd3"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#1d2939"))
    app.setPalette(pal)


def run_ui_check():
    import tempfile
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["PAPER_PROJECT_DIR"] = tempfile.mkdtemp(prefix="pa_uicheck_")
    from core import log
    log.setup_logging()
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    app.setStyle("Fusion")
    apply_light_theme(app)
    from gui.main_window import MainWindow
    win = MainWindow()
    win.show()
    app.processEvents()
    sizes = [(900, 650), (1280, 720), (1366, 768), (1600, 900), (1920, 1080),
             (2560, 1440), (3840, 2160)]
    lines = []
    for w, h in sizes:
        win.resize(w, h)
        app.processEvents()
        for i in range(win.stack.count()):
            win.sidebar.setCurrentRow(i)
            win.pages[i].refresh()
            app.processEvents()
        adv = win.pages[2]
        for i in range(adv.stack.count()):
            adv.nav.setCurrentRow(i)
            app.processEvents()
        sidebar_state = "自动折叠" if w < 1100 else "显示"
        lines.append(f"{w}x{h}: 布局加载正常（侧边栏{sidebar_state}）")
        assert win.width() == w and win.height() == h, (w, h, win.width(), win.height())
    win.resize(600, 400)
    app.processEvents()
    assert win.width() >= 900 and win.height() >= 650, "最小尺寸限制失效"
    lines.append("最小尺寸限制 900x650: 生效")
    win.resize(1400, 900)
    app.processEvents()
    win.close()
    from config.manager import ConfigManager
    cfg = ConfigManager()
    g = cfg.get("window_geometry") or {}
    assert int(g.get("w") or 0) == 1400, g
    lines.append("窗口状态记忆: 已保存并验证 (1400x900)")
    from core import log as lg
    lg.get().info("UI 布局检查通过 %s", "; ".join(lines))
    print("UI CHECK OK")
    for line in lines:
        print("  -", line)


def main():
    if "--selfcheck" in sys.argv:
        run_selfcheck()
        return
    if "--ui-check" in sys.argv:
        run_ui_check()
        return

    from core import log, paths
    paths.ensure_all_dirs()
    log.setup_logging()

    log.get().info("程序启动 version=%s release=%s frozen=%s",
                   paths.VERSION, paths.RELEASE_DATE, getattr(sys, "frozen", False))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app.setStyle("Fusion")
    apply_light_theme(app)
    app.setApplicationName("论文智能研究与写作助手")

    from gui.main_window import MainWindow
    win = MainWindow()
    win.show()

    if not _any_model_key(win.config):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            win, "首次运行配置",
            "未检测到任何已启用模型的 API Key。\n\n"
            "请到【设置 → AI 模型管理】中配置模型供应商与 API Key\n"
            "（也可通过各供应商环境变量提供，如 DEEPSEEK_API_KEY）。\n"
            "若暂无 Key，可先进行论文信息填写与资料检索。")
        win.show_settings_dialog()

    sys.exit(app.exec())


def _any_model_key(cfg):
    try:
        from core.ai.credentials import CredentialError, resolve_api_key
        from core.ai.domain import AIProvider
        from core.ai.runtime import credential_store
        store = credential_store()
        for provider_id, record in cfg.ai_providers().items():
            provider = AIProvider.from_dict(provider_id, record)
            if not provider.enabled:
                continue
            legacy = cfg.models().get(provider_id, {})
            try:
                if resolve_api_key(provider, store, str(legacy.get("api_key") or "")):
                    return True
            except CredentialError:
                pass
            if provider.adapter_type.value == "ollama" and "localhost" in provider.base_url:
                return True
    except (ImportError, KeyError, TypeError, ValueError):
        pass
    for key, m in cfg.models().items():
        if not m.get("enabled"):
            continue
        env_name = m.get("env_key") or ""
        if env_name and os.environ.get(env_name, "").strip():
            return True
        if str(m.get("api_key") or "").strip():
            return True
        if m.get("type") == "openai_compatible" and "localhost" in str(m.get("base_url") or ""):
            return True
    return False


if __name__ == "__main__":
    main()

# 版本: v2.3.0 (2026-08-19) 更新: 自动质量门自检契约
