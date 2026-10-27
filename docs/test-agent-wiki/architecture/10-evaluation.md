---
category: Agent
contentType: 架构设计
outline: [2, 3]
---

# 10. 知识库与 Agent 评测

[返回目录](./index.md)

## 1. 评测是平台能力, 被评对象可以是自己

平台提供统一数据集、目标适配器、执行调度、评分与报告. 自有知识库和外部知识库都可接入. 评测自己不是禁止事项, 关键是参考答案、评分规则、运行条件与被测版本独立且可复现.

不采用同一次对话里“模型生成答案, 再问它是否满意”的做法证明质量. 生成式测试数据可作候选, 经过人工确认后进入版本化测试集. 独立裁判模型仍有偏差, 需要人工校准. [官方评测实践](https://developers.openai.com/api/docs/guides/evaluation-best-practices)

[![数据集冻结、目标调用、分层评分和人工校准](/images/test-agent-wiki/08-evaluation.svg)](/images/test-agent-wiki/08-evaluation.svg)

从冻结测试集开始. 检索评分、答案规则评分和模型裁判按可用证据分别执行, 不能让检索评分失败阻止保存答案表现. 缺失证据标记不可计算, 不记作零分或通过.

## 2. 目标适配器与可评边界

| 能力层 | 目标提供内容 | 可评内容 | 不应报告 |
| --- | --- | --- | --- |
| answer_only | 最终回答 | 正确性、拒答、延时 | 检索召回率、隐藏工具正确率 |
| answer_with_context | 回答、检索片段、引用 | 忠实度、引用、检索质量(有标注时) | 未提供的重排内部效果 |
| agent_trace | 工具调用、参数、事件、结果 | 工具与参数正确性、任务完成、策略遵守 | 无证据的内部推理质量 |
| corpus_access | 语料和版本可访问 | 离线标注、切分/检索诊断 | 没有实际调用的端到端表现 |

适配器声明 supports_contexts、supports_citations、supports_trace、supports_reset、supports_version、rate_limit. 接口响应转为统一 EvalObservation, 不用前端页面外观推断内部检索.

## 3. 数据集 schema 与治理

每条样本包含 sample_id、question、category、reference_answer/answer_rubric、relevant_document_ids、relevance_grades、reference_contexts、expected_tool_constraints、expected_outcome、source_version、annotator_status、difficulty、tags.

按需要填写, 没有检索标注的题不可算 Recall@K. 没有可确定答案的开放题用明确 rubric, 不强塞单一字符串精确匹配.

数据集划分为开发集与冻结验收集. 不用验收集反复调提示后再把相同结果当独立泛化证据. 覆盖正常问题、无答案、资料冲突、多跳、中文术语、过期知识、权限隔离、提示注入、缺参和工具失败.

Agent 评测的 memory_profile 固定为 empty 或指定快照. 评测运行禁用自动写长期记忆, 避免被测系统跨题泄漏答案. 若外部系统不能重置记忆, 报告明确不可控因素.

## 4. 指标定义

| 指标 | 计算对象与定义 | 前提 |
| --- | --- | --- |
| Recall@K | 前 K 中命中的相关文档数 / 已标注相关文档总数 | 相关集合足够完整, 文档/片段粒度固定 |
| Precision@K | 前 K 中相关项数 / 实际返回项数 | 记录不足 K 的情况, 本稿采用实际返回项分母 |
| MRR@K | 各题首个相关结果排名倒数的均值, 无命中为 0 | 相关性标注 |
| nDCG@K | 折损累计相关增益 / 理想排序增益 | 分级相关标签, 公式与实现版本固定 |
| answer correctness | 规则/人工/rubric 对业务正确性的判定 | 参考依据 |
| faithfulness | 回答中可核验陈述被提供证据支持的比例 | 检索上下文及陈述拆分规则 |
| citation precision | 引用确实支持对应陈述的比例 | 引用可定位 |
| citation completeness | 需要依据的陈述中已有有效引用的比例 | 待引用陈述定义 |
| appropriate abstention | 无答案/越权/证据不足时合理拒答比例 | 题目标签 |
| task success | 达到预期任务结果的样本比例 | 外部可观察判定 |
| tool/parameter correctness | 符合允许工具与参数约束的调用比例 | 可见轨迹和规则 |
| policy compliance | 未绕过审批/范围限制的运行比例 | 明确策略与事件证据 |
| operational metrics | 延时分位数、失败率、Token/成本、调用数 | 实际计量, 价格与币种来源明确 |

Recall 与 MRR 示例: 标注相关文档为 A、B, Top3 为 C、A、D, 则 Recall@3=1/2, Precision@3=1/3, reciprocal rank=1/2. 这是教学算例, 不是平台实测.

nDCG 使用 DCG@K = Σ(2^rel_i - 1)/log2(i+1), 再除以 IDCG@K. 无相关标签时 IDCG=0, 标记 N/A, 不硬设为满分.

## 5. 三类评分器

1. 规则评分器: schema、ID 命中、数值误差、工具约束、权限与状态, 能确定计算就不用模型替代.
2. 模型裁判: 语义正确性和证据支持, 输入问题、回答、证据、rubric, 输出结构化分项与依据.
3. 人工抽查: 校准裁判, 检查高风险和分歧样本, 不只抽成功样本.

裁判不能看到目标品牌/版本标签以减少偏见, 不把目标输出中的指令当评测指令. 目标和裁判的模型可不同, 同模型也必须独立调用与隔离上下文; 即使不同模型也不宣称无偏.

报告裁判与人工的一致率、分歧率及样本数; 对有序类别可考虑加权一致性指标, 具体方法按标签类型决定. 不凭很少样本宣布裁判可靠.

## 6. 评测任务执行

冻结 target_version、dataset_version、corpus/index_version、prompt_version、model_id、judge_version、metric_version、memory_profile、参数与随机性设置.

批任务按样本建立子记录, 支持限流、取消和安全重试. 评分请求失败不能重调被测系统再挑一个更好答案; 保留原 observation, 只重试评分. 被测调用失败则独立记录 execution_error.

聚合至少展示 total、completed、execution_error、judge_error、not_applicable 与 scored 数量. 各指标公布自己的分母. “成功样本上的质量”与“全量请求可靠性”分开, 不默默删除失败样本提高均分.

## 7. 不确定性与版本比较

样本质量指标报告样本数与适当置信区间, 比例可用 Wilson 区间, 均值/差值可用适当 bootstrap. Agent 多轮随机行为需要重复运行, 报告分布而非最好一次.

比较 A/B 时使用相同题集、知识版本、记忆条件和预算, 顺序随机化或交错避免时段影响. 同题配对比较, 不把完全不同样本集均值直接相减证明改进. 缺少可固定的外部版本时, 报告“时间窗口内观测”, 不称严格回归.

## 8. 失败与缺证据分支

| 条件 | 结果 |
| --- | --- |
| 没有相关文档标注 | 检索标签指标 N/A, 可继续答案评测 |
| 外部系统不返回上下文 | faithfulness/context 指标 N/A |
| 裁判输出不合法 | 限次修正, 仍失败记 judge_error |
| 目标返回空答案/超时 | 记录执行失败, 不丢样本 |
| 数据集与语料版本冲突 | 预检阻塞或明确分层, 不静默混用 |
| 外部系统不能重置状态 | 标注可复现性限制 |
| 人工与裁判分歧高 | 不使用该裁判作为发布门槛, 先校准 |
| 预算不足 | 保存已完成样本, completeness=partial, 不宣称整集完成 |

报告包括逐样本回答、可见上下文、评分理由、来源、错误、聚合、版本和复现条件. “总分”不是必要字段; 先展示有明确含义的指标, 权重若要合成必须经评审.
