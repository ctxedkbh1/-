# 开发日志（docs/ai/CHANGELOG）

> 本文件记录**开发过程**层面的变更（文档体系、工程操作等）。
> **产品功能**版本记录以仓库根目录的 CHANGELOG.md 为准；本文件只记录开发者需要的根因、文件、迁移、测试和发布证据。

## 2026-08-19 — v2.3.0

- 自动质量门：新增 `core/quality_gate.py`，`core/auto_pipeline.py` 统一汇总事实核查状态、引用/参考文献双向关系、结构、字数、资料不足、风险阈值和高优先级质量问题。导出结果新增 `requirements_ok` 与 `requirement_failures`；失败/跳过/未执行统一为“自动判定未达标”。
- 事实核查修复：`factcheck2` 优先于 `factcheck`；跳过状态不再因空 `issues` 被当成通过。`core/quality_report.py`、`gui/auto_mode_page.py` 和离线全自动测试使用同一语义。
- 用户数据：`core/paths.py` 默认目录迁移到 `%LOCALAPPDATA%\\PaperAssistant\\paper_project`；`core/data_migration.py` 复制桌面单文件版、完整版和旧程序目录，配置只补齐缺失字段，冲突保留备份，报告不含 Key 内容。实际迁移扫描到两套旧目录、复制 24 个文件、备份 7 个冲突、合并 148 个配置字段、错误 0 个。
- 更新系统：新增 `core/updater.py`、`gui/update_check.py`、About 检查按钮和帮助菜单入口；GitHub latest Release 请求在线程内执行，校验 SemVer，返回真实 Release URL/资产和 HTTP/网络错误。
- 稳定性：`auto_pipeline.py` 显式导入 `paths`，不可用自定义输出目录回退分支已有本地回归；新增 Claude/Gemini 假 HTTP 请求测试，断言模型 ID、系统提示、消息角色和认证头。
- 发布自动化：新增 `.github/workflows/release.yml`，Tag 触发 Windows 测试、PyInstaller EXE/ZIP 构建和 GitHub Release；`build.bat/build_share.bat` 改用系统 PowerShell 与 ASCII 传输名；补充 `workflow` scope 后已成功推送 workflow。
- 发布回归修复：修复 job 级测试目录错误使用不可用 `runner.temp` 导致 workflow 启动失败的问题；修复 Windows PowerShell 传递中文资产 label 被截断的问题，改为 ASCII JSON Unicode 转义后通过 GitHub API 更新 label。手动 workflow run `32163898669` 的测试、编译、打包和 Release 上传全部成功，两个中文 label 已远程核对。
- 文档接管：新增根目录 `AGENTS.md`、`docs/ai/CHANGE_HISTORY.md`、`DEVELOPMENT_GUIDE.md`，同步 23 阶段、稳定数据、自动质量门、两类日志受众和每次修复必须发版上传的规则。
- 测试与发布：`dev_known_issues_test.py`、`dev_auto_test.py`、AI Center、Reference Center、Annotation、Integrations、Settings、`py_compile`、`main.py --selfcheck`、`--ui-check`、两个 Windows 资产自检和 ZIP 私人数据扫描均通过；main 提交 `b84746b` 已创建 Tag `v2.3.0`，Release 已发布，两个资产状态为 `uploaded`，中文 label 已核对。

## 2026-08-18
- v2.2.0：新增独立批注系统；版本源已从 v2.1.2 升为 v2.2.0，源码与中文 EXE/ZIP 资产已验证，尚未提交、创建 Tag 或发布。
- 数据层：新增 `AnnotationStore`、`AnnotationStyleStore`、`annotations.json` 和 `annotation_styles.json`；内部 `annotation_id` 与显示编号分离。
- 兼容层：旧 `[E001]` 证据无损同步为证据批注；解析兼容 `[E001]`、`[E-001]`、`[E_001]`，证据库仍是事实来源的唯一所有者。
- UI：主侧边栏新增批注管理页，支持搜索、样式/状态筛选、新增编辑、批量删除、按样式重新编号、样式模板管理和批注导出；写作页支持选中文本后创建批注并写回章节。
- 一致性：按样式重新编号后，同步替换各章节中的对应批注标记，避免 registry 与正文断链。
- 写作与质量：正文批注标记可点击；写作检查报告未登记批注；自然化与定向修改同时保护证据引用和普通批注。
- 导出：统一 Document 增加批注说明，DOCX/PDF/PPTX/TXT/Markdown/HTML 全部支持；全自动模式输出批注表 JSON/Markdown，历史记录读取动态输出路径。
- 测试：`tests/dev_annotation_test.py`、参考文献回归、离线全自动测试、批注页离屏刷新、`py_compile` 和 `main.py --selfcheck` 均通过。
- 发布门：`scripts/release.py verify` 已加入批注回归测试；中文单文件 EXE 与完整版 ZIP 内 EXE 的 `--selfcheck` 已通过，GitHub Release 尚未执行。
- 资产命名：GitHub 强制规范化非 ASCII 文件名；从 v2.2.0 起上传脚本使用 ASCII 传输名并设置中文 label `论文助手_vX.Y.Z_单文件版` / `论文助手_vX.Y.Z_完整版`，打包脚本仍在本地 `release_assets` 保留中文文件。

