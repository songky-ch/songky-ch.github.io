---
category: Agent
contentType: 架构设计
outline: [2, 3]
---

# 15. 术语与官方依据

[返回目录](./index.md)

## 1. 术语

| 名称 | 中文含义 | 本项目具体作用 |
| --- | --- | --- |
| Agent | 智能体运行系统 | 模型、状态、工具、策略与反馈的组合 |
| Tool calling | 工具调用 | 模型提案, 应用校验与执行 |
| Workflow | 工作流 | 明确步骤、条件、状态和不可跳过的约束 |
| HITL | 执行中人工介入 | 补问、审批、选择、认证和证据核对 |
| Skill | 可复用方法包 | 指令、模板、参考资料与可审查脚本 |
| IDaaS | 身份即服务 | 公司登录与身份验证体系 |
| client_id | OAuth 客户端标识 | 标识获准接入应用, 不等同密码或用户工号 |
| WebView2 | Windows 内嵌浏览器控件 | 桌面工作台和内网页面入口 |
| WPF | Windows Presentation Foundation | 建议的 Windows 桌面壳框架 |
| RAG | 检索增强生成 | 根据可见知识证据回答 |
| Agentic RAG | 由 Agent 决定检索步骤 | 有预算地选择检索、改写、补问或停止 |
| OCR | 光学字符识别 | 从扫描页/图片识别文字, 不直接理解全部业务关系 |
| Embedding | 向量表示 | 为文本建立语义查询索引 |
| Rerank | 重排 | 对候选片段进一步排序 |
| Memory | 记忆 | 跨轮/跨会话复用的用户与项目上下文 |
| Checkpoint | 检查点 | 保存图运行的恢复状态, 不保证外部副作用恰好一次 |
| Run / Task / Attempt | 请求运行/任务/执行尝试 | 区分对话、专项工作和具体进程尝试 |
| Lease | 租约 | 限时确认调度所有权与活跃状态 |
| Fencing token | 执行代次令牌 | 拒绝旧 attempt 覆盖新结果, 不阻止所有外部副作用 |
| Idempotency | 幂等 | 重复提交不产生重复业务效果或任务 |
| CAS | 比较并更新 | 用期望版本解决并发更新与取消竞态 |
| SSE | 服务器发送事件 | 单向流式传递回答与任务状态 |
| JSON Schema / OpenAPI | 数据/API 描述规范 | 统一表单、工具、后端契约 |
| cgroup | Linux 资源控制组 | 限制和清理任务进程集合 |
| systemd | Linux 服务管理器 | 管理主服务与受控任务生命周期 |
| DAG | 有向无环图 | 接口套件步骤依赖, 不等于业务流程不能有循环 |
| VU | 虚拟用户 | 封闭负载模型中的并发执行单元 |
| QPS / RPS | 每秒查询/请求数 | 必须与迭代率、并发数分开报告 |
| p95 / p99 | 延时分位数 | 95%/99% 观测不超过的对应值, 不能简单平均合并 |
| Recall / MRR / nDCG | 召回与排序指标 | 在明确标注集合上衡量检索 |
| LLM-as-a-Judge | 模型裁判 | 使用固定评分规范辅助语义评测 |
| Rubric | 评分细则 | 让语义判断有可审查依据 |
| SLO | 服务目标 | 需业务和实测决定, 不编造通用数值 |
| RPO / RTO | 恢复点/恢复时间目标 | 约束备份与恢复演练 |
| Trace | 调用轨迹 | 定位模型、工具、任务与指标证据 |
| N/A / INCONCLUSIVE / UNKNOWN | 不适用/证据不足/执行结果未知 | 三者不同, 不混记为通过或零分 |

## 2. 来源与核查范围

核查日期: 2026-10-26. 使用一手官方文档和项目官方仓库. 网页属于动态文档, 未冻结源代码 commit; 因此本文不声称验证了未来实施所用的精确依赖版本. 列表用于能力与语义依据, 本项目架构和分支设计由当前需求推导, 不冒称官方推荐整套技术组合.

