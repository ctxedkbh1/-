# 当前状态（CURRENT_STATUS）

> 本文件是项目状态的**单一事实来源**。每次改动代码后必须同步更新本文件。

## 当前版本
v2.3.0（2026-08-19，已正式发布）

## 当前开发阶段
v2.3.0 已完成自动质量门、无损统一数据目录与迁移、GitHub Release 更新检查、导出回退修复、Provider 请求回归测试和 Windows Release workflow；客户/开发者日志已分离更新，已完成正式发布。

## 最近完成
1. 高级模式工作台（六阶段流程化指导）——v2.0.0 核心功能
2. AI 模型中心、动态发现、参考文献/Zotero/Notebook、独立 AnnotationStore——v2.1.0/v2.2.0
3. 全自动 23 阶段流水线、统一自动质量门：自动判定“可以导出”或“自动判定未达标”
4. 稳定数据目录 `%LOCALAPPDATA%\PaperAssistant\paper_project` 和旧版无损复制/冲突备份
5. GitHub Release 异步更新检查、真实错误展示和下载页入口
6. Claude/Gemini 请求回归测试、导出回退修复、Windows Tag Release workflow

## 当前正在处理
无 v2.3.0 发布遗留动作。后续修复、功能、UI、依赖或安全更新必须按本项目规则递增版本、同步两类日志、测试、打包并发布。

## 下一步
等待下一项用户明确需求；任何新变更都必须先阅读本文件、架构和相关源码，再按发布规则递增版本并同步两类日志。

## 当前已知 Bug
未发现新的核心崩溃。政府检索、CNKI 登录和长论文耗时仍是外部环境/设计限制，见 KNOWN_ISSUES.md。

## 当前不能修改的模块
- **防编造机制相关**（core/evidence.py、core/writer.py、core/naturalizer.py、core/fact_checker.py 的约束逻辑）：项目最高优先级，任何改动不得削弱
- **core/paths.py**：APP_NAME / VERSION / RELEASE_DATE 是版本号唯一来源，修改版本号只能改这里并同步首页显示
- 版本戳约定：改动文件末尾追加 `# 版本: vX.Y.Z (日期) 更新: 内容`

## 最后一次正常运行状态
- 桌面仅保留固定名称的完整版目录、单文件 EXE 和分享 ZIP；旧版本源码归档到 backup/releases
- 2026-08-18 使用 CRLF 批处理重新打包 v2.1.2；源码和两个 EXE 的 `--selfcheck` 均通过
- 2026-08-18 v2.3.0 通过已知问题离线回归、Provider 假 HTTP、数据迁移、全自动、AI 中心、参考文献、批注、集成、设置、语法编译、`--selfcheck` 和 `--ui-check`
- 完整版目录 EXE、桌面单文件 EXE 与分享 ZIP 均已构建；ZIP 结构和私人文件扫描通过
- GitHub main 分支已推送至提交 `bd2be1b`；Tag `v2.3.0` 指向发布提交 `b84746b`；Release `v2.3.0` 已创建并包含两个已上传资产，中文 label 已核对；workflow run `32163898669` 已成功完成 Windows 测试、打包和上传

## Baseline 信息
- 日期：2026-08-19
- Commit：`29bcaa5`（发布后客户日志去重确认）
- Branch：`main`
- Tag/Release：远程最新为 `v2.3.0`；Release URL：`https://github.com/ctxedkbh1/paper-workbench/releases/tag/v2.3.0`
