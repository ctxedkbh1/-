# Codex 项目上下文

## 当前版本
v2.2.0（2026-08-18，已发布）

## 当前状态
- 分支：`main`
- 工作目标：完成独立批注系统并保持旧证据引用兼容
- 兼容要求：现有普通/全自动/高级模式、EvidenceStore、导出和用户数据不得破坏

## 已有主要功能
- 三种论文模式、多 Provider 模型路由、联网检索、EvidenceStore、防编造检查
- AnnotationStore、批注样式模板、证据批注同步、批量管理和批注导出
- DOCX/PDF/PPTX/TXT/Markdown/HTML 导出
- 历史记录、断点恢复、完整版本地部署、GitHub Release

## 当前任务
v2.2.0 批注系统代码、文档、回归测试和中文 Release label 资产已完成并验证；main、Tag 和 GitHub Release 均已发布。Actions 文件仍等待 OAuth `workflow` scope。

## 下一步
1. 用户授权 `workflow` scope 后同步 `.github/workflows/release.yml`
2. 后续每个 bug/功能/UI 改动均按 RELEASE_PROCESS.md 递增版本发布

## 重要文件
- `core/paths.py`：版本唯一来源
- `config/manager.py`：现有配置与旧模型迁移入口
- `core/ai/`：动态 Provider、Model、Discovery、Registry、Credential、AIService
- `core/references/`：ReferenceStore、导入、去重、CitationMap、样式
- `core/llm.py`, `core/deepseek.py`：现有 AI 调用链
- `core/evidence.py`, `core/fact_checker.py`：证据与引用约束
- `core/annotations.py`, `gui/pages/annotation_page.py`：批注数据、样式与管理 UI
- `core/exporter.py`, `core/exporters/`：统一导出
- `gui/main_window.py`：应用壳层
- `DESIGN.md`：UI 唯一视觉契约
- `docs/ai/RELEASE_PROCESS.md`：发布规则

## 不可违反
- 源码高于文档，文档高于聊天记忆
- 不伪造模型能力和参考文献
- API Key、Zotero Token、用户数据不得进入 Git/日志/截图
- 测试未通过不得升级版本或发布
