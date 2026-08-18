# 项目总说明（PROJECT_CONTEXT）

## 项目名称
- 产品名：**论文助手**（窗口标题：论文智能研究与写作助手）
- 仓库名：`paper-workbench`（GitHub 不支持中文仓库名，见 KNOWN_ISSUES.md）

## 项目用途
Windows 桌面论文写作辅助工具：选题 → 权威资料检索 → 证据库 → AI 大纲 → 分章节写作 → 事实核查 → 多格式导出，全流程可视化引导。

## 项目目标
1. 把论文写作全流程做进一个桌面软件，逐步引导、可暂停、可回溯
2. **最高优先级**：AI 只能引用检索到的真实证据，绝不允许凭空编造内容（防编造机制）
3. 面向小白用户：EXE 双击即用，无需装任何环境

## 项目定位
AI 辅助写作 + 资料整理 + 文档生成工具，不代替用户思考，不提供绕过 AI 检测/伪造人工痕迹功能。

## 主要用户
在校学生、初学写作者。

## 技术栈
- 语言：Python 3.10+
- 界面：PySide6（>=6.8）
- 打包：PyInstaller（>=6.11；桌面固定名称覆盖，GitHub Release 使用版本化 EXE + ZIP）
- 依赖：requests / python-docx / python-pptx / reportlab（见 requirements.txt）

## 运行环境
- 成品 EXE：Windows 10/11 x64，免任何环境
- 源码运行：Python 3.10+（打包机需勾选 Add to PATH）

## 数据库
无数据库。全部数据为本地 JSON + Markdown 文件（见"运行数据"）。

## AI 模型（core/llm.py 统一 LLMProvider 接口）
- OpenAICompatibleProvider：DeepSeek（默认，deepseek-chat）/ OpenAI / 通义千问 / Moonshot / 智谱 / OpenRouter / Ollama 本地 / 自定义 base_url
- ClaudeProvider：Anthropic Messages API
- GeminiProvider：Google Gemini API
- 模型路由、失败自动切换备用、成本控制（估算）

## 外部 API / 检索源（sources/）
- OpenAlex、Crossref（公开学术 API）
- 政府官网（公开搜索引擎，尽力而为）
- 通用网页搜索
- CNKI：仅手动录入 + RIS/BibTeX 导入（不绕过登录/验证码/付费墙）

## 主要功能
三种模式（普通 8 步 / 全自动 23 步 / 高级工作台 6 阶段）、证据库防编造、独立批注与样式管理、写作质量检测与自然化修改、自动质量门、事实核查（最多 3 轮）、定向修改、6 格式导出（DOCX/PPTX/PDF/TXT/MD/HTML）、历史记录、断点恢复、自定义输出目录、GitHub Release 更新检查。详见 FEATURES.md。

## 当前开发阶段
v2.3.0 已完成自动质量门、稳定数据迁移、更新检查、Provider 回归和 Windows workflow 源码测试（2026-08-19）；EXE/ZIP、Tag 和 Release 均已发布并核对。

## 项目目录
- 源码根目录：`C:\Users\Administrator\Documents\Default Project\PaperAssistant`
- GitHub：https://github.com/ctxedkbh1/paper-workbench
- 运行数据目录（仓库外，禁止上传）：默认 `%LOCALAPPDATA%\PaperAssistant\paper_project\`，可用环境变量 `PAPER_PROJECT_DIR` 覆盖。首次升级从旧桌面目录无损复制并保留冲突备份；内含 config.json（API Key）、project.json、evidence.json、annotations.json、annotation_styles.json、auto_checkpoint.json、chapters/、logs/、output/ 等。

## 重要文件
| 文件 | 作用 |
|---|---|
| main.py | 入口（含 --selfcheck 自检） |
| core/paths.py | APP_NAME / VERSION / RELEASE_DATE 统一定义、数据目录路径 |
| core/llm.py | 全部 AI Provider 实现 |
| core/auto_pipeline.py | 全自动模式控制器（23 步、断点恢复、自动质量门） |
| core/quality_gate.py | 起始要求自动判定 |
| core/data_migration.py | 稳定数据目录与旧版无损迁移 |
| core/updater.py / gui/update_check.py | GitHub Release 更新检查 |
| core/annotations.py | 批注记录、样式模板、证据同步与重新编号 |
| config/manager.py | API Key 配置管理（环境变量 > config.json） |
| gui/main_window.py | 主窗口 |
| build.bat / build_share.bat | 完整版目录打包 / 分享版 ZIP 打包 |
| docs/ai/AI_HANDOFF.md | AI 交接入口（新对话先读它） |
