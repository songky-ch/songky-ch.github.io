---
title: "美团 Agent 评测全览带读: 从四个模块到可运行双环"
category: AI 评测
contentType: 文档带读
---

# 美团 Agent 评测全览带读: 从四个模块到可运行双环

Agent (智能体, 能根据任务调用工具并执行动作的系统) 的评测, 需要同时检查业务结果、执行过程和评判标准. 本文沿美团原文的结构解释机制, 再用一个无需账号的合成练习把问题收集、判断、修复与回测串起来.

配套阅读: [开发与测试面试专题](../../interviews/ai-evaluation/meituan-agent-evaluation-overview.md).

## 学习目标与证据范围

学完能够把一个业务目标写成可检查的成功条件, 区分 Agent 缺陷、评判缺陷与观测缺口, 并解释为什么版本得分提高仍可能不能发布.

前置条件: 能阅读 Python 字典、条件分支与测试断言. 本文不要求评测平台或模型账号.

| 资料 | 本次实际读取范围 | 版本与限制 |
| --- | --- | --- |
| [用户提供的小红书笔记](https://www.xiaohongshu.com/explore/6ab23d9b000000003a0215bc) | 美团技术团队发布的标题及正文 | 页面标注编辑于 09-22, 未明确年份; 未逐张读取 7 张配图, 不把评论作为技术依据 |
| [美团《Agent 评测白皮书》系列01](https://tech.meituan.com/2026/09/10/Agent-Evaluation-White-Paper-01.html) | 综述、前言、一至八节的可提取文字 | 发布于 2026-09-10; 图像内的表格与成熟度细项未逐图核实; 未读取该系列其他篇章 |
| [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | 评判器类型、随机性指标、任务与环境设计相关段落 | 在线文档, 访问时内容; 用于补充指标定义与实践边界 |
| [OpenTelemetry: Traces](https://opentelemetry.io/docs/concepts/signals/traces/) | Trace、Span、上下文传播与关联定义 | 在线文档, 本页无固定发布版本; 未部署采集系统 |
| [Langfuse: Datasets](https://langfuse.com/docs/evaluation/experiments/datasets) | 数据集、版本与生产样本入集相关文字 | 2026-10-17 访问时的在线文档, 无固定版本; 未调用其接口 |

核查日期: 2026-10-17. 验证状态: Python 3.9.6 上已执行本地确定性合成练习. 没有运行真实 Agent、生产流量、模型裁判或线上实验. 本文代码、数据结构、图解和数值实验均为教学补充, 不代表美团内部实现或用户项目经历.

## 1. 阅读地图: 四个模块怎样连起来

原文位置: 第一节 1.2、1.4 与第七节. 原文以四个模块组织评测体系, 在问题归因与评测资产处连接 Agent 演进和评测演进两条 Loop (反馈循环). 这是一种职责划分, 不是统一的行业产品架构. [官方原文](https://tech.meituan.com/2026/09/10/Agent-Evaluation-White-Paper-01.html#_1-4-评测体系的构成).

![评测模块、共享样本与两条迭代循环](/images/meituan-agent-evaluation-overview/dual-loops.svg)

读图: 上半部分先收集运行证据和异常样本; 中间人工复核或规则检查; 下半部分分成修 Agent 与修评测两路, 汇入固定版本回测. 证据不足进入补采集路径, 不能直接等价成 Agent 失败. 蓝色与绿色两路可以同时发生.

下面的表把职责翻译成本文教学案例里的具体产物. 案例是“为 A 门店生成销售报告”, 与原文商家分析场景相近, 但数据和实现由本文重新构造.

| 模块 | 要回答的问题 | 本例应留下什么 |
| --- | --- | --- |
| 离线评测 | 这次改动是否破坏已知能力? | 同一任务、同一标准、同一销售快照上的版本对照 |
| 在线评测与监控 | 实际用户任务是否成功, 运行是否异常? | 报告完成判定、工具错误、耗时, 连同各自分母 |
| 样本挖掘与归因 | 哪个样本值得复查, 问题在哪一层? | 错误门店参数、缺失报告、误判标准或证据缺口 |
| 观测基建 | 能否还原实际执行的输入、动作与结果? | 门店参数、返回数据、报告产物、运行关联标识 |

这张表是实施映射, 不是四套必须分别建设的服务. 一个脚本、一份任务表与一套可追踪记录也能承担最小职责.

## 2. 先定义“办成了什么”, 再决定怎样打分

原文位置: 第二节 2.1.1、2.1.2. 其中的三元组和两类评测, 可以在本文案例中落实为 Task (有明确输入与成功标准的任务)、可验收产物和 Rubric (逐项评价标准). [原文定位](https://tech.meituan.com/2026/09/10/Agent-Evaluation-White-Paper-01.html#_2-1-1-评测集的构成).

教学任务的输入不是一句孤立的“做报告”, 还需要固定任务所依赖的事实:

```json
{
  "task_id": "sales-A",
  "input": {"shop": "A", "sales_snapshot": {"A": 100, "B": 9}},
  "expected_outcome": {"artifact": {"shop": "A", "sales": 100}},
  "rubric": {
    "tool_scope": "查询参数指向 A 门店",
    "artifact_exists": "报告产物存在",
    "artifact_correct": "产物门店为 A, 销售额为 100"
  }
}
```

这只是本文的 JSON (结构化数据表示格式) 契约, 不是某个平台的接口格式. 数值 100 来自合成销售快照, 真实系统应关联明确日期和口径的数据源.

### 端到端结果与过程证据各看什么

End-to-End / E2E (端到端) 检查用户要的报告是否实际生成、内容是否满足约束. 过程检查关注工具是否选对门店、输入和返回值是否正确、聚合过程是否保留了条件. 两者可能不一致:

- 工具返回成功, 但查的是 B 门店: 调用状态正常, 业务任务失败.
- 查询和聚合都正确, 最后没有报告: 过程前半段正确, 端到端失败.
- 用另一种合法顺序得到正确报告: 不应因顺序不同而扣分, 除非任务明确约束该顺序.

最后一点是教学边界: 过程检查应针对必要约束, 不把唯一示范轨迹当作唯一合法策略. 本例固定查询工具是为了让练习容易验收; 它不要求真实业务必须使用同一个工具.

### 资产用途与评测对象是两个维度

原文的评测对象区分与资产用途区分可以交叉. 例如错题集既能保存“产物没生成”的端到端任务, 也能保存“跨门店参数错传”的过程检查. 黄金样本用来对齐业务质量, 挑战样本用来探索困难边界; 它们都需要明确来源、标准和适用范围. 本例的五条合成样本只演示机制, 不能充当真实业务的黄金集.

## 3. 两条循环: 同一个样本可能要修两处

原文位置: 第四节 4.3. 原文要求归因后既检查 Agent, 也检查 Rubric, 防止系统只学会迎合存在偏差的评分器. [原文定位](https://tech.meituan.com/2026/09/10/Agent-Evaluation-White-Paper-01.html#_4-3-归因-从-这里出了问题-到-为什么出问题).

教学旧标准是“回复包含 `已完成` 即通过”. 它至少有两类问题:

| 可观察事实 | 旧标准结果 | 复核结果与去向 |
| --- | --- | --- |
| 回复“已完成”, 实际查错门店 | 通过 | Agent 的选参有错, 标准也漏检; 两路都要修 |
| 回复“已完成”, 但没有报告 | 通过 | 产物未交付, 同时是标准误放行 |
| 报告正确, 回复“报告已生成” | 失败 | 标准误拒绝, 无需强迫 Agent 改成固定措辞 |
| 缺失查询记录 | 可能通过 | 过程结论未知, 先恢复所需证据 |

误放行是 False Accept (错误地接受失败结果), 误拒绝是 False Reject (错误地拒绝正确结果). 它们必须相对独立复核的参考判定计算, 不能让评分器用自己的结果证明自己正确.

下面是教学伪代码, 不可直接运行. `review_evidence` 代表按业务事实复核, `revise_agent` 和 `revise_rubric` 分别对应两个修改流程, 并不是真实软件接口.

```python
for case in sampled_cases:
    review = review_evidence(case)
    if review.evidence_missing:
        collect_missing_evidence(case)
        continue
    if review.agent_defect:
        revise_agent(case)
    if review.judge_disagreement:
        revise_rubric(case)
    add_reviewed_case_to_versioned_dataset(case)
replay_versions_on_same_dataset_and_rubric()
```

“同一标准”很关键. 如果旧版 Agent 用旧标准、新版 Agent 用新标准, 分数改变混合了系统能力变化与尺子变化. 应先在同一批记录上对比两把尺子, 再用固定的新标准比较两个 Agent 版本. [Langfuse 数据集文档](https://langfuse.com/docs/evaluation/experiments/datasets#versioning)提供了数据版本与生产记录入集的对应概念; 本练习仅记录版本标识, 未接入该平台.

## 4. 观测如何支持归因, 特别是多轮会话

原文位置: 第五节. 观测应提供足够的执行证据, 支持定位与复现. 本文将 Trace (一次执行的关联记录) 和 Span (其中一个操作单元) 按 [OpenTelemetry 官方定义](https://opentelemetry.io/docs/concepts/signals/traces/#spans)解释, 不要求采集模型不可获得的内部思考.

![会话、执行与操作的关联层级](/images/meituan-agent-evaluation-overview/evidence-chain.svg)

读图: 一次跨轮任务用会话与任务标识串联, 每轮执行可以有独立追踪, 操作间保留父子关系. 第二轮的日期修正要沿着输入、工具参数和最终报告逐项检查. 图中标识为教学示意, 不是 OpenTelemetry 报文.

本文建议记录的最小教学字段如下, 字段选择来自检查需求:

| 字段或证据 | 用途 |
| --- | --- |
| `session_id`, `task_id`, `turn_id` | 区分会话、跨轮目标和具体轮次 |
| `trace_id`, `span_id`, `parent_span_id` | 关联某次执行和它的子操作; 实际接入时按协议格式生成 |
| 用户本轮输入、当前业务约束 | 判断新指令是否覆盖了旧条件 |
| 工具名、参数、结果、时间 | 区分选参错误、工具错误和后续使用错误 |
| 产物或最终状态的稳定引用 | 独立验证报告是否存在、内容是否正确 |
| Agent、数据、标准、环境版本 | 让版本对照可以解释和复现 |

多轮例子: 第一轮要求“上周销售”, 第二轮改成“改为本周, 仍看 A 店”. 只看第二轮最终回复, 无法确定是否保留门店并更新了日期. 应顺序检查: 接收到的会话约束 → 工具日期与门店 → 数据 → 报告. 若下游使用了错误日期, 再核对上游传入的信息, 才能区分状态传递、参数构造与工具处理的问题. 第一处观察到的错误是定位线索, 不自动等于最终根因.

跨服务使用 Context Propagation (上下文传播) 关联 Span; 异步或独立执行还可使用关联链接. 会话标识属于应用层组织方式, 不需要把整段长会话塞成单一 Trace. 这些是基于 OpenTelemetry 的教学设计, 不代表美团实际字段或架构.

证据不足的处理取决于检查项. 如果只缺过程记录, 但最终产物可独立验证, 可以报告“结果通过、过程未知”. 本例要求结果和过程都满足条件, 因而联合判定记为 `None`, 另报证据覆盖率. 真实环境只保存获准保留的必要数据, 不把原始用户记录带入公开练习.

## 5. 离线、在线与统计口径

### 固定回测条件, 避免因果混淆

原文第二节强调控制输入、标准和环境. 本例固定 `d1` 数据与 `r2` 标准, 只改变门店选择行为. 真实回测还要隔离每次试验的文件、数据库和缓存, 并记录模型、工具和知识版本. 若下游快照发生变化, 不能把分数变化直接归因于提示词修改. Anthropic 原文的 “Design the eval harness and graders” 也强调每次试验从干净环境开始. [补充来源](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

### 不把 pass rate、pass@k 和 pass^k 混用

美团 2.2 将重复试验与 Pass@k 放在同一条表述中. 实施时应采用明确数学定义: Trial (单次试验) 的成功占比是 Pass Rate (试验通过率); pass@k 表示 $k$ 次至少一次成功; pass^k 表示 $k$ 次全部成功. [Anthropic 对随机性的说明](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

仅在同一任务的各次试验独立且成功概率相同为 $p$ 的简化条件下:

$$
\mathrm{pass@}k = 1-(1-p)^k, \qquad \mathrm{pass}^{k}=p^k
$$

若 $p=0.75$, $k=3$, 三者分别为 75%、98.44%、42.19%. 这里是概率模型示例, 不是三个真实样本足以估计可靠性的结论. 重复使用同一缓存或共享故障会破坏独立性; 多种任务混合时应逐任务估计后按已声明权重汇总.

本练习是确定性回放, 重复运行不会产生新的独立模型试验, 不用它测量真实 pass@k.

### 在线验证要保留业务判定

原文第三节分别讨论线上质量与运行指标. 本文把线上操作翻译成以下待实施方案, 本次未实际执行:

- 影子模式: 复制真实请求到隔离执行环境, 验证真实输入下的质量; 有写副作用的工具必须隔离, 避免重复提交业务动作.
- A/B Test (随机分组对照实验): 在可比较的分组上检查业务收益与约束, 避免仅比较两段时间的平均分.
- 巡检: 周期运行少量代表性任务, 保存失败证据与分数变化.

工具接口全部返回成功, 并不能证明报告内容正确. 任务比例变化也能改变总成功率, 因此同时报告任务分层、样本量、质量判定与系统错误. 本文不规定通用上线阈值, 也不把得分提高等同于业务价值已被验证.

## 6. 实操: 一次回放同时检查 Agent 和尺子

环境: Python 3.9 或更新版本, 仅使用标准库, 不安装依赖、不访问网络. <a href="/examples/meituan-agent-evaluation-overview/practice.py" download>下载完整代码</a>, [查看本次完整运行结果](/examples/meituan-agent-evaluation-overview/practice-results.txt).

输入是脚本中的五种合成记录: 正常、查错门店、报告缺失、合法同义回复、过程证据缺失. `v2` 只修复查错门店, 保留其他问题, 这样可以观察回测是否诚实地保留未解决的风险.

1. 下载 `practice.py`, 阅读 `cases` 和两个版本的构造逻辑.
2. 在保存文件的目录运行:

```bash
python3 practice.py
```

3. 检查输出中的逐样本结论和两组汇总. 关键判定直接展示如下, 代码在完整练习中已执行:

```python
checks = {
    "tool_scope": record["tool"]["shop"] == "A",
    "artifact_exists": record["artifact"] is not None,
    "artifact_correct": record["artifact"] == {"shop": "A", "sales": 100},
}
verdict = all(checks.values())
```

这段逻辑只适用于本练习的窄数据契约. 真实报告必须解析实际产物并核对证据, 不能把 Agent 自报的字典当成已落盘事实. 完整脚本先处理证据缺失分支, 不会用上述片段访问缺失的工具记录.

### 本次已执行结果

| 指标 | v1 | v2 | 分母与解释 |
| --- | --- | --- | --- |
| 旧标准通过 | 3/4 | 3/4 | 只在四条证据完整记录中对照两把尺子 |
| 新标准联合通过 | 2/4 | 3/4 | 同一数据 d1、标准 r2; 门店问题已修复 |
| 所需证据完整 | 4/5 | 4/5 | 全部五条记录; 缺失一条过程证据 |
| 旧标准误放行数 | 2 | 1 | 相对合成参考判定的计数, 不是线上误判率 |
| 旧标准误拒绝数 | 1 | 1 | 合法同义回复仍被旧标准拒绝 |
| 示例发布门禁 | BLOCK | BLOCK | 本例要求五条均有证据且通过, 不是通用阈值 |

验收输出最后两行:

```text
IID illustration: pass rate=75.00%; pass@3=98.44%; pass^3=42.19%
Acceptance: scope error, missing artifact, rubric disagreement, unknown evidence and release gate verified.
```

IID (独立同分布) 只是最后一行概率算例的假设. 脚本中的断言同时核对逐样本结论、误判计数与门禁. 脚本退出码为 0 表示教学判定符合预设, 与输出中的 Agent 版本 `BLOCK` 不冲突.

### 最小练习与验收

- 在本地副本修复 `no_artifact` 的产物交付, 并相应修改预期断言. 保留缺失证据分支时应得到四条可判定样本全部通过、总覆盖仍为 4/5、门禁仍为 `BLOCK`.
- 再补回 `missing_trace` 的所需证据, 更新预期. 验收应为新标准 5/5、覆盖 5/5、门禁 `ALLOW`. 如果有任一缺口仍为 `ALLOW`, 检查是否误把未知样本排出了门禁分母.
- 添加“只修改报告措辞, 内容不变”的样本. 验收: 新标准判定不变; 旧标准可能变化, 说明它依赖无关表面特征.

上述扩展练习未替读者执行. 本次实测范围仅为下载代码的原始五种样本与两个版本.

## 7. 易混淆点与自测

| 现象 | 先查什么 | 不能直接下的结论 |
| --- | --- | --- |
| 离线高分, 线上质量低 | 输入分布、环境快照、标准和结果证据 | 直接认定模型变差 |
| 工具正常, 最终结果错 | 业务参数、返回值语义、聚合与产物 | 调用成功就算业务成功 |
| 人工与评分器分歧 | 独立复核依据、条目歧义、缺失证据 | 一律要求 Agent 迎合评分器 |
| 总分变化, 分层分数稳定 | 任务类型比例与汇总权重 | 一定是版本能力改变 |
| 同一失败连续出现 | 共享工具故障、残留状态、数据版本 | 多次结果就一定独立可信 |

自测 1: 旧标准和新标准分别评旧版与新版, 能证明新版更好吗? 参考答案: 不能, 版本与标准两个变量同时变化; 需要交叉复评或固定标准比较.

自测 2: 报告能验证, 但工具轨迹缺失, 是否必须判整个任务失败? 参考答案: 取决于任务契约. 可以分别报告结果通过与过程未知; 本练习的联合契约需要过程证据, 所以标未知并阻断示例门禁.

自测 3: 为什么“所有工具都正确”仍可能无法交付? 参考答案: 中间数据正确不保证最终报告存在、保存位置正确或内容合格. 需要独立验证最终状态.

## 术语表

| 英文名称与缩写 | 中文含义 | 本文具体作用 |
| --- | --- | --- |
| Agent | 智能体 | 被评测的工具执行与报告交付系统 |
| Loop | 反馈循环 | 区分修系统能力与校准评测标准的演进路径 |
| Task | 任务 | 固定输入、事实和成功条件的评测单元 |
| Rubric | 逐项评价标准 | 把门店、产物和内容要求写成检查项 |
| JSON | 结构化数据表示格式 | 表示教学任务契约与运行输出 |
| End-to-End / E2E | 端到端 | 验证用户目标和最终交付是否实现 |
| False Accept / False Reject | 误放行 / 误拒绝 | 分析旧标准相对参考判定的两类错误 |
| Trace / Span | 执行追踪 / 操作跨度 | 关联一次执行和其中的工具操作 |
| Context Propagation | 上下文传播 | 支持跨服务操作的关联 |
| Trial | 单次试验 | 区分一次执行与多次概率统计 |
| Pass Rate | 试验通过率 | 成功试验数除以相应试验总数 |
| pass@k / pass^k | k 次至少一次成功 / k 次全部成功 | 区分多次尝试能力与一致成功要求 |
| IID | 独立同分布 | 概率公式成立的简化假设 |
| A/B Test | 随机分组对照实验 | 在线检验业务影响, 本次未执行 |
| OpenTelemetry | 开放遥测规范与工具体系 | 追踪与跨度定义的补充来源 |
| Langfuse | 大模型应用观测与评测平台 | 数据资产与生产样本入集的补充来源, 本次未接入 |

## 参考资料

1. [小红书原始笔记: Agent评测怎么搭](https://www.xiaohongshu.com/explore/6ab23d9b000000003a0215bc). 只读取标题与正文, 未逐图带读.
2. [美团: 《Agent 评测白皮书》系列01](https://tech.meituan.com/2026/09/10/Agent-Evaluation-White-Paper-01.html). 重点位置: 1.2、1.4、2.1、2.2、第三至第五节与 FAQ.
3. [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents). 重点位置: Types of graders、How to think about non-determinism、Design the eval harness and graders.
4. [OpenTelemetry: Traces](https://opentelemetry.io/docs/concepts/signals/traces/). 重点位置: Context Propagation、Spans、Span Links.
5. [Langfuse: Datasets](https://langfuse.com/docs/evaluation/experiments/datasets). 重点位置: Versioning、Create items from production data.
