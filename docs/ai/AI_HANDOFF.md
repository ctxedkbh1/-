# AI项目交接文档（AI_HANDOFF）

> **新 AI 必读**：这是项目交接入口。请按顺序阅读：
> 1. 本文件（先读）
> 2. docs/ai/CURRENT_STATUS.md（项目状态单一事实来源）
> 3. docs/ai/ARCHITECTURE.md（架构）
> 4. docs/ai/FEATURES.md（功能清单）
> 5. docs/ai/FILE_MAP.md（文件地图）
> 6. docs/ai/TODO.md、KNOWN_ISSUES.md、DEVELOPMENT_RULES.md
> 7. docs/ai/RELEASE_PROCESS.md（发版与日志受众规则）
>
> 阅读完成后，先向用户输出【项目理解确认】（模板见文末），等待指令，**不要直接修改代码**。
>
> 最高原则：【源码 > 项目文档 > AI 记忆 > AI 猜测】。源码与本文档不符时以源码为准，无法确认时如实说明。

---

## 项目
Windows 桌面论文智能研究与写作助手（品牌名：论文助手）。选题 → 权威资料检索 → 证据库 → AI 大纲 → 分章节写作 → 事实核查 → 多格式导出。**防编造是最高优先级设计**：AI 只能引用检索到的真实证据。

## 当前版本
v2.0.1（2026-08-17）

## 当前Baseline
- 日期：2026-08-17
- Tag：v2.0.1（指向最新基线提交）
- 本地备份：`C:\Users\Administrator\Documents\Default Project\backup\project-baseline-2026-08-17-v2.0.1\`
- GitHub：https://github.com/ctxedkbh1/paper-workbench（公开，main 分支）

## 技术栈
Python 3.10+ / PySide6 / requests / python-docx / python-pptx / reportlab / PyInstaller。Windows 10/11 x64。无数据库（本地 JSON + Markdown）。

## 当前状态
维护中：v2.0.1 已发布（GitHub Release 提供 EXE + ZIP）；动态 AI 模型中心已按用户要求暂停，尚未修改业务代码。源码目录：`C:\Users\Administrator\Documents\Default Project\PaperAssistant`。

## 已完成
- 三种模式：普通 8 步 / 全自动 21 步（断点恢复）/ 高级工作台 6 阶段
- 多模型：OpenAI 兼容（DeepSeek/OpenAI/Qwen/Moonshot/智谱/OpenRouter/Ollama/自定义）+ Claude + Gemini；模型路由/备用切换/成本控制/健康检查/预设
- 5 个检索源：OpenAlex/Crossref/政府网页/通用搜索/CNKI 手动导入（RIS/BibTeX）
- 证据库防编造：E001 编号、证据不足强制声明、引用↔参考文献双向检查、自然化修改保护事实
- 质量体系：style_checker/naturalizer/fact_checker（3 轮）/quality_report/targeted_edit/detector
- 导出：DOCX/PPTX/PDF/TXT/MD/HTML 6 格式 + 验证重生成；自定义输出目录
- 历史记录、断点恢复、日志脱敏、响应式 UI/DPI
- 工程：--selfcheck、4 个离线测试、build.bat 完整版目录打包、build_share.bat 分享 ZIP 打包
- GitHub 发布：公开仓库 + Release v2.0.1 + README/CHANGELOG/LICENSE + docs/ai 知识库

## 正在开发
无（封存状态）。

## 下一步
见 TODO.md。P0/P1 均为空或可选；任何任务开始前需用户确认。

## 已知问题
见 KNOWN_ISSUES.md：EXE 首启慢、政府检索不稳定、CNKI 仅手动导入、长文全自动耗时。均 Open（设计限制），无致命 Bug。

## 重要文件
main.py（入口）、core/paths.py（版本号唯一来源）、core/llm.py（AI Provider）、core/auto_pipeline.py（全自动编排）、core/exporter.py（导出）、config/manager.py（配置）、gui/main_window.py（主窗口）、build.bat（打包）。详见 FILE_MAP.md。

## 核心架构
```
PySide6 GUI（gui/，三模式+8阶段页+历史+导出+模型管理）
  → 应用层 core/（编排 auto_pipeline/advanced_state；写作 writer/naturalizer/targeted_edit；
    质量 fact_checker/style_checker/quality_report；证据 evidence/research/checkpoint；
    文档 document/exporter；基础 paths/log/history/output_location/prompts/project）
  → AI 层 core/llm.py（OpenAICompatible/Claude/Gemini 三套 Provider + 路由）
  → 检索层 sources/（openalex/crossref/government/websearch/cnki）
  → 存储层 paper_project\（JSON+MD 本地文件，无数据库）
