# 发布与更新日志规则（RELEASE_PROCESS）

## 1. 两类日志，禁止混写

### 客户可见
- GitHub Release Notes
- 仓库根目录 `CHANGELOG.md`

只写客户能够理解和感知的内容：新增功能、体验改进、问题修复、必要的已知限制。
禁止写内部文件路径、类名、实现机制、命令、测试过程、开发计划、AI 审计状态。

### 用户与开发 AI 可见
- `docs/ai/CHANGELOG.md`
- `docs/ai/CURRENT_STATUS.md`

记录具体修改文件、技术机制、配置迁移、测试证据、未完成工作和风险。仍然禁止记录 API Key 或其他敏感值。

## 2. GitHub Release 格式

每个正式版本至少提供两个版本化资产：
- `PaperAssistant-vX.Y.Z-windows-x64.exe`
- `PaperAssistant-vX.Y.Z-windows-x64.zip`

Release Notes 必须按客户语言编写。补丁版本默认只保留 `## 修复` 章节。

## 3. 桌面交付格式

桌面只保留以下固定名称，每次更新直接覆盖：
- `论文智能研究与写作助手_完整版\`
- `论文智能研究与写作助手.exe`
- `论文助手.zip`

不得在桌面累计带版本号的 EXE、ZIP、完整版目录或源码目录。

## 4. 用户数据

- 完整版更新必须合并并保留已有 `paper_project`。
- 分享 ZIP 和 GitHub 资产不得包含用户 `paper_project`、API Key、论文或历史记录。
- 日志只允许记录是否迁移成功，不得输出 Key 内容。

## 5. 旧源码归档

旧源码只保存在：
`C:\Users\Administrator\Documents\Default Project\backup\releases\vX.Y.Z\`

每个版本最多保留一个源码 ZIP，不在桌面留副本。

## 6. 发布前检查

1. 版本号、README、客户 CHANGELOG 一致
2. 内部 CHANGELOG 与 CURRENT_STATUS 已更新
3. EXE 与 ZIP 均实际运行/解压验证
4. ZIP 无私人数据
5. 桌面固定名称已覆盖，旧版本重复文件已清理
6. Git 工作区干净，Tag 与 Release 一致
