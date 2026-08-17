# 开发日志（docs/ai/CHANGELOG）

> 本文件记录**开发过程**层面的变更（文档体系、工程操作等）。
> **产品功能**版本记录以仓库根目录的 CHANGELOG.md 为准（v2.0.1 / v2.0.0 / v1.6.0 / v1.5.0）。

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
