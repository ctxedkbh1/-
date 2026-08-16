import os
import threading
import time

from PySide6.QtCore import QObject, Signal

from config.manager import ConfigManager
from core import detector, exporter, fact_checker, log, naturalizer, outline as outline_mod, \
    quality_report, research, style_checker, writer as writer_mod
from core.checkpoint import AutoCheckpoint

STAGE_LABELS = [
    ("info", "读取论文要求"),
    ("topic", "解析论文题目"),
    ("outline_read", "分析论文大纲"),
    ("queries", "生成检索关键词"),
    ("openalex", "OpenAlex 文献检索"),
    ("crossref", "Crossref 文献核验"),
    ("government", "政府官方资料检索"),
    ("cnki", "读取已有 CNKI 资料"),
    ("evidence", "建立证据库"),
    ("verify", "证据真实性检查"),
    ("structure", "生成论文结构"),
    ("write", "分章节生成论文"),
    ("citations", "引用检查"),
    ("references", "参考文献检查"),
    ("structure_check", "检查论文结构"),
    ("wordcount_check", "检查字数"),
    ("factcheck", "事实核查"),
    ("quality", "相似内容与模板化分析"),
    ("naturalize", "定位并优化问题段落"),
    ("factcheck2", "修改后再核查"),
    ("citations2", "再次引用检查"),
    ("export", "生成 Word 与报告"),
    ("done", "完成"),
]

MAX_QUERIES = 5
MAX_OPENALEX_TOTAL = 15
MAX_GOV_PAGES = 3
MAX_QUALITY_ROUNDS = 5
RISK_PRESETS = [5, 10, 20, 30, 40, 50, 60]


class PipelineCancelled(Exception):
    pass


class PipelineError(Exception):
    pass


class Controller:
    def __init__(self):
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()

    def pause(self):
        self.pause_event.set()

    def resume(self):
        self.pause_event.clear()

    def cancel(self):
        self.cancel_event.set()


