---
title: "RAG、Agent 与混合评测: 流程、指标、框架和真实案例"
category: AI 评测
contentType: 技术对比
---

# RAG、Agent 与混合评测: 流程、指标、框架和真实案例

先看同一个退款请求. 如果系统只回答“这单能不能退”, 我们要查它有没有找全规则、有没有解释对. 如果系统还替用户办理退款, 就要继续查它操作的是哪张订单、退了多少钱、是否取得确认, 以及任务结束后的实际业务状态 (后文简称终态).

回答前先从资料里找证据, 叫检索增强生成 (RAG, Retrieval-Augmented Generation); 根据任务选择工具并检查结果, 是智能体 (Agent) 的工作方式. 两者可以组合. 所以本文先分别讲怎么评, 再把“找证据、做判断、执行动作、核验结果”接成一条完整评测链.

配套阅读: [开发与测试面试专题](../../interviews/ai-evaluation/rag-agent-evaluation.md). 配套资源: <a href="/examples/rag-agent-evaluation/evaluate.py" download>离线练习</a>、[合成输入](/examples/rag-agent-evaluation/cases.json)、[实际运行结果](/examples/rag-agent-evaluation/results.json).

## 1. 读完要能做什么, 哪些结果已经验证

读完后, 你应能拿一个真实任务, 写清输入和成功条件, 搭出可重复执行的评测步骤, 为每项指标说明证据和分母, 再根据失败记录决定改哪一步. 通用助手与垂直业务的差别, 会落实到数据、判据和环境, 而不只是换一组行业名词. 前置条件是能够阅读 Python 字典与条件分支, 了解检索、工具调用和软件测试的基本含义.

技术事实核查日期: **2026-10-18**. 本次讲解与图解更新于 **2026-10-19**, 保留原来源版本和练习运行记录; 没有将图文更新标作重新运行真实模型或完整基准. 框架能力以 2026-10-18 的官方资料快照为依据, “常见框架”指本文覆盖的代表性方案, 不代表市场份额排名. 本文没有运行真实模型、商业评测平台、在线用户实验或全部公开基准. 已执行部分仅是第 10 节的本地确定性练习, 环境为 Python 3.9.6, [运行元数据与文件摘要](/examples/rag-agent-evaluation/run-metadata.json)可复核. 公式推导、业务扩展、工程架构和合成样本均为教学设计, 与引用项目的原始实现分别说明.

