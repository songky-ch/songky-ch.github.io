---
category: Agent
contentType: 架构设计
outline: [2, 3]
---

# 05. 任务、执行器与恢复

[返回目录](./index.md)

## 1. 三种对象不能混为一谈

- Run: 一次 Agent 请求, 可以只聊天, 也可以等待多个 Task.
- Task: 一次可调度的专项工作, 例如解析文档、执行套件、运行评测.
- Attempt: Task 的某次执行尝试, 有独立进程标识、资源和证据.

任务恢复不等于继续旧进程, 也不等于重新发起全部业务请求. 每个可恢复步骤需要留下结果引用与副作用账本.

## 2. 统一任务状态

[![任务认领、执行、人工等待、停止与未知结果处理](/images/test-agent-wiki/04-task.svg)](/images/test-agent-wiki/04-task.svg)

图中 UNKNOWN 是重要的事实状态: 程序失联时, 无法证明业务请求没发生, 因此不能直接重试. 人工等待不占用运行槽位, 已开始的压测不能冻结后恢复为一次连续测试.

| 状态 | 含义 | 允许的下一状态 |
| --- | --- | --- |
| CREATED | 已持久化, 尚未通过预检 | WAITING_INPUT / WAITING_AUTH / WAITING_APPROVAL / QUEUED / REJECTED / FAILED / CANCELLED |
| WAITING_INPUT | 缺参数或需澄清 | CREATED / EXPIRED / CANCELLED |
| WAITING_AUTH | 需要有效目标凭证 | CREATED / EXPIRED / CANCELLED |
| WAITING_APPROVAL | 等待动作批准 | CREATED / REJECTED / EXPIRED / CANCELLED |
| QUEUED | 通过预检, 等待资源 | STARTING / CREATED(预检条件变化) / CANCELLED / EXPIRED |
| STARTING | 已认领, 创建执行环境 | RUNNING / FAILED / STOPPING / UNKNOWN |
| RUNNING | 执行中 | SUCCEEDED / FAILED / STOPPING / WAITING_INPUT / WAITING_AUTH / WAITING_APPROVAL / UNKNOWN |
| STOPPING | 正在终止进程树 | CANCELLED / TIMED_OUT / FAILED / UNKNOWN |
| UNKNOWN | 失联或外部副作用结果不明 | 经核对转 SUCCEEDED / FAILED / CANCELLED / TIMED_OUT, 或确认可安全恢复后转 CREATED 重新预检 |
| SUCCEEDED | 执行完整结束, 结果可判定 | 终态 |
| FAILED | 执行基础设施或不可恢复工具错误 | 终态 |
| CANCELLED | 已确认执行停止, 用户/退出触发 | 终态 |
| TIMED_OUT | 达截止时间且确认停止 | 终态 |
| REJECTED | 人工或策略拒绝 | 终态 |
| EXPIRED | 排队/等待有效期届满 | 终态 |

独立字段 verdict = PASS / FAIL / INCONCLUSIVE / NOT_APPLICABLE. 例如测试工具完整执行, 发现接口断言错误: status=SUCCEEDED, verdict=FAIL. 失败样本不因为模型报告生成成功就变成 PASS.

另有 completeness = complete / partial / none, 描述结果覆盖程度, 不是任务状态. report_status = pending / running / ready / failed, 描述解释报告的生成状态. 取消的评测可以有 partial 结果, 执行成功也可能报告解释失败.

RUNNING → WAITING_* 仅适用于能在步骤边界安全停住且已保存检查点的工作. 必须终止/释放该 attempt 的资源; 无法确认停止则转 UNKNOWN. 压测过程出现登录失效时先停止本次 attempt, 记录无效测试窗口, 不无缝续接原曲线.

## 3. 调度与数据库事实

