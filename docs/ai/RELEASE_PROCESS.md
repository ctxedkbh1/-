# 发布与更新日志规则（RELEASE_PROCESS）

## 1. 两类日志，禁止混写

### 客户可见（必须详尽但不暴露内部实现）
- GitHub Release Notes
- 仓库根目录 `CHANGELOG.md`

只写客户能够理解和感知的内容：新增功能、体验改进、问题修复、兼容迁移、使用入口、失败提示、必要的已知限制和升级影响。说明应尽可能完整，让客户能知道升级前后行为差异和如何使用。
禁止写内部文件路径、类名、实现机制、命令、测试过程、开发计划、AI 审计状态。

### 用户与开发 AI 可见
- `docs/ai/CHANGELOG.md`
- `docs/ai/CURRENT_STATUS.md`

记录具体修改文件、技术机制、配置迁移、测试证据、未完成工作和风险。仍然禁止记录 API Key 或其他敏感值。

## 2. GitHub Release 格式

每个正式版本至少提供两个版本化资产：
- 本地与传输文件：`paperassistant-vX.Y.Z-single.exe`、`paperassistant-vX.Y.Z-full.zip`（ASCII 名避免 Windows 编码损坏）
- GitHub 中文显示名（label）：`论文助手_vX.Y.Z_单文件版`、`论文助手_vX.Y.Z_完整版`

Release Notes 必须按客户语言编写。补丁版本默认只保留 `## 修复` 章节。
Release 标题统一使用客户品牌 `论文助手 vX.Y.Z`；仓库名保持 `paper-workbench`。GitHub 会强制规范化非 ASCII 文件名，因此从 v2.2.0 起由上传 API 设置稳定的中文 label，页面显示名统一为上述中文名称。

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

## 7. 每次更新的强制规则

- 任何 Bug 修复、新功能、UI 改进、依赖升级或安全修复都视为一次更新，不允许以“未发布的小改动”长期留在桌面或 main 工作区；完成后必须自动走测试、提交、推送、Tag 和 GitHub Release 上传。
- Bug 修复默认递增 patch 版本；新功能默认递增 minor 版本；破坏性变更递增 major 版本。
- 完成功能或修复的同一轮工作中必须先更新版本元数据和日志，再向用户报告完成；不能把版本号补录留到下一轮。
- 每次更新必须同步 `core/paths.py`、README、根目录客户 CHANGELOG、`RELEASE_NOTES.md`、`docs/ai` 内部日志、版本化 EXE/ZIP、Git Commit、Git Tag 和 GitHub Release。
- 发布说明应尽可能详细：客户日志描述用户能看到的行为变化和使用方式；内部日志补充根因、迁移、修改范围、测试证据和残余风险。
- GitHub Release 创建或上传失败时不得宣称已发布；必须保留阻塞原因，并在权限恢复后补传同一版本资产。远程动作只有收到 GitHub 成功响应并核对 Tag、Release 和资产 label 后才算完成。
