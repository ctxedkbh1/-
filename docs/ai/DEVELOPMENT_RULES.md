# 开发规则（DEVELOPMENT_RULES）

> 所有 AI（包括当前和未来的任何模型）修改本项目前，必须遵守本文件。

## 总原则
【源码 > 项目文档 > AI 记忆 > AI 猜测】。源码是唯一事实依据。

## 必须遵守的规则

1. **修改前先读源码**：先读相关文件，再动手
2. **禁止凭记忆修改**：不读源码就改代码 = 违规
3. **禁止猜测文件结构**：文件是否存在、函数叫什么，必须用工具确认
4. **禁止删除现有功能**：任何重构不得移除已实现功能
5. **禁止随意重构**：没有用户明确要求，不重写已有代码
6. **修改前说明影响范围**：列出准备修改的文件、原因、影响，经用户确认后再改
7. **修改后必须验证**：语法检查（python -m py_compile）+ python main.py --selfcheck + 相关 tests/ 测试；无法验证时必须明说"该功能尚未实际运行验证"，禁止说"应该没问题"
8. **同步文档**：改代码后同步更新根目录 CHANGELOG.md 和 docs/ai/CURRENT_STATUS.md，必要时更新 ARCHITECTURE.md / FEATURES.md / FILE_MAP.md
9. **不确定就问**：任何不确定内容必须询问用户，禁止编造
10. **禁止 AI 幻觉**：不知道就说不知道；禁止"我记得""应该是""可能是"然后直接改代码

## 本项目特定规则

- **防编造机制不可削弱**（详见 ARCHITECTURE.md）：AI 只能引用证据库、自然化修改保护事实/引用、双向引用检查——这些是最高优先级
- **版本号唯一来源**：core/paths.py 的 VERSION / RELEASE_DATE；发版时同步更新 README（版本行）、CHANGELOG.md、Git Tag、GitHub Release
- **每次更新都要发版**：任何 Bug 修复、新功能、UI 改进、依赖升级或安全修复都必须递增版本号、更新详细日志、重新打包并上传 GitHub Release；不得把修复留在未发布的桌面产物中
- **版本戳约定**：每次改动文件末尾追加 `# 版本: vX.Y.Z (日期) 更新: 内容`
- **Git 提交规范**：feat: / fix: / docs: / refactor: / style: / chore:
- **中文命令行坑（重要教训）**：Windows PowerShell 向 git/gh 传中文参数会被编码损坏（曾导致 GitHub 仓库名变成 "-"）。凡需要中文的提交信息、API 请求体，一律写进 UTF-8 文件再用 `git commit -F 文件`、`gh api --input 文件` 传递
- **GitHub 平台限制**：仓库名、Release 附件名不支持中文（会自动剥除）；用英文名 + 中文描述/标签（见 KNOWN_ISSUES.md）
- **敏感信息**：paper_project/config.json 含 API Key，已被 .gitignore 忽略；任何提交前自查不要带入 .env、密钥、个人数据
- **禁止 push --force**（分支）；移动标签需用户明确同意
- **打包**：发版用 build.bat（需 Python 3.10+ 环境），产物复制到桌面
- **日志受众必须分离**：根目录 CHANGELOG.md 与 GitHub Release 给客户看，只写用户可感知的新增/改进/修复；docs/ai/CHANGELOG.md 与 CURRENT_STATUS.md 给用户和开发 AI 看，记录文件、机制、迁移、测试和未完成事项
- **桌面不留多版本**：桌面只保留固定名称的完整版目录、EXE、ZIP，每次更新直接覆盖；带版本号的下载文件只存在 GitHub Release
- **旧源码归档**：只保存到 `Default Project\backup\releases\vX.Y.Z\`，不得堆在桌面
- **发布流程**：每个正式版本的 GitHub Release 至少提供版本化 EXE 与 ZIP 两个资产；详细清单见 RELEASE_PROCESS.md

## 修改前检查协议（用户要求）
1. 读 CURRENT_STATUS.md → ARCHITECTURE.md → FEATURES.md → 相关源码
2. 检查是否已有类似功能
3. 确定要修改的文件
4. 向用户报告：准备修改（文件清单）→ 原因 → 影响 → 等待确认

## 修改后检查协议（用户要求）
1. 语法检查 2. 依赖检查 3. 相关模块检查 4. 运行测试 5. 无法测试时如实说明 6. 更新文档
