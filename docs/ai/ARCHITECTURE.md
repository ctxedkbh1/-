# 项目架构（ARCHITECTURE）

> 依据：真实源码分析（2026-08-18，v2.2.0）。若与源码不符，以源码为准。

## 分层架构

```
PySide6 图形界面（gui/）
    ├── main_window.py            主窗口（三模式导航）
    └── pages/                    8 个阶段页 + 全自动页 + 高级工作台 + 历史页 + 导出页 + 批注管理页
        │
        ▼
应用层（core/）
    ├── 任务编排：auto_pipeline.py（全自动 Controller/Engine，21 步，断点恢复）
    │             advanced_state.py（高级工作台 6 阶段状态机）
    ├── 写作引擎：writer.py / outline.py / naturalizer.py / targeted_edit.py
    ├── 质量体系：fact_checker.py / style_checker.py / quality_report.py / detector.py
    ├── 证据与批注：evidence.py / annotations.py / research.py / checkpoint.py
    ├── 文档引擎：document.py（统一模型）/ exporter.py（6 格式导出）
    └── 基础设施：paths.py / log.py / history.py / output_location.py / prompts.py / project.py
        │
        ▼
AI Provider 层（core/llm.py + core/deepseek.py + core/model_presets.py）
    ├── OpenAICompatibleProvider（DeepSeek/OpenAI/Qwen/Moonshot/智谱/OpenRouter/Ollama/自定义）
    ├── ClaudeProvider（Anthropic Messages API）
    └── GeminiProvider（Google Gemini API）
        │
        ▼
检索层（sources/）
    ├── openalex.py / crossref.py    公开学术 API
    ├── government.py / websearch.py 公开网页（尽力而为，失败跳过）
    └── cnki.py                      手动录入 + RIS/BibTeX 导入
        │
        ▼
存储层（本地文件，无数据库）
    paper_project\（config.json / project.json / evidence.json / annotations.json /
                    annotation_styles.json / auto_checkpoint.json /
                    research_plan.md / outline.md / chapters\ / logs\ / cache\ / output\）
```

## 模块清单与位置

| 层 | 文件 | 职责 |
|---|---|---|
| 入口 | main.py | 启动 GUI；--selfcheck 无界面自检；浅色主题 |
| UI | gui/main_window.py | 主窗口、页面导航 |
| UI | gui/pages/home_page.py | 首页（三模式入口） |
| UI | gui/pages/{info,search,evidence,outline,writing,factcheck,export}_page.py | 普通模式 8 阶段页 |
| UI | gui/pages/auto_mode_page.py | 全自动模式（表单/进度/完成面板） |
| UI | gui/pages/advanced_workspace.py | 高级模式工作台 |
| UI | gui/pages/history_page.py | 论文历史 |
| UI | gui/pages/annotation_page.py | 批注、样式模板、批量删除与重新编号 |
| UI | gui/pages/model_manager.py | 模型管理 |
| UI | gui/widgets.py | 公共控件 |
| 配置 | config/manager.py | API Key 管理；环境变量（DEEPSEEK_API_KEY 等）优先于 config.json |
| AI | core/llm.py | LLMProvider 接口 + 三套 Provider + 模型路由 |
| AI | core/deepseek.py | DeepSeek 专用（旧版兼容，主要逻辑已并入 llm.py） |
| AI | core/model_presets.py | 模型预设方案 |
| AI | core/prompts.py | 全部提示词 |
| 编排 | core/auto_pipeline.py | 全自动 21 步；自动重试；on_fail=skip；断点恢复 |
| 编排 | core/advanced_state.py | 高级工作台状态 |
| 编排 | core/checkpoint.py | 断点数据 auto_checkpoint.json |
| 写作 | core/writer.py | 分章节写作（只能引用证据 [E001]） |
| 写作 | core/outline.py | 大纲生成 |
| 写作 | core/naturalizer.py | 自然化修改（事实/数字/引用/参考文献强制保护） |
| 写作 | core/targeted_edit.py | 定向修改 |
| 质量 | core/fact_checker.py | AI 逐句事实核查（最多 3 轮） |
| 质量 | core/style_checker.py | 模板化/重复/句式单一/空洞检测 |
| 质量 | core/quality_report.py | 质量报告 |
| 质量 | core/detector.py | 内置启发式 AI 痕迹分析（未接第三方检测 API） |
| 证据 | core/evidence.py | 证据表 evidence.json（E001 编号） |
| 批注 | core/annotations.py | annotations.json、annotation_styles.json、旧证据同步与显示编号 |
| 证据 | core/research.py | 研究方案、检索编排 |
| 文档 | core/document.py | 统一 Document 模型 |
| 文档 | core/exporter.py | DOCX/PPTX/PDF/TXT/MD/HTML 导出 + 验证 |
| 检索 | sources/openalex.py, crossref.py, government.py, websearch.py, cnki.py | 5 个检索源 |
| 基础设施 | core/paths.py | 版本号、数据目录（**版本号唯一来源**） |
| 基础设施 | core/log.py | 日志（不含 API Key） |
| 基础设施 | core/history.py | 历史任务归档 |
| 基础设施 | core/output_location.py | 自定义输出目录 |
| 基础设施 | core/project.py | 项目信息 project.json |
| 测试 | tests/dev_auto_test.py 等 4 个 | 离线端到端/历史/自然化/设置测试 |
| 打包 | build.bat / build_share.bat | PyInstaller 打包并复制到桌面 |

## 关键数据流

1. 用户选择模式 → 对应页面收集输入
2. 检索层返回结果 → core/research.py 整理 → evidence.py 生成证据表
3. AnnotationStore 将旧 E-ID 同步为证据批注，并独立管理普通批注与样式模板
4. 写作：writer.py 携带证据编号调用 AI → 引用只能来自 evidence.json
5. 质量循环：style_checker → naturalizer（保护事实与批注标记）→ fact_checker（最多 3 轮）
6. exporter.py 从统一 Document 模型导出 6 格式、批注说明和批注表并验证
7. 全自动模式：auto_pipeline.py 按 21 步串行执行，checkpoint.py 每步落盘断点

## 防编造机制（最高优先级，禁止削弱）

1. AI 写作只能引用 evidence.json 已有证据，引用处标注 `[E001]` 编号
2. 证据不足时强制输出"暂无足够可靠资料支持该观点"
3. 自然化修改只改句式表达；数字/事实/引用编号/参考文献被程序强制保护，变化即撤销该章修改
4. 输出前执行引用 ↔ 参考文献双向检查 + 逐句事实核查（最多 3 轮）
5. 著录信息不全的文献标记“待完善”，不自动猜测补全

## v2.2.0 当前实现状态

- `core/ai/` 已提供 Provider/Model 数据域、官方发现、缓存、Credential Manager、Registry、AIService；`core/deepseek.py` 保持旧入口兼容。
- `core/references/` 已提供 ReferenceStore、RIS/BibTeX/CSL JSON、本地文件、CitationMap 和样式入口。
- `sources/zotero.py` 支持官方 Local/Web 增量读取；`sources/notebook.py` 支持本地文件和 Notebook Enterprise 官方写入。
- `gui/model_center.py`、`gui/reference_center.py`、`gui/about_dialog.py` 已接入主窗口；全自动/高级模型选择已使用稳定 ModelRef。
- `core/annotations.py` 与 `gui/pages/annotation_page.py` 已提供独立批注 registry、样式 registry、证据同步、批量管理、正文跳转和导出附录。
- v2.2.0 已通过源码回归、自检、中文资产和远程 Release label 验证；Actions workflow 因 OAuth scope 暂未远程写入。
