# 当前状态（CURRENT_STATUS）

> 本文件是项目状态的**单一事实来源**。每次改动代码后必须同步更新本文件。

## 当前版本
v2.0.0（2026-08-16，高级模式工作台）

## 当前开发阶段
已发布（公开 GitHub 仓库 + Release v2.0.0），维护模式。**当前处于项目封存状态，无新功能开发。**

## 最近完成
1. 高级模式工作台（六阶段流程化指导）——v2.0.0 核心功能
2. GitHub 公开发布：仓库 paper-assistant、Release v2.0.0（EXE + ZIP 两个安装包）、README/CHANGELOG/LICENSE 文档体系
3. 建立 AI 项目知识库 docs/ai/（本目录）

## 当前正在处理
无（封存状态）。新对话必须先读 docs/ai/AI_HANDOFF.md。

## 下一步
见 TODO.md。当前无 P0/P1 紧急任务。

## 当前已知 Bug
无未修复的致命或功能性 Bug。已知限制见 KNOWN_ISSUES.md（均属设计限制或外部环境问题）。

## 当前不能修改的模块
- **防编造机制相关**（core/evidence.py、core/writer.py、core/naturalizer.py、core/fact_checker.py 的约束逻辑）：项目最高优先级，任何改动不得削弱
- **core/paths.py**：APP_NAME / VERSION / RELEASE_DATE 是版本号唯一来源，修改版本号只能改这里并同步首页显示
- 版本戳约定：改动文件末尾追加 `# 版本: vX.Y.Z (日期) 更新: 内容`

## 最后一次正常运行状态
- v2.0.0 EXE 已打包成功并部署在桌面（论文智能研究与写作助手_v2.0.0.exe、论文助手_v2.0.0.zip）
- python main.py --selfcheck 通过（打包前自检）
- GitHub main 分支与 Release 均已验证正常

## Baseline 信息
- 日期：2026-08-16
- Commit：9dea0c5（docs: 修正 README 下载文件名与 Release 附件一致）→ 最新基线提交见 git log
- Tag：v2.0.0
- 本地备份：`Default Project\backup\project-baseline-2026-08-16\`