建议主服务通过小事务认领 PostgreSQL 任务行, 写入 lease_owner、lease_until、attempt_id 和递增 fence_token. 行锁只在认领事务内持有, 不跨整个测试时长. PostgreSQL 的 SKIP LOCKED 可用于跳过已被认领的队列行, 不是一般业务查询的一致性方案. [官方 SELECT 文档](https://www.postgresql.org/docs/current/sql-select.html)

限额同时包括全局、用户、任务类型和目标系统. 同一目标压测默认互斥作为评审提案; 是否允许重叠必须显式配置. 单一主服务启动也要获取数据库调度锁, 防止误启动第二份实例.

任务状态、tool_call 账本、审计事件在同一个数据库事务里落库. LangGraph 检查点是单独的恢复结构: 节点重放时按 tool_call_id 查既有任务, 不重复创建. 不假设框架检查点和业务事务天然原子.

## 4. 子进程启动协议

1. 校验任务配置哈希、脚本哈希、工具版本、审批有效期、凭证状态和资源额度.
2. 创建唯一 attempt 与任务目录, 写入不含秘密的 ExecutionSpec.
3. 在已验证的 OS 隔离配置中启动 runner, 使用参数数组, 不拼 shell 字符串.
4. 建立受限控制/事件通道, 只传本任务临时凭证和文件引用.
5. runner 发出 READY, 主服务条件更新 STARTING → RUNNING.
6. 消费事件、心跳和产物清单; 输出量有上限, 防止管道阻塞与磁盘耗尽.
7. 验证退出状态、结果 schema、文件哈希和进程树清空, 再提交终态.

ExecutionSpec 包含 task_id、attempt_id、fence_token、runner_type/version、config_hash、script_hash、artifact_input_refs、credential_ref、deadline、resource_profile、allowed_targets. runner 不直接连接业务数据库, 也不读取主服务模型密钥.

Python 提供异步子进程 API; 超时和进程树清理仍需应用自己实现. [Python 子进程文档](https://docs.python.org/3/library/asyncio-subprocess.html)

## 5. 不使用 Docker 时如何隔离

建议的生产前提: 主服务以非 root 用户运行; runner 使用独立任务身份或动态用户、独立任务目录与 cgroup, 挂载/文件系统限制、进程限制和出站网络策略由受控 OS launcher 实施. 通过经过运维约束的 systemd 任务单元或等价内核隔离方式创建执行环境, 不授予主服务任意 sudo/systemd 管理权限.

这意味着“一个业务主服务”仍可有系统托管的短期任务进程; OS 管理器不是新增业务微服务. 狭窄 launcher 的允许参数和目录必须固定, 不能让模型指定系统单元属性.

同 UID 子进程通常可能读取同权限文件和其他秘密, 仅清空环境变量不够. AST 检查和脚本扫描也不是沙箱. 若 Linux 环境不能提供隔离, 生成脚本执行不通过生产验收, 不宣称“企业级安全执行已完成”.

## 6. 超时、取消与失败恢复

| 故障窗口 | 必须如何处理 |
| --- | --- |
| 保存任务后尚未启动即崩溃 | 任务仍可在重启后认领 |
| 已启动但 RUNNING 未落库 | 先按 attempt/unit 标识核对, 不启动第二份 |
| 心跳中断 | UNKNOWN + 停止/核对旧 attempt, 不能仅租约到期就重新执行 |
| 进程被 OOM 终止 | FAILED, 保存资源证据与部分输出 |
| 已发业务写请求但响应丢失 | 核对业务幂等键/查询结果, 不能盲重试 |
| 请求取消与成功同时到达 | 通过状态版本 CAS 定序; 成功先提交则返回已完成, 取消先提交则完成清理再终态 |
| TERM 后仍有浏览器后代 | 按 attempt cgroup 强制终止, 确认无遗留进程 |
| 结果生成但数据库暂不可用 | 保存受控结果清单, 停止新认领, 恢复后对账 |
| 退出码成功但报告缺失/损坏 | FAILED 或 INCONCLUSIVE, 不能按退出码判测试通过 |

fence_token 防止旧 attempt 写回覆盖新结果, **不保证旧进程不会继续访问被测系统**. 重派前必须确认旧进程停止, 或依赖目标系统支持的幂等机制. 无法证明则停在 UNKNOWN.

systemd 的 control-group 终止语义覆盖组内进程; 如果任务使用独立 unit, 主服务停止时需显式关联停止与启动对账, 不能假设另一个 unit 自动随父进程退出. [进程清理语义](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html)

## 7. 重启与人工等待

启动顺序: 校验数据库版本 → 获取调度锁 → 核对遗留 attempt → 恢复 WAITING_* → 开放新任务. UNKNOWN 尚未解决的目标不允许重叠执行.

安全可重试的读取、解析与纯计算可创建新 attempt. 业务写入、压测和 UI 操作默认要求核对与重新授权. 终态不可原地“重置”; 用户重跑创建新 task, 关联 previous_task_id.

## 8. 流式反馈独立于任务

客户端使用 SSE 接收有序事件, 断开连接不会取消任务. durable events 在 PostgreSQL 维护递增 seq. Token delta 可合并后持久化; 不保证每个网络包重放, 但保证可恢复的消息快照与最终消息.

重连发送 after_seq, 服务器补发可保留的事件; 超出保留窗口返回 reset_required 与当前快照. 慢客户端可丢弃可重建的进度快照, 不能丢失审批和终态. 事件先脱敏再持久化, 不传完整内部推理.
