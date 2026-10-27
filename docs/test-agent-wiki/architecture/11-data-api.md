---
category: Agent
contentType: 架构设计
outline: [2, 3]
---

# 11. 数据模型与 API 契约

[返回目录](./index.md)

本章为建议契约, 不是已经实现的 API 文档. 字段与路径在评审后进入真实 OpenAPI 和数据库迁移.

## 1. 主要实体

| 表/实体 | 关键字段 | 约束 |
| --- | --- | --- |
| users | id, company_subject, display_name, status | company_subject 唯一, 工号只是显示/映射字段 |
| platform_sessions | id_hash, user_id, expires_at, revoked_at | 不保存明文会话令牌 |
| target_credentials | id, user_id, target_id, ciphertext, key_version, expiry, status | 禁止返回 ciphertext 到模型/前端 |
| conversations/messages | id, owner_id, role, content, attachment_refs, version | 明确所有者和作用域 |
| agent_runs | id, conversation_id, state, checkpoint_ref, budget, versions | 同会话活跃 run 串行 |
| tool_calls | id, run_id, name, version, params_hash, effect_class, task_id | 稳定调用 ID 去重 |
| tasks | id, user_id, type, state, verdict, config, config_hash, version | 状态 CAS, config 不含秘密 |
| task_attempts | id, task_id, fence_token, lease, unit_ref, process_identity, result_ref | 旧 fence 不可覆盖结果 |
| task_steps | task_id, step_id, effect_key, state, result_ref | 步骤去重与副作用核对 |
| interactions | id, run_id/task_id, type, payload, expiry, decision, version | 决定一次有效 |
| approvals | id, interaction_id, action_hash, target_set, policy_version, expiry | 执行前绑定复核 |
| events | stream_id, seq, type, payload, created_at | (stream_id, seq) 唯一 |
| artifacts | id, owner_id/scope, task_id, relative_key, hash, type, sensitivity, retention | 不允许用户指定任意服务器路径 |
| knowledge_documents/versions | id, scope, source, hash, status, active_version | 部分入库版本不可见 |
| knowledge_chunks | id, version_id, text, source_location, embedding_version | 精确来源与权限过滤 |
| memory_records | id, owner/scope, kind, content, source, version, status | 来源、冲突与 tombstone |
| eval_datasets/samples | id, version, labels, rubric, split | 冻结验收版本 |
| eval_runs/observations/scores | run_id, sample_id, attempt, target_snapshot, score, scorer_version | 原始回答与评分分开 |
| skill_versions | id, name, hash, manifest, activation_status | 未激活包不可运行 |
| audit_events | actor, action, target, policy_result, before/after_hash, trace_id | 追加记录, 非防篡改保证 |

不是每张表都要首日创建. 按功能阶段交付, 但身份、任务、审批、事件、产物之间的引用从基础阶段保持稳定.

## 2. 实体关系

::: details 补充流程图源码 (Mermaid)

```text
erDiagram
    USER ||--o{ CONVERSATION : owns
    CONVERSATION ||--o{ AGENT_RUN : contains
    AGENT_RUN ||--o{ TOOL_CALL : proposes
    TOOL_CALL o|--o| TASK : dispatches
    USER ||--o{ TASK : owns
    TASK ||--o{ ATTEMPT : executes
    TASK ||--o{ INTERACTION : waits
    INTERACTION ||--o| APPROVAL : records
    TASK ||--o{ ARTIFACT : produces
    USER ||--o{ MEMORY : owns
    DOCUMENT ||--o{ DOCUMENT_VERSION : versions
    DOCUMENT_VERSION ||--o{ CHUNK : contains
    EVAL_RUN ||--o{ OBSERVATION : collects
    OBSERVATION ||--o{ SCORE : receives
```

:::

用户 ID 从认证上下文注入, 不能直接使用请求体里的 owner_id 授权. 共享项目知识的读取范围与个人会话分开. 文件下载、SSE、记忆检索、评测样本查询同样校验范围.

## 3. API 分组

| 方法与路径 | 职责 | 核心响应 |
| --- | --- | --- |
| POST /api/v1/auth/exchange | 使用获准且可验证的身份材料建立平台会话 | 用户摘要与会话状态, 具体协议待 Q01 |
| GET /api/v1/me | 当前身份和能力 | 用户与可用能力 |
| POST /api/v1/auth/logout | 撤销会话和相关授权 | 撤销/停止请求状态 |
| POST /api/v1/conversations | 新对话 | conversation_id |
| POST /api/v1/conversations/{id}/messages | 提交消息并启动 run | 202, run_id |
| GET /api/v1/runs/{id} | 运行快照 | state, pending_interactions |
| GET /api/v1/runs/{id}/events | SSE, 支持 after_seq | 事件流 |
| POST /api/v1/runs/{id}/cancel | 停止 Agent 后续动作 | 当前状态与取消请求 |
| POST /api/v1/tasks | 表单直接提交领域任务 | 202, task_id, state |
| GET /api/v1/tasks/{id} | 任务详情与结果 | state, verdict, completeness |
| GET /api/v1/tasks/{id}/events | 任务事件 | SSE |
| POST /api/v1/tasks/{id}/cancel | 幂等取消 | 当前状态 |
| POST /api/v1/interactions/{id}/responses | 补充/批准/拒绝 | 新版本或 409/410 |
| POST /api/v1/artifacts/uploads | 受限上传 | artifact_id, parse_status |
| GET /api/v1/artifacts/{id}/download | 授权下载 | 文件流 |
| POST /api/v1/knowledge/documents | 建立知识入库任务 | task_id, document_id |
| POST /api/v1/knowledge/search | 调试范围内检索 | 片段、来源与版本 |
| GET/PATCH/DELETE /api/v1/memories/{id} | 查看、纠正、忘记 | 记录或清除任务 |
| POST /api/v1/evaluations | 提交评测任务 | task_id, eval_run_id |
| GET /api/v1/evaluations/{id}/report | 评测报告 | 指标与分母、逐题链接 |
| GET /api/v1/capabilities | 工具/模型/执行器是否就绪 | supported / blocked + reason |

