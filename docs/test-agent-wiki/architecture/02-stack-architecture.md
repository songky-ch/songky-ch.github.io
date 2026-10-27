---
category: Agent
contentType: 架构设计
outline: [2, 3]
---

# 02. 技术底座与模块架构

[返回目录](./index.md)

## 1. 推荐组件与调用边界

下表是建议选型. 具体补丁版本在开发前用兼容性验证锁定, 不使用浮动 latest 上线, 也不把官网当前版本等同于依赖组合已兼容.

| 层 | 建议组件 | 本项目职责 | 调用方式 |
| --- | --- | --- | --- |
| Windows 壳 | C# / 受支持的 .NET LTS / WPF / WebView2 | 浏览器嵌入、受控桌面桥、安装更新 | 原生 API 与有限消息桥 |
| 工作台 | React + TypeScript + Vite | 聊天、任务、配置、HITL、知识库、报告 | HTTPS REST + SSE |
| API | Python 3.12 候选 + FastAPI / Uvicorn | 请求认证、参数校验、事件流 | 单 worker, asyncio |
| 契约 | Pydantic | 请求、工具参数、输出结构校验 | 生成 JSON Schema / OpenAPI |
| Agent | LangGraph OSS | 显式节点、条件路由、检查点和中断 | 在主服务调用库, 不部署额外 Agent Server |
| 模型适配 | 公司网关对应 SDK 或 HTTP 客户端 | chat、工具调用、视觉、向量、重排、裁判 | 按实际能力适配, 不假设 OpenAI 兼容等于功能全兼容 |
| 数据访问 | SQLAlchemy + Alembic + PostgreSQL | 事务、迁移、任务和业务记录 | 异步连接池, 小事务 |
| 语义检索 | PostgreSQL + pgvector | 知识片段与记忆的向量索引 | 向量检索加数据范围过滤 |
| 缓存 | Redis | 活跃上下文缓存、短期限流计数 | 有 TTL, 不做任务唯一事实来源 |
| 任务调度 | 主服务内调度模块 | 认领任务、限额、租约、取消和结果落库 | PostgreSQL 任务表 + OS runner |
| 文件 | Linux 独立数据目录 | 原文、页图、脚本、trace、报告 | 文件 ID 映射, 授权下载 |
| 文档 | pypdf / python-docx / 页渲染组件 + PaddleOCR 候选 | 文本、表格、图片、扫描页和版面 | 隔离解析子进程, 兼容性与许可证待审查 |
| 接口 | pytest + HTTPX | 参数化套件、断言、报告 | 专项 runner |
| UI | Playwright Python + Chromium | Linux 页面探查、脚本执行、截图和 trace | 专项 runner + 独立 browser context |
| 压力/性能 | k6 | 负载生成、阈值判断、原始指标 | 受控 CLI 参数数组, 不是模型直接执行 shell |
| 运维 | systemd + 结构化日志 + OpenTelemetry | 生命周期、资源限制、追踪 | OS 配置与 SDK |
| 指标集成 | 现有 Prometheus 兼容接口 | 读取目标监控, 关联压测窗口 | 只读范围查询 |