| 来源 | 本次用途 |
| --- | --- |
| [WebView2 in WinUI 3](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/webview2) | 核查内嵌认证限制, 非 WPF 技术选型依据 |
| [WebView2 WPF 入门](https://learn.microsoft.com/en-us/microsoft-edge/webview2/get-started/wpf) | WPF 集成能力 |
| [WebView2 安全](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/security) | 来源和消息校验, 避免通用宿主代理 |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | 检查点和长期存储的区别 |
| [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | 中断恢复及节点重放语义 |
| [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | 后台工作与可靠任务系统的区别 |
| [FastAPI workers](https://fastapi.tiangolo.com/deployment/server-workers/) | 多 worker 进程与部署边界 |
| [Pydantic models](https://pydantic.dev/docs/validation/latest/concepts/models/) | 数据结构与校验能力 |
| [SQLAlchemy](https://www.sqlalchemy.org/) | 数据库访问技术定位 |
| [PostgreSQL SELECT](https://www.postgresql.org/docs/current/sql-select.html) | 行锁与 SKIP LOCKED 语义 |
| [pgvector 官方仓库](https://github.com/pgvector/pgvector) | 精确/近似搜索和过滤注意事项 |
| [Python asyncio subprocess](https://docs.python.org/3/library/asyncio-subprocess.html) | 异步子进程能力 |
| [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) | 进程身份与执行环境限制 |
| [systemd.resource-control](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html) | cgroup 资源限制 |
| [systemd.kill](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html) | 进程组清理语义 |
| [React Learn](https://react.dev/learn) | 工作台组件化能力 |
| [Playwright auth](https://playwright.dev/python/docs/auth) | 独立 context 与敏感认证状态 |
| [Playwright browsers](https://playwright.dev/python/docs/browsers) | 浏览器与系统依赖匹配 |
| [pytest](https://docs.pytest.org/en/stable/) | 断言、参数化、fixture 和结果机制 |
| [HTTPX](https://www.python-httpx.org/) | Python 同步/异步 HTTP 客户端能力 |
| [k6 open vs closed](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/) | 负载模型与迭代到达率 |
| [k6 thresholds](https://grafana.com/docs/k6/latest/using-k6/thresholds/) | 阈值判定 |
| [PaddleOCR PP-StructureV3](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html) | 版面与文档解析候选能力 |
| [pypdf](https://pypdf.readthedocs.io/en/stable/) | PDF 文本/元数据提取 |
| [python-docx](https://python-docx.readthedocs.io/en/latest/) | DOCX 处理候选 |
| [Agent Skills specification](https://agentskills.io/specification) | Skill 目录和元信息格式 |
| [OpenAI tool calling](https://developers.openai.com/api/docs/guides/function-calling) | 模型请求与应用执行的分工 |
| [Codex approvals](https://learn.chatgpt.com/docs/agent-approvals-security) | 权限边界与审批策略分离 |
| [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | 评测分层、人工校准和裁判偏差 |
| [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/) | 日志、指标、追踪的观测定位 |
| [Prometheus HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/) | 目标监控只读查询接口 |

Redis 官方持久化/数据类型页面本次读取超时, 因此未引用其具体版本行为. 本稿仅建议它承担非唯一缓存与限流角色; 精确版本、许可、部署与持久化配置在实施前复核.

## 3. 证据边界

- 已阅读: 上述官方页面的相关能力与语义说明.
- 已设计: 本 Wiki 的组件组合、状态、契约、分支和验证计划.
- 未验证: 公司认证、内网网络、模型网关、Linux 隔离、OCR 效果、压测容量、数据库恢复.
- 原始文档编写阶段未执行: 业务开发、真实登录、凭证提取、真实测试、外部写入、公开发布. 本轮已获准将文档发布到公开站点, 业务开发与测试仍未执行.

本文不会因为参考资料中出现较新版本就自动替用户升级依赖. 任何架构变更都应回到决策表并更新对应流程与验收项.
