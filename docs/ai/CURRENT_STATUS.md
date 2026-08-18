# 当前状态（CURRENT_STATUS）

> 本文件是项目状态的**单一事实来源**。每次改动代码后必须同步更新本文件。

## 当前版本
v2.2.0（2026-08-18，源码已更新，尚未发布）

## 当前开发阶段
v2.2.0 已完成批注数据层、样式模板、证据同步、批量管理、正文跳转、安全改写保护和多格式导出接入。源码回归测试及中文 EXE/ZIP 资产验证已通过，尚未提交、创建 Tag 或发布 GitHub Release；最新已发布版本仍为 v2.1.2。

## 最近完成
1. 高级模式工作台（六阶段流程化指导）——v2.0.0 核心功能
2. GitHub 公开发布：仓库 paper-workbench、Release v2.0.0（EXE + ZIP 两个安装包）、README/CHANGELOG/LICENSE 文档体系
3. 建立 AI 项目知识库 docs/ai/（本目录）
4. 修复 Windows 批处理、用户数据迁移和 Release 资产格式；桌面固定名称覆盖，GitHub 提供版本化 EXE + ZIP
5. 新增独立 AnnotationStore 和批注管理页，兼容旧 E-ID 并输出批注附录/批注表

## 当前正在处理
v2.2.0 功能代码、版本文档和发布资产已完成；待完成 Git 提交/Tag 和 GitHub Release。远程 workflow 权限仍未恢复。

## 下一步
下一步：用户明确要求发布后完成 v2.2.0 打包与发布；用户重新授权 GitHub OAuth `workflow` scope 后，将本地 `.github/workflows/release.yml` 写入远程。后续每个 bug/功能按发布规则递增版本。

## 当前已知 Bug
无未修复的致命或功能性 Bug。已知限制见 KNOWN_ISSUES.md（均属设计限制或外部环境问题）。

## 当前不能修改的模块
- **防编造机制相关**（core/evidence.py、core/writer.py、core/naturalizer.py、core/fact_checker.py 的约束逻辑）：项目最高优先级，任何改动不得削弱
- **core/paths.py**：APP_NAME / VERSION / RELEASE_DATE 是版本号唯一来源，修改版本号只能改这里并同步首页显示
- 版本戳约定：改动文件末尾追加 `# 版本: vX.Y.Z (日期) 更新: 内容`

## 最后一次正常运行状态
- 桌面仅保留固定名称的完整版目录、单文件 EXE 和分享 ZIP；旧版本源码归档到 backup/releases
- 2026-08-18 使用 CRLF 批处理重新打包 v2.1.2；源码和两个 EXE 的 `--selfcheck` 均通过
- 2026-08-18 v2.2.0 源码通过批注回归、参考文献回归、离线全自动测试、GUI 刷新检查、语法编译和 `main.py --selfcheck`；中文单文件 EXE 与 ZIP 内完整版 `--selfcheck` 均返回 0
- 完整版目录 EXE、桌面单文件 EXE 与分享 ZIP 均已构建；ZIP 结构和私人文件扫描通过
- GitHub main 分支与 v2.1.2 Release 已验证正常；v2.2.0 尚未提交或发布

## Baseline 信息
- 日期：2026-08-17
- Commit：v2.0.1 标签指向的提交（见 git log）
- Tag：v2.0.1
- 本地备份：`Default Project\backup\project-baseline-2026-08-17-v2.0.1\`
