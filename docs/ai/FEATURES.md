# 功能清单（FEATURES）

> 依据：真实源码（2026-08-18，v2.2.0）。区分"已实现 / 部分实现 / 计划实现"，禁止把计划写成已实现。

## 已实现

### 写作模式
- 普通模式：8 步手动流程（论文信息 → 选题解析 → 资料检索 → 证据库 → 大纲 → 分章节写作 → 事实核查 → 输出）
- 全自动模式：一键完成（检索 → 证据库 → 证据核验 → 结构设计 → 分章写作 → 引用/参考文献双向检查 → 事实核查 → 质量检测 → 自然化修改 → 再次核查 → 导出全部），21 步，自动重试/自动保存/暂停/取消/**断点恢复**
- 高级模式工作台：题目 → 提纲 → 初稿 → 论证 → 结构优化 → 终稿 六阶段流程化指导

### AI 模型
- 统一 LLMProvider 接口（core/llm.py）：OpenAI 兼容（DeepSeek 默认 deepseek-chat / OpenAI / 通义千问 / Moonshot / 智谱 / OpenRouter / Ollama / 自定义 base_url）、Anthropic Claude、Google Gemini
- 模型路由（按任务选模型）、失败自动切换备用模型
- 模型健康检查、模型预设一键切换（model_presets.py）
- 成本控制：单次最大调用次数/Token/预算（估算），达限自动暂停
- API Key 本地保存、界面掩码显示、不进日志；环境变量 DEEPSEEK_API_KEY 优先

### 检索与证据
- OpenAlex、Crossref 公开学术 API 检索
- 政府官网检索、通用网页搜索（失败自动跳过并提示）
- CNKI 手动录入 + RIS/BibTeX 导入
- 证据表 evidence.json（E001 编号）、防编造硬约束（见 ARCHITECTURE.md）
- 独立批注 registry 和样式 registry；证据 E-ID 无损同步为证据批注
- 批注搜索、样式/状态筛选、新增编辑、批量删除、按样式重新编号和 Markdown/JSON 导出
- 分章节写作页可对选中文本直接添加批注；重新编号同步更新章节标记

### 质量体系
- 写作质量检测（模板化/重复/句式单一/空洞）
- 自然化修改（事实/数字/引用编号/参考文献强制保护）
- AI 逐句事实核查（最多 3 轮质量循环）
- 论文质量报告（quality_report.py）
- 定向修改（targeted_edit.py，只改指定章节/段落）
- 内置启发式 AI 痕迹分析（detector.py）

### 导出与数据
- 6 格式导出：DOCX（真实格式写入）/ PPTX / PDF（内嵌中文字体）/ TXT / Markdown / HTML，导出后自动验证，失败自动重生成
- 正文中使用的普通批注导出到“批注说明”附录；全自动流程输出批注表 JSON/Markdown
- 自定义文件名（清理非法字符）、自动追加姓名/日期、自定义输出目录
- 论文历史（history.py + history_page.py）：任务归档、回看、继续
- 断点恢复（checkpoint.py）
- 运行日志（不含 API Key）

### 工程
- python main.py --selfcheck 无界面自检
- 发布门包含 AI、检索、参考文献、批注、集成、设置、视觉、自检和 UI 检查
- build.bat 覆盖桌面固定名称的“完整版”目录；build_share.bat 覆盖固定名称的分享 ZIP；GitHub Release 使用版本化 EXE + ZIP
- 响应式窗口与高 DPI 支持

## 部分实现

- **政府网页检索**：尽力而为（公开搜索引擎），受站点反爬影响可能失败；程序自动跳过，用户可手动补充
- **CNKI 检索**：仅手动录入与文件导入，不支持自动登录检索（设计限制，不绕过验证码/付费墙）
- **AI 痕迹检测**：仅内置启发式分析，未接入正规第三方检测 API（结果明确标注"内部分析值"）
- **成本控制**：预算为估算值，非实时账单对接

## 计划实现

- **无已排期的开发计划**（README 亦如此表述）。
- 候选方向（未确认、未排期，仅记录）：补充界面截图（docs/images/）、更多模型/检索源接入、检索稳定性优化、UI 细节优化。任何新功能需用户明确确认后才列入开发。

## v2.1.2 已发布

- AI ModelRef 选择实际进入假 HTTP 请求的 `model` 字段
- 旧配置与双 Key 迁移到系统凭据的回归测试
- Zotero Local/Web 响应解析、Notebook Enterprise 请求和本地文档导入
- 引用 E-ID → Reference ID → 导出编号映射
- 设置/模型中心/参考文献中心/About 离屏构造、窗口尺寸和 UI 检查
- Provider/Model 启用复选框、模型配置删除、预设导入二次确认和模型中心 Emoji 操作标识
- Windows Credential Manager 旧顶层凭据解析、桌面单文件 EXE 同步构建和 DeepSeek `/models` 刷新修复
- OpenAlex 429 退避重试、礼貌访问参数和空资料安全停止，避免生成 0 资料/0 文献论文

## v2.2.0 已发布

- AnnotationStore 与 AnnotationStyleStore 独立持久化，旧 E-ID 通过兼容层同步
- 批注管理页、样式模板页、正文批注链接和未登记批注检查
- 安全改写保护批注标记；统一 Document 和六种导出器支持批注说明
- 全自动输出批注表，历史记录关联完整导出文件
- 批注、参考文献、全自动、GUI 刷新、语法编译和主自检均通过
- GitHub Release `论文助手 v2.2.0` 已发布，资产页面使用中文 label 区分单文件版和完整版
