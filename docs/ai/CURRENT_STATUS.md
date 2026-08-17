# 当前状态（CURRENT_STATUS）

> 本文件是项目状态的**单一事实来源**。每次改动代码后必须同步更新本文件。

## 当前版本
v2.0.1（2026-08-17，Windows 打包脚本修复）

## 当前开发阶段
已发布 v2.0.1（公开 GitHub 仓库 + 完整版 ZIP Release），维护模式。动态 AI 模型中心仍处于只读审计与方案设计阶段。

## 最近完成
1. 高级模式工作台（六阶段流程化指导）——v2.0.0 核心功能
2. GitHub 公开发布：仓库 paper-workbench、Release v2.0.0（EXE + ZIP 两个安装包）、README/CHANGELOG/LICENSE 文档体系
3. 建立 AI 项目知识库 docs/ai/（本目录）
4. 修复 Windows 批处理 LF 行尾与 UTF-8 连续中文 echo 解析问题；v2.0.1 改为桌面完整版目录 + 分享 ZIP

## 当前正在处理
动态 AI 模型中心处于只读审计与方案设计阶段；尚未修改模型业务代码。

## 下一步
等待用户确认动态 AI 模型中心升级方案后再进入实现；开始前必须建立新 Baseline。

## 当前已知 Bug
无未修复的致命或功能性 Bug。已知限制见 KNOWN_ISSUES.md（均属设计限制或外部环境问题）。

## 当前不能修改的模块
- **防编造机制相关**（core/evidence.py、core/writer.py、core/naturalizer.py、core/fact_checker.py 的约束逻辑）：项目最高优先级，任何改动不得削弱
- **core/paths.py**：APP_NAME / VERSION / RELEASE_DATE 是版本号唯一来源，修改版本号只能改这里并同步首页显示
- 版本戳约定：改动文件末尾追加 `# 版本: vX.Y.Z (日期) 更新: 内容`

## 最后一次正常运行状态
- v2.0.1 完整版目录与分享 ZIP 已部署在桌面（不再单独提供单文件 EXE）
- 2026-08-17 使用 CRLF 批处理重新打包；python main.py --selfcheck 通过
- 完整版目录 EXE 与分享版目录 EXE 均已实际启动并显示主窗口；ZIP 结构验证通过
- GitHub main 分支与 Release 均已验证正常

## Baseline 信息
- 日期：2026-08-17
- Commit：v2.0.1 标签指向的提交（见 git log）
- Tag：v2.0.1
- 本地备份：`Default Project\backup\project-baseline-2026-08-17-v2.0.1\`