来源与固定版本集中在[文末资料表](#_13-参考资料与阅读顺序). 下文图解均为教学补充, 用来展开原有机制, 不代表引用项目未公开的内部结构.

## 2. 先把三类评测放到同一张地图上

<picture>
  <source media="(max-width: 640px)" srcset="/images/rag-agent-evaluation/evaluation-map-mobile.svg" />
  <img src="/images/rag-agent-evaluation/evaluation-map.svg" alt="三类被测应用各自产生运行记录, 评判器独立持有真值并判定" />
</picture>

读图时先看被测应用做了什么. 只回答问题时, 沿着“资料 → 片段 → 回答”检查; 办理任务时, 还要沿着工具动作查到实际业务状态. 三类系统都把这次运行的记录交给评判器, 但参考答案和目标状态由评判器单独保管, 不进入被测应用. 混合系统多问一步: 找到的证据, 到底能不能支持这次动作?

动手实现时, 先分清下面五份工作由谁负责、交付什么, 再选工具. 例如退款金额对不对可以直接比对业务库; 规则是否真的支持回答, 可能还需要模型或专家来判断.

| 层 | 必须交付的内容 | 具体问题 |
| --- | --- | --- |
| 任务与数据层 | 问题、知识快照、初始状态、用户身份、可用工具、成功条件 | 任务是否可解? 哪些动作被允许? |
| 执行层 | 被测版本、环境重置、预算、重复试验、超时记录 | 两个版本是否在同一条件下运行? |
| 观测层 | 整次运行记录 (Trace)、单次操作记录 (Span)、检索片段、工具返回、终态 | 能否还原每个结论和动作的依据? |
| 判定层 | 代码规则、按评分细则判断语义的大模型 (LLM-as-a-Judge)、人工专家 | 能确定计算的用代码, 语义判断才交给裁判 |
| 分析与闭环层 | 按任务类型分组的指标、置信区间、失败证据、版本比较、回归样本 | 是产品退化、评判器误判, 还是观测不足? |

本框架是教学归纳. Anthropic 把一道任务 (task)、一次试验 (trial)、评分用的判定器 (grader)、运行记录 (transcript)、最终结果 (outcome) 和评测运行器 (evaluation harness) 分开定义. 这样就能区分“题目是什么”“这次具体怎样跑”“谁根据什么打分”. 同一道任务可以重复执行, 判定器分别读取运行记录或实际环境结果. **运行器是测量基础设施, 被测 Agent 的编排器是系统本身的一部分**, 比模型时也必须控制后者. [官方说明: The structure of an evaluation](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

### 2.1 先写“什么算成功”, 再写评分代码

全文使用同一个教学业务: “先查售后规则, 判断订单是否可退; 若用户确认且符合条件, 创建一次退款并告知结果”. 假设规则是签收 7 天内且商品未使用, 此规则完全是合成业务条件, 不是任何平台的真实政策.

- RAG 版本: 用户只问能不能退, 系统输出依据、适用条件与引用.
- Agent 版本: 规则作为确定性配置提供, 系统查询订单、获得必要确认并办理操作.
- 混合版本: 系统从版本化知识库检索规则, 将其与实时订单状态结合, 再选择和执行动作.

RAG 任务需要参考事实与证据; Agent 任务还需要初始状态、允许动作、终态断言; 混合任务需要增加证据与动作之间的依赖. 参考答案和目标终态只给评判器, 不能泄漏给被测系统.

### 2.2 怎样保证这次与上次测的是同一件事

每次实验记录数据集与分割版本、知识库原文和切分版本、检索/重排配置、提示词、模型标识与采样配置、工具契约、环境快照、用户模拟器、裁判模型与评分规则、运行预算、运行器版本. 尽量保存不可变标识和内容摘要, 不只记“最新版”. 随机种子便于排查, 但不能保证远程模型服务逐字重现.

## 3. RAG 评测: 从语料到可信回答

### 3.1 从同一份资料出发, 每一步都留下证据

不要只保存最终答案. 例如退款规则有两项条件, 先确认原文里都有, 再逐步查它们是否进入候选片段、重排结果和模型实际输入. 下图固定这同一个问题, 让丢失的位置直接可见.

<picture>
  <source media="(max-width: 640px)" srcset="/images/rag-agent-evaluation/rag-evidence-flow-mobile.svg" />
  <img src="/images/rag-agent-evaluation/rag-evidence-flow.svg" alt="A和B都存在于语料与检索结果, B在压缩装配阶段消失, 修改后从装配阶段重新执行" />
</picture>

从上往下追踪 A、B: 前三步都有, 第四步却只剩 A, 所以此例先查压缩或截断. 修复线回到上下文装配, 重新把 A、B 交给生成器, 然后重评本题. 如果原始解析结果就没有 B, 排查位置应更早, 不能照搬本图的结论. 图中 A、B 与丢失记录均为教学设定.

| 步骤 | 输入与操作 | 输出与验证 |
| --- | --- | --- |
| 1. 定义任务 | 确定是事实查询、多跳推理、表格计算还是开放研究; 规定回答粒度、时点、引用要求与拒答行为 | 任务契约; 领域专家确认问题在指定资料下可解 |
| 2. 固定语料 | 固定原文、权限、生效日期与解析结果; 保留页码、段落、表头、单位 | 可追溯语料快照; 验证正文与结构没有丢失 |
| 3. 建立评测集 | 从脱敏真实问题、专家题和合成题组成; 标注参考事实、相关证据、不可回答原因 | 样本及标注指南; 双人复核争议题 |
| 4. 划分数据 | 按文档、实体、时间或任务族分组, 避免相近改写分散到调优集与测试集 | 冻结留出集; 检查问题和证据泄漏 |
| 5. 独立测检索 | 对问题运行查询改写、词法/向量检索、融合、重排, 逐阶段记录结果 | Recall@k、nDCG@k 等, 同时报告 k 与 token 预算 |
| 6. 独立测生成 | 给生成器相同证据, 或给人工确认充分的 Oracle Context (理想证据上下文) | 检查模型能否正确利用充足证据, 将检索问题与生成问题分开 |
| 7. 测完整链路 | 输入真实检索结果, 生成答案和引用, 记录截断后的实际模型上下文 | 正确性、依据性、引用、拒答、耗时与费用 |
| 8. 校准判定器 | 用人工标注集检查裁判, 特别关注错误年份、单位、否定和无答案题 | 裁判混淆矩阵、分组误判及争议样本 |
| 9. 对照与回归 | 固定测试集比较候选版本, 分析最先损坏的阶段, 将线上新失败入回归集 | 有证据的修复结论, 再运行直接相关回归 |

步骤 5 的分阶段记录很关键: 检索候选集有答案, 重排后被挤掉, 是重排问题; 重排仍有答案, 上下文压缩时删掉关键条件, 是上下文构造问题. 只记录最终 `retrieved_contexts` 会漏掉这一区分. 同一答案藏在不同切分位置时, 应按“支持哪一个事实”的语义单位标注, 避免换 chunk (文本片段) 策略就让所有 ID 标签失效.

### 3.2 先问“漏了什么”, 再看指标分母

令问题为 q, 前 k 个检索结果为 Rₖ, 标注相关集合为 G, 生成答案为 a, 实际交给模型的上下文为 C. 相关性标签可以是二值或等级分, 所用定义必须写入报告. 下文 card(S) 表示集合 S 的元素个数, relᵢ 表示第 i 项的相关性等级.

| 指标 | 判定对象与证据 | 口径、局限 |
| --- | --- | --- |
| Recall@k (前 k 项召回率) | 是否找齐标注相关证据 | card(Rₖ ∩ G) / card(G). 未穷尽标注会低估新找到的有效证据; G 为空的题单独处理 |
| Precision@k (前 k 项精确率) | 前 k 项里有多少相关结果 | card(Rₖ ∩ G) / k, 此处约定实际返回 k 项; 返回不足 k 项时明确分母约定 |
| Hit@k (命中率) | 至少找到一条相关证据 | 1[ Rₖ ∩ G ≠ ∅ ], 多跳任务命中一条仍可能不够 |
| MRR@k (截断平均倒数排名) | 第一条相关证据出现得早不早 | 单题为 1 / r₍first₎, 前 k 未命中为 0, 再跨题平均; 无法表达全部证据是否找齐 |
| nDCG@k (归一化折损累计增益) | 高相关证据是否排在前面 | DCG@k = ∑ᵢ₌₁ᵏ (2^relᵢ − 1) / log₂(i + 1), 除以理想排序的 DCG; 理想值为 0 时声明处理方式 |
| Context Recall (上下文召回) | 参考答案中的事实是否能被上下文支持 | Ragas 的模型版按参考答案事实拆分, 分母是参考事实数, 不等于文档 Recall@k |
| Context Precision (上下文精确性) | 有用片段是否排在前面 | Ragas 的排序敏感口径见下文, 不能直接当普通 Precision@k |
| Faithfulness / Groundedness (忠实性 / 依据性) | 答案事实能否从实际上下文推出 | 支持的答案事实数 / 全部待核验答案事实数; 证明“有据”, 不证明来源本身真实、适用或最新 |
| Answer Correctness (答案正确性) | 是否符合独立参考事实 | 结构化字段、数值规则或语义裁判; 不等于相似度, 避免只用文字重合 |
| Answer Relevance (答案相关性) | 是否回应问题 | 能识别答非所问, 无法单独判断事实真伪 |
| Citation Precision / Recall (引用精确率 / 覆盖率) | 引用是否支持对应事实, 应引用事实是否被覆盖 | 本文定义: 有效事实-引用对 / 全部事实-引用对; 被有效引用支持的应引用事实 / 全部应引用事实 |
| Abstention (拒答) 指标 | 该拒答时是否拒答, 可答时是否误拒 | 分别统计无答案题误答率和可答题误拒率, 不把“全部拒答”当高质量 |
| Latency / Cost (耗时 / 费用) | 单任务资源 | p50、p95 耗时、超时率、输入输出 token 及实际计费; 裁判费用单列 |

其中 Citation Recall 也常称 citation completeness, 不同论文可能使用不同粒度, 本文口径是教学定义. 一个事实引用两个片段时, 对“事实-引用对”去重后计数, 覆盖率的事实只计一次. 空答案没有可核验事实时, Faithfulness 记为不适用并单独判拒答, 不机械设为 1.

Ragas 的排序口径为:

**CP@K = [∑ᵢ₌₁ᴷ (P@i × vᵢ)] / [∑ᵢ₌₁ᴷ vᵢ], 其中 vᵢ ∈ {0, 1}.**

若相关标签是 `[1, 0, 1]`, 普通 Precision@3 为 2/3, CP@3 为 (1 + 2/3) / 2 = 5/6. 两者高低并不矛盾, 测的是不同问题. 当没有相关项时, 按所用实现明确记录零分或不适用的约定, 不直接使用零分母公式. CP 分母只包含已检索结果中的相关项, 因而可能在漏掉关键证据时仍很高, 要搭配召回. Ragas 的无参考变体可能将生成答案当作相关性参照, 此时有遗漏的答案也会影响测量, 不能把它等同于独立金标准. [Context Precision 原文](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/).

Ragas 的 Context Recall 用“参考答案事实”作分母, Faithfulness 用“生成答案事实”作分母. 若参考需要解释 A、B、C, 系统只找到 A 并只回答 A, Faithfulness 可以为 1, Context Recall 只有约 1/3, 答案完整性仍失败. [Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/), [Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/).

<picture>
  <source media="(max-width: 640px)" srcset="/images/rag-agent-evaluation/rag-metric-coverage-mobile.svg" />
  <img src="/images/rag-agent-evaluation/rag-metric-coverage.svg" alt="参考需要A B C, 实际上下文和生成答案只有A, 上下文召回1/3而忠实性1" />
</picture>

先看三行事实, 再看下面两个分母. 上下文召回问“参考答案要求的三件事, 找到了几件”; 忠实性问“已经说出的这一件事, 有没有依据”. 所以图里一个是 1/3, 另一个是 1, 两项结果可以同时成立. 接下来还得检查回答是否完整, 不能只拿后一项满分作为通过依据.

TruLens 的 RAG Triad (RAG 三元评测) 从上下文相关、依据性、答案相关三个方向观察链路. 用它能组织诊断, 但还需独立真值、完整性、权限和时效检查, 高分不能作为绝对正确保证. [官方定义](https://www.trulens.org/getting_started/core_concepts/rag_triad/).

### 3.3 数据怎样做才有区分度

| 场景分组 | 必须放入的样本 | 期待暴露的问题 |
| --- | --- | --- |
| 常规可答 | 单文档事实、术语别名、中文口语问法 | 基础覆盖与语义匹配 |
| 多证据 | 条件在不同段落、跨文档比较、表格与脚注结合 | 只命中一段但误以为完整 |
| 时效冲突 | 新旧规则同时存在, 问题带历史日期 | 检索到相关但已失效内容 |
| 无答案 | 文档没有该事实、用户前提错误 | 编造与过度拒答 |
| 干扰与攻击 | 相似实体、错误单位、文档内夹带指令 | 噪声敏感、上下文注入 |
| 权限 | 相同问题, 不同租户和身份 | 越权召回与跨用户信息混用 |

合成题适合扩大覆盖, 但出题模型可能偏向原文措辞和显式事实. 应混入真实问题、人工难例与无法回答题, 由独立人员复核. 给检索器的语料不能夹带参考答案文件, 给模型的样本不能包含裁判标签.

### 3.4 真实案例一: CRAG 的通用知识问答

CRAG 是真实公开基准, 覆盖多个领域、不同问题类型、长尾实体与时效性, 并提供模拟网页/知识图谱接口. 论文报告 4,409 个问答对. 它适合检验“广泛问题能否得到可靠事实答案”, 与企业单一知识库的分布并不相同. [论文](https://arxiv.org/abs/2406.04744), [仓库说明](https://github.com/facebookresearch/CRAG/tree/ad1518887dd4d9ebcd7de95388c7a62751e7705c).

可复用的实施流程是: 固定题集、检索输入与查询时点 → 执行检索和回答 → 将答案与独立真值匹配或交给裁判 → 区分正确、缺答与错误 → 按领域、时效和问题类型分组. 该快照自动评分说明采用正确 +1、缺答 0、错误 -1, 因而汇总可写为 (N_correct − N_wrong) / N. 它显式惩罚自信错误; 仍需同时报告缺答率, 防止通过过度拒答美化错误率. [README: Evaluation Metrics](https://github.com/facebookresearch/CRAG/blob/ad1518887dd4d9ebcd7de95388c7a62751e7705c/README.md#-evaluation-metrics).

源码定位: `generate_predictions` 将 `answer` 从模型输入批次移除; `evaluate_predictions` 汇总 `score`、`accuracy`、`hallucination` 与 `missing`. 这是评测真值隔离与分指标汇报的具体实现例子. 本次仅静态读取, 该快照脚本还存在入口实参数量与函数签名不一致等问题, 因此不将原样启动命令标成已验证可运行. [固定版本源码](https://github.com/facebookresearch/CRAG/blob/ad1518887dd4d9ebcd7de95388c7a62751e7705c/local_evaluation.py).

### 3.5 真实案例二: FinanceBench 的金融文档问答

FinanceBench 公开仓库提供 150 条带答案和证据的样本; 发布者说明完整研究集合为 10,231 题, 不能把两个规模混用. 已核实首条 `financebench_id_03029`: 问 3M 2018 财年的资本支出, 单位是百万美元; 参考值为 1577, 来源标识是 `3M_2018_10K`, JSON 中证据页索引为 59, 提取页脚显示 60. 此处是数据集参考答案, 并非本次重新审计年报. [公开样本](https://github.com/patronus-ai/financebench/blob/cc39aeb4afdf33909ee1412188bf89035950c2eb/data/financebench_open_source.jsonl), [发布者范围说明](https://docs.patronus.ai/docs/research_and_differentiators/financebench).

围绕这条真实题可以落地四层检查: 检索是否命中正确公司、年份和报表 → 表格解析是否保留年份列和单位 → 答案数值与单位是否一致 → 引用是否指向支持该数字的页. 如果回答“1577 十亿美元”, 文本相似度可能很高, 数值规范化后的事实判定必须失败. 如果命中同一报表的 2017 列, 文档命中率通过也不代表事实召回通过. 这说明垂直 RAG 要把领域实体、时间和计量口径纳入标签, 通用相似度分数不够.

## 4. Agent 评测: 从多轮动作到实际结果

### 4.1 一次任务从哪里开始, 到哪里才算结束

先选一条能成功办理的任务, 从用户请求一直跟到业务库. 谁发起查询、谁确认、谁真正改变状态, 都要分清. 下图只画正常退款路径, 拒绝、补查和等待确认的分支在图 05 展开.

<picture>
  <source media="(max-width: 640px)" srcset="/images/rag-agent-evaluation/agent-run-sequence-mobile.svg" />
  <img src="/images/rag-agent-evaluation/agent-run-sequence.svg" alt="正常退款中用户确认早于写入, 工具返回后智能体告知, 会话结束后评测器独立核验业务状态" />
</picture>

沿实线走一遍: 用户请求 O-1 退款, 智能体先查询条件和金额, 再请求确认, 取得确认后才提交写操作. 工具返回执行结果后, 它据此告知用户. 底部虚线连到评测器自己的查库步骤: 即使前面说“完成”, 也要另查 O-1 的金额、其他订单和退款次数. 时序记录还要证明确认发生在写入之前.

| 步骤 | 操作 | 关键验证 |
| --- | --- | --- |
| 1. 定义任务契约 | 写用户目标、可用信息、允许动作、确认条件、最终状态与禁止副作用 | 确认“做什么”和“不能怎样做”都可检查 |
| 2. 构建环境 | 固定数据库、文件、浏览器或服务沙箱, 每次试验从同一快照重置 | 并行任务不共享可变状态, 上轮产物不会污染下轮 |
| 3. 设计用户交互 | 单轮固定输入, 或多轮用户模拟器/人工脚本; 隐藏目标只给模拟用户 | 用户不能因看到答案或环境真值而暗示 Agent |
| 4. 运行被测系统 | 固定模型、提示词、工具、最大步骤、时间与费用预算 | 记录停止原因, 区分正常完成、超时、模型或工具错误 |
| 5. 收集证据 | 记录消息、调用参数、工具返回、动作时间、前后状态与产物 | 同一调用能通过 ID 关联请求、返回和状态变化 |
| 6. 多层判定 | 终态检查、必要流程约束、工具参数规则、输出语义与交互质量 | “说已完成”不能代替数据库或产物证据 |
| 7. 重复与压力测试 | 每题多次从干净快照运行, 注入工具超时、歧义与状态竞争 | 统计稳定性、恢复行为和重复副作用 |
| 8. 失败归因与回归 | 判定首个有证据的失败阶段, 复核环境和裁判问题 | 修复后重跑同任务及相关风险任务组 |

Trace 收集的是可观测消息和动作, 不要求读取模型隐藏思维链. “规划质量”如果只能从外部行为推断, 应明确推断依据, 不把模型自述计划当作已经正确执行.

### 4.2 任务完成、动作正确和资源开销分别测

| 指标 | 本文操作定义 | 重要边界 |
| --- | --- | --- |
| Task Success Rate (任务成功率) | 符合完整任务契约的试验数 / 所有计划试验数 | 超时等产品失败计入分母; 基础设施未能开始的任务另列覆盖缺口, 不静默丢弃 |
| Outcome Accuracy (终态正确率) | 实际数据库/文件/产物通过目标断言的比例 | 应同时检查不该变化的字段、重复动作与副作用 |
| Tool Selection (工具选择) | 与必要或允许调用相符的情况 | 参考路径可以不唯一, 需要区分禁止工具和可选工具 |
| Argument Correctness (参数正确性) | 订单、金额、币种、身份等业务参数正确的调用数 / 可判定调用数 | JSON Schema (结构化数据约束) 通过只证明形状正确 |
| Tool Execution Success (工具执行成功率) | 工具明确成功的调用 / 工具调用数 | 调用了错误订单的 API 也可能技术执行成功 |
| Constraint Compliance (约束遵守) | 符合确认、顺序、权限与业务规则的试验比例 | 高风险违规单列, 不用好文风抵消 |
| Conversation Quality (对话质量) | 澄清是否必要、用户目标是否正确理解、告知是否清楚 | 用明确评分项和专家校准, 不能只凭最终一句话 |
| Recovery (恢复能力) | 可恢复故障后仍正确达成目标且无副作用的比例 | 故障注入类型和恢复预算必须固定 |
| Efficiency (效率) | 成功任务的步骤、工具数、费用分布; 另列所有任务耗费 | 正确澄清和必要重试不应机械扣分 |
| Reliability (重复可靠性) | 同一任务多次执行的成功情况 | 指标的 k 和重复次数一起报告, 见下文 |

最终状态只是必要证据之一. 即使最终退款金额正确, “先扣两次再冲回一次”可能违反任务契约; 反过来, 对一个应该拒绝的请求, 正确终态可能是数据库完全不变并解释原因. 因此要按任务规定哪些时序是硬约束, 其余合理路径保留自由度.

DeepEval 的工具正确性支持参考工具集合比较, 参数/返回值与顺序需要相应配置; Task Completion 是另一类判定. 不应看到工具名匹配就认定业务正确. [Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness), [Task Completion](https://deepeval.com/docs/metrics-task-completion).

### 4.3 轨迹怎样比较才不会误杀正确方案

AgentEvals 支持 `strict`、`unordered`、`subset` 与 `superset`. 前者检查固定顺序, 无序匹配放宽顺序; 子集模式限制实际调用不超出参考, 超集模式要求至少包含参考调用. 参数如何比较还要单独配置. 使用全量严格轨迹前必须确认只有这一条路径合法. [官方文档](https://docs.langchain.com/langsmith/trajectory-evals).

实际业务通常更适合“局部顺序 + 终态”: 退款前必须取得有效确认, 但查询订单与读取政策可以交换先后; 只要求证据在决策之前可用. 可以把必要事件构成 DAG (Directed Acyclic Graph, 有向无环依赖图), 检查依赖边和终态, 而不是把所有调用锁成一条列表. 这是本文的工程设计, 并非声称所有框架自动支持该判定.

### 4.4 pass@k 和 pass^k 必须分开

pass@k (k 次中至少一次成功) 衡量多次尝试能否找到解; pass^k (k 次全部成功) 衡量一致性. 假设单题每次成功独立且概率固定为 p, 则:

**pass@k = 1 − (1 − p)ᵏ; pass^k = pᵏ.**

当 p = 0.8, k = 3 时, 两者分别是 0.992 与 0.512. 实际数据里题目难度不同, 应先逐题计算再平均; 不能简单拿整体平均成功率取 k 次方. 若同一任务 n 次中成功 c 次, 且 n ≥ k, 可用以下组合估计量, 约定不足 k 个成功或失败时相应组合数为 0:

**估计 pass@k = 1 − C(n − c, k) / C(n, k); 估计 pass^k = C(c, k) / C(n, k).**

其中 C(n, k) 表示从 n 次试验中选择 k 次的组合数.

它们需要独立重置且可比的试验协议. 多次试验共享记忆或沿用上一次修复结果时, 测量对象已改变. 生产里带反馈的自动重试应作为一个完整策略另测, 记录重试成本与重复副作用. [Anthropic: Understanding non-determinism](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), [τ-bench 论文](https://arxiv.org/abs/2406.12045).

### 4.5 真实案例三: τ-bench 的业务操作

原始 τ-bench 包含零售与航空服务, 模拟用户与 Agent 多轮交互, 工具连接业务数据库, 同时存在领域规则. 一次试验要从固定状态开始, 完成对话后核验结果. 它把“能否说出合理答案”推进到“能否持续正确办理任务”. [项目说明](https://github.com/sierra-research/tau-bench/tree/59a200c6d575d595120f1cb70fea53cef0632f6b), [论文](https://arxiv.org/abs/2406.12045).

所读取的后续 τ² 仓库评测文档明确区分 `evaluation_criteria.actions` 与 `reward_basis`: 参考动作可被回放来构造目标数据库状态, 不意味着被测 Agent 必须逐步照抄. 当奖励依据是 DB 和 COMMUNICATE 时, 终态和告知检查共同决定奖励; 只有配置 ACTION 时才额外要求匹配参考动作. 这里引用的是**指定提交的文档行为**, 不能把不同版本分数直接混为同一榜单. [固定版本评测规范](https://github.com/sierra-research/tau2-bench/blob/96a3ef92329baf908ffe9dfe188cea34e8701d2a/docs/evaluation.md).

实现上的启发是把“参考解用于生成真值”与“参考解是唯一合法路径”分开. 同时, 基准自动奖励覆盖什么就只能证明什么; 若业务另有权限、全程确认和幂等要求, 应增设独立断言, 不能推断 DB 得分高就证明全程合规.

### 4.6 真实案例四: GAIA 与 SWE-bench

GAIA 提供多步骤通用助手问题, 涉及浏览、文件与不同能力组合; 原论文摘要报告 466 道题. 它适合检验开放任务中获取信息、组织工具和得到答案的能力, 对会改变外部状态的业务约束仍需补充专用测试. [GAIA 原论文](https://arxiv.org/abs/2311.12983).

SWE-bench 则把真实仓库 issue 转为补丁任务, 在固定环境中应用补丁并运行测试. 落地顺序是固定仓库版本 → Agent 生成补丁 → 干净容器应用补丁 → 运行修复相关测试和保留行为测试 → 汇总是否解决. Agent 的“测试通过”自述无法代替判题器执行. 它是软件工程垂直任务, 在工具规划维度可借鉴到通用 Agent, 不能当作所有领域 Agent 能力的完整代表. [SWE-bench 官方评测指南](https://www.swebench.com/SWE-bench/guides/evaluation/).

## 5. RAG 与 Agent 评测的同异点

| 统一维度 | RAG | Agent | 混合后的要求 |
| --- | --- | --- | --- |
| 共同目标 | 用户问题正确解决 | 用户任务正确完成 | 问答与动作都符合目标 |
| 核心对象 | 检索、上下文、答案与引用 | 多轮决策、工具、状态与产物 | 再检查知识到动作的依赖 |
| 金标准 | 参考事实、相关证据、无答案标签 | 终态断言、必要约束、可接受轨迹 | 证据/规则/动作映射 |
| 环境 | 语料与索引快照 | 状态沙箱、工具、用户模拟器 | 知识时点与业务状态同时冻结 |
| 观察粒度 | 问题、检索阶段、答案事实 | 会话、试验、调用、状态变化 | 每次检索绑定到后续决策 |
| 随机性 | 查询改写、采样、裁判 | 额外包含路径、工具与用户交互 | 各来源随机性分别控制 |
| 典型假阳性 | 答案有据但依据过期 | 自述成功但实际未完成 | 文本正确但操作错对象 |
| 典型误判 | 换切分后有效证据 ID 不一致 | 合法不同路径被严格匹配判错 | 只按局部高分判端到端成功 |
| 高价值归因 | 候选召回、重排、压缩、生成 | 理解、决策、参数、执行、状态 | 最早失效的依赖边 |
| 生产反馈 | 新知识、新问题与拒答漂移 | 业务变化、工具变化、用户目标变化 | 新规则和工具状态共同回归 |

共同方法包括分布代表性、真值隔离、版本冻结、代码/模型/人工组合、裁判校准、重复试验与线上闭环. 区别主要来自被测系统能否改变状态、能否动态选择下一步以及是否存在长程依赖, 不来自“RAG 永远单轮, Agent 永远多轮”这种划分.

## 6. RAG + Agent 混合评测: 证据怎样变成正确动作

### 6.1 先区分“研究后回答”和“查规则后办事”

有的系统会自己决定查什么、何时补查, 最后写一份报告. 这类由智能体控制的检索问答, 常称 Agentic RAG, 重点是资料是否充分、来源是否可靠、何时停止搜索. 另一类系统查完规则后还要退款或改签, 可以称为基于知识证据的行动智能体 (Knowledge-grounded Agent), 除了回答质量, 还得核对授权、实际状态和额外副作用.

<picture>
  <source media="(max-width: 640px)" srcset="/images/rag-agent-evaluation/evidence-to-action-mobile.svg" />
  <img src="/images/rag-agent-evaluation/evidence-to-action.svg" alt="混合流程中补查回流、资料不足停止、不符合条件拒绝、等待确认和执行后的三种评测结论" />
</picture>

从顶部的“规则证据 + 实时订单”开始走. 如果资料不足但还有预算, 就先补查或澄清, 补齐后回到资料判断; 预算用尽仍无法确认, 就停止执行并说明缺口. 资料齐全后再看订单是否符合规则, 不符合时解释原因且不写入. 符合条件也还不能直接退款, 必须取得有效确认和授权. 最后核验实际状态、额外副作用与结果告知. 图里的“通过、失败、不可判定”是评测结论, 与被测系统自己说“完成了”分开.

### 6.2 把输入、环境和评分答案分开存

以下是**教学 JSON 契约**, 不是某个 SDK 的官方格式. `public_input` 交给被测系统, 其余内容由环境或判定器持有. 真实运行时还应保留检索文本与状态快照的受控存储入口, 公开报告不披露私有内容.

```json
{
  "case_id": "refund-eligible-01",
  "public_input": "请根据售后规则, 判断订单 O-1 能否退款, 符合条件时在我确认后办理.",
  "environment": {
    "clock": "2026-10-18T09:00:00+08:00",
    "kb_version": "policy-v3",
    "db_snapshot": "orders-v12",
    "user_id": "U-1"
  },
  "evaluator_only": {
    "required_evidence": ["window-7d", "unused"],
    "expected_decision": "refund",
    "expected_state": {"order_id": "O-1", "refund_cents": 10000},
    "constraints": ["confirm_before_write", "no_duplicate_refund"]
  }
}
```

一份混合任务的完整运行记录至少包含 `case_id`、`trial_id`、`trace_id`、`span_id`、父子关系、时间戳、检索 query、候选与最终证据、证据版本与生效时段、可观察的决策结果及其证据引用、工具参数、工具返回、状态前后差异和最终输出. 如果业务允许缓存, 也要记录缓存证据和命中信息, 不能把“没有本轮检索”直接等同于“无证据”.

### 6.3 先单测每一步, 再查交接, 最后跑完整任务

1. **组件层**: 给固定问题测检索, 给固定证据测规则判断, 给固定决策测参数构造, 给固定调用测工具状态变化.
2. **交接层**: 检索证据是否包含决策所需条件; 决策引用是否真的支持该动作; 金额、对象和时间是否正确传入工具; 工具返回是否正确反馈给最终回答.
3. **完整任务层**: 从用户输入开始运行真实循环, 动态决定查什么、何时澄清、何时停止、是否执行动作, 最后核验任务目标和全程约束.

三层都需要, 但作用不同. 组件成功不能直接推出整体成功; 完整任务成功也可能掩盖偶然猜中答案、遗漏证据或产生未察觉副作用.

### 6.4 怎样把各项检查合成任务结论

| 维度 | 检查项 | 证据和分母 |
| --- | --- | --- |
| 检索 | 多跳事实覆盖、适用版本、权限过滤 | 必需事实或合规证据集合, 按需要检索的任务计算 |
| 决策 | 规则判断正确、证据真正支持动作 | 正确且有足够证据支撑的决策 / 可核验决策 |
| 参数 | 订单、金额、币种、受益人等正确 | 正确业务参数的调用 / 可核验调用 |
| 执行 | 终态和副作用符合契约 | 通过状态与不变量断言的试验 / 全部计划试验 |
| 回答 | 事实、引用、结果告知与真实执行一致 | 事实和引用级指标, 加用户目标完成检查 |
| 稳定与资源 | 重复成功、尾延迟、预算内成功 | 每题重复试验及所有尝试成本 |

这里额外检查一件事: 对每个需要知识支持的业务决策, 确认“该决策前已可用、对该用户可见、在该时点适用的证据”是否充分支持所采取的动作. 本文把这一项称为证据到动作有效性 (Evidence-to-Action Validity). 这是自定义指标, 不是所有平台统一内置指标. 证据 ID 相同或引用字符串出现只能证明关联存在, 语义支持关系还需独立规则或校准过的裁判.

对行动任务, 可定义严格的端到端成功:

**Successᵢ = Goalᵢ ∧ Evidenceᵢ ∧ Constraintsᵢ ∧ Stateᵢ ∧ Communicationᵢ.**

各项是任务预先约定的布尔条件, 不适用项显式标记并从该任务契约中排除. **先检查硬条件, 再在达标任务上比较效率与表达质量**. 风险条件不能靠加权平均抵消. 同时保留各项通过率, 否则只有一个端到端分数无法定位问题.

不能把各项总体均值直接相乘当真实成功率, 因为失败往往相关. 如果链路阶段构成预先定义的必要条件, 可用条件通过率的链式乘积分析漏斗, 最终仍以逐任务联合判定的实际结果为准.

### 6.5 用干预实验定位故障

| 观察 | 受控干预 | 可以支持的诊断 |
| --- | --- | --- |
| 答案或决策错误 | 仅把实际上下文替换成已核验的充分证据 | 若明显改善, 检索/上下文供应是重要瓶颈; 不能排除组件交互 |
| 有证据仍选错动作 | 固定正确证据和实时状态, 单独测试决策 | 更指向规则理解或决策层 |
| 决策正确但办错订单 | 固定决策, 比较参数与用户/订单映射 | 指向参数构造或状态关联 |
| 参数正确但终态错误 | 回放工具返回并核对事务、重试和状态变化 | 区分工具、编排、重试与环境缺陷 |
| 状态正确但用户收到错误告知 | 固定工具结果测试结果汇总 | 指向执行结果解释或最终回答 |

Oracle 替换是诊断干预, 不是完整因果证明. 修改证据可能改变后续路径, 比较时应保持其他条件固定, 多次运行并检查轨迹. 将所有失败都归给“模型能力不行”或“检索不准”都缺少必要证据.

### 6.6 同一个售后任务怎样判

以下全部是教学变体, 用于说明联合判定, 不是某家公司实测.

| 变体 | RAG 局部表现 | Agent 局部表现 | 整体判断 |
| --- | --- | --- | --- |
| 正常链路 | 找全窗口与未使用条件, 引用有效规则 | 取得确认, 给正确订单退款一次 | 成功 |
| 只找退货窗口 | 回答的每句话都忠于片段, 但遗漏未使用条件 | 给已使用商品执行退款 | 证据不充分且决策失败 |
| 规则正确、订单参数错 | 答案和规则引用都对 | 对 O-2 退款, O-1 未退款 | 参数与状态失败 |
| 读到过期规则 | 对旧文档很忠实 | 按旧规则作出错误决策 | 适用性与决策失败 |
| 工具成功后超时 | 检索正常 | 盲目重试造成重复退款 | 幂等与副作用失败 |
| 正确拒绝 | 检索证明不符合条件 | 无写操作, 清楚说明拒绝原因 | 可以成功, 不能因没调用写工具扣分 |
| 缺关键日志 | 只能看到最终说退款完成 | 无法确认实际工具与终态 | 不可判定, 报告证据覆盖缺口 |

### 6.7 真实混合案例: Anthropic Research

Anthropic 的公开工程文章介绍了实际 Research 系统: 主 Agent 分解问题, 子 Agent 动态搜索并返回发现, 主 Agent 汇总并决定是否继续, 最后由引用处理环节对齐来源. 按本文分类, 这属于广义 Agentic RAG 的真实案例; 这是本文对架构的归类, 不是将它说成固定向量库问答系统. [Architecture overview 原文](https://www.anthropic.com/engineering/multi-agent-research-system).

其评测同时观察事实、引用、完整性、来源质量与工具效率, 并保留人工检查. 可借鉴的流程是: 从代表性查询建立基线 → 运行完整研究过程 → 按明确细则检查输出和来源 → 查看搜索与协作过程 → 人工找出自动判题漏掉的问题 → 纳入回归. 这直接结合了 RAG 的证据质量与 Agent 的工具策略. 对于办理退款等有写操作的产品, 还必须增加它所不直接覆盖的业务终态与副作用断言. 公开文章没有开放完整内部测集, 因而本文不复现或引用其性能提升比例作为通用结论. [Effective evaluation of agents 原文](https://www.anthropic.com/engineering/multi-agent-research-system).

## 7. 通用领域与垂直领域分别怎样落地

### 7.1 通用领域

通用领域重点是**问题与环境的多样性**: 多主题、长尾实体、多语言、多种文档、网页变化、多种工具组合. 评测集按知识主题、任务形式、所需工具、推理步骤和开放程度分层. 各组都报告, 同时给宏平均与接近真实流量的加权平均, 避免高频简单题淹没困难题.

| 系统 | 数据与环境 | 判定重点 | 真实案例与限制 |
| --- | --- | --- | --- |
| 通用 RAG | 多主题查询、时间戳、网页/知识库快照、无答案题 | 事实正确、证据覆盖、时效、拒答、来源质量 | CRAG; 检索器也可借助 BEIR 检验跨领域迁移, 但 BEIR 不评生成答案 |
| 通用 Agent | 浏览、文件、计算等组合任务; 可重置环境 | 目标完成、结果核验、工具使用、步骤与费用 | GAIA; 单一最终答案判题不覆盖所有状态副作用 |
| 通用混合系统 | 多轮研究、比较、汇总和必要的工具行动 | 子问题覆盖、来源冲突处理、停止条件、证据到结论/动作 | 用通用基准检查能力面, 再补产品真实任务契约 |

BEIR 是检索基准, 用于观察不同数据分布下的检索表现, 不能凭它的 nDCG 推导整个 RAG 的准确率. [BEIR 原论文](https://arxiv.org/abs/2104.08663).

开放研究任务可能没有唯一答案, 应先列关键应覆盖方面与可信来源要求, 再评事实和综合质量. 动态网页的线上执行反映当前产品能力, 固定快照反映版本差异; 两组结果分开, 不把环境更新混成模型改进.

### 7.2 垂直领域

垂直领域重点是**业务语义、领域真值与错误代价**. 不只是把通用题换成行业术语, 还要增加单位、时点、权限、专业规则、状态不变量和人工裁决标准. 垂直不意味着只能用专用框架, 更多是需要专用数据与判定器.

| 领域 | RAG 要额外检查 | Agent 要额外检查 | 混合评测的关键连接 |
| --- | --- | --- | --- |
| 金融文档分析 | 公司、报告期、币种、单位、表格列与计算口径 | 报告/分析产物准确, 若有行动则核实授权和操作范围 | 每个用于计算或动作的数字可追溯到适用证据; 参考 FinanceBench |
| 零售/航空客服 | 规则版本、商品/舱位例外、用户适用条件 | 确认、退款/改签终态、对象、金额与重复操作 | 规则 + 实时订单 + 用户授权共同支持动作; 参考 τ-bench |
| 医疗知识服务 | 指定指南版本、证据适用人群、信息完整与专业审阅 | 只按预定产品边界处理流程, 核实身份与授权 | 知识条件与个案事实是否匹配, 高风险判断由相应专业人员复核 |
| 法律/合同服务 | 法域、生效时间、条款上下文与例外 | 文档/流程操作范围、授权、交付状态 | 条款证据是否支持当前情形下的结论或操作, 由领域专家定义判据 |
| 软件研发 | 仓库版本、API 版本、相关代码与文档 | 补丁有效、原功能保留、测试与构建实际通过 | 检索到的代码约束是否落实到正确修改; 参考 SWE-bench |

医疗与法律行是评测设计维度, 不构成行业法规或专业意见, 本文没有据此宣称任何系统满足监管要求. 最小实施顺序是: 领域专家定义不可接受错误 → 规范事实/单位/时点 → 建立可复核任务与反例 → 冻结规则和环境 → 分层判题 → 对高代价错误单列频率与人工复核. 不给无依据的统一“合格分数”.

### 7.3 两类领域共享的报告口径

通用系统关注跨任务覆盖, 垂直系统关注业务损失与适用边界, 两者都需要: 样本量、覆盖分组、成功率、不可判定率、超时率、裁判误判、成本和不确定性. 风险加权分数可以辅助排序, 但保留原始各类错误数及分母, 否则一个加权均值无法说明真实风险.

## 8. 常见框架与方案怎样组合

下面按职责分层, 能力来自核查日官方文档. 不能把评测库、观测平台、Agent 编排框架与公开基准视为同一种产品, 也不需要一次安装全部方案.

| 方案 | 适合承担的职责 | RAG / Agent / 混合落点 | 不能代替什么 |
| --- | --- | --- | --- |
| Ragas | 指标、数据集与实验评测 | RAG 的上下文、事实与答案; 也有工具/目标类指标 | 业务终态真值与私有权限规则 |
| DeepEval | 测试用例与指标, 组件/端到端评判 | RAG 质量、工具正确性、任务完成 | 真实业务状态检查, 工具名匹配不等于参数正确 |
| TruLens | 观测与反馈函数, RAG 三元结构 | 从相关性与依据性拆解问答问题 | 语料真实性、完整业务契约 |
| LangSmith + AgentEvals | 数据集、实验、轨迹记录与匹配/裁判 | 多轮轨迹、局部步骤与版本比较 | 自动推导唯一正确路径或业务金标准 |
| Langfuse | 观测、数据集实验、代码/模型评测与人工分数 | 关联生产运行与离线实验 | 自带所有领域判定; 自托管仍需正确配置 |
| Phoenix | 可观测性、实验与评测 | 检索 span、Agent 调用与故障分析 | 可重置业务环境与任务真值 |
| Promptfoo | 配置化评测、断言与红队测试 | 提示词/模型对照, RAG 注入和数据泄露等专项 | 状态系统完整判题与所有生产业务规则 |
| LangChain / LangGraph / LlamaIndex | 构建被测应用与运行流程 | 生成检索或 Agent 运行链路并输出证据 | 本身并不定义业务成功标准 |
| CRAG / FinanceBench / GAIA / τ-bench / SWE-bench | 任务集、环境或判题协议 | 检查特定能力与公开可比性 | 本产品真实流量、规则和风险覆盖 |

来源: [Ragas 目录](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/), [DeepEval](https://deepeval.com/docs/metrics-tool-correctness), [LangSmith](https://docs.langchain.com/langsmith/trajectory-evals), [Langfuse Code Evaluators](https://langfuse.com/docs/evaluation/evaluation-methods/code-evaluators), [Phoenix](https://arize.com/docs/phoenix/), [Promptfoo RAG 指南](https://www.promptfoo.dev/docs/guides/evaluate-rag/), [Promptfoo 红队配置](https://www.promptfoo.dev/docs/red-team/configuration/). 框架的托管范围、许可、收费和功能版本需在实际选型时另行核实, 本文不作未经查证的承诺.

### 8.1 一次评测怎样接入这些工具

以本文售后任务为例: 让一个运行器负责重置环境、启动应用和收集记录, 再把同一份记录交给不同判定器. 平台负责存记录、比较版本, 业务代码负责定义哪些结果算对:

1. 运行器读取任务契约, 重置订单快照和知识版本, 驱动被测应用.
2. 应用把检索结果、工具请求返回和终态写入同一运行记录; 可以选择 LangSmith、Langfuse 或 Phoenix 中的一套作为主要记录与比较平台.
3. 代码判定器检查金额、对象、授权时间、状态不变量与预算; Ragas 或 DeepEval 适配器读取指定检索上下文和答案; 轨迹约束可用 AgentEvals 或自定义规则.
4. 需要语义判定的项给模型裁判, 裁判输出结论、证据定位与无法判断原因; 人工复核争议与高风险样本.
5. 汇总器按 case/trial 关联各项, 先算联合成功, 再算分组表现、稳定性与成本.

该设计允许替换平台而保留任务与判据. 主观分数与硬业务结果分别保存, 所有 SDK 字段通过适配器映射, 不把不同框架同名指标直接平均.

### 8.2 Ragas 接入的真实 API 形状

以下是按 2026-10-18 核实的 Faithfulness 官方页整理的**未执行示例**, 需要对应版本 Ragas、OpenAI 客户端及具备权限的模型服务. 本次不调用收费接口, 模型占位符必须由使用者替换; 正式使用先锁定经过验证的依赖版本.

```python
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness

client = AsyncOpenAI()
judge_llm = llm_factory("YOUR_JUDGE_MODEL", client=client)
metric = Faithfulness(llm=judge_llm)
result = metric.score(
    user_input="本例订单符合哪些退款条件?",
    response="签收 7 天内且商品未使用, 才符合本例规则.",
    retrieved_contexts=["本例政策: 签收 7 天内且商品未使用可退."],
)
print(result.value)
```

此调用只检查文字依据性, 并没有验证订单实际是否满足条件, 也没有检查退款数据库. Agent 轨迹与状态必须另外传给相应判定器. [官方接口示例](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/).

以下为**教学伪代码, 不可直接运行**, 表示适配器职责, 没有伪装成真实 SDK 方法:

```python
for case in frozen_cases:
    for trial in range(repeat_count):
        env = reset_environment(case.environment)
        run = execute_system(case.public_input, env, fixed_budget)
        evidence = collect_observable_evidence(run, env)
        hard = check_business_invariants(case.evaluator_only, evidence)
        semantic = grade_answer_and_evidence(case.evaluator_only, evidence)
        save_trial(case, trial, evidence, hard, semantic)
report = aggregate_joint_results_and_slices()
```

## 9. 让评测结果可信: 裁判、统计与线上闭环

### 9.1 先拿人工答案检查评分模型

先找一组容易误判的题, 请专家独立给出结论并处理分歧, 再把判断理由写成固定的评分细则 (Rubric). 评分模型读取同一组必要证据和统一字段, 将结果与人工结论比较. 将“无证据”“证据冲突”“不可判定”保留为独立结果, 不要求模型强行给分. 对每个评分项检查人工间一致性与裁判相对人工的误差, 不只看总相关系数.

若“有害错误”是正类, 则漏报率为 FN/(TP+FN), Precision 为 TP/(TP+FP), Recall 为 TP/(TP+FN). 必须说明正类, 否则“裁判召回高”含义不清. 可以辅以 Cohen's kappa (扣除偶然一致的双人一致性系数), 但它受类别比例影响, 应与混淆矩阵一起解释.

模型裁判的典型偏差包括篇幅偏好、候选顺序偏好、风格偏好与提示注入. 成对比较随机候选顺序, 可交换顺序复核; 评分前隐藏版本名; 将检索内容和被评答案作为待评数据而非指令. 换裁判模型或提示词属于测量系统变化, 需要重新校准, 不应将新旧分数无标注串成趋势. 多裁判一致也不代表独立正确, 共享偏差仍需人工难例检查.

### 9.2 分数差了多少, 有多少样本真的能判断

同一批任务对照候选版本, 按任务计算差异. 多次试验不能当作更多独立任务: 同一问题的难度和错误模式相关, 可按任务进行 Bootstrap (有放回重采样), 给出差值区间; 二值配对结果可按协议使用配对检验. 本文没有对真实数据执行这些统计检验.

不规定统一样本量或 0.8/0.9 的合格线. 样本量取决于风险、分组、基线和希望识别的差异. 一个没有失败的测试集也不能证明真实失败概率为零; 在独立同分布的简化假设下, 零失败时 95% 上界可用约 3/n 作粗略估计, 这不能代替稀有风险的定向覆盖.

报告至少包含:

- 计划任务数、实际完成运行数、可判定数、环境失败与观测缺口.
- 全体成功率与分组结果, 每项指标自己的样本量与分母.
- 候选版本相对基线的配对变化与不确定性, 重复试验的 k 和次数.
- 所有试验的总费用、成功任务平均耗费、总费用 / 成功数及尾延迟; 失败、重试与裁判成本不能消失.
- 高代价错误、关键失败证据、裁判校准状态与具体结论边界.

### 9.3 把真实失败变成下一轮回归题

先离线冻结评测, 再在产品授权范围内逐步验证真实环境. 在线记录能反映真实分布, 但缺少完整金标准; 用户点赞也不能替代业务状态与事实正确性. 对行动系统, Shadow Mode (影子运行) 只生成决策或运行隔离沙箱, 不重复执行用户真实写操作. 真实 A/B Test (随机对照实验) 需要相应产品授权、组间隔离和完整任务级分流, 不能把同一多轮会话拆入不同版本.

在线异常 → 脱敏与权限审查 → 固定快照 → 专家补标 → 转入回归集 → 对照复测. 持续关注知识更新、工具变更、用户目标变化、评判器漂移四类变化. 这段是评测实施流程, 本次未接入生产环境或部署在线实验.

## 10. 可运行练习: 把局部通过与整体成功分开

### 10.1 输入什么, 怎样运行, 先检查什么

前置条件: Python 3.9+, 仅使用标准库, 无账号、网络、模型或外部写操作. 输入包含 7 份确定性合成运行记录, 其中 1 份缺少终态. 所有政策、订单和支持关系都是人工写定的教学标签; 练习不实现自动语义判断、真实检索器或完整 Agent. 原练习在 2026-10-18 已执行, 本次保留代码、输入、输出与原运行元数据, 只核对图文与其一致.

下载并将 `evaluate.py` 与 `cases.json` 放在同一目录:

```bash
python3 evaluate.py
```

运行器读取合成记录, 先按标注 ID 计算证据召回与精确率, 再分别判断决策、参数、授权、终态与重复退款, 输出 `results.json`. 缺终态时用 `None` 表示“不知道”, 不把它当作 `False` 或默认通过. 它用**独立的期望条件**比对每层, 而不是让被测答案自己证明自己. 核心判定如下, 完整实现见下载文件:

```python
required = set(case["required_evidence"])
retrieved = set(case["retrieved_evidence"])
evidence_ok = required <= retrieved and case["policy_current"]
decision_ok = case["decision"] == case["expected_decision"]
params_ok = all(
    call["order_id"] == case["order_id"]
    and call["amount_cents"] == case["expected_refund_cents"]
    for call in case["refund_calls"]
)
state_ok = None if case["observed_refund_cents"] is None else (
    case["observed_refund_cents"] == case["expected_refund_cents"]
    and case["other_order_refund_cents"] == 0
)
```

本例 `policy_current` 来自合成标签; 生产中应通过适用日期、用户范围与规则版本判定. `required <= retrieved` 仅检查标注 ID 覆盖, 不能取代真实证据语义充分性. 金额用整数分, 避免练习中引入浮点货币比较.

### 10.2 为什么是 2 成功、4 失败、1 不可判定

<picture>
  <source media="(max-width: 640px)" srcset="/images/rag-agent-evaluation/result-decision-mobile.svg" />
  <img src="/images/rag-agent-evaluation/result-decision.svg" alt="六项检查独立产生结果, 有已知失败先判失败, 无失败但缺必需证据判不可判定, 其余判成功" />
</picture>

这张图表达的是代码怎样汇总检查结果, 不是让六项按顺序互相放行. 每项分别判断: 已知任何一项失败, 这次就是失败, 同时保留其他缺失项; 没有已知失败, 但仍缺必需证据, 才归为不可判定; 其余才算成功. 它对应完整代码中的 `failed` 和 `status`, 不是所有框架默认的统一汇总规则.

例如 `wrong-order` 的证据检查通过, 但参数和状态失败, 因此整体失败. `missing-state` 的其他检查通过, 只是终态没有记录, 因此不可判定. 如果一份记录既办错订单又缺终态, 错订单这一项已足以判失败, 不会被日志缺失抹去.

```python
failed = [name for name, value in checks.items() if value is False]
status = "failure" if failed else (
    "unknown" if any(value is None for value in checks.values()) else "success"
)
```

可判定的 6 份记录中, 正常退款和正确拒绝成功, 另有证据遗漏、错订单、过期规则和重复退款 4 类失败. 第 7 份缺少终态, 必须进入 unknown (不可判定), 不能假装通过或从覆盖统计消失. 精确比例与每条失败项见同目录实际结果文件.

验收标准:

1. `known_successes` 为 2, `known_failures` 为 4, `unknown` 为 1.
2. 已观测成功 / 计划试验为 2/7, 可判定样本条件成功率为 2/6, 判定覆盖率为 6/7; 同时保留三者.
3. 成功率识别区间为 [2/7, 3/7], 对应未知样本全部失败或全部成功; 这不是统计置信区间.
4. `wrong-order` 的证据检查通过, 参数和终态失败, 验证 RAG 正确不代表 Agent 成功.
5. `missing-condition` 的 ID 召回为 0.5, 但已有上下文只包含正确事实, 验证“忠于已有片段”仍可能信息不足.
6. `correct-refusal` 没有退款调用且能成功, 验证工具调用越多并非越好.

扩展练习: 仅将 `wrong-order` 的调用订单与终态改为符合目标, 对照输出应减少该例对应的参数和状态失败, 其余样本不变. 这是单因素修复验收; 不要把所有失败字段同时改成成功来制造通过.

## 11. 自测与参考答案

**问: Faithfulness=1, 能否发布?** 不能据此决定. 它只表示答案事实被所给上下文支持, 还需独立正确性、完整性、适用性、引用、风险条件及 Agent 终态检查.

**问: 工具调用列表和参考不一致, 是否失败?** 先看契约. 禁止动作、缺失必要动作或违反必需时序应失败; 合法替代路径只要终态与约束满足, 不应因列表不同被误杀.

**问: Agent 正确拒绝, 没有检索, 是否通过?** 取决于任务是否要求检索以及是否已有适用证据. 不能仅根据“有无调用”判定; 对需要知识依据的决策要追溯证据来源, 包括受控缓存.

**问: 新版本总分涨了, 高频退款任务跌了, 如何判断?** 检查分布权重和分组退化. 总分无法抵消硬业务约束失败, 应按预先约定的关键任务组标准和配对证据决定.

**问: 找到正确证据后整体仍失败, 还要测检索吗?** 要保留检索检查, 但下一步应沿依赖检查决策、参数与终态. 用已核验充分证据的受控测试区分后续瓶颈, 避免只继续调检索.

## 12. 术语表

| 英文名称与缩写 | 中文含义 | 本文具体作用 |
| --- | --- | --- |
| RAG / Retrieval-Augmented Generation | 检索增强生成 | 用外部证据支持回答 |
| Agent | 智能体 | 选择下一步、调用工具并可能改变状态 |
| Agentic RAG | 智能体控制的检索问答 | 动态决定检索与停止, 最终可只产出答案 |
| Knowledge-grounded Agent | 基于知识证据的行动智能体 | 将规则证据用于业务操作 |
| Task / Trial | 任务 / 单次试验 | 区分独立题目与重复运行 |
| Evaluation Harness / Agent Harness | 评测运行器 / 智能体运行框架 | 分开测量基础设施与被测编排系统 |
| Grader / Rubric | 判定器 / 评分细则 | 规定每项分数依据与判定方法 |
| LLM / LLM-as-a-Judge | 大语言模型 / 大模型裁判 | 处理难以确定计算的语义判断 |
| Trace / Span / Trajectory | 完整运行记录 / 操作片段 / 轨迹 | 关联检索、消息、工具与终态 |
| Chunk / Reranking | 文本片段 / 重排 | 切分知识并重新安排检索结果次序 |
| Oracle Context | 人工核验的理想证据 | 分离检索供应与证据使用能力 |
| Recall@k / Precision@k / Hit@k | 召回率 / 精确率 / 命中率 | 检查检索覆盖、噪声与至少命中 |
| MRR@k / nDCG@k | 截断倒数排名均值 / 归一化折损累计增益 | 检查第一条相关项与整体排序 |
| Context Recall / Context Precision | 上下文召回 / 上下文精确性 | 按指定框架口径测证据覆盖和排序 |
| Faithfulness / Groundedness | 忠实性 / 依据性 | 检查答案事实是否被上下文支持 |
| Answer Correctness / Relevance | 答案正确性 / 相关性 | 分别测独立事实真值与是否回应问题 |
| Citation Precision / Recall | 引用精确率 / 覆盖率 | 检查引用支持及事实覆盖 |
| Abstention | 拒答 | 处理不可回答题及避免编造 |
| RAG Triad | RAG 三元评测 | 以相关性与依据性组织诊断 |
| Outcome / State Invariant | 最终结果 / 状态不变量 | 检查业务完成及不该变化的部分 |
| Task Success / Tool Correctness | 任务成功 / 工具正确性 | 区分全任务完成与局部工具匹配 |
| Argument Correctness | 参数正确性 | 检查对象、金额、身份等业务值 |
| JSON Schema | 结构化数据约束 | 检查参数形状, 无法代替业务语义 |
| DAG | 有向无环依赖图 | 表达必要事件先后, 允许合法替代路径 |
| pass@k / pass^k | 至少一次成功 / 全部成功 | 分别观察解题机会与重复可靠性 |
| Evidence-to-Action Validity | 证据到动作有效性 | 本文自定义的跨层依赖判定 |
| Bootstrap / Confidence Interval | 重采样 / 置信区间 | 表达抽样不确定性, 与未知样本边界区分 |
| TP / FP / FN | 真阳性 / 假阳性 / 假阴性 | 计算裁判漏报、精确率与召回率 |
| Cohen's kappa | 校正偶然一致的系数 | 辅助核验人工或裁判一致性 |
| Shadow Mode / A/B Test | 影子运行 / 随机对照实验 | 从离线走向真实产品验证 |
| Token / p50 / p95 | 模型文本计量单元 / 中位数 / 95 分位数 | 统计费用与耗时分布 |
| CRAG / FinanceBench / BEIR | 通用 RAG / 金融问答 / 检索基准 | 覆盖不同知识与领域任务 |
| GAIA / τ-bench / SWE-bench | 通用助手 / 业务交互 / 软件修复基准 | 对照不同 Agent 判题方式 |

## 13. 参考资料与阅读顺序

| 来源 | 实际读取范围与版本 | 用途与未验证范围 |
| --- | --- | --- |
| [Ragas 指标文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/) | Context Precision、Context Recall、Faithfulness 及指标目录, stable 在线快照 | 核对字段、公式及 collections API; 未安装或运行 SDK |
| [TruLens RAG Triad](https://www.trulens.org/getting_started/core_concepts/rag_triad/) | 三元评测定义 | 理解相关性与依据性分工; 不将高分解释为无幻觉保证 |
| [LangChain 轨迹评测](https://docs.langchain.com/langsmith/trajectory-evals) | 匹配模式、参数匹配及模型裁判 | 核对 AgentEvals 接口与适用范围; 未调用平台 |
| [DeepEval Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness)、[Task Completion](https://deepeval.com/docs/metrics-task-completion) | 所需数据与判定方式 | 区分工具名、参数及任务完成; 未运行 SDK |
| [CRAG](https://github.com/facebookresearch/CRAG/tree/ad1518887dd4d9ebcd7de95388c7a62751e7705c) | README、`local_evaluation.py` 的生成与汇总逻辑, commit `ad1518887dd4d9ebcd7de95388c7a62751e7705c` | 真实通用 RAG 基准; 没有下载完整数据或复现榜单 |
| [FinanceBench](https://github.com/patronus-ai/financebench/tree/cc39aeb4afdf33909ee1412188bf89035950c2eb) | README、公开 JSONL 首条样本, commit `cc39aeb4afdf33909ee1412188bf89035950c2eb` | 真实金融问答及证据字段; 未逐页核对原始公司年报 |
| [τ-bench](https://github.com/sierra-research/tau-bench/tree/59a200c6d575d595120f1cb70fea53cef0632f6b) | README、retail 规则文档, commit `59a200c6d575d595120f1cb70fea53cef0632f6b` | 多轮业务操作与重复试验; 未运行模拟用户 |
| [τ²-bench 评测文档](https://github.com/sierra-research/tau2-bench/blob/96a3ef92329baf908ffe9dfe188cea34e8701d2a/docs/evaluation.md) | 任务契约、reward_basis 和状态评判, commit `96a3ef92329baf908ffe9dfe188cea34e8701d2a` | 核对不同轨迹可达相同终态的机制; 未审计全部评判器实现 |
| [AgentEvals](https://github.com/langchain-ai/agentevals/tree/946ad15b9f2ce9bc9843edd2bb773bd07d78ca7e) | README 的轨迹与图节点评测, commit `946ad15b9f2ce9bc9843edd2bb773bd07d78ca7e` | 轨迹评测能力边界; 未通读源码 |
| [SWE-bench Evaluation Guide](https://www.swebench.com/SWE-bench/guides/evaluation/)、[GAIA 论文](https://arxiv.org/abs/2311.12983) | 容器判题、预测格式; GAIA 摘要 | 软件任务与通用助手实例; 未复现分数 |
| [Anthropic Research 工程案例](https://www.anthropic.com/engineering/multi-agent-research-system) | 2025-06-13 发布文章中的架构与 Effective evaluation of agents 章节 | 真实检索研究系统的混合评测; 未获得其内部评测集或运行系统 |

其他官方来源在对应章节就近列出. 文档接口会变化; 实际项目应冻结依赖版本与评测配置, 不能把本文的核查日期当作所有框架的发行版本.


先读 [Ragas Context Precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)、[Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)、[Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/), 搞清事实分母与排序. 再读 [Anthropic Agent Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) 的任务、结果和非确定性章节, 配合 [AgentEvals](https://docs.langchain.com/langsmith/trajectory-evals) 了解轨迹匹配. 最后对照 [CRAG](https://github.com/facebookresearch/CRAG/tree/ad1518887dd4d9ebcd7de95388c7a62751e7705c)、[FinanceBench](https://github.com/patronus-ai/financebench/tree/cc39aeb4afdf33909ee1412188bf89035950c2eb)、[τ² 评测规则](https://github.com/sierra-research/tau2-bench/blob/96a3ef92329baf908ffe9dfe188cea34e8701d2a/docs/evaluation.md) 和 [SWE-bench](https://www.swebench.com/SWE-bench/guides/evaluation/), 观察不同任务如何建立真值与判题环境. 这些资料提供机制依据, 本文混合架构、练习和跨层指标是独立的教学归纳.
