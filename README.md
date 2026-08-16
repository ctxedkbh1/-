# 论文智能研究与写作助手

Windows 桌面软件：选题 → 权威资料检索 → 证据表 → AI 大纲 → 分章节写作 → 事实核查 → Word/Markdown 输出。

## 双模式

- **手动研究模式**：按 1→8 步逐步控制（论文信息 → 选题解析 → 资料检索 → 证据库 → 大纲 → 分章节写作 → 事实核查 → 输出）
- **全自动研究模式**：只需填写班级/姓名/论文题目并粘贴大纲，一键自动完成
  检索（OpenAlex/Crossref/政府网页）→ 证据库 → 证据核验 → 结构设计 → 分章写作 →
  引用/参考文献双向检查 → 事实核查 → 写作质量检测 → 自然化修改（不改变事实与引用）→
  再次核查 → 输出全部文件。全程支持：自动重试、自动保存、日志、暂停/取消、**断点恢复**（程序崩溃或关机后重启可继续）。

## 一键打包 EXE

1. 双击 `build.bat`（会自动安装依赖、自检、打包并复制到桌面）
2. 桌面出现 `论文智能研究与写作助手.exe`，双击即可使用

> 打包机需要 Python 3.10+（勾选 Add to PATH）。最终用户不需要安装任何环境。

## 开发运行

```bash
pip install -r requirements.txt
python main.py               # 启动界面
python main.py --selfcheck   # 无界面自检
python tests/dev_auto_test.py  # 离线端到端全自动流水线测试
```

## 目录结构

```
PaperAssistant/
├── main.py                # 入口
├── gui/                   # PySide6 界面（首页+全自动+8个手动阶段页面）
│   └── auto_mode_page.py  # 全自动模式（表单/进度/完成面板）
├── core/                  # 项目/证据/研究方案/大纲/写作/核查/输出
│   ├── auto_pipeline.py   # 全自动任务控制器（21步，断点恢复）
│   ├── checkpoint.py      # 断点数据 auto_checkpoint.json
│   ├── style_checker.py   # 写作质量检测（模板化/重复/句式单一/空洞）
│   ├── naturalizer.py     # 自然化修改（事实/引用/数字安全校验）
│   └── quality_report.py  # 论文质量报告
├── sources/               # OpenAlex / Crossref / 政府网页 / 网页搜索 / CNKI导入
├── config/manager.py      # API Key 配置（环境变量 > config.json）
├── requirements.txt
└── build.bat
```

## 运行数据（自动创建）

```
paper_project\
├── config.json            # API Key（本地保存，不进日志）
├── project.json           # 论文信息/大纲/状态（自动保存）
├── evidence.json          # 证据表 E001、E002……
├── auto_checkpoint.json   # 全自动任务断点
├── research_plan.md       # 研究方案
├── outline.md             # 大纲
├── chapters\01.md ...     # 各章正文
├── logs\YYYY-MM-DD.log    # 运行日志（不含 API Key）
├── cache\
└── output\
    ├── 论文.docx           # 真实 Word 文档
    ├── 论文.md
    ├── 资料核验报告.md
    ├── 证据表.json         # 全自动模式额外输出
    ├── 论文质量报告.md
    └── 全自动运行日志.md
```

## 防编造机制（最高优先级）

- AI 写作只能引用 evidence.json 中已有的证据，引用处标注 `[E001]` 格式编号
- 证据不足时强制输出“暂无足够可靠资料支持该观点”
- 所有检索均为真实来源：OpenAlex / Crossref 公开 API、政府网页（仅抓取确认存在的 URL）、
  CNKI 手动录入与 RIS/BibTeX 导入（不绕过登录/验证码/付费墙）
- 自然化修改只能改变句式与表达，数字/事实/引用/[Ex] 编号/参考文献均被程序强制保护，
  一旦变化立即撤销该章修改
- 输出前执行：引用 ↔ 参考文献双向检查 + AI 逐句事实核查（最多 3 轮质量循环）
- 著录信息不全的文献标记“待完善”，不自动猜测补全

## 多格式导出系统（v1.6.0）

- 统一 Document 模型（core/document.py）→ 同一份内容导出 6 种标准格式，均可脱离本程序独立打开：
  - **DOCX**（python-docx，支持用户格式要求：字体/字号/行距/首行缩进/页边距真实写入）
  - **PPTX**（python-pptx，封面+各章+参考文献真实可编辑幻灯片）
  - **PDF**（reportlab，内嵌中文字体，浏览器/Acrobat 直接打开）
  - **TXT / Markdown / HTML**（HTML 为完整独立页面，内嵌 CSS，无需服务器）
- 导出页支持：多格式同时导出、自定义文件名（自动清理 Windows 非法字符）、自动追加姓名/日期
- 导出后自动验证文件结构与内容（失败自动重生成一次）
- 输出文件夹文件管理：双击打开、删除选中、清空全部输出

## 版本管理规则

- 当前版本：v1.5.0（2026-08-16，多模型供应商系统）
- 每次更新后，所有改动文件的末尾都会追加版本号注释：`# 版本: vX.Y.Z (日期) 更新: 内容`
- 版本号统一定义在 `core/paths.py` 的 `VERSION` / `RELEASE_DATE`，首页与启动日志同步显示

## 多模型供应商（v1.5.0）

- 统一 `LLMProvider` 接口：OpenAI Compatible / Anthropic Claude / Google Gemini / 本地 Ollama，可自由添加自定义模型
- Model Router：按任务（论文生成/结构分析/文本优化/最终检查）选择模型，失败自动切换备用模型
- 模型方案一键切换、模型健康检查、API Key 本地保存（界面掩码显示，不进日志）
- 成本控制：单次最大调用次数 / Token / 预算（估算），达到限制自动暂停优化
- 检测服务 Provider 接口：内置启发式分析 + 自定义检测 API，未接入正规第三方 API 时明确标注"内部分析值"

## 注意事项

- 不提供任何绕过 AI 检测、伪造人工痕迹等功能；论文自然程度来自真实资料与原创论证
- API Key 只保存在本地 config.json，优先读取环境变量 DEEPSEEK_API_KEY
- 全自动模式的政府网页检索为尽力而为（公开搜索引擎），失败时自动跳过并在日志中提示手动补充
