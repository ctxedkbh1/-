# 论文助手（论文智能研究与写作助手）

Windows 桌面论文智能研究与写作助手：选题 → 权威资料检索 → 证据库 → AI 大纲 → 分章节写作 → 事实核查 → 多格式导出。

| | |
|---|---|
| 项目状态 | 维护中（个人项目，不定期更新） |
| 当前版本 | v2.0.0（2026-08-16） |
| 平台 | Windows 10/11 x64 |
| 许可证 | MIT |
| 最新下载 | [Releases 页面](https://github.com/ctxedkbh1/paper-assistant/releases) |

---

## 目录

- [项目简介](#项目简介)
- [核心功能](#核心功能)
- [三种写作模式](#三种写作模式)
- [支持的 AI 模型](#支持的-ai-模型)
- [联网资料检索](#联网资料检索)
- [防编造机制](#防编造机制)
- [多格式导出](#多格式导出)
- [系统要求](#系统要求)
- [安装方法](#安装方法)
- [启动方法](#启动方法)
- [AI 模型配置](#ai-模型配置)
- [运行数据说明](#运行数据说明)
- [项目架构](#项目架构)
- [目录结构](#目录结构)
- [常见问题](#常见问题)
- [已知问题](#已知问题)
- [安全说明](#安全说明)
- [免责声明](#免责声明)
- [版本管理](#版本管理)
- [更新计划](#更新计划)
- [贡献说明](#贡献说明)
- [许可证](#许可证)

---

## 项目简介

面向在校学生与初学写作者的 AI 辅助论文写作工具。它不代替你思考，而是把"选题、查资料、整理证据、搭大纲、分章写作、查事实、改表述、排版导出"这一整条论文流程做进一个桌面软件里，逐步引导、可暂停、可回溯，最终导出规范的 Word/PDF/PPT 等文件。

**核心原则：AI 只能引用你检索到的真实证据，绝不允许凭空编造内容**（详见[防编造机制](#防编造机制)）。

## 核心功能

- **AI 辅助论文生成**：选题解析 → 资料检索 → 证据库 → 研究方案 → 大纲 → 分章节写作 → 事实核查 → 多格式导出，全流程可视化
- **三种写作模式**：普通模式（8 步手动控制）、全自动模式（一键生成）、高级模式（流程化工作台）
- **多模型支持**：OpenAI 兼容接口（DeepSeek / OpenAI / 通义千问 / Moonshot / 智谱 / OpenRouter / Ollama 本地模型 / 自定义）、Anthropic Claude、Google Gemini
- **模型管理**：模型预设一键切换、健康检查、按任务自动选模型、失败自动切换备用模型、成本控制（调用次数/Token/预算上限）
- **联网学术检索**：OpenAlex、Crossref（外文文献）、政府官网政策文献、通用网页搜索、CNKI 手动录入与 RIS/BibTeX 导入
- **证据库**：检索结果统一整理为 E001、E002… 编号的证据表，写作时逐条引用
- **写作质量检测**：模板化/重复/句式单一/空洞表述自动分析，并给出质量报告
- **自然化修改**：优化 AI 痕迹与表述，程序强制保护数字、事实、引用编号、参考文献不被改动
- **定向修改**：对某一章、某一段单独提出修改要求，只改指定位置
- **多格式导出**：DOCX / PPTX / PDF / TXT / Markdown / HTML 六种格式，导出后自动验证文件完整性
- **历史记录**：每次写作任务自动保存，可随时回到任意历史任务查看或继续
- **断点恢复**：全自动模式崩溃或关机后，重启可从中断处继续
- **自定义输出目录**：所有产出文件可指定保存位置

## 三种写作模式

| 模式 | 适合谁 | 流程 |
|---|---|---|
| **普通模式** | 想逐步掌控每一步的人 | 按 1→8 步手动推进：论文信息 → 选题解析 → 资料检索 → 证据库 → 大纲 → 分章节写作 → 事实核查 → 输出 |
| **全自动模式** | 想一键出稿的人 | 填好班级/姓名/题目并粘贴大纲，自动完成：检索 → 证据库 → 证据核验 → 结构设计 → 分章写作 → 引用/参考文献双向检查 → 事实核查 → 质量检测 → 自然化修改 → 再次核查 → 导出全部文件。全程自动重试、自动保存、支持暂停/取消/断点恢复 |
| **高级模式** | 想要流程化指导的人 | 工作台式引导：题目 → 提纲 → 初稿 → 论证 → 结构优化 → 终稿，每阶段独立执行与检查 |

## 支持的 AI 模型

统一 `LLMProvider` 接口，在软件内"设置"页自由切换：

| 供应商 | 说明 | 默认模型 |
|---|---|---|
| OpenAI 兼容 | DeepSeek / OpenAI / 通义千问 / Moonshot / 智谱 / OpenRouter / Ollama / 自定义 base_url | deepseek-chat |
| Anthropic Claude | Claude Messages API | — |
| Google Gemini | Gemini generateContent API | — |

> 模型 Key 只保存在本机，界面掩码显示，绝不写入日志与导出文件。

## 联网资料检索

- **OpenAlex**：公开学术数据库 API，检索外文论文
- **Crossref**：外文文献元数据（DOI、作者、期刊、年份）
- **政府网页**：公开搜索引擎定位 gov.cn 等官方页面（尽力而为，失败自动跳过）
- **通用网页搜索**：补充检索
- **CNKI 导入**：手动录入 + RIS/BibTeX 文件导入（不绕过登录/验证码/付费墙）

## 防编造机制

本项目最高优先级设计，AI 生成内容受以下硬性约束：

1. AI 写作只能引用 `evidence.json` 中已有的证据，引用处标注 `[E001]` 格式编号
2. 证据不足时强制输出"暂无足够可靠资料支持该观点"，不允许 AI 自己补事实
3. 所有检索均为真实来源：OpenAlex / Crossref 公开 API、政府网页（仅抓取确认存在的 URL）、CNKI 手动录入
4. 自然化修改只能改变句式与表达；数字 / 事实 / 引用编号 / 参考文献由程序强制保护，一旦变化立即撤销该章修改
5. 输出前执行：引用 ↔ 参考文献双向检查 + AI 逐句事实核查（最多 3 轮质量循环）
6. 著录信息不全的文献标记"待完善"，不自动猜测补全

## 多格式导出

统一 Document 模型，同一份内容导出 6 种标准格式，均可脱离本程序独立打开：

- **DOCX**：真实 Word 文档（字体/字号/行距/首行缩进/页边距写入）
- **PPTX**：封面 + 各章 + 参考文献的可编辑幻灯片
- **PDF**：内嵌中文字体，浏览器/Acrobat 直接打开
- **TXT / Markdown / HTML**：HTML 为完整独立页面，内嵌 CSS

导出支持多格式同时导出、自定义文件名（自动清理 Windows 非法字符）、导出后自动验证（失败自动重新生成一次）。

## 系统要求

| | 最低 | 推荐 |
|---|---|---|
| 系统 | Windows 10 x64 | Windows 10/11 x64 |
| 运行 EXE | 无需安装任何环境 | — |
| 运行源码 | Python 3.10+ | Python 3.10+ |
| 网络 | 需要联网（AI 接口 + 学术检索） | — |
| AI 账号 | 至少一个模型供应商的 API Key | DeepSeek（国内可直连，便宜） |

## 安装方法

### 方式一：下载 EXE（推荐，小白可用）

1. 打开 [Releases 页面](https://github.com/ctxedkbh1/paper-assistant/releases)
2. 下载最新版的 `论文助手_vX.Y.Z.exe`（单文件版）或 `论文助手_vX.Y.Z.zip`（绿色版，解压即用）
3. 双击运行，**首次启动需要 10~30 秒**（PyInstaller 解压运行环境），请耐心等待

> 若 Windows SmartScreen 提示"已保护你的电脑"，点"更多信息 → 仍要运行"即可（未签名软件的正常提示）。

### 方式二：源码运行（开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/ctxedkbh1/paper-assistant.git
cd paper-assistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python main.py
```

## 启动方法

- **图形界面**：双击 EXE，或源码下执行 `python main.py`
- **无界面自检**：`python main.py --selfcheck`
- **离线端到端测试**：`python tests/dev_auto_test.py`（不联网的全自动流水线测试）
- **一键打包**：双击 `build.bat`（自动装依赖、自检、打包并复制到桌面）

## AI 模型配置

**第一步：获取 API Key**

| 供应商 | 获取方式 |
|---|---|
| DeepSeek | 访问 platform.deepseek.com → 注册 → API Keys 页面创建 |
| OpenAI | platform.openai.com → API Keys |
| Claude | console.anthropic.com → API Keys |
| Gemini | aistudio.google.com → API Key |

**第二步：在软件里填写**

启动软件 → 进入"设置/模型"页 → 选择供应商 → 粘贴 API Key → 点击健康检查确认可用。

**第三步（可选）：环境变量方式**

程序优先读取环境变量，适合进阶用户：

```powershell
# DeepSeek（默认供应商的 Key 环境变量名）
setx DEEPSEEK_API_KEY "你的Key"

# 自定义运行数据目录（默认在程序目录 paper_project\ 或用户目录）
setx PAPER_PROJECT_DIR "D:\我的论文数据"
```

> 所有示例中的"你的Key"只是占位符，请勿在 README、Issue 或任何公开位置粘贴真实 Key。

## 运行数据说明

程序运行时自动创建数据目录（默认 `paper_project\`，可用 `PAPER_PROJECT_DIR` 修改）：

```
paper_project\
├── config.json            # API Key 配置（本地保存，不进日志、不要上传）
├── project.json           # 论文信息/大纲/状态（自动保存）
├── evidence.json          # 证据表 E001、E002……
├── auto_checkpoint.json   # 全自动任务断点
├── research_plan.md       # 研究方案
├── outline.md             # 大纲
├── chapters\01.md ...     # 各章正文
├── logs\YYYY-MM-DD.log    # 运行日志（不含 API Key）
├── cache\
└── output\                # 导出产物
    ├── 论文.docx / 论文.md / 论文.pdf / 论文.pptx / 论文.html / 论文.txt
    ├── 资料核验报告.md
    ├── 论文质量报告.md
    └── 全自动运行日志.md
```

## 项目架构

```
PySide6 图形界面（三模式 + 8 个阶段页面 + 模型管理）
        │
        ▼
    应用层（core/）
    ├── 任务编排：auto_pipeline（全自动 21 步）/ advanced_state（高级工作台）
    ├── 写作引擎：writer / outline / naturalizer / targeted_edit
    ├── 质量体系：fact_checker / style_checker / quality_report
    ├── 证据体系：evidence / research / checkpoint
    └── 文档引擎：document / exporter（6 种格式）
        │
        ▼
    AI Provider 层（core/llm.py）
    ├── OpenAICompatibleProvider（DeepSeek/OpenAI/Qwen/智谱/Ollama…）
    ├── ClaudeProvider（Anthropic Messages API）
    └── GeminiProvider（Google Gemini API）
        │
        ▼
    检索层（sources/）
    ├── openalex / crossref（公开学术 API）
    ├── government / websearch（公开网页）
    └── cnki（手动录入 + RIS/BibTeX 导入）
        │
        ▼
    存储层：paper_project\（JSON + Markdown，本地文件）
```

## 目录结构

```
PaperAssistant/
├── main.py                    # 入口（--selfcheck 自检）
├── gui/                       # PySide6 界面
│   └── pages/                 # 首页/8个阶段页/全自动/高级工作台/历史/导出/模型管理
├── core/                      # 核心逻辑（见架构图）
├── sources/                   # 5 个检索源
├── config/manager.py          # API Key 配置（环境变量 > config.json）
├── tests/                     # 离线测试
├── docs/images/               # 截图（欢迎补充）
├── build.bat / build_share.bat# 一键打包脚本
├── requirements.txt
├── README.md / CHANGELOG.md / LICENSE
└── .gitignore
```

## 常见问题

**Q：双击 EXE 没反应？**
首次启动需要 10~30 秒解压运行环境，请稍等。若长时间无窗口，检查任务管理器中进程是否被杀毒软件拦截。

**Q：没有 API Key 能用吗？**
不能。AI 写作依赖模型接口，请在设置页配置至少一个供应商的 Key（无 Key 仍可浏览历史与已有项目文件）。

**Q：DeepSeek 返回 401？**
Key 无效或已过期。检查是否有多余空格、是否已充值/账户正常，然后点"健康检查"验证。

**Q：生成的内容是假的怎么办？**
程序强制 AI 只能引用证据库，但公开学术 API 的数据本身可能有误。**导出前请人工核对所有事实、数据与引用**（见[免责声明](#免责声明)）。

**Q：政府网页检索经常失败？**
该检索为尽力而为（公开搜索引擎），网络波动或站点反爬会导致失败，程序会自动跳过并在日志提示，可手动补充资料后继续。

**Q：导出的 PDF 中文正常吗？**
正常。PDF 内嵌中文字体，无需目标电脑安装字体。

**Q：数据存在哪里？会不会上传？**
全部数据存在本机 `paper_project\`。本软件没有任何云同步/遥测功能，唯一出站流量是 AI 接口与检索源。

## 已知问题

- 首次启动 EXE 较慢（PyInstaller 单文件特性）
- 政府网页检索成功率受目标站点反爬影响
- CNKI 受登录/验证码限制，仅支持手动录入与文件导入
- 长论文全自动模式耗时较长，建议使用断点恢复分次完成

## 安全说明

- **不要**把 API Key、密码、Token、个人隐私信息放进本仓库或 Issue
- **不要**提交 `paper_project\config.json`（已被 .gitignore 忽略，上传前请自查）
- API Key 仅保存在本机；日志与导出文件中不会出现 Key
- 若怀疑 Key 泄露，请立刻到对应平台吊销并重新生成

## 免责声明

本项目用于 AI 辅助写作、资料整理和文档生成。AI 生成内容**不应被视为绝对可靠的信息来源**，用户应当自行核实所有事实、数据、引用与参考文献。因使用本软件生成内容造成的任何后果，由使用者自行承担。本项目不提供任何绕过 AI 检测、伪造人工痕迹等功能；论文自然程度来自真实资料与原创论证。

## 版本管理

- 当前版本：**v2.0.0**（2026-08-16，高级模式工作台）
- 版本号统一定义在 `core/paths.py` 的 `VERSION` / `RELEASE_DATE`，首页与启动日志同步显示
- 每次更新后，改动文件末尾追加版本戳：`# 版本: vX.Y.Z (日期) 更新: 内容`
- 更新记录见 [CHANGELOG.md](CHANGELOG.md)

## 更新计划

暂无具体排期。需求与问题请提交 [Issues](https://github.com/ctxedkbh1/paper-assistant/issues)，欢迎讨论。

## 贡献说明

欢迎提 Issue 报告问题或建议；提交 PR 请：

1. Fork 本仓库并创建功能分支
2. 遵循现有代码风格与版本戳约定
3. 保持"防编造机制"不退化
4. 提交前运行 `python main.py --selfcheck`

## 许可证

[MIT](LICENSE) © 2026 ctxedkbh1
