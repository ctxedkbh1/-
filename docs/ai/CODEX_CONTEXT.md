# Codex 项目上下文

## 当前版本
v2.3.0（2026-08-19，源码完成，待正式发布）

## 当前状态
- 分支：`main`
- 工作目标：完成自动质量门、稳定用户数据、更新检查和正式发布；保持既有批注/证据兼容
- 兼容要求：现有普通/全自动/高级模式、EvidenceStore、导出和用户数据不得破坏

## 已有主要功能
- 三种论文模式、多 Provider 模型路由、联网检索、EvidenceStore、防编造检查
- AnnotationStore、批注样式模板、证据批注同步、批量管理和批注导出
- DOCX/PDF/PPTX/TXT/Markdown/HTML 导出
- 历史记录、断点恢复、完整版本地部署、GitHub Release

## 当前任务
v2.3.0 自动质量门、数据迁移、更新检查、Provider 回归和 workflow 已完成源码与离线验证；main/Tag/Release 待本轮构建发布。

## 下一步
1. 构建 v2.3.0 EXE/ZIP，运行发布门并核对无私人数据
2. 推送 main、创建 Tag/Release、上传两个资产并核对中文 label
3. 后续每个 bug/功能/UI 改动均按 RELEASE_PROCESS.md 递增版本并自动上传

## 重要文件
- `core/paths.py`：版本唯一来源
- `core/quality_gate.py`：统一自动判定起始要求
- `core/data_migration.py`：稳定目录与旧数据无损迁移
- `core/updater.py`、`gui/update_check.py`：GitHub Release 异步更新检查
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