Python 3.12 是候选兼容基线, 不是“最新版本”声明. PaddleOCR、浏览器系统库、LangGraph 持久化插件必须共同验证后锁定. WPF 支持 WebView2, 但浏览器壳与登录协议是两个独立问题. [WPF 官方入门](https://learn.microsoft.com/en-us/microsoft-edge/webview2/get-started/wpf)

## 2. 为什么不是把所有能力交给一个大提示词

模型负责判断“下一步适合做什么”, 程序负责判断“这一步是否合法、是否有参数、是否能执行、是否真正成功”.

例如用户说“把查询接口压到 100, 看看能不能撑住”. 模型能识别压力测试意图, 但不能替用户确定 100 是并发用户还是每秒请求数. 参数模块发起补问, 用户回答后形成可追溯配置. 调度模块只有在配置、授权与执行环境均满足时才启动任务.

## 3. 模块划分与依赖方向

| 模块 | 输入 | 输出 | 不承担的职责 |
| --- | --- | --- | --- |
| identity | 平台会话或受信任身份断言 | 服务端用户上下文 | 不相信客户端自报工号 |
| conversations | 用户消息和附件引用 | 消息记录、运行请求 | 不直接启动测试进程 |
| agent_runtime | 用户目标、上下文、可用工具 | 回复或 ToolCallProposal | 不绕过策略直接操作系统 |
| policy_hitl | 动作、参数、目标、授权范围 | allow / deny / ask | 不凭模型判断扩权 |
| tools | 合法调用和工具版本 | ToolResult 或 task_id | 不自行决定用户身份 |
| task_scheduler | 已授权 TaskSpec | 执行租约与任务状态 | 不用内存队列承担唯一持久化 |
| executor | ExecutionSpec | 事件、退出状态、文件清单 | 不持有数据库和模型全局密钥 |
| knowledge_memory | 范围明确的读写请求 | 片段、来源、记忆候选 | 不从文本继承系统权限 |
| evaluation | 冻结数据集和目标配置 | 逐样本结果与聚合指标 | 不把缺失证据算成通过 |
| artifacts | 文件流及元数据 | 授权文件引用 | 不直接暴露服务器路径 |

主链: API → 用户上下文 → Agent/领域服务 → 策略 → 工具 → 调度 → 执行器. 领域服务也可从表单直接进入, 不必绕经模型重新解释确定的参数.

## 4. 一次请求的调用时序

::: details 补充流程图源码 (Mermaid)

```text
sequenceDiagram
    participant U as Windows 工作台
    participant A as API 主服务
    participant G as Agent 图
    participant P as 策略与 HITL
    participant D as PostgreSQL
    participant E as 执行器
    U->>A: 创建消息 / 提交任务, request_id
    A->>D: 验证身份与持久化请求
    A-->>U: run_id / task_id
    U->>A: 订阅事件流, after_seq
    A->>G: 目标 + 范围 + 上下文
    G->>P: 工具提案和参数
    alt 需要人工输入或审批
        P->>D: 保存等待项和检查点
        A-->>U: interaction.required
        U->>A: 决定 + 期望版本
        A->>P: 校验并恢复
    else 已在授权范围
        P-->>G: allow
    end
    G->>D: 保存工具调用和任务
    A->>E: 调度已认领任务
    E-->>A: 事件 / 结果 / 文件清单
    A->>D: 保存事实与状态
    A-->>U: 进度与最终结果
```

:::

这是主成功时序, 拒绝、过期、重试和重启细节见 [任务状态](05-tasks-executor.md) 与 [分支目录](13-branches-acceptance.md).

## 5. 最小部署不是零基础设施

常驻业务服务只有一个, PostgreSQL 和 Redis 是独立基础设施进程, 可以复用公司现有服务. Linux 执行器按任务启动. 前端构建为静态文件随主服务部署, 不要求额外 Node 常驻服务. HTTPS 入口优先复用公司已有网关, 其是否存在仍待确认.

LangGraph 提供状态编排与持久化机制, 不替代业务任务队列、执行隔离或凭证管理. [LangGraph 持久化](https://docs.langchain.com/oss/python/langgraph/persistence)

FastAPI 的 BackgroundTasks 适合响应后的后台工作, 本方案的长任务仍须持久化、调度和恢复, 不能只放入它就宣称支持可靠执行. [FastAPI 背景任务说明](https://fastapi.tiangolo.com/tutorial/background-tasks/)

## 6. 技术验证清单

开发前建立精确版本清单: OS、Python、.NET、WebView2 SDK/Runtime、数据库与扩展、模型网关、Playwright 与浏览器二进制、OCR 模型文件及哈希、k6. 记录安装来源、许可、内网分发方式和兼容性测试结果. 不在本轮安装这些运行依赖.

## 7. 上下文、Prompt 与 Harness 的位置

上下文选择/压缩与 Prompt 组装属于主服务内 `agent_runtime` 的逻辑职责, 使用现有 Python/Pydantic、PostgreSQL、Redis 与文件产物, 不新增部署进程. 上下文先筛选材料并分配预算, Prompt 组装器按固定版本形成模型请求, 工具提案继续经过策略与既有调度器.

Harness 是这些运行控制模块的整体, 不是与调度器平行的第二套控制中心. LangGraph 管理流程与检查点, 调度器管理任务和资源, 执行器管理 attempt. 详细职责见 [18](18-harness-runtime.md); 输入预算见 [16](16-context-engineering.md); 模板契约见 [17](17-prompt-engineering.md).
