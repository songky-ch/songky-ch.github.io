---
title: "我的 Agent benchmark 设计: 任务、状态与证据"
category: AI 评测
contentType: 实践教程
pageClass: testing-notes
---

# 我的 Agent benchmark 设计: 任务、状态与证据

<p class="article-kicker">工作记录 · A3 · 设计思路与待验证方案</p>

我对 Agent 评测最困惑的地方之一, 是怎样把一批问题变成可以比较版本的 benchmark. 只有问题文本还不够: 同一个“昨天”, 如果执行日期、账号或数据快照不同, 结果就失去可比性.

我的设计从每条任务的条件开始, 固定允许行为、成功判据、执行方式和汇总口径. 我把 [A2 的调用测试](../agent/single-call-tool-testing.md)、[数据生命周期](../api-testing/api-data-lifecycle.md)和[异常模拟](../mock-testing/fault-sequences.md)连接起来, 分别处理查询、录入、澄清和拒绝.

> 这是待验证的 D4 评测方案. 单次请求最多派发一次业务工具且不重试. 任务规模、工具、数据和结果均为示例, 未交付完整 120 条任务文件, 未运行模型或形成公司实际 benchmark.

## 每条任务的执行条件

先看同一句“查昨天的发货量”. 如果一个账号只能看 SITE-A / CUSTOMER-X, 另一个账号能看全部客户, 如果一轮在 22 日执行、另一轮在 23 日执行, 这已经不是相同条件下的比较.

<figure><picture><source media="(max-width: 600px)" srcset="/images/agent-benchmark-design/task-mobile.svg"><img src="/images/agent-benchmark-design/task.svg" alt="任务记录由输入、初始状态、允许行为、预期结果和证据要求组成, 每次尝试基于同一版本任务启动独立环境, 输出轨迹与最终状态."></picture><figcaption>图 1. 任务定义在运行之前. Agent 的实际输出进入证据, 不能反过来成为参考答案.</figcaption></figure>

下面给一条完整的查询任务记录. 为了独立阅读, 将上一批的时钟和参数再次写出. `fixture`、`tool_script` 和 `policy_version` 都是本文的自定义字段, 不属于某个评测框架 API.

```json
{
  "task_id": "D4-SHIP-001",
  "family_id": "ship-yesterday-explicit-scope",
  "task_version": "1",
  "input": "查 SITE-A、CUSTOMER-X 昨天的光模块发货量",
  "history": [],
  "clock": "2026-10-22T10:00:00+08:00",
  "timezone": "Asia/Shanghai",
  "principal_profile": "reader_ax",
  "fixture": "shipments_snapshot_v1",
  "tool_script": "shipments_ok_v1",
  "policy_version": "single_dispatch_v1",
  "expected": {
    "route": "tool",
    "tool": "query_shipments",
    "arguments": {
      "site_id": "SITE-A", "customer_id": "CUSTOMER-X",
      "start": "2026-10-21T00:00:00+08:00",
      "end": "2026-10-22T00:00:00+08:00"
    },
    "dispatch_count": 1,
    "quantity": 12840,
    "unit": "只",
    "business_state_change": false
  },
  "evidence_required": ["decision", "dispatch", "tool_result", "answer", "state_check"]
}
```

`reader_ax` 的权限定义是只读 SITE-A / CUSTOMER-X. 工具脚本针对正确参数返回 12,840 只, 错参数会被调用断言发现, 不能对所有请求无条件认可. 数据快照、账号配置、脚本内容和工具目录还应有固定版本或内容摘要, 名字相同但内容被改掉也会破坏比较.

这些任务字段不应原样全部交给被测模型. 用户输入、允许的历史与当前时间是系统可见信息; `expected` 和测试侧评分条件保留在评测器一侧. 否则是在把答案塞进题目, 得到的高分没有解释力.

## 查询、写入与零调用任务的成功条件

下面是同一 D4 任务集中的四个相邻 demo. 每条都沿用单次派发约定, 但初始状态与成功条件不同:

| 任务 | 初始条件和输入 | 允许行为 | 成功证据 |
| --- | --- | --- | --- |
| 录入 | 有写权限; 本次独占标记无记录; 明确录入 A/X 在 10 月 21 日 09:20 的“复测异常” | 录入一次, 不追加查询动作 | 标记范围内恰有一条, 字段准确, 回答与实际编号一致 |
| 澄清 | 无历史对象; “查昨天的发货量” | 询问局点和客户, 零派发 | 澄清针对缺失信息, 没有虚构数量, 无业务写入 |
| 拒绝 | 只读账号请求录入, 字段齐全 | 说明权限不足, 零派发 | 拒绝与原因正确, 无新记录 |
| 超时处理 | 完整的发货查询, 工具脚本抛指定超时 | 派发一次后结束, 不重试 | 说明未取得结果, 没有伪造数量, 无业务写入 |

