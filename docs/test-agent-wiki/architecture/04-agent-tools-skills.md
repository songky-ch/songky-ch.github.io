---
category: Agent
contentType: 架构设计
outline: [2, 3]
---

# 04. Agent、工具与 Skill

[返回目录](./index.md)

## 1. Agent 运行层做什么

Agent 不是模型本身. 本项目将模型调用、上下文、工具目录、策略检查、运行状态与结果解释组合成一个运行层. 建议先使用一个主 Agent, 按领域路由到固定子流程, 不引入多个自主 Agent 互相对话.

[![从消息到回答、补问、工具调用和停止的 Agent 分支](/images/test-agent-wiki/03-agent.svg)](/images/test-agent-wiki/03-agent.svg)

普通问答可以直接返回. 需要工具时先校验提案; 缺参数进入人工输入; 超过预算停止; 工具结果回到同一个受限运行循环. 图片、文档和检索结果均是待分析数据, 不能提升工具权限.

## 2. 显式节点与状态

| 节点 | 输入 | 行为 | 输出 |
| --- | --- | --- | --- |
| load_context | user_id / conversation_id / run_id | 读取消息、检查点、范围内记忆 | 有 token 预算的上下文 |
| classify | 当前目标与工具目录 | 区分聊天、检索、用例、API、UI、负载、评测 | 意图候选与缺失信息 |
| extract | 用户描述或表单 | 按领域 schema 提取参数和原文依据 | 参数草稿 |
| validate | 参数草稿 | 类型、单位、目标、边界和冲突校验 | 合法配置或补问项 |
| plan | 合法目标 | 生成受支持步骤与依赖 | 带版本的执行计划 |
| policy | 工具、参数与授权 | allow / ask / deny | 策略决定 |
| dispatch | 获准提案 | 读取工具或创建持久任务 | ToolResult / task_id |
| observe | 工具事实 | 判断完成、需要下一步或人工处理 | 后续提案或结论 |
| summarize | 事实与证据 | 组织回答, 标明缺失 | 最终消息与引用 |
| memory_extract | 完成的对话与用户反馈 | 提炼长期记忆候选 | 异步记忆更新请求 |

这些是逻辑职责, 不是要求每次都调用九次模型. 明确表单输入可跳过 classify/extract; 规则校验不消耗模型; 简单聊天不创建测试任务.

RunState 最小字段: run_id、conversation_id、user_id、status、goal、intent、validated_params、plan_version、pending_interaction_id、tool_call_refs、task_refs、evidence_refs、budget_usage、checkpoint_version. 凭证内容不在状态中.

同一会话同一时刻只允许一个活跃修改上下文的 run. 用户追加消息先排队; 显式“停止”或“修改当前任务”走控制接口, 修改已审批参数会生成新版本并重新校验. 不把新消息直接混入正在执行的脚本.

Run 状态使用 CREATED / RUNNING / WAITING_INPUT / WAITING_APPROVAL / WAITING_AUTH / WAITING_TASK / COMPLETED / FAILED / CANCELLED / EXPIRED. 它与 Task 状态是不同枚举. 工具返回 task_id 后, 图保存 WAITING_TASK 和依赖引用, 释放模型连接; 主服务消费持久任务事件后按 run_id 与 checkpoint_version 唤醒图, 同一事件不得重复推进. 不通过无限轮询模型等待压测结束.

一个 run 可等待多个已批准任务. 必须依赖的任务按 DAG 顺序, 无依赖的任务在资源额度内并行. 单个任务失败时按计划的 fail_fast 或 collect_all 策略处理; 未配置策略先补问或使用经评审的领域固定规则, 不由完成顺序决定. 取消 run 会阻止新工具动作, 并对它拥有且尚未终止的任务发取消请求; 返回值区分“已请求取消”和“已确认全部停止”.

## 3. 模型能力适配

每个模型登记支持项: stream、tools、structured_output、vision、embedding、reasoning_summary、context_limit. 用实际请求验证, 不依据兼容 API 的名称推定能力.