## 2026-08-18
- v2.1.2：OpenAlex 429 限流修复。
- 根因：OpenAlex 请求虽有固定 2 秒重试，但没有区分 HTTP 429、没有读取 `Retry-After`，连续关键词或重复点击时容易在短时间内再次触发限流。
- 修复：增加全局请求最小间隔；429 使用响应头或指数退避等待；连续限流最终转换为可操作的 `SourceError`；支持 `OPENALEX_MAILTO` 注入礼貌访问参数；User-Agent 标识当前应用版本。
- 测试：新增 `tests/dev_openalex_test.py`，覆盖两次 429 后恢复、连续 429 最终失败、Retry-After、mailto 和 User-Agent。
- 安全流程：检索结束后若证据库仍为 0 条，流水线抛出 `PipelineError` 并停止，不再继续写作和导出空资料论文；新增离线空资料安全停止断言。
- 客户日志只保留检索体验和用户可感知行为，内部根因与测试证据保留在本文件及 `docs/ai/CHANGELOG.md`。
- 发布元数据修正：v2.1.1/v2.1.2 Release 标题统一为 `论文助手 vX.Y.Z`，避免回退为内部英文项目名。

## 2026-08-18
- v2.1.1：将上一轮模型中心修复和本轮启用交互、凭据启动判断、Emoji UI 一并纳入正式版本。
- 根因：桌面单文件 EXE 未随 v2.1.0 工作区修复重新构建；启动判断只检查旧 `models[*].api_key`，没有通过 AI Provider/Windows Credential Manager 解析实际凭据。
- 凭据修复：`resolve_api_key()` 现在按环境变量、Provider Credential Manager 引用、旧顶层迁移引用、旧配置字段顺序解析；不记录或输出 Key 内容。
- UI 修复：Provider 和 Model `QListWidgetItem` 增加可持久化勾选状态；模型停用后从自动路由、任务选项和最新模型候选中排除。
- UI 改进：模型中心新增 `🔌`、`🟢`、`⚪`、`🧠`、`⭐`、`🔄`、`🧪`、`📚`、`🗑️` 等轻量 Emoji 标识，文字含义仍保留。
- 构建修复：`build.bat` 同时构建完整版 onedir 和桌面固定名称单文件 EXE；`build_share.bat` 保留完整运行环境 ZIP。
- 测试证据：AI Center、Reference Center、Integrations、Settings、Release Automation、Visual、`main.py --selfcheck`、`main.py --ui-check` 全部通过；真实 DeepSeek `/models` 返回模型列表。
- 配置证据：桌面完整版用户数据文件数量和手动模型数量保持不变；分享 ZIP 不包含 `paper_project`、配置、参考文献或 API Key。
- 发布注意：GitHub Actions workflow 仍受 OAuth `workflow` scope 限制，本版本使用已验证的本地打包资产手动上传 GitHub Release；后续获得 scope 后再同步 workflow。

## 2026-08-18
- 完成动态 AI Provider/Model/Discovery/Registry/Cache/AIService 首轮实现。
- 完成 ReferenceStore、CitationMap、RIS/BibTeX/CSL JSON、本地文件和 Zotero/Notebook 接入层。
- 完成模型中心、参考文献中心、About、统一 QSS 和 7 档分辨率离屏检查。
- 完成 AI/引用/集成/设置/发布门测试；workflow 文件仍受 GitHub OAuth workflow scope 限制，待权限恢复后同步。
- v2.1.0 已创建 Tag、推送 main 并发布 EXE + ZIP Release；workflow 仍待权限恢复后写入远程。
- 修复模型中心：DeepSeek 模型列表 URL 归一到 `/models`、同名预设导入改为二次确认、模型启用/停用与删除可持久化。
- 新增本地预设库隐藏/恢复入口；API Key 保存增加 Windows Credential Manager 写入校验和错误提示。

## 2026-08-17
- 发布 v2.0.1：修复 build.bat/build_share.bat 的 LF 行尾与 cmd.exe UTF-8 说明行解析问题
- 新增 .gitattributes，强制 `*.bat` 使用 CRLF
- 完整版改为 PyInstaller onedir 并将整个目录复制到桌面；分享版继续生成 ZIP，不再只提供单文件 EXE
- GitHub v2.0.1 Release 统一为 EXE + ZIP 两个资产；客户 Release Notes 仅保留“修复”章节
- 建立 RELEASE_PROCESS.md：客户日志与内部日志分层、桌面固定名称覆盖、旧源码集中归档
- 桌面固定为 `论文智能研究与写作助手_完整版`、`论文智能研究与写作助手.exe`、`论文助手.zip`
- 动态 AI 模型中心仅完成只读审计与方案设计，尚未修改业务代码

## 2026-08-16
- 建立 AI 项目知识库 docs/ai/（PROJECT_CONTEXT / ARCHITECTURE / FEATURES / CURRENT_STATUS / DEVELOPMENT_RULES / CHANGELOG / TODO / KNOWN_ISSUES / FILE_MAP / AI_HANDOFF）
- 项目封存：暂停新功能开发，建立基线（git tag v2.0.0 → 最新提交，本地 backup 快照）
- 完成 GitHub 公开发布：仓库 paper-workbench、Release v2.0.0（EXE+ZIP）、README/CHANGELOG/LICENSE
- 教训记录：Windows 命令行传中文曾损坏仓库/附件名称；中文请求体需使用 UTF-8 文件或 API 工具，Release 资产可使用中文并需上传后核对