class AutoPipelineEngine(QObject):
    stage_changed = Signal(str, str)
    progress = Signal(int)
    log_line = Signal(str)
    finished = Signal(dict)
    aborted = Signal()
    failed = Signal(str)

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.project = mw.project
        self.store = mw.evidence
        self.checkpoint = AutoCheckpoint()
        self.controller = Controller()
        self.input = dict(self.checkpoint.data.get("input") or {})
        self._done = 0
        self._total = len(STAGE_LABELS)
        cfg = ConfigManager()
        self.ai_limit = self._limit("ai_risk_limit", cfg.get_int("ai_risk_limit", 20), 100)
        self.repeat_limit = self._limit("repeat_risk_limit", cfg.get_int("repeat_risk_limit", 20), 100)
        self.max_rounds = self._rounds_limit(cfg.get_int("max_optimization_rounds", 5))
        from core import deepseek
        deepseek.set_task_models(self.input.get("task_models") or {})

    def _limit(self, key, fallback, cap):
        v = self.input.get(key, fallback)
        try:
            v = int(v)
        except (TypeError, ValueError):
            v = fallback
        return max(0, min(cap, v))

    def _rounds_limit(self, fallback):
        v = self.input.get("max_rounds", fallback)
        try:
            v = int(v)
        except (TypeError, ValueError):
            v = fallback
        return max(1, min(10, v))

    # ---------- 基础设施 ----------

    def log(self, msg, level="INFO"):
        self.checkpoint.add_log(msg, level)
        log.get().info("[AUTO] %s", msg)
        self.log_line.emit(msg)

    def _check_cancel(self):
        if self.controller.cancel_event.is_set():
            raise PipelineCancelled()

    def _wait(self):
        while self.controller.pause_event.is_set():
            self._check_cancel()
            time.sleep(0.3)

    def _bump(self):
        self._done += 1
        self.progress.emit(min(99, int(self._done / self._total * 100)))

    def _stage(self, key, fn, on_fail="raise"):
        cp = self.checkpoint
        if cp.is_done(key):
            self.stage_changed.emit(key, "done")
            self._bump()
            return None
        self._wait()
        self._check_cancel()
        self.stage_changed.emit(key, "running")
        for attempt in range(2):
            try:
                result = fn()
                cp.mark_done(key)
                self.stage_changed.emit(key, "done")
                self._bump()
                return result
            except PipelineCancelled:
                raise
            except Exception as e:
                log.get().warning("步骤 %s 第%d次失败: %s", key, attempt + 1, e)
                if attempt == 0:
                    self.log(f"步骤 {key} 失败，自动重试一次：{e}", "WARN")
                    time.sleep(2)
                    self._wait()
                    self._check_cancel()
                    continue
                cp.mark_failed(key, str(e))
                self.stage_changed.emit(key, "failed")
                if on_fail == "skip":
                    cp.mark_skipped(key, str(e))
                    self.stage_changed.emit(key, "skipped")
                    self.log(f"步骤 {key} 跳过：{e}", "WARN")
                    self._bump()
                    return None
                raise PipelineError(f"{dict(STAGE_LABELS)[key]} 失败：{e}")

    def run(self):
        try:
            self._execute()
        except PipelineCancelled:
            self.checkpoint.save()
            self.log("任务已取消，进度已保存，可断点恢复。")
            self.aborted.emit()
        except Exception as e:
            log.get().exception("全自动流程失败")
            self.checkpoint.add_log(f"流程中止：{e}", "ERROR")
            self.failed.emit(str(e))

    # ---------- 流程 ----------

    def _execute(self):
        self.log(f"全自动任务开始（任务ID {self.checkpoint.data.get('task_id')}）")
        if self.checkpoint.done_count() == 0:
            from core import deepseek
            deepseek.reset_usage()
            self.log("新任务开始，API 用量统计已重置。")
        self._stage("info", self._step_info)
        self._stage("topic", self._step_topic)
        self._stage("outline_read", self._step_outline_read)
        self._stage("queries", self._step_queries)
        self._stage("openalex", self._step_openalex, on_fail="skip")
        self._stage("crossref", self._step_crossref, on_fail="skip")
        self._stage("government", self._step_government, on_fail="skip")
        self._stage("cnki", self._step_cnki)
        self._stage("evidence", self._step_evidence)
        self._stage("verify", self._step_verify, on_fail="skip")
        self._stage("structure", self._step_structure)
        self._stage("write", self._step_write)
        self._stage("citations", self._step_citations)
        self._stage("references", self._step_references)
        self._stage("structure_check", self._step_structure_check)
        self._stage("wordcount_check", self._step_wordcount_check)
        self._stage("factcheck", self._step_factcheck, on_fail="skip")
        self._stage("quality", self._step_quality)
        self._stage("naturalize", self._step_naturalize)
        self._stage("factcheck2", self._step_factcheck2, on_fail="skip")
        self._stage("citations2", self._step_citations2)
        self._stage("export", self._step_export)
        self._stage("done", self._step_done)
        result = self._result()
        self.checkpoint.set("result", result)
        self.checkpoint.mark_finished()
        self.progress.emit(100)
        self.log("全自动任务完成。")
        self.finished.emit(result)

    # ---------- 各步骤 ----------

    def _info_fields(self):
        return {
            "topic": self.input.get("topic", "").strip(),
            "name": self.input.get("name", "").strip(),
            "class_name": self.input.get("class_name", "").strip(),
            "course": self.input.get("course", "").strip(),
            "school": self.input.get("school", "").strip(),
            "word_count": int(self.input.get("word_count") or 3000),
            "format_note": self.input.get("format_note", "默认格式"),
        }

    def _step_info(self):
        fields = self._info_fields()
        if not fields["topic"] or not fields["name"]:
            raise PipelineError("论文题目与姓名为必填项")
        self.project.update_info(fields)
        self.log(f"论文信息已载入：{fields['topic']}")

    def _step_topic(self):
        plan = research.generate_plan(self.project.info())
        self.project.set("research_plan", plan)
        from core import paths
        with open(paths.research_plan_md(), "w", encoding="utf-8") as f:
            f.write(research.plan_markdown(self.project.info(), plan))
        self.checkpoint.set("plan", plan)
        self.log(f"题目解析完成，关键词：{'、'.join(plan.get('keywords', [])[:8])}")

    def _step_outline_read(self):
        user_outline = (self.input.get("user_outline") or "").strip()
        if not user_outline:
            self.log("未提供大纲，将由 AI 根据题目与证据自动设计。")
            self.checkpoint.set("user_sections", None)
            return
        sections = outline_mod.structure_user_outline(self.project.info(), user_outline)
        self.checkpoint.set("user_sections", sections)
        self.log(f"用户大纲已结构化：{len(sections['sections'])} 章")

    def _step_queries(self):
        plan = self.checkpoint.get("plan") or self.project.get("research_plan") or {}
        kws = plan.get("keywords") or []
        topic = self.project.info().get("topic", "")
        queries = []
        if topic:
            queries.append(topic)
        for k in kws:
            queries.append(k)
            if len(queries) < MAX_QUERIES:
                queries.append(f"{topic} {k}")
        queries = list(dict.fromkeys(queries))[:MAX_QUERIES]
        self.checkpoint.set("queries", queries)
        self.log(f"检索关键词：{'、'.join(queries)}")

    def _step_openalex(self):
        from sources import openalex
        queries = self.checkpoint.get("queries") or []
        added = []
        seen = set()
        for e in self.store.all():
            key = (e.get("doi") or "").lower() or (e.get("title") or "").lower()
            if key:
                seen.add(key)
        for q in queries:
            self._wait()
            self._check_cancel()
            try:
                records = openalex.search(q, 8)
            except Exception as e:
                self.log(f"OpenAlex 检索失败（继续下一关键词）: {e}", "WARN")
                continue
            for rec in records:
                key = (rec.get("doi") or "").lower() or (rec.get("title") or "").lower()
                if key and key in seen:
                    continue
                seen.add(key)
                rec["content"] = rec.get("abstract") or "（无摘要，请打开来源核对后补充证据内容）"
                rec["organization"] = rec.get("journal") or ""
                eid = self.store.add(rec)
                added.append(eid)
                if len(added) >= MAX_OPENALEX_TOTAL:
                    break
            if len(added) >= MAX_OPENALEX_TOTAL:
                break
        self.checkpoint.set("openalex_added", added)
        self.log(f"OpenAlex 新增证据 {len(added)} 条：{'、'.join(added) or '无'}")

    def _step_crossref(self):
        from sources import crossref
        checked = updated = 0
        for e in self.store.all():
            doi = (e.get("doi") or "").strip()
            if not doi:
                continue
            self._wait()
            self._check_cancel()
            try:
                rec = crossref.lookup_doi(doi)
            except Exception as ex:
                self.log(f"DOI 核验失败 {doi}: {ex}", "WARN")
                continue
            checked += 1
            patch = {}
            for key in ("authors", "journal", "year", "volume_issue_pages", "publisher"):
                if rec.get(key) and not e.get(key):
                    patch[key] = rec.get(key)
            if patch:
                self.store.update(e["id"], patch)
                updated += 1
            self.store.update(e["id"], {"verified": True})
        self.log(f"Crossref 核验 {checked} 条，补全著录 {updated} 条。")

    def _step_government(self):
        from sources import government, websearch
        queries = self.checkpoint.get("queries") or []
        added = []
        seen_urls = {e.get("url") for e in self.store.all() if e.get("url")}
        for q in queries[:3]:
            self._wait()
            self._check_cancel()
            try:
                links = websearch.search_government_links(q, 4)
            except Exception as e:
                self.log(f"政府网页搜索不可用（跳过）: {e}", "WARN")
                continue
            for url in links:
                if url in seen_urls:
                    continue
                self._wait()
                self._check_cancel()
                try:
                    rec = government.fetch(url)
                except Exception as e:
                    self.log(f"政府网页抓取失败 {url}: {e}", "WARN")
                    continue
                seen_urls.add(url)
                eid = self.store.add(rec)
                added.append(eid)
                self.log(f"政府资料已加入：{eid} {rec.get('title') or url}")
                if len(added) >= MAX_GOV_PAGES:
                    break
            if len(added) >= MAX_GOV_PAGES:
                break
        self.checkpoint.set("gov_added", added)
        if not added:
            self.log("未自动获取到政府网页。建议在手动模式【3 资料检索 → C 政府官方网站】中补充官方资料。", "WARN")

    def _step_cnki(self):
        cnki_evs = [e for e in self.store.all() if e.get("source_type") == "cnki"]
        self.checkpoint.set("cnki_count", len(cnki_evs))
        self.log(f"已有 CNKI 证据 {len(cnki_evs)} 条（CNKI 资料通过手动录入/导入，程序不绕过登录或验证码）。")

    def _step_evidence(self):
        n = len(self.store.all())
        self.checkpoint.set("evidence_total", n)
        if n == 0:
            self.log("证据库为空：正文将按规范标注“暂无足够可靠资料支持该观点”，不会编造任何内容。", "WARN")
        else:
            self.log(f"证据库共 {n} 条，全部可追溯编号。")

    def _step_verify(self):
        import requests as _requests
        from sources import crossref
        ok = fail = skip = 0
        for e in self.store.all():
            self._wait()
            self._check_cancel()
            url = (e.get("url") or "").strip()
            doi = (e.get("doi") or "").strip()
            try:
                if url.startswith("http"):
                    r = _requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                                      timeout=15, allow_redirects=True)
                    self.store.update(e["id"], {"verified": r.status_code < 400})
                    ok += 1 if r.status_code < 400 else 0
                    fail += 0 if r.status_code < 400 else 1
                elif doi:
                    crossref.lookup_doi(doi)
                    self.store.update(e["id"], {"verified": True})
                    ok += 1
                else:
                    skip += 1
            except Exception:
                skip += 1
        self.log(f"证据真实性检查：可验证 {ok} 条、异常 {fail} 条、无链接跳过 {skip} 条。")

    def _step_structure(self):
        user_sections = self.checkpoint.get("user_sections")
        if user_sections:
            outline = outline_mod.assign_evidence(user_sections, self.store)
        else:
            outline = outline_mod.generate_outline(self.project.info(), self.store)
        self.project.set_outline(outline)
        from core import paths
        with open(paths.outline_md(), "w", encoding="utf-8") as f:
            f.write(outline_mod.outline_markdown(outline, self.store))
        self.checkpoint.set("outline", outline)
        secs = outline.get("sections", [])
        total = sum(s.get("target_words", 0) for s in secs)
        self.log(f"论文结构已确定：{len(secs)} 章，总目标 {total} 字。")

    def _step_write(self):
        outline = self.project.outline() or {}
        sections = outline.get("sections", [])
        if not sections:
            raise PipelineError("论文结构为空，无法写作")
        done_ids = set(self.checkpoint.data.get("chapters_done", []))
        checks = self.checkpoint.get("chapter_checks") or {}
        insufficient = list(self.checkpoint.get("insufficient_chapters") or [])
        base = self._done + 1
        for idx in range(1, len(sections) + 1):
            self._wait()
            self._check_cancel()
            if idx in done_ids and writer_mod.read_chapter(idx).strip():
                continue
            sec = sections[idx - 1]
            assigned = list(sec.get("evidence_ids", []))
            for sub in sec.get("subsections", []):
                assigned += sub.get("evidence_ids", [])
            if not assigned and not self.store.all():
                insufficient.append(f"{sec.get('title', '')}（第{idx}章）")
                self.checkpoint.set("insufficient_chapters", insufficient)
            text = None
            for attempt in range(2):
                self._wait()
                self._check_cancel()
                try:
                    text = writer_mod.write_chapter(self.project.info(), outline, idx, self.store)
                    break
                except Exception as e:
                    log.get().warning("第%d章写作失败(第%d次): %s", idx, attempt + 1, e)
                    if attempt == 0:
                        self.log(f"第 {idx} 章写作失败，自动重试：{e}", "WARN")
                        time.sleep(2)
                        continue
                    raise PipelineError(f"第 {idx} 章写作失败：{e}")
            check = writer_mod.check_chapter(text, self.store, assigned)
            checks[str(idx)] = check
            if check.get("unknown"):
                self.log(f"第 {idx} 章出现未知引用编号 {check['unknown']}，自动重新生成一次。", "WARN")
                self._wait()
                self._check_cancel()
                try:
                    text = writer_mod.write_chapter(self.project.info(), outline, idx, self.store)
                    check = writer_mod.check_chapter(text, self.store, assigned)
                    checks[str(idx)] = check
                except Exception as e:
                    self.log(f"第 {idx} 章重新生成失败：{e}", "WARN")
            self.checkpoint.data.setdefault("chapters_done", []).append(idx)
            self.checkpoint.set("chapter_checks", checks)
            self.checkpoint.save()
            self.log(f"第 {idx} 章完成（{check['words']} 字，引用 {check['cited'] or '无'}）。")
            self.progress.emit(min(99, int((base + idx - 1) / self._total * 100)))
        if insufficient:
            self.log("以下章节资料不足，正文已按规范标注：\n" + "\n".join(insufficient), "WARN")

    def _full_text(self):
        return exporter.build_full_text(self.project)

    def _step_citations(self):
        analysis = fact_checker.analyze(self._full_text(), self.store)
        self.checkpoint.set("analysis", analysis)
        self.project.set("check", analysis)
        if analysis.get("unresolved"):
            self.log(f"引用检查发现未知编号：{analysis['unresolved']}（将保留标注并在报告中提示）。", "WARN")
        else:
            self.log(f"引用检查通过：正文引用 {analysis['citation_count']} 处，全部可追溯到证据库。")

    def _step_references(self):
        analysis = self.checkpoint.get("analysis") or {}
        if analysis.get("unused"):
            self.log(f"参考文献检查：{len(analysis['unused'])} 条证据未在正文使用（将保留并在报告中提示）。", "WARN")
        else:
            self.log("参考文献检查通过：所有证据均被正文使用，正文引用与参考文献一一对应。")

    def _step_structure_check(self):
        from core import style_checker
        full = self._full_text()
        outline = self.project.outline() or {}
        stats = style_checker.structure_stats(
            full, len(outline.get("sections", [])),
            self.project.get("final_meta") or {})
        self.checkpoint.set("structure_stats", stats)
        problems = []
        if stats["sections"] and stats["headings"] < stats["sections"]:
            problems.append("章节标题数少于大纲章节数")
        if stats["paragraphs"] < stats["sections"]:
            problems.append("部分章节缺少段落内容")
        if not stats["has_abstract"]:
            problems.append("尚未生成摘要")
        if problems:
            self.log("结构检查发现问题：" + "；".join(problems), "WARN")
        else:
            self.log(f"结构检查通过：{stats['sections']} 章、{stats['paragraphs']} 段、"
                     f"{stats['headings']} 个标题。")

    def _step_wordcount_check(self):
        from core import style_checker
        full = self._full_text()
        required = int(self.project.info().get("word_count") or 3000)
        actual = style_checker.structure_stats(full).get("words", 0)
        ok = actual >= required * 0.85
        self.checkpoint.set("wordcount", {"required": required, "actual": actual, "ok": ok})
        if ok:
            self.log(f"字数检查通过：正文约 {actual} 字（要求 {required} 字）。")
        else:
            self.log(f"字数检查：正文约 {actual} 字，低于要求 {required} 字，"
                     "将在优化阶段于证据范围内补充分析（不新增任何事实）。", "WARN")

    def _step_factcheck(self):
        issues = fact_checker.ai_fact_check(self._full_text(), self.store)
        self.checkpoint.set("issues", issues)
        self.project.set("check_ai_issues", issues)
        if issues:
            self.log(f"事实核查发现 {len(issues)} 处问题（详见核验报告）。", "WARN")
        else:
            self.log("事实核查通过：未发现与证据表冲突的内容。")

    def _step_quality(self):
        style = style_checker.analyze(self._full_text())
        ai_issues = style_checker.ai_content_check(self._full_text(), self.store)
        self.checkpoint.set("style", style)
        self.checkpoint.set("style_ai", ai_issues)
        self.log(f"写作质量检测：模板化 {style['template_score']}，重复 {style['repeat_count']} 处，"
                 f"空洞 {len(style['empties'])} 处，连接词占比 {style['uniformity']}%。")

    def _step_naturalize(self):
        from core import style_checker
        style = self.checkpoint.get("style") or {}
        ai_issues = self.checkpoint.get("style_ai") or []
        wordcount = self.checkpoint.get("wordcount") or {}
        need_expand = bool(wordcount) and not wordcount.get("ok", True)
        detection = detector.detect(self._full_text(), style)
        target_met = self._target_met(detection)
        needs_work = style.get("needs_work") or any(
            i.get("severity") in ("高", "中") for i in ai_issues)
        if target_met and not needs_work and not need_expand:
            self.checkpoint.set("detection_final", detection)
            self.checkpoint.set("quality_rounds", 0)
            self.log(f"检测结果已满足目标：AI文本风险 {detection['ai_risk']}% ≤ {self.ai_limit}%，"
                     f"重复/相似内容风险 {detection['repeat_risk']}% ≤ {self.repeat_limit}%，无需优化。")
            return
        outline = self.project.outline() or {}
        sections = outline.get("sections", [])
        existing_log = list(self.checkpoint.get("modification_log") or [])
        start_rnd = len(existing_log) + 1
        rounds_used = 0
        total_naturalized = 0
        total_reverted = 0
        mod_log = existing_log
        for rnd in range(start_rnd, start_rnd + self.max_rounds):
            rounds_used = rnd
            from core import deepseek
            limit_hit = deepseek.limits_reached()
            if limit_hit:
                self.log(f"已触发成本/调用限制（{limit_hit}），暂停自动优化。", "WARN")
                break
            round_paras = 0
            round_chapters = []
            changed = 0
            focus = self._focus_hint(detection)
            for idx in range(1, len(sections) + 1):
                self._wait()
                self._check_cancel()
                orig = writer_mod.read_chapter(idx)
                if not orig.strip():
                    continue
                results, flagged = style_checker.analyze_paragraphs(orig)
                if detection["repeat_risk"] > self.repeat_limit:
                    for r in results:
                        if r.get("dup_sentences") and r["index"] not in flagged:
                            flagged.append(r["index"])
                expand_this = need_expand and rnd == start_rnd
                if not flagged and not expand_this:
                    continue
                try:
                    new_text = naturalizer.naturalize_paragraphs(
                        orig, flagged, self.project.info(),
                        sections[idx - 1].get("title", ""),
                        expand=expand_this, focus=focus)
                except Exception as e:
                    self.log(f"第 {idx} 章段落优化失败（保留原文）: {e}", "WARN")
                    continue
                safe = naturalizer.safe_rewrite(orig, new_text)
                if safe is None:
                    total_reverted += 1
                    self.log(f"第 {idx} 章修改被撤销（引用编号或数字发生变化，未改变事实）。", "WARN")
                    continue
                writer_mod.save_chapter(idx, safe)
                total_naturalized += 1
                changed += 1
                round_paras += len(flagged) if flagged else 1
                round_chapters.append(idx)
            if round_chapters:
                entry = {"round": rnd, "paragraphs_modified": round_paras,
                         "chapters": round_chapters,
                         "expand": need_expand and rnd == start_rnd,
                         "ai_risk_before": detection.get("ai_risk"),
                         "repeat_risk_before": detection.get("repeat_risk")}
                mod_log.append(entry)
                self.checkpoint.set("modification_log", mod_log)
            style = style_checker.analyze(self._full_text())
            self.checkpoint.set("style", style)
            detection = detector.detect(self._full_text(), style)
            target_met = self._target_met(detection)
            self.checkpoint.set("detection_final", detection)
            self.log(f"第 {rnd} 轮优化：修改 {len(round_chapters)} 章 {round_paras} 个段落。"
                     f"当前 AI文本风险 {detection['ai_risk']}%（目标 ≤ {self.ai_limit}%），"
                     f"重复/相似内容风险 {detection['repeat_risk']}%（目标 ≤ {self.repeat_limit}%）。")
            if not changed:
                self.log("本轮无可优化段落，优化结束。")
                break
            if target_met and not (need_expand and not wordcount.get("ok") and rnd == start_rnd):
                break
        maxed = rounds_used >= start_rnd + self.max_rounds - 1
        if maxed and not self._target_met(detection):
            self.log(f"已经达到最大自动优化次数（{self.max_rounds} 轮），"
                     f"当前 AI文本风险 {detection['ai_risk']}% / 重复风险 {detection['repeat_risk']}%，"
                     "未完全达到用户设置的输出条件。", "WARN")
        self.checkpoint.set("quality_rounds", rounds_used)
        self.checkpoint.set("naturalized_count", total_naturalized)
        self.checkpoint.set("reverted_count", total_reverted)
        self.checkpoint.set("modification_log", mod_log)
        self.checkpoint.set("detection_final", detection)
        self.log(f"优化结束：本次 {self.max_rounds} 轮上限内共修改 {total_naturalized} 章、"
                 f"撤销 {total_reverted} 章（修改过程中未改变任何事实、数据与引用）。"
                 f"最终检测：{detector.source_label(detection)}。")

    def _target_met(self, detection):
        return (detection.get("ai_risk", 100) <= self.ai_limit and
                detection.get("repeat_risk", 100) <= self.repeat_limit)

    def _focus_hint(self, detection):
        parts = []
        if detection.get("ai_risk", 0) > self.ai_limit:
            parts.append("降低模板化表达与机械句式，避免空泛套话，增强具体分析")
        if detection.get("repeat_risk", 0) > self.repeat_limit:
            parts.append("重组重复/高相似段落，合并重复观点，改写重复句")
        return "；".join(parts) or "整体提升表达自然度与具体性"

    def _step_factcheck2(self):
        issues = fact_checker.ai_fact_check(self._full_text(), self.store)
        self.checkpoint.set("issues2", issues)
        self.project.set("check_ai_issues", issues)
        self.log(f"自然化后事实核查：{'发现问题 ' + str(len(issues)) + ' 处' if issues else '通过'}。")

    def _step_citations2(self):
        analysis = fact_checker.analyze(self._full_text(), self.store)
        prev = self.checkpoint.get("analysis") or {}
        self.checkpoint.set("analysis2", analysis)
        self.project.set("check", analysis)
        lost = set(prev.get("refs") or []) - set(analysis.get("refs") or [])
        if lost:
            self.log(f"引用复查：与自然化前相比引用变化 {sorted(lost)}（将在报告中提示）。", "WARN")
        elif analysis.get("unresolved"):
            self.log(f"引用复查：存在未知编号 {analysis['unresolved']}。", "WARN")
        else:
            self.log("再次引用检查通过：引用与参考文献双向对应。")

    def _step_export(self):
        analysis = self.checkpoint.get("analysis2") or self.checkpoint.get("analysis") or {}
        issues = self.checkpoint.get("issues2") or self.checkpoint.get("issues") or []
        sections = (self.project.outline() or {}).get("sections") or []
        done = [i for i in range(1, len(sections) + 1) if writer_mod.read_chapter(i).strip()]
        total = sum(writer_mod.cjk_count(writer_mod.read_chapter(i)) for i in done)
        from core import output_location
        cfg = ConfigManager()
        choice = self.input.get("export_choice") or cfg.get("export_choice", "default")
        custom = self.input.get("export_custom_path") or cfg.get("export_custom_path", "")
        out_dir = output_location.resolve_output_dir(choice, custom)
        ok, err = output_location.ensure_dir(out_dir)
        if not ok:
            self.log(f"输出目录创建失败，改用默认位置：{err}", "WARN")
            out_dir = paths.output_dir()
            output_location.ensure_dir(out_dir)
        writable, werr = output_location.is_writable(out_dir)
        if not writable:
            self.log(f"输出目录不可写，改用默认位置：{werr}", "WARN")
            out_dir = paths.output_dir()
            output_location.ensure_dir(out_dir)
        self.log(f"输出目录：{out_dir}")
        paths_out = exporter.export_files(self.project, self.store, analysis, issues,
                                          len(done), total,
                                          self.checkpoint.get("chapter_checks") or {},
                                          out_dir=out_dir)
        out_dir = os.path.dirname(paths_out["md"])
        with open(os.path.join(out_dir, "证据表.json"), "w", encoding="utf-8") as f:
            f.write(self.store.export_json())
        with open(os.path.join(out_dir, "全自动运行日志.md"), "w", encoding="utf-8") as f:
            f.write(self.checkpoint.build_log_markdown())
        style = self.checkpoint.get("style") or style_checker.analyze(self._full_text())
        ai_style = self.checkpoint.get("style_ai") or []
        structure_stats = self.checkpoint.get("structure_stats") or {}
        wordcount = self.checkpoint.get("wordcount") or {}
        refs_count = len(analysis.get("refs", []))
        scores = style_checker.score(style, structure_stats,
                                     wordcount.get("ok"), refs_count)
        self.checkpoint.set("scores", scores)
        detection = self.checkpoint.get("detection_final") or \
            detector.detect(self._full_text(), style)
        self.checkpoint.set("detection_final", detection)
        qr = quality_report.build(self.project, self.store, analysis, style,
                                  self.checkpoint.get("quality_rounds") or 0,
                                  self.checkpoint.get("insufficient_chapters") or [],
                                  self.checkpoint.get("naturalized_count") or 0,
                                  ai_style,
                                  structure_stats=structure_stats,
                                  wordcount=wordcount,
                                  scores=scores,
                                  modification_log=self.checkpoint.get("modification_log") or [],
                                  reverted_count=self.checkpoint.get("reverted_count") or 0,
                                  detection=detection,
                                  ai_limit=self.ai_limit,
                                  repeat_limit=self.repeat_limit,
                                  max_rounds=self.max_rounds)
        with open(os.path.join(out_dir, "论文质量报告.md"), "w", encoding="utf-8") as f:
            f.write(qr)
        report_path = paths_out["report"]
        with open(report_path, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n" + qr)
        self.checkpoint.set("export_paths", paths_out)
        self.log("已生成：论文.docx、论文.md、资料核验报告.md、证据表.json、论文质量报告.md、全自动运行日志.md")

    def _step_done(self):
        self.log("全自动流程全部步骤完成。")

    def _result(self):
        analysis = self.checkpoint.get("analysis2") or self.checkpoint.get("analysis") or {}
        style = self.checkpoint.get("style") or {}
        pending = len(self.store.pending_count())
        scores = self.checkpoint.get("scores") or {}
        detection = self.checkpoint.get("detection_final") or {}
        target_met = self._target_met(detection) if detection else False
        quality = "良好"
        if style.get("template_score") == "高":
            quality = "较差"
        elif style.get("template_score") == "中":
            quality = "一般"
        final_status = "可以导出"
        if analysis.get("unresolved"):
            final_status = "需人工检查"
        return {
            "paths": self.checkpoint.get("export_paths") or {},
            "evidence_count": len(self.store.all()),
            "verified": self.store.verified_count(),
            "pending": pending,
            "factcheck_ok": not (self.checkpoint.get("issues2") or self.checkpoint.get("issues")),
            "citations_ok": not analysis.get("unresolved"),
            "references_ok": bool(analysis.get("bidirectional_ok")),
            "style_level": style.get("template_score", "低"),
            "quality": quality,
            "rounds": self.checkpoint.get("quality_rounds") or 0,
            "insufficient": self.checkpoint.get("insufficient_chapters") or [],
            "final_status": final_status,
            "scores": scores,
            "structure_stats": self.checkpoint.get("structure_stats") or {},
            "wordcount": self.checkpoint.get("wordcount") or {},
            "modification_log": self.checkpoint.get("modification_log") or [],
            "naturalized_count": self.checkpoint.get("naturalized_count") or 0,
            "reverted_count": self.checkpoint.get("reverted_count") or 0,
            "ai_risk": detection.get("ai_risk"),
            "repeat_risk": detection.get("repeat_risk"),
            "ai_limit": self.ai_limit,
            "repeat_limit": self.repeat_limit,
            "max_rounds": self.max_rounds,
            "target_met": target_met,
            "detection_source": detector.source_label(detection) if detection else "",
        }

# 版本: v1.8.0 (2026-08-16) 更新: 自定义输出文件夹