录入任务不应把服务端动态编号固定为某个字符串. 测试可从实际提交记录取得编号, 核对回答引用的是同一条记录; 业务字段和“恰好一条”的预期仍必须独立确定. 读取测试证据的状态检查属于评测器动作, 不计入 Agent 的业务工具预算, 也不回灌给 Agent 帮它补做任务.

超时处理用例通过, 表示它遵守了故障处理契约, 不表示用户已获得发货数量. 汇总时要把“正常业务完成”和“按约定处理失败”分组, 否则会把不同目标混在一个完成率里.

## 每次尝试的初始状态

一条任务重复运行一次叫一次尝试, 英文是 trial. 同一任务做三次, 仍是一个任务、三个尝试. [Agent 评测术语原文](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)区分任务、尝试、轨迹与环境结果, 这里用这个区分组织自己的示例方案.

<figure><picture><source media="(max-width: 600px)" srcset="/images/agent-benchmark-design/reset-mobile.svg"><img src="/images/agent-benchmark-design/reset.svg" alt="每次尝试独立准备数据、身份、历史、时钟和工具脚本, 执行一次请求后冻结证据再清理; 准备失败不进入执行, 清理失败单独记录且不抹去主结果."></picture><figcaption>图 2. 三次重复是三份独立起点. 清理属于收尾, 不应该先删数据再去验证写入结果.</figcaption></figure>

模拟环境中可为每次尝试生成独立数据命名空间. 真实测试环境则需要隔离账号、唯一数据标记和可核查的清理, 沿用 I4 的范围控制. 除了数据, 还要重建会话历史、缓存和 M3 的 `side_effect` 序列. 第一轮已经消耗过一次异常的替身, 不能直接拿给第二轮用.

下面只表达调度顺序. `prepare_isolated` 要创建上述独立条件, `capture_evidence` 要在清理前保存轨迹和业务状态, `cleanup_owned` 只处理本次数据. 都是示例抽象, 不是实际框架方法.

```python
# Python 3.9 风格教学伪代码, 不可直接运行.
for task in frozen_tasks:
    for trial_no in (1, 2, 3):
        env = None
        try:
            env = prepare_isolated(task, trial_no)
            answer = run_agent_once(task["input"], env)
            evidence = capture_evidence(env, answer)
            save_trial(task["task_id"], trial_no, evidence)
        except PreparationError as error:
            save_blocked(task["task_id"], trial_no, str(error))
        except Exception as error:
            save_incomplete(task["task_id"], trial_no, str(error))
        finally:
            if env is not None:
                save_cleanup_status(cleanup_owned(env))
```

这里规定 `prepare_isolated` 失败时由准备函数清理自己尚未交出的半成品; `cleanup_owned` 将清理异常转成独立状态, 不覆盖已经保存的主错误. 这两个接口契约省去了无关实现, 不能省去实际工程中的残留检查.

被测工具的超时脚本应由系统按约定转成可观察结果; 评测平台自身断连、没采集到结束事件, 则不能当作 Agent 的业务失败直接计分. 如果已有可靠证据表明越权写入, 即使其他证据缺失, 仍应记录该失败. 没有任何可靠判定依据的尝试才记为证据不足.

## 围绕风险组织任务集

用 120 条任务作一个可管理的起步规模示例, 并非通用最小标准. 每条只指定一个主分组以便计数, 同时可以有日期歧义、跨客户、写操作等多个风险标签.

| 主分组 | 总任务数 | 开发集 | 冻结评测集 | 要能区分的情况 |
| --- | ---: | ---: | ---: | --- |
| 结构化查询 | 40 | 28 | 12 | 生产/现网/发货, 时间与范围 |
| 录入 | 20 | 12 | 8 | 完整字段、正确对象、恰好一次 |
| 澄清 | 20 | 14 | 6 | 缺对象、歧义时间、复合诉求 |
| 拒绝 | 20 | 14 | 6 | 无权限、能力范围外 |
| 故障处理 | 20 | 12 | 8 | 超时、错误结构、失败表达 |
| 合计 | 120 | 80 | 40 | 分组和风险分开统计 |