- 必要能力缺失: 对应功能标记不可用, 不通过解析任意自然语言凑成可执行命令.
- 结构错误: 在限定次数内要求修正; 仍失败则结束为 MODEL_OUTPUT_INVALID.
- 限流/暂时不可用: 只对尚未产生副作用的模型请求做有上限退避, 受总时长和预算约束.
- 内容或工具不受支持: 明确原因, 不假造工具返回.
- 推理型模型: 页面展示计划、进度和可提供的推理摘要; 不承诺输出完整内部思维链.

工具调用是模型产生请求、应用执行并回传结果的协作流程. [Function calling 官方说明](https://developers.openai.com/api/docs/guides/function-calling)

## 4. 工具注册表

每个工具包含 name、version、input_schema、output_schema、effect_class、allowed_targets、timeout、idempotency_mode、runner_type、required_capabilities. 工具名称必须来自注册表, 不运行模型凭空生成的工具名.

| 工具示例 | 效果类型 | 执行方式 |
| --- | --- | --- |
| knowledge.search | 只读 | 异步数据库/检索调用 |
| documents.parse | 内部持久写入, 资源型 | 解析任务 |
| cases.generate | 生成产物 | Agent 流程 + 文件产物 |
| api_suite.run | 可能修改被测业务 | 专项任务, 按步骤识别副作用 |
| ui.inspect | 页面读取, 可能有页面加载副作用 | 隔离浏览器任务, 禁止任意点击 |
| ui.run | 业务操作 | 已审批脚本任务 |
| load.run | 持续负载与业务影响 | 必须明确目标与负载范围 |
| evaluation.run | 读目标 + 模型开销 | 持久批任务 |

ToolResult 分开记录 execution_status、business_verdict、data_ref、evidence_refs、error_code. pytest 断言失败可能是“执行完成, 测试失败”, 不能全部算工具故障.

## 5. Skill 复用方式

建议兼容 Agent Skills 的 SKILL.md 元信息与正文, 加上 references、scripts、assets 资源. 格式标准并不保证任意 Skill 在本平台可执行. [Agent Skills 规范](https://agentskills.io/specification)

导入流程: 检查包与路径 → 读取元信息 → 确认依赖和工具映射 → 审阅脚本 → 记录版本和内容哈希 → 激活. zip 路径穿越、符号链接逃逸、未知工具和不支持的依赖均拒绝或保持未激活.

运行流程: 先加载 description 做匹配 → 加载所选 Skill 正文 → 按需读取引用 → 经工具网关执行脚本. 不把全部 Skill 全文塞进每次提示词, 不因 Skill 写了 allowed-tools 就自动给权限.

平台单独保存 Skill 的 capabilities、文件哈希、工具映射、依赖与审核状态. 不向原有 SKILL.md 强塞非标准必填字段. 本轮不创建或编辑任何实际 Skill.

文档用例 Skill 需要声明输入为“规范化需求及流程结构”, 输出为“用例 schema + 来源引用”. OCR 是上游工具能力, Skill 不应把图片文字猜测成已确认事实.

## 6. Agent 与工作流怎么配合

Agent 决定进入哪个受支持流程、何时补问和如何解释; 工作流规定不能跳过的阶段, 例如校验、审批和证据归档. 不允许模型自由改写安全节点.

LangGraph 中断恢复可能重新执行节点前段, 所以副作用不能放在中断之前且没有幂等保护的位置. 检查点仅保存恢复状态, 不保证外部请求恰好执行一次. [中断语义](https://docs.langchain.com/oss/python/langgraph/interrupts)

## 7. 预算与停止

每次 run 必须绑定最大模型调用数、工具调用数、总时长、费用/Token 预算和检索轮数. 数值由容量评审确定, 缺少生产配置不得默认为无限.

达到上限时保留已有证据, 返回 BUDGET_EXCEEDED 与未完成项. 后续继续作为明确的新授权或新 run, 不自行无限循环.
