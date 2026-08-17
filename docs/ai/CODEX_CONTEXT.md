# Codex 项目上下文

## 当前版本
v2.0.1（稳定基线；重大升级开发中，尚未发布 v2.1.0）

## 当前状态
- 分支：`feat/dynamic-model-center`
- 工作目标：增量实现 AI 模型中心、参考文献中心、UI 统一与自动发布
- 兼容要求：现有普通/全自动/高级模式、EvidenceStore、导出和用户数据不得破坏

## 已有主要功能
- 三种论文模式、多 Provider 模型路由、联网检索、EvidenceStore、防编造检查
- DOCX/PDF/PPTX/TXT/Markdown/HTML 导出
- 历史记录、断点恢复、完整版本地部署、GitHub Release

## 当前任务
Phase 2：AI 模型中心、参考文献中心与 UI 增量实现；正式版本号仍保持 v2.0.1。

## 下一步
1. 完成全自动/高级工作流的模型选择验证
2. 完成 Zotero/Notebook UI 流程和引用验证
3. 完成 UI/高 DPI/真实 Windows QA
4. 所有发布门通过后升级到 v2.1.0

## 重要文件
- `core/paths.py`：版本唯一来源
- `config/manager.py`：现有配置与旧模型迁移入口
- `core/ai/`：动态 Provider、Model、Discovery、Registry、Credential、AIService
- `core/references/`：ReferenceStore、导入、去重、CitationMap、样式
- `core/llm.py`, `core/deepseek.py`：现有 AI 调用链
- `core/evidence.py`, `core/fact_checker.py`：证据与引用约束
- `core/exporter.py`, `core/exporters/`：统一导出
- `gui/main_window.py`：应用壳层
- `DESIGN.md`：UI 唯一视觉契约
- `docs/ai/RELEASE_PROCESS.md`：发布规则

## 不可违反
- 源码高于文档，文档高于聊天记忆
- 不伪造模型能力和参考文献
- API Key、Zotero Token、用户数据不得进入 Git/日志/截图
- 测试未通过不得升级版本或发布
