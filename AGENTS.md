# PaperAssistant 长期维护规则

## 项目身份

这是已持续开发的 Windows 桌面论文工具，不是新项目。GitHub 正式仓库是
`https://github.com/ctxedkbh1/paper-workbench.git`，默认分支 `main`。必须继承既有
OpenCode 功能、数据格式、兼容层和 Git 历史，禁止重写技术栈、删除功能或重置历史。

## 技术栈与入口

- Python 3.10+、PySide6、requests、python-docx、python-pptx、ReportLab、PyInstaller、keyring。
- `main.py` 是 GUI 入口；`python main.py --selfcheck` 是无界面发布自检；`--ui-check` 是离屏布局检查。
- 核心分层是 `gui/` → `core/` → `core/llm.py` Provider → 外部 AI/检索 API；存储是本地 JSON + Markdown，无数据库。
- 全自动模式在 `core/auto_pipeline.py`，源码有 23 个阶段；普通模式 8 步，高级模式 6 阶段。

## 不能破坏的业务约束

- 防编造最高优先级：AI 只能引用证据库；资料不足必须明确标注；自然化修改保护事实、数字、引用和批注；引用与参考文献必须双向检查。
- 唯一正式批注系统是 `core/annotations.py` 的 `AnnotationStore`，不得另建第二套 E-ID/批注系统。
- Provider 必须真正使用用户选择的 Model ID；测试必须检查实际 HTTP 请求中的 `model` 或供应商对应模型字段。
- 全自动结果必须由统一质量门自动判定起始要求是否满足：通过为“可以导出”，失败、跳过或不可判定为“自动判定未达标”，不得误报为通过，也不把人工审查作为成功条件。
- 政府站点反爬、CNKI 登录/验证码/付费墙等外部限制不得违规绕过；失败要显示真实原因。

## 数据与安全

- 版本唯一来源是 `core/paths.py` 的 `VERSION` / `RELEASE_DATE`。
- 默认用户数据目录是 `%LOCALAPPDATA%\PaperAssistant\paper_project`；`PAPER_PROJECT_DIR` 可覆盖。
- 首次启动会无损兼容旧桌面单文件版、完整版和程序目录的数据；冲突写入 `migration_backups`，源目录不删除。
- `config.json`、API Key、Zotero/Notebook Token、用户论文和历史绝不进入 Git、日志、截图、Release 资产或测试输出。

## 版本、日志与发布

- 每个 Bug 修复、功能、UI 改进、依赖或安全变更都算一次正式版本更新；Bug 默认 patch，功能默认 minor，破坏性变更 major，遵循现有 SemVer。
- 每次更新必须同步 `core/paths.py`、README、根目录客户 `CHANGELOG.md`、`RELEASE_NOTES.md`、`docs/ai/CURRENT_STATUS.md`、`docs/ai/CHANGE_HISTORY.md` 及必要架构文档，并在改动文件末尾追加版本戳。
- 客户日志和开发者日志严格分离。根目录 `CHANGELOG.md`、`RELEASE_NOTES.md`、GitHub Release 只写用户可见行为、使用方式、兼容/限制和完整修复说明，不写内部类名、密钥或测试噪音；`docs/ai/CHANGELOG.md`、`CHANGE_HISTORY.md`、CURRENT_STATUS 记录根因、文件、迁移、测试、风险和未完成项。
- 完成并通过发布门后执行 `git status`、`git diff`、敏感信息扫描、`git add/commit/push`，再创建 Tag 和 GitHub Release；禁止 `push --force`。无权限时如实报告，不宣称已发布。
- 发布资产必须是版本化单文件 EXE 和完整版 ZIP；GitHub 传输名用 ASCII，页面 label 使用 `论文助手_vX.Y.Z_单文件版` / `论文助手_vX.Y.Z_完整版`。

## 每次任务流程

1. 先读本文件、`docs/ai/CURRENT_STATUS.md`、`ARCHITECTURE.md`、`CHANGE_HISTORY.md`、`FILE_MAP.md`、`DEVELOPMENT_GUIDE.md`、README 和 Git 状态。
2. 搜索真实源码和调用链，说明影响范围，再编辑；旧代码只有确认无调用且删除安全时才可清理。
3. 修改后运行相关测试、`py_compile`、`main.py --selfcheck`、`--ui-check`，并审查 diff/status。
4. 同步两类日志和 AI 长期文档；不要把未验证内容写成已完成。

## 常用命令

```powershell
python -m compileall -q config core gui sources main.py
python scripts/release.py verify
python main.py --selfcheck
python main.py --ui-check
```

## 关键文件

`core/auto_pipeline.py`（23 阶段与自动质量门）、`core/quality_gate.py`（统一判定）、
`core/paths.py`（版本与数据目录）、`core/data_migration.py`（无损迁移）、`core/llm.py`（Provider）、
`core/annotations.py`（正式批注）、`core/exporter.py`（导出）、`core/updater.py` 与
`gui/about_dialog.py`（GitHub 更新检查）、`scripts/release.py`（发布门）。完整地图见 `docs/ai/FILE_MAP.md`。

# 版本: v2.3.0 (2026-08-19) 更新: Codex 长期维护规则