<figure><picture><source media="(max-width: 600px)" srcset="/images/agent-benchmark-design/split-mobile.svg"><img src="/images/agent-benchmark-design/split.svg" alt="任务按语义家族分组, 同一家族的近义改写整体进入开发集或冻结集; 开发集80条用于调整, 冻结集40条用于比较, 不把改写副本分到两侧."></picture><figcaption>图 3. 按语义家族切分, 不能把“昨天发了多少”和“昨日发货数量”拆到两边, 再宣称测到了新问题.</figcaption></figure>

开发集用来查看失败、修改工具说明和提示词. 冻结集用于在固定条件下比较版本. 同一业务模板的近义改写、只换客户代号的副本应归在同一语义家族, 整体放在一边. 这是一项防止题目过度相似的方案设定, 不保证完全消除污染.

任务的参考答案也要复核. 两个人对“这个输入应该澄清还是直接查询”意见不同, 先找契约是否缺失, 不是让模型投票定规则. 如果确实允许多种路径, 就记录允许集合或结果约束, 不强行限制到唯一工具序列. 这份方案仍采用单次工具约定, 多步骤合法路径在 A5 展开.

若根据冻结集的具体失败持续调过系统, 这批题就参与了开发. 可以保留作回归集, 但下一次独立比较需要新的保留任务, 不能只改文件名继续说“从未见过”.

## 重复执行与结果汇总的分母

假设冻结集 40 条, 每条运行 3 次, 共计划 120 次尝试. 下面是另一份**合成结果**, 与 A2 的 100 条示例不是同一批数据:

| 每条任务三次中的通过次数 | 任务数 | 贡献的通过尝试 |
| --- | ---: | ---: |
| 3 次通过 | 28 | 84 |
| 2 次通过 | 6 | 12 |
| 1 次通过 | 2 | 2 |
| 0 次通过 | 4 | 0 |
| 合计 | 40 | 98 |

其余 22 次中, 18 次明确失败, 4 次证据不足. “0 次通过”不能直接读成“三次都明确失败”, 因为可能含证据不足.

<figure><picture><source media="(max-width: 600px)" srcset="/images/agent-benchmark-design/trials-mobile.svg"><img src="/images/agent-benchmark-design/trials.svg" alt="40条任务各重复3次共120次尝试, 98次通过、18次失败、4次证据不足; 三次全通过的任务28条, 至少通过一次的任务36条, 两种任务指标不同."></picture><figcaption>图 4. 尝试通过比例、至少一次成功和每次都成功, 回答的是三个不同问题.</figcaption></figure>

按计划尝试计, 已确认通过占比是 `98/120=81.67%`, 证据不足占 `4/120=3.33%`. 只看可判定尝试, 是 `98/116=84.48%`, 必须同时披露被排除的 4 次. 按任务计, 至少一次通过为 `36/40=90%`, 三次全通过为 `28/40=70%`. 不要把 90% 写成“单次请求成功率”, 更不要用“挑最好的一次”掩盖不稳定.

有限的三次重复也不能证明稳定性已充分验证. 这些指标仅描述本次任务与环境, 不能直接外推到全量用户请求. 温度设为零也不保证所有模型服务完全确定; 应保留采样参数及提供方能给出的版本信息, 对多个版本使用相同任务、状态和评分规则.

一份可复查的报告至少关联任务版本、系统版本、提示词/工具目录、模型标识、运行配置、每次尝试证据、分项评分和清理状态. 真实模型调用、工具替身、真实服务集成应分开标明, 不能混成同一种测试覆盖. 下一篇 [A4](rule-and-llm-graders.md)负责把证据变成分项判定, [A3 面试专题](../../interviews/ai-evaluation/agent-benchmark-design.md)帮助讲清任务集设计.

## 术语与依据

| 英文名称与缩写 | 中文含义 | 本篇具体作用 |
| --- | --- | --- |
| Benchmark / Task | 评测任务集 / 单项任务 | 固定比较范围和成功条件 |
| Trial | 一次尝试 | 同一任务的一次独立运行 |
| Fixture | 初始数据与条件 | 固定账号、数据、时钟等起点 |
| Trace / Outcome | 轨迹 / 环境结果 | 保存动作证据与最终业务状态 |
| Holdout / Leakage | 保留集 / 信息泄漏 | 防止用过于相似或已参与调试的题冒充独立评测 |
| Grader | 评分器 | 按约定解释本次尝试的证据 |

核查日期: 2026-10-22. 任务与尝试等术语参考 Anthropic 2026-01-09 的 [The structure of an evaluation](https://www.anthropic.com/research/demystifying-evals-for-ai-agents). 任务结构、分组、切分和数值是本文方案设定. 未执行模型、120 条任务或真实环境清理; 代码仅做静态语法检查.
