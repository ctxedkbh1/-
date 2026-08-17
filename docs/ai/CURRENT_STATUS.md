# 当前状态（CURRENT_STATUS）

> 本文件是项目状态的**单一事实来源**。每次改动代码后必须同步更新本文件。

## 当前版本
v2.1.1（2026-08-18）

## 当前开发阶段
v2.1.1 已完成本地发布门和桌面构建，公开 GitHub Tag/Release 正在上传；GitHub Actions workflow 仍因 OAuth scope 尚未写入远程。

## 最近完成
1. 高级模式工作台（六阶段流程化指导）——v2.0.0 核心功能
2. GitHub 公开发布：仓库 paper-workbench、Release v2.0.0（EXE + ZIP 两个安装包）、README/CHANGELOG/LICENSE 文档体系
3. 建立 AI 项目知识库 docs/ai/（本目录）
4. 修复 Windows 批处理、用户数据迁移和 Release 资产格式；桌面固定名称覆盖，GitHub 提供版本化 EXE + ZIP

## 当前正在处理
AI 模型中心核心、参考文献核心、官方集成层、启用复选框、凭据判断、Emoji UI、发布脚本和最终打包均已测试；待完成项是上传 v2.1.1 Release 和远程 workflow 权限。

## 下一步
下一步：完成 v2.1.1 GitHub Release 上传；用户重新授权 GitHub OAuth `workflow` scope 后，再将本地 `.github/workflows/release.yml` 写入远程。

## 当前已知 Bug
无未修复的致命或功能性 Bug。已知限制见 KNOWN_ISSUES.md（均属设计限制或外部环境问题）。

## 当前不能修改的模块
- **防编造机制相关**（core/evidence.py、core/writer.py、core/naturalizer.py、core/fact_checker.py 的约束逻辑）：项目最高优先级，任何改动不得削弱
- **core/paths.py**：APP_NAME / VERSION / RELEASE_DATE 是版本号唯一来源，修改版本号只能改这里并同步首页显示
- 版本戳约定：改动文件末尾追加 `# 版本: vX.Y.Z (日期) 更新: 内容`

## 最后一次正常运行状态
- 桌面仅保留固定名称的完整版目录、单文件 EXE 和分享 ZIP；旧版本源码归档到 backup/releases
- 2026-08-18 使用 CRLF 批处理重新打包 v2.1.1；源码和两个 EXE 的 `--selfcheck` 均通过
- 完整版目录 EXE、桌面单文件 EXE 与分享 ZIP 均已构建；ZIP 结构和私人文件扫描通过
- GitHub main 分支与 Release 均已验证正常

## Baseline 信息
- 日期：2026-08-17
- Commit：v2.0.1 标签指向的提交（见 git log）
- Tag：v2.0.1
- 本地备份：`Default Project\backup\project-baseline-2026-08-17-v2.0.1\`