```
详见 ARCHITECTURE.md。

## AI Provider
- 统一 LLMProvider 接口（core/llm.py）
- OpenAI 兼容：DeepSeek 默认（deepseek-chat, https://api.deepseek.com）、OpenAI、通义千问、Moonshot、智谱、OpenRouter、Ollama、自定义 base_url
- Anthropic Claude（Messages API）、Google Gemini（generateContent）
- 环境变量 DEEPSEEK_API_KEY 优先；Key 存 paper_project/config.json，界面掩码、日志脱敏

## 外部服务
OpenAlex / Crossref（公开学术 API）；政府官网与通用网页（公开搜索引擎，尽力而为）；CNKI（仅手动导入，不绕过登录）。AI 接口按用户配置。**无云同步、无遥测**，唯一出站流量是 AI 接口与检索源。

## 数据结构（paper_project\，仓库外，gitignore）
- config.json：模型配置与 API Key（**禁止上传/提交**）
- project.json：论文信息/大纲/状态
- evidence.json：证据表（E001 编号）
- auto_checkpoint.json：全自动断点
- research_plan.md / outline.md / chapters\01.md… / logs\ / cache\
- output\：论文.docx/.md/.pdf/.pptx/.html/.txt、资料核验报告.md、论文质量报告.md、全自动运行日志.md

## 最近修改
2026-08-17：修复 Windows 批处理 CRLF 与 cmd.exe UTF-8 解析问题，重新打包并实际启动验证 v2.0.1；动态 AI 模型中心仅完成扫描与方案设计。

## 修改原因
用户要求项目封存：建立任何 AI 都能读取的项目知识库，防止未来因上下文不足而误改代码。

## 测试状态
- python main.py --selfcheck：打包前已通过
- tests/ 4 个离线测试：打包前已通过
- v2.0.1 完整版目录 EXE 与分享版目录 EXE：已实际启动并显示主窗口，正常
- 本次交接仅新增文档，未改业务代码

## 不要修改的内容
- 防编造机制（evidence/writer/naturalizer/fact_checker 约束逻辑）
- core/paths.py 版本定义（改版本号按 DEVELOPMENT_RULES.md 流程）
- 用户已部署的 v2.0.1 成品（改代码≠改已发布包，发新包需用户确认）
- 不得 push --force 分支；移动正式版本标签需用户同意

## 当前开发规则
见 DEVELOPMENT_RULES.md（源码优先、修改前检查协议、修改后验证协议、禁止幻觉协议、中文命令行用文件传递、版本戳约定、同步 CHANGELOG/CURRENT_STATUS）。

## 下一步建议
1. 无用户指令时保持封存状态，只回答项目相关问题
2. 用户要求开发时：先走"修改前检查协议"，列出文件/原因/影响等确认
3. 上下文即将不足时：主动建议更新本文件与 CURRENT_STATUS.md 后再继续
4. 发版流程：改代码 → 版本戳 → VERSION 递增 → 测试 → CHANGELOG/CURRENT_STATUS 更新 → build.bat 打包 → git commit/push → tag → GitHub Release

---

## 【项目理解确认】模板（新 AI 第一次回复必须使用）

项目：（名称）
当前版本：（vX.X.X）
技术栈：（…）
已经完成：（…）
正在开发：（…）
已知问题：（…）
下一步：（…）
准备修改：（无，等待指令）
