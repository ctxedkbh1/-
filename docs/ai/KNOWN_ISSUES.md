# 已知问题（KNOWN_ISSUES）

> 状态只允许如实填写：Open / 已解决（附解决方式与日期）。禁止假装修复。

## 产品层面

### 1. 旧版单文件 EXE 首次启动慢（10~30 秒）
- 问题：v2.0.0 及更早版本的单文件 EXE 启动前需要解压运行环境
- 出现位置：历史 PyInstaller onefile 产物
- 原因：PyInstaller 单文件模式特性
- 解决方案：v2.0.1 起默认发布 onedir 完整版目录与分享 ZIP
- 状态：已解决（2026-08-17）

### 2. 政府网页检索可能失败
- 问题：部分任务中该步骤检索无结果或被跳过
- 出现位置：sources/government.py、core/auto_pipeline.py（on_fail=skip）
- 原因：目标站点反爬、网络波动（尽力而为设计）
- 临时解决方案：程序自动跳过并在日志提示；用户手动补充资料后继续
- 状态：Open

### 3. CNKI 只能手动录入/文件导入
- 问题：无法在软件内自动登录 CNKI 检索
- 出现位置：sources/cnki.py
- 原因：设计限制——不绕过登录/验证码/付费墙
- 临时解决方案：使用 RIS/BibTeX 导入或手动录入
- 状态：Open（设计决定，不会"修复"）

### 4. 长论文全自动模式耗时长
- 问题：全自动任务可能运行较久
- 出现位置：core/auto_pipeline.py（21 步串行 + 多轮 AI 调用）
- 原因：流程步数与 AI 接口响应时间
- 临时解决方案：使用断点恢复分次完成；网络高峰时改用较快模型
- 状态：Open

## 平台/工程层面（经验记录，已解决）

### 5. Windows 命令行编码曾损坏 GitHub 中文名称
- 问题：早期通过命令行传中文时，仓库名曾变成 "-"，附件名曾变成 "_v2.0.0.exe"
- 原因：Windows 控制台参数编码不一致，不是 GitHub Release 资产本身禁止中文
- 解决方案：仓库名保持 `paper-workbench`；从 v2.2.0 起使用 ASCII 传输名并通过 GitHub API 设置中文 label `论文助手_vX.Y.Z_单文件版` / `论文助手_vX.Y.Z_完整版`，上传后核对远程显示名
- 状态：已解决（2026-08-18）

### 6. Windows PowerShell 命令行传中文给 git/gh 会被编码损坏
- 问题：中文参数乱码导致仓库创建名错误等
- 原因：控制台代码页与程序参数编码不一致
- 解决方案：中文提交信息用 `git commit -F 文件`；GitHub API 中文请求体用 UTF-8 文件 + `gh api --input 文件`
- 状态：已解决（2026-08-16，写入 DEVELOPMENT_RULES.md 长期遵守）

## 敏感信息防护（已验证，非问题）
- 扫描确认：仓库内无真实 API Key、无 .env、无 *.pem/*.key
- main.py 第 151 行的 `sk-abcdefgh123456` 是自测用假 Key，非真实凭据
- paper_project/config.json（含用户真实 Key）位于仓库外，已被 .gitignore 忽略
