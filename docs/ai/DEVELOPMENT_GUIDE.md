# Codex 开发指南

## 开始任务

先读取 `AGENTS.md`、`CURRENT_STATUS.md`、`ARCHITECTURE.md`、`CHANGE_HISTORY.md`、`FILE_MAP.md`、`KNOWN_ISSUES.md`、README 和相关源码；然后执行 `git status --short --branch`、`git remote -v`、`git log -5 --oneline --decorate`。不凭空猜文件、API 或旧实现。

## 影响范围

新增模型要同时检查 Provider、Registry、ModelRef、AIService、任务选择、普通/全自动/高级模式和实际请求；新增论文流程要检查证据、引用、事实核查、质量门、导出、历史和断点；更新机制要检查版本源、打包、workflow、Release 资产和数据迁移。

## 测试门

- 修改核心 Python：`python -m compileall -q config core gui sources main.py`。
- 运行与变更相关的 `tests/dev_*.py`，再运行 `python scripts/release.py verify`。
- GUI 变更至少运行 `python main.py --ui-check`；发布前运行 `python main.py --selfcheck`。
- Provider 测试必须使用本地假 HTTP 服务，断言真实模型字段、请求格式、错误转换和 Key 不出日志；禁止调用真实付费 API。
- 测试失败、网络失败或权限失败都要如实记录，不得用放宽断言掩盖问题。

## 文档与发布

客户文档要详尽描述用户可见变化、使用路径、兼容行为、已知限制和失败提示；开发文档补充根因、文件、数据迁移、测试证据、风险和后续工作。两者不能混写。

每次更新先递增 SemVer，再同步 README、CHANGELOG、RELEASE_NOTES、CURRENT_STATUS、CHANGE_HISTORY 和版本戳，之后构建 EXE/ZIP，扫描 Secret，审查 diff/status，提交并推送。Tag/Release/资产必须与版本完全一致。

## 安全与兼容

不提交 `paper_project`、`.env`、密钥、Token、私人论文或截图；不删除源数据；迁移只复制并保留冲突备份；不绕过政府网站/CNKI 的登录和反爬限制；不削弱证据约束和自然化保护。

# 版本: v2.3.0 (2026-08-19) 更新: Codex 开发流程
