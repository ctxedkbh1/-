# 项目文件地图（FILE_MAP）

> 记录重要文件与作用（v2.0.0，依据真实源码）。省略无意义小文件。

## 入口与配置
| 文件 | 作用 |
|---|---|
| main.py | 程序入口；--selfcheck 无界面自检；UI 检查；浅色主题 |
| requirements.txt | 依赖：PySide6/requests/python-docx/python-pptx/reportlab/pyinstaller |
| build.bat | 完整版打包（装依赖→自检→PyInstaller onedir→复制整个目录到桌面） |
| build_share.bat | 分享版打包（PyInstaller onedir → ZIP → 复制桌面） |
| .gitignore | 忽略 __pycache__/build/dist/.venv/.env/paper_project 等 |
| config/manager.py | API Key 配置（环境变量优先于 config.json；默认 DeepSeek deepseek-chat） |

## AI 层
| 文件 | 作用 |
|---|---|
| core/llm.py | LLMProvider 统一接口；OpenAICompatible / Claude / Gemini 三套 Provider；模型路由与备用切换 |
| core/deepseek.py | DeepSeek 相关（历史兼容，主体已并入 llm.py） |
| core/model_presets.py | 模型预设方案 |
| core/prompts.py | 全部提示词模板 |
| core/detector.py | 内置启发式 AI 痕迹检测（未接第三方 API） |

## 核心业务
| 文件 | 作用 |
|---|---|
| core/project.py | 论文信息 project.json 读写 |
| core/research.py | 研究方案、检索编排 |
| core/evidence.py | 证据表 evidence.json（E001 编号体系） |
| core/outline.py | 大纲生成 outline.md |
| core/writer.py | 分章节写作（强制只引用证据库） |
| core/naturalizer.py | 自然化修改（事实/数字/引用/参考文献强制保护） |
| core/fact_checker.py | 逐句事实核查（最多 3 轮） |
| core/style_checker.py | 写作质量检测（模板化/重复/句式单一/空洞） |
| core/quality_report.py | 论文质量报告生成 |
| core/targeted_edit.py | 定向修改（只改指定位置） |

## 编排与状态
| 文件 | 作用 |
|---|---|
| core/auto_pipeline.py | 全自动模式：Controller/Engine，21 步，自动重试、on_fail=skip、暂停/取消 |
| core/checkpoint.py | 断点数据 auto_checkpoint.json（崩溃恢复） |
| core/advanced_state.py | 高级工作台六阶段状态 |
| core/history.py | 论文历史任务归档 |
| core/output_location.py | 自定义输出目录 |

## 导出与基础设施
| 文件 | 作用 |
|---|---|
| core/document.py | 统一 Document 模型（一份内容多格式） |
| core/exporter.py | DOCX/PPTX/PDF/TXT/MD/HTML 导出 + 完整性验证 + 自动重生成 |
| core/paths.py | **版本号唯一来源**（APP_NAME/VERSION/RELEASE_DATE）+ 数据目录路径（PAPER_PROJECT_DIR 可覆盖） |
| core/log.py | 日志（脱敏，不含 API Key） |

## 检索源
| 文件 | 作用 |
|---|---|
| sources/openalex.py | OpenAlex 公开学术 API |
| sources/crossref.py | Crossref 外文文献 |
| sources/government.py | 政府官网检索（尽力而为） |
| sources/websearch.py | 通用网页搜索 |
| sources/cnki.py | CNKI 手动录入 + RIS/BibTeX 导入 |

## UI
| 文件 | 作用 |
|---|---|
| gui/main_window.py | 主窗口、三模式导航 |
| gui/pages/home_page.py | 首页 |
| gui/pages/info_page.py 等 8 个阶段页 | 普通模式 1-8 步界面 |
| gui/pages/auto_mode_page.py | 全自动模式界面 |
| gui/pages/advanced_workspace.py | 高级工作台 |
| gui/pages/history_page.py | 历史记录界面 |
| gui/pages/export_page.py | 导出界面 |
| gui/pages/model_manager.py | 模型管理界面 |
| gui/widgets.py | 公共控件 |

## 测试
| 文件 | 作用 |
|---|---|
| tests/dev_auto_test.py | 离线端到端全自动流水线测试 |
| tests/dev_history_test.py | 历史功能测试 |
| tests/dev_nat_test.py | 自然化修改测试 |
| tests/dev_sett_test.py | 设置/模型测试 |

## 文档
| 文件 | 作用 |
|---|---|
| README.md | 项目主页（GitHub 展示） |
| CHANGELOG.md | 产品版本更新记录 |
| LICENSE | MIT |
| docs/ai/* | AI 知识库（本目录）；AI_HANDOFF.md 为交接入口 |
