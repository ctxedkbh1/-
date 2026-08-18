# 开发历史与变更确认

本文件面向后续 Codex/开发者，记录可由 Git、源码、README、CHANGELOG 或 Release 确认的历史。无法确认的内容必须标记“未知 / 需要进一步确认”。

## 已确认时间线

- v2.0.0：高级工作台、历史任务、定向修改、自定义输出目录、多 Provider 基础能力和全自动断点恢复进入正式版本。
- v2.0.1：修复 Windows 打包和旧用户数据兼容；完整版改为 onedir，Release 同时提供 EXE + ZIP。
- v2.1.0：AI 模型中心、动态模型发现与缓存、ReferenceStore/CitationMap、Zotero Local/Web、Notebook Enterprise 接入、统一 UI 主题完成。
- v2.1.1：Provider/Model 启停持久化、Credential Manager 迁移、DeepSeek `/models` 修复、预设覆盖确认和模型路由修复。
- v2.1.2：OpenAlex 429 退避与礼貌访问、空资料安全停止、发布标题规范化。
- v2.2.0：AnnotationStore、批注样式模板、证据批注同步、批量管理、正文跳转、批注附录/批注表导出和中文 Release label。
- v2.3.0：自动质量门、无损统一数据目录、GitHub Release 更新检查、导出目录回退修复、Claude/Gemini 本地请求回归测试和 Windows Release workflow。

## OpenCode 遗留资产

- `core/deepseek.py` 是旧入口兼容层，主 Provider 逻辑已在 `core/llm.py`，不得因“旧”字样直接删除。
- `EvidenceStore` 的 E-ID、`AnnotationStore` 的独立批注 ID、旧配置模型字段和历史 JSON 都必须保持兼容。
- `scripts/release.py` 是现有发布入口；不要另建会绕过版本/资产/敏感信息检查的发布脚本。

## 版本更新纪律

每次修复都必须产生一个版本更新，写入客户日志和开发日志，并在测试通过后推送 main、创建 Tag、更新 GitHub Release。发布动作失败时记录真实阻塞原因，不能把本地完成写成远程已发布。

# 版本: v2.3.0 (2026-08-19) 更新: 接管 OpenCode 开发历史
