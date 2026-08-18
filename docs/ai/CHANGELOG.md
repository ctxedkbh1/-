# 开发日志（docs/ai/CHANGELOG）

> 本文件记录**开发过程**层面的变更（文档体系、工程操作等）。
> **产品功能**版本记录以仓库根目录的 CHANGELOG.md 为准（v2.1.2 / v2.1.1 / v2.1.0 / v2.0.1 / v2.0.0 / v1.6.0 / v1.5.0）。

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
- 教训记录：GitHub 不支持中文仓库名/附件名；Windows 命令行传中文需用文件方式