DELETE 代表用户在产品中明确要求删除, 不代表本轮调用这些接口. 身份材料 exchange 不能接受未经验证的任意工号, 也不承诺导入所有浏览器 Cookie.

## 4. 任务提交示例

以下 JSON 仅说明结构, 不可直接执行. target_id 为虚构标识, 数值不是批准的生产配置.

```json
{
  "task_type": "load_test",
  "target_id": "demo-test-query",
  "config_version": 1,
  "parameters": {
    "load_model": "constant_arrival_rate",
    "iteration_rate": 10,
    "rate_time_unit": "1s",
    "duration_seconds": 60,
    "max_vus": 20
  },
  "credential_ref": "credential-reference",
  "approval_mode": "manual"
}
```

API 应返回 WAITING_INPUT 或 WAITING_APPROVAL 等真实状态, 不能因 202 就展示“已开始发压”. 平台仍需检查场景、阈值、停止策略和请求映射.

## 5. 事件契约

```json
{
  "stream_id": "task-example",
  "seq": 42,
  "type": "interaction.required",
  "occurred_at": "2026-10-26T14:00:00Z",
  "task_id": "task-example",
  "attempt_id": null,
  "payload": {
    "interaction_id": "interaction-example",
    "interaction_type": "approve_action",
    "version": 1
  }
}
```

事件类型至少包括 message.delta、message.snapshot、plan.summary、tool.proposed、task.state_changed、task.progress、interaction.required、artifact.ready、run.completed、error. 不定义 thought.raw 事件. 相同 stream 的 seq 单调, 不依赖客户端时间排序.

## 6. 幂等、并发与错误

创建任务/消息接收 Idempotency-Key, 唯一范围为 user + route + key. 相同键相同请求返回原结果; 同键不同请求哈希返回 409. 有效期明确配置, 数据库唯一约束作最后保护.

更新使用 expected_version. 400/422 参数错误; 401 未登录/过期; 403 无权; 404 不可见资源; 409 版本或幂等冲突; 410 等待项过期; 429 限额; 503 必需依赖不可用. 错误体包含 code、message、request_id、retryable 和脱敏 details, 不暴露堆栈和秘密.

时间以 UTC 保存, Windows 按用户时区展示. 体积、页数、事件保留、并发和截止时间需要明确上限; 未设置上限不能默认为无限.

## 7. 文件与数据库一致性

文件先写临时位置 → 校验哈希 → 原子移动到受控路径 → 提交元数据. 崩溃产生的未引用文件由带保留窗口的清理任务识别. 元数据已提交但文件不可读时返回 artifact_unavailable, 不伪造下载.

备份必须包含数据库与对应文件版本. 仅恢复数据库而丢失报告/原文不是完整恢复.

## 8. 上下文与 Prompt 追踪补充契约

| 实体/扩展 | 建议字段 | 约束 |
| --- | --- | --- |
| context_summaries | id, run_id, scope, source_range/version/hash, schema_version, parent_id, content, status | 按来源版本 CAS 激活; 纠正/删除使派生项失效 |
| context_snapshots | id, run_id, model_call_id, selected_refs, omitted_reasons, token_usage, policy_version, redacted_artifact_ref | 保存输入清单与必要脱敏产物, 默认不全量复制敏感原文 |
| version_manifests | id, global/node_prompt_versions, tool_schema_versions, skill_versions, model_config_ref, context_policy_version, workflow_version | run 固定版本组合; 当前权限撤销仍实时生效 |
| model_calls | id, run_id, manifest_ref, context_snapshot_ref, status, usage, latency, error_code | 区分失败和未知计费, 不记录完整内部思维链 |
| agent_runs 扩展 | version_manifest_ref, context_snapshot_ref | 与原检查点引用并存, 不新建另一套状态 |

模板源文件在代码仓库, 数据库只保存运行所需版本清单和追踪引用. 小规模实施允许版本清单作为已有 run 的结构化字段, 无需为设计表格强制拆分数据库表. 具体物理结构在 P2 迁移评审确定.

这些数据先供内部诊断和评测, 不新增对所有用户开放的 Prompt 编辑或任意历史读取 API. 原有 run/task 接口继续提供状态; 补参、审批、取消仍使用既有接口. 新增错误原因 `CONTEXT_REQUIRED_TOO_LARGE`、`PROMPT_INPUT_INVALID` 映射为 run 失败原因和脱敏 error 事件, 不把已受理异步任务的失败伪装为初始 HTTP 成功完成.

日志/事件可记录 `context.compacted` 与 `model.call_completed`, 仅含引用、版本和计量. 事件仍按原 stream/seq 排序; 不向未获范围授权的客户端发送原始 Prompt、其他用户资料或凭证.
