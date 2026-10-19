---
title: 五种 RAG 的同异对比与实现流程
category: RAG
contentType: 技术对比
outline: deep
---

# 五种 RAG 的同异对比与实现流程

回答一个资料里的问题时, 先把相关原文找出来, 再让模型依据原文作答. 这种做法叫检索增强生成 (RAG, Retrieval-Augmented Generation). 这篇文章要比较的五个名称, 关注的其实是不同问题: 流程由谁决定, 资料怎样找回来, 谁负责找全证据, 知识又怎样组织.

你可以让代码固定执行检索, 也可以让模型根据任务选择工具并检查结果. 后一种执行主体叫智能体 (Agent). 它控制整个问答过程时, 通常称为 Agentic RAG; 只负责查资料并向上层交付证据时, 本文称为 Agent-as-retriever. 混合检索改变的是找资料的方法, GraphRAG 则引入图中的对象和关系. 因此, 五者能组合, 不能直接排成一条升级路线.

本文约定: “传统 RAG”指常见的固定检索再生成基线, 其中用单路向量召回举例; “混合检索”专指关键词与语义召回融合. 传统流程也可以使用关键词检索, 并不天然等于向量数据库.

- 学习目标: 能画出五种方案的离线和在线链路, 解释每一步的输入输出, 判断失败发生在哪一层, 并说明它们如何组合.
- 前置条件: 理解 Python, 文档检索和大模型调用. 不要求已使用某个框架.
- 技术主分类: RAG. 内容类型: 技术对比.
- 最后核查: 2026-10-18. 框架依据为当日在线官方文档, 未绑定 SDK (Software Development Kit, 软件开发工具包) 安装版本; 不把伪代码当成现行 SDK 接口.
- 原验证状态: 2026-10-18 已核查官方机制并实际运行本地练习, 只验证排名融合, 证据返回格式, 脚本化检索过程和图路径来源. 未运行真实文本向量模型 (Embedding), 大语言模型 (LLM, Large Language Model), 搜索数据库或 Microsoft GraphRAG 完整服务.
- 表达与图解更新: 2026-10-19 按新版学习规范改写讲解并补齐 6 张机制图. 保留原来源核查日期和练习结果; 本次不把格式更新记成重新核查事实或重新运行模型.
- 配套阅读: [开发与测试面试专题](../../interviews/rag/rag-architectures.md).

## 1. 先把五个名称放在正确位置

### 1.1 用同一组问题比较五种方案 {#_1-1-统一比较维度}

| 方案 | 主要改变什么 | 检索由谁决定 | 检索对象 | 典型在线路径 | 主要解决的问题 | 主要代价 |
| --- | --- | --- | --- | --- | --- | --- |
| 传统 RAG | 固定执行流程 | 应用代码 | 通常是文本块 | 问题 → 单次召回 → 上下文 → 答案 | 给常规问答补充外部知识 | 单次召回可能遗漏证据 |
| 混合检索 RAG | 召回与融合 | 通常仍是应用代码 | 同一语料的词法和向量索引 | 双路召回 → 融合 → 可选重排 → 答案 | 同时覆盖精确标识和语义表达 | 索引一致性, 分词和融合参数 |
| Agentic RAG (智能体控制的 RAG) | 控制流程 | Agent (智能体) 根据状态选择下一步 | 文档, 数据库, 搜索接口等 | 判断 → 工具 → 观察 → 再判断 → 答案 | 多跳问题, 动态信息缺口, 多源任务 | 多轮延迟, 工具错误, 停止策略 |
| Agent-as-retriever (智能体承担检索职责) | 检索组件的内部实现与职责边界 | 检索 Agent 在任务范围内决定 | 文件, 网页, 代码, 搜索结果等 | 上层请求 → 检索循环 → 证据包 → 上层生成 | 需要搜索, 打开, 追踪引用才能找到证据 | 证据接口, 原文保真, 搜索成本 |
| GraphRAG (图增强 RAG) | 知识表示与上下文构建 | 可以固定执行, 也可以由 Agent 调度 | 实体, 关系, 原文块, 某些实现含社区报告 | 实体定位/社区检索 → 图与文本上下文 → 答案 | 关系密集问题, 或跨语料主题综合 | 抽取错误, 实体对齐, 图和摘要更新 |

Agentic RAG 不要求多个 Agent, 不要求每题都检索, 也不要求使用向量库. 图检索同样不要求 Agent. 将多种方法串起来, 不会自动获得它们各自的收益.

LangChain 官方把 2-Step RAG (先检索后生成的两步流程), Agentic RAG 和 Hybrid RAG (固定流程与智能体流程的混合) 放在架构层比较. 此处用户所说的“混合检索 RAG”, 位于召回层, 与该文中的 Hybrid RAG 不是同一个定义. [来源: Retrieval / RAG architectures](https://docs.langchain.com/oss/python/deepagents/retrieval#rag-architectures).

### 1.2 先看分工, 再看怎样组合 {#_1-2-一张图看组合关系}

![四个设计问题分别对应控制流程, 召回方式, 检索职责和知识表示](/images/rag-architectures/architecture-map.svg)

从图中的 01 读起. 先问“流程由谁决定”, 再问“资料怎样找回来”. 03 把检索职责单独拿出来, 04 才讨论知识怎样组织. 这些行表示分工, 不表示先后步骤. 图底部的组合例子可以这样读: 上层智能体先选工具, 工具内部做混合检索或图检索; 若还缺原文, 再请检索智能体补齐.

接下来用同一组事故资料走完五条链路. 六张图分别回答分工, 固定流程, 双路融合, 智能体循环, 证据交接, 图查询这六个问题. 图中实线表示处理或调用, 虚线表示返回的数据或反馈; 分区边界不表示另一条执行路径.

### 1.3 Agent-as-retriever 到底指谁在找资料? {#_1-3-agent-as-retriever-的术语边界}

不同资料对这个名称的用法不完全一样, 没有一套跨框架统一接口. 本文先把职责说清: **上层提出要查什么, 检索智能体自己搜索和阅读, 把原文与出处交回来, 上层再组织最终答案**. 后面的流程和图都按这个约定解释.

它有两种相关用法:

1. 主动搜索: 通过 `list`, `search`, `open`, `read` 等只读工具, 逐步发现文件和相关片段, 按需加载上下文. Anthropic 称这类方式为 Just-in-time context (按需上下文加载), 不强制提前建立向量索引. [来源: Context retrieval and agentic search](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents#context-retrieval-and-agentic-search).
2. 可组合的检索组件: 上层把文档 Agent 或专门检索 Agent 当成一个可调用组件. LlamaIndex 的历史示例展示了检索路由至文档 Agent, 再由文档 Agent 选择搜索或摘要工具的模式. 该示例是 v0.10.17 历史架构材料, 本文不复用其中旧 API (Application Programming Interface, 编程接口). [来源: Recursive Retriever + Document Agents](https://docs.llamaindex.ai/en/v0.10.17/examples/query_engine/recursive_retriever_agents.html).

检索 Agent 也可以使用混合检索或图检索. “Agent-as-retriever = 完全不用索引”不成立. 如果同一个 Agent 同时搜索和最终作答, 它与一般 Agentic RAG 的边界会重合, 无须强行另分一类. 下文返回“证据包”的接口是教学设计, 不是上述框架共同规定的标准.

## 2. 先约定同一批资料和返回格式 {#_2-五种方案共用同一案例与证据契约}

以下是**合成教学案例**, 不代表真实生产事故.

| 文档 | 已知事实 | 用途 |
| --- | --- | --- |
| D1: 故障记录 | 2026-10-01, 支付服务出现 E1042, 当次原因为连接池耗尽 | 精确错误码和当次根因 |
| D2: 支付运行手册 | 常规排查连接池和请求积压 | 语义相关资料, 不能单独证明当次根因 |
| D3: 结算依赖说明 | 结算服务依赖支付服务 | 影响关系的第一跳 |
| D4: 对账依赖说明 | 对账服务依赖结算服务 | 影响关系的第二跳 |
| D5: 另一事故记录 | 2026-10-03, 通知服务出现模板配置错误 | 主题综合的另一类事故 |

用三个问题贯穿全文:

- Q1: “2026-10-01 支付 E1042 的原因是什么?” 必要证据是 D1.
- Q2: “如果支付服务不可用, 哪些服务有潜在依赖影响?” 必要证据包括 D3, D4; 它不等于询问当次实际故障波及情况.
- Q3: “这批事故记录反映哪些问题类型?” 需要覆盖 D1, D5, 单取最相似的一个文本块不够.

### 2.1 查回来什么, 上层才有办法核对? {#_2-1-共同的证据格式}

不管底层用了哪一种搜索, 上层至少要知道“找到了哪段原文, 它来自哪里, 还缺什么”. 本文把这些内容放在一起, 称为证据包. 下面是一份教学格式, 字段不是框架统一标准:

```json
{
  "request_id": "q1-demo",
  "index_version": "corpus-demo-v1",
  "status": "sufficient",
  "evidence": [
    {
      "chunk_id": "D1#1",
      "doc_id": "D1",
      "version": "v1",
      "source": "incidents/payment-2026-10-01.md",
      "locator": "L1-L2",
      "text": "2026-10-01, 支付服务出现 E1042, 当次原因为连接池耗尽.",
      "retrieved_by": ["lexical", "dense"]
    }
  ],
  "missing": []
}
```

`status` 说的是“这次要回答的问题, 已知证据够不够”, 不是模型觉得自己有多大把握. 比如 Q2 要查两跳关系, 就要分别记住 D3 支持哪一跳, D4 又支持哪一跳. 如果只找到了 D3, 返回 `insufficient` 并写清第二跳还没确认. 这不等于对账服务没有依赖关系.

### 2.2 所有方案共有的准备工作

1. 确定语料范围, 使用者权限和版本. 保留原文, 使任何片段可回到文档位置.
2. 解析标题, 段落, 表格和附件. 表格不能只保留脱离表头的数字, 错误码不能被解析丢失.
3. 为文档和片段分配稳定标识. 保留 `doc_id`, `chunk_id`, 来源, 时间, 版本和访问范围.
4. 对每个问题准备必要证据清单和参考结论, 将检索失败与生成失败分开验收.

以下流程是依据官方机制设计的**教学实现蓝图**, 具体步数, 证据字段和预算值不是任一框架的固定规范.

## 3. 传统 RAG: 先找原文, 再按固定流程回答 {#_3-传统-rag-固定检索-再生成}

### 3.1 问题到来前, 要先准备哪些资料? {#_3-1-离线建库}

| 步骤 | 输入 → 输出 | 实现重点 |
| --- | --- | --- |
| 1. 解析清洗 | 源文档 → 保留结构的文本 | 去掉导航噪声, 保留标题和出处 |
| 2. 分块 | 文档 → Chunk (可独立检索的文本片段) | 根据段落, 标题和表格边界切分, 不能一刀切断必要条件 |
| 3. 向量化 | 片段文本 → 稠密向量 | 选适合语言与领域的模型, 记录模型和处理版本 |
| 4. 存储索引 | 向量 + 片段标识 → 可检索索引 | 向量对应原文, 元数据可过滤 |
| 5. 建库验收 | 已知问题 → 召回与来源检查 | 先确认 D1 能进入候选, 再接生成 |

分块是把长文拆成可单独检索的小段, 通常称为 Chunk. 片段太短, 可能只剩“连接池耗尽”, 却不知道是哪天哪项服务; 太长又可能夹进大量无关内容. 因此大小和重叠要看实际资料与检索结果, 没有通用固定值. 问题与文档的向量还必须能在同一空间比较; 如果所用模型要求两者采用不同的编码格式, 就分别遵循.

![传统 RAG 的离线准备, 在线检索和有依据或证据不足两种出口](/images/rag-architectures/traditional-flow.svg)

先走上半部分: D1 被解析, 切成片段, 编码后进入索引, 同时保留能找回原文的标识. 再走下半部分: Q1 查索引并取回原文, 如果上下文中保留了 D1, 就能支持“当次为连接池耗尽”. 若 D1 没有找到或被裁掉, 图右侧出口要求说明缺口. 图中的依据判定是本文的输出要求, 不声称所有传统 RAG 都内置独立检查节点.

### 3.2 Q1 到来后, 一次请求怎样走? {#_3-2-在线查询}

1. 接收 Q1, 解析日期, 服务和错误码, 先确定访问范围.
2. 编码问题, 在允许范围内进行相似度检索. Top-k (保留前 k 个结果) 表示候选数量, 并不保证其中含有答案.
3. 取回片段原文, 去重; 若命中文档中的孤立句, 可按已知位置补齐相邻段落.
4. 可选 Reranking (重排): 对候选与问题重新评分, 保留更相关的证据. 仍然是固定流程.
5. 根据上下文容量选择证据, 让生成模型依据证据回答, 给出出处, 对缺失部分明确说明.
6. 检查回答中的“2026-10-01”“E1042”“连接池耗尽”是否都由 D1 支持. D2 只能提供排查背景.

向量召回常用余弦相似度: 将问题向量与文档向量的点积, 除以两个向量长度的乘积.

它衡量向量接近程度, 不是事实正确概率. 若实际系统使用点积或距离度量, 索引, 归一化和排序方向要对应.

**教学伪代码, 不可直接运行**. `encode_query` 编码问题, `vector_search` 召回可访问片段, `pack_context` 选择上下文, `generate` 调用生成模型:

```python
query_vector = encode_query(question)
hits = vector_search(query_vector, scope=access_scope, limit=candidate_k)
context = pack_context(hits, token_budget=context_budget)
answer = generate(question, context, require_citations=True)
```

### 3.3 答错时, 怎样查是哪一步丢了依据? {#_3-3-适用条件和失败定位}

适合有稳定知识库, 问题能由少量局部片段回答的场景. 如果 D1 不在候选, 查解析, 分块, 编码和过滤; D1 在候选却没进入上下文, 查排序与裁剪; 上下文已有 D1 但答成“网络故障”, 查生成与引用支持关系.

RAG 原始论文研究了参数记忆与非参数记忆结合的训练模型. 本文采用常见工程问答流程, 不等于复现论文的 RAG-Sequence / RAG-Token 两种训练与生成公式. [来源: Lewis 等, 2020](https://arxiv.org/abs/2005.11401). 建库与检索链路可对照 [Anthropic 的 RAG primer](https://www.anthropic.com/engineering/contextual-retrieval#a-primer-on-rag-scaling-to-larger-knowledge-bases).

## 4. 混合检索 RAG: 双路召回, 再融合

### 4.1 为什么增加关键词召回

Q1 同时含精确字符串 `E1042` 和“原因”这一语义需求. 稠密向量可能偏向通用排障文档 D2; 词法检索可能更容易保住 D1 的错误码. 当用户只说“付款一直卡住”, 语义召回又能补充词面不同的资料. 两路互补是否成立, 应在实际语料上验证.

关键词一路不是简单地比较整段字符串是否相等. 常用的 BM25 (Best Matching 25, 词法相关性排序函数) 会看词出现多少次, 这个词有多能区分资料, 以及文档长度. 它依赖分词与索引规则. 对错误码, 版本号等标识, 应检查分词是否保留完整标识. [来源: Elastic Hybrid search](https://www.elastic.co/docs/solutions/search/hybrid-search).

### 4.2 离线建库

1. 沿用共同解析, 分块和标识.
2. 建立词法索引: 片段文本 → 分词项与倒排索引 (由词找到片段的数据结构).
3. 建立向量索引: 同一批片段 → 稠密向量.
4. 两个索引用同一 `chunk_id` 和语料版本, 同步更新, 失效和访问范围. 两路命中 D1 时, 应合成一条证据.
5. 单独验证两路召回. 否则融合效果差时, 不知道是哪一路没有贡献.

### 4.3 两份排名怎样合成一份, 又会在哪儿出问题? {#_4-3-在线查询与融合}

1. 同一问题, 同一权限和语料范围进入两路查询. 词法路应保留精确标识, 可与语义路采用不同查询表达.
2. 分别获得前若干候选及排名, 例如词法 `[D1, D2]`, 语义 `[D2, D3]`.
3. 用 RRF (Reciprocal Rank Fusion, 倒数排名融合) 或经过校准的分数组合, 得到统一列表.
4. 基于稳定标识去重, 记录每个候选来自哪一路. 融合后可再用 Cross-encoder (交叉编码器, 联合编码问题与候选的相关性模型) 重排.
5. 选取上下文, 生成带引用答案, 与传统流程相同.

拿到两份排名后, 可以让每个名次贡献一点分数, 再把同一片段的贡献加起来. 这就是这里使用的倒数排名融合. 对每一路出现的候选, 先把平滑常数与排名相加, 再用这一路权重除以它, 最后累加各路贡献. 对应 Python 表达式是 `sum(weight / (constant + rank) for weight, rank in matched_ranks)`.

![相同问题独立进入关键词和语义召回, 按固定排名融合后 D2 排在 D1 前面](/images/rag-architectures/hybrid-fusion.svg)

先沿图顶端的两个分叉各走一次. 它们从同一个问题独立出发, 关键词一路找到 D1 和 D2, 语义一路找到 D2 和 D3. 合并时 D2 因为两路都出现而排第一. 再看底部的两种上下文预算: 只留一条时丢掉了 D1, 当次根因仍没有依据; 保留前两条时 D1 在场, 但上层仍要核对它是否支持这个问题. 这正是“候选变多”和“证据够用”之间的区别.

其中排名从 1 开始, `constant` 是平滑常数, `weight` 是各路权重; 普通等权 RRF 令权重都为 1. 候选未出现在某路时, 该路贡献为 0. Elastic 文档描述的 RRF 使用等权子检索器, 不能假定它支持上述教学规则中的任意权重. `constant=60` 是其文档默认值, 不是所有引擎和语料的最佳值. [来源: Elastic RRF 定义与参数](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion).

**教学伪代码, 不可直接运行**. `lexical_search` 和 `dense_search` 返回同标识的候选列表; `rrf` 按排名融合, `rerank` 可选:

```python
lexical = lexical_search(question, scope=access_scope, limit=lexical_k)
dense = dense_search(question, scope=access_scope, limit=dense_k)
candidates = rrf([lexical, dense], constant=60)
selected = rerank(question, candidates)[:context_k]
answer = generate(question, pack_context(selected), require_citations=True)
```

两路无依赖时可以并行. 不应直接把 BM25 分数与余弦相似度各乘 0.5 相加而不处理量纲; RRF 正是通过排名绕开原始分值不兼容. 重排只能在收到的候选中选择, 无法凭空找回两路都没召回的 D1. Qdrant 官方 Query API (查询接口) 展示了先执行多路 `prefetch` (候选预取), 再融合或重排的实现方式. [来源: Hybrid and Multi-Stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/).

### 4.4 主要边界

它解决“怎样更好地召回和排序”, 不会自动把 Q2 拆成两跳, 也不会自动补全 Q3 的全语料覆盖. 两路召回更广可能带来更多噪声; 应分别观察单路, 融合和重排后的结果, 不只看最终回答.

## 5. Agentic RAG: 让模型决定何时检索和下一步做什么

### 5.1 智能体开始查资料前, 应用要准备什么? {#_5-1-离线准备}

1. 准备可用数据源, 可以复用传统或混合检索索引, 也可以使用已有只读搜索接口.
2. 将能力封装为少量清楚的工具, 如 `search_incidents`, `search_dependencies`, `open_document`. 每个工具有参数约束, 范围, 返回证据和错误状态.
3. 定义状态: 用户问题, 未解决子问题, 已收集证据, 已执行动作, 调用次数, 剩余时间与上下文预算.
4. 定义允许的动作与结束条件. 本案例只查资料, 不提供改配置或重启服务工具.
5. 准备需要检索, 不需检索, 证据不足, 循环和工具失败场景. 检索前后的决策都需要验收.

### 5.2 找到第一条线索后, 谁来决定还要不要查? {#_5-2-在线控制循环}

1. **判断任务**: Q2 需要依赖关系, 不能仅凭通用服务知识回答.
2. **形成当前信息需求**: 先查谁直接依赖支付服务.
3. **选择工具并执行**: 检索 D3, 得到“结算依赖支付”. 调用前由应用检查参数, 权限和预算.
4. **观察与更新状态**: 已知结算可能受影响, 还不清楚结算的下游服务.
5. **继续检索**: 用结算作为新实体, 检索 D4, 得到对账依赖结算.
6. **检查完成条件**: 根据问题要求的范围, 证据覆盖和预算判断是否继续. 发现重复查询或无新增证据时结束, 保留覆盖限制.
7. **生成最终回答**: 给出潜在依赖链, 引用 D3, D4; 不把潜在依赖写成已发生的事故传播.

![智能体检索循环, 预算检查与证据出口](/images/rag-architectures/agent-loop.svg)

从“问题 + 已知证据”开始. 如果应用允许不查资料直接回答, 比如打招呼, 走右上角的直答出口; 企业事实问答要求来源时, 就继续检查证据. 对 Q2, 初始没有关系证据, 先查 D3; 新发现的结算服务又成为下一轮线索, 再查 D4. 虚线把这些新观察送回“证据齐全吗?”, 不是回到一个凭空重新开始的问题.

再走一条不足路径: 只查到 D3 就用完预算, 下一次检查会从“允许调用且还有预算吗?”走到缺口出口. 图中还单独画出了工具失败和反复没有新证据的出口. 它们都不能变成“没有第二跳关系”的业务结论. 日志记工具, 参数, 结果和简短决策理由即可, 不需要暴露模型内部推理.

**教学伪代码, 不可直接运行**. `may_reply_without_retrieval` 合并任务判断与应用对来源的要求; `evidence_sufficient` 检查当前证据; `may_call` 检查参数, 权限和预算. 工具结果用 `ok` 表示执行是否成功. `record_observation` 记录证据并扣减已用预算; 最后一个函数同时说明已知缺口:

```python
if may_reply_without_retrieval(question):
    answer = reply_directly(question)
else:
    state = init_state(question, max_calls=4)
    while not evidence_sufficient(question, state.evidence):
        action = choose_action(state)
        if not may_call(action, access_scope, state.budget):
            break
        result = execute_read_tool(action)
        state = record_observation(state, action, result)
        if not result.ok or repeated_without_new_evidence(state):
            break
    answer = generate_with_known_gaps(question, state.evidence)
```

这里将直答与证据回答分开, 也把应用不能继续调用和工具失败写成明确出口. 它只补齐教学流程的表达, 不代表配套脚本已经实现真实模型决策.

`4` 是教学预算, 不是行业推荐阈值. 实际应同时限制调用次数, 墙钟时间, 模型用量和单次工具返回大小. 对企业事实问答, 即使 Agent 认为能直接回答, 应用也可以要求必须有来源.

官方 LangGraph 教程展示了模型选择检索, 相关性判定, 不相关时改写再检索的流程. 这是 Agentic RAG 的一种实现, “每轮都要额外判分模型”和“每次都先规划完整任务”不是定义要求. [来源: Generate a query or respond / Grade documents / Rewrite question](https://docs.langchain.com/oss/python/langgraph/agentic-rag).

### 5.3 失败定位

- 未查 D3 就作答: 决策或应用要求问题.
- 选对工具但把 `payment` 写成另一个服务: 工具参数问题.
- D3 已返回但第二跳仍查询支付: 状态更新或行动选择问题.
- D3, D4 都找到却漏掉对账: 综合生成问题.
- 不断重复查询: 停止策略或预算执行问题.

Agentic RAG 的执行路径可变, 不代表结果必然比固定流程好. 对 Q1 这种局部事实问题, 多轮行动可能只增加成本.

## 6. Agent-as-retriever: 把“找全证据”做成一个组件

### 6.1 与 Agentic RAG 的精确关系

这两个名称最容易混在一起. 前者问的是“整个问答过程的下一步由谁决定”; 后者问的是“查资料这项工作交给谁, 最后要交回来什么”. 本文让检索智能体交回证据, 上层负责作答, 所以边界是:

```text
固定生成器 或 上层任务 Agent
    → retrieve(信息需求, 范围, 预算)
        → 检索 Agent: 搜索 → 打开 → 阅读 → 追踪引用 → 查缺
    ← 证据包: 原文 + 位置 + 缺口 + 检索轨迹
    → 综合答案
```

这是一种架构分工, 不是必须部署两个模型或两个进程. 也不能把函数名叫作 `agent_retriever` 就当成已实现自主检索.

### 6.2 离线准备: 可以不用向量库, 但不能没有数据准备

1. 接入可读取的语料: 文件目录, 知识平台, 网页或业务查询接口.
2. 使文件可发现, 提供目录, 标题, 摘要或搜索能力. PDF 和扫描件仍需解析或识别, 不能指望文本搜索直接理解图片.
3. 设计只读工具: `list_sources` 找范围, `search` 返回命中位置, `open` 读取指定范围, `follow_link` 打开相关出处.
4. 工具返回稳定文档标识, 版本和位置. 搜索摘要仅用于定位, 重要结论应打开原文确认.
5. 定义证据包, 限定文档范围和预算. 如果资料更新中, 返回每份资料的实际版本或读取时间.

### 6.3 从上层提出需求, 到原文交回来, 中间发生什么? {#_6-3-在线详细流程}

1. 上层提交 Q1, 明确需要“当次事故原因”, 而不是通用排查建议.
2. 检索 Agent 查看目录或来源列表, 定位事故记录和运行手册.
3. 搜索 `E1042`, 命中 D1, 获取路径与行号.
4. 打开 D1 的对应段落, 读取日期, 服务, 原因和相邻限制条件.
5. 若 D1 引用了另一份根因报告, 沿链接打开; 若与 D2 内容不同, 区分“当次结论”与“一般可能原因”.
6. 将已确认原文放入证据包, 附来源与已知缺口. 摘要与原文分字段保存, 不把摘要伪装成引用原句.
7. 上层基于证据生成答案, 检查引用与结论一一对应.

![上层, 检索智能体与资料工具之间的搜索, 原文读取, 查缺和证据返回](/images/rag-architectures/retriever-contract.svg)

按三个角色从上往下读. 上层先交代要查“当次根因”, 检索智能体搜索后先拿到 D1 的位置, 再打开原文. 因此“搜到一个标题”和“拿到可核对的原文”是两次不同的数据交接. 证据足够时, 右侧路径把充分证据包交回上层; 不够但还有预算和线索时, 返回搜索; 不能继续则交回已有原文和明确缺口. 每次工具调用的权限, 预算与失败处理按第 5 节执行, 本图重点展开角色交接.

**教学伪代码, 不可直接运行**. `retrieval_agent.run` 表示受预算约束的搜索阅读循环, 不是某个 SDK 的真实方法:

```python
bundle = retrieval_agent.run(
    need="2026-10-01 支付 E1042 的当次根因与原文出处",
    sources=allowed_sources,
    tools=[list_sources, search, open_document],
    max_calls=4,
)
validate_evidence_bundle(bundle)
answer = generate(question, bundle.evidence, missing=bundle.missing)
```

### 6.4 与预建索引的取舍

已有目录结构良好, 需要频繁追踪文件引用时, 主动搜索阅读很自然. 海量同质文档, 模糊语义提问或检索量很大时, 索引可能更有效. 搜索工具也可能使用服务端索引, “应用没有向量库”不能推出“系统没有任何索引”.

实时打开资料减少了依赖旧向量快照的机会, 但仍受来源本身, 搜索索引和缓存新鲜度影响. Anthropic 的按需上下文实践支持搜索阅读路线, 并未证明向量检索对所有任务都已失效. [来源: Context retrieval and agentic search](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents#context-retrieval-and-agentic-search).

## 7. GraphRAG: 用实体关系和图派生上下文组织证据

### 7.1 先区分广义 GraphRAG 与 Microsoft GraphRAG

如果问题一直在问“谁依赖谁, 某个人和哪些项目有关”, 就可以把这些对象及连接整理成图, 帮助寻找证据. 这类做法统称图增强检索生成 (GraphRAG). 图可以直接来自已有业务关系表, 也可以从文本抽取. Microsoft GraphRAG 是其中一条具体路线, 还会把图中联系紧密的对象分组并生成报告; 其他图检索方案不一定做这一步.

图里先有对象, 例如支付服务与结算服务, 这些对象称为实体; 连接两个对象的边说明关系. `结算 --依赖--> 支付` 的方向不能倒过来. 两个服务出现在同一段里, 不等于其中一个依赖另一个; 即使确有依赖, 也不能单凭它证明这次故障已经传播.

### 7.2 离线建图: 以 Microsoft 路线为机制参考

| 步骤 | 输入 → 输出 | 实现与验收重点 |
| --- | --- | --- |
| 1. 文本单元 | 原文 → TextUnit (带来源的文本单元) | 保留与原文文档的对应 |
| 2. 抽取 | 文本单元 → Entity (实体), Relationship (关系) | 类型, 方向, 描述和来源要可追踪 |
| 3. 对齐与整理 | 同名/别名实体与重复关系 → 统一标识 | 支付服务与 payment-service 是否同一实体需依据, 同名实体不能盲目合并 |
| 4. 建图 | 实体与关系 → 图及映射表 | 每条关系回链原文, 保留业务时间范围 |
| 5. 社区检测 | 图 → Community (连接较紧密的实体群) 及层级 | 社区是结构分组, 不是天然真实组织架构 |
| 6. 社区报告 | 社区信息 → Community Report (社区综合摘要) | 报告为生成内容, 应能追踪到底层证据 |
| 7. 向量表示 | 文本/实体描述/报告 → 对应检索表示 | 按查询方式准备所需索引 |

Microsoft 官方默认数据流包含文本单元, 实体关系抽取与摘要, 图社区, 社区报告和文本表示; Claim (带条件的陈述) 抽取为可选项. 实体消歧, 业务时间和访问规则是落地时需明确的设计, 不应假定任何默认抽取器都已解决. [来源: Default Dataflow](https://microsoft.github.io/graphrag/index/default_dataflow/).

图存储可以是图数据库, 关系表或文件, 本质要求是支持所需的关系检索和来源映射. 选用 Neo4j 并不自动等于 Microsoft GraphRAG, 社区摘要也不要求一定存进 Neo4j.

### 7.3 局部搜索: 已知支付服务, 怎样找到有关的关系? {#_7-3-在线-local-search-从具体实体进入}

问一个具体对象时, 可以先定位它, 再找与它相连的关系和原文. Microsoft 把这种查询称为局部搜索 (Local Search). 它以语义相关实体为入口, 汇集关系, 关联原文和其他上下文, 过滤与排序后交给生成模型, 不是只把一段图查询结果交给模型. [来源: Local Search / Methodology](https://microsoft.github.io/graphrag/query/local_search/).

对 Q2 可设计以下关系查询流程, 这是基于案例的确定性遍历设计, 不声称是官方默认 Local Search 的固定执行轨迹:

1. 将“支付服务”对齐到实体 `payment`.
2. 问题要求下游影响, 因此沿“依赖”边的反方向找依赖者: 从支付找到结算.
3. 在问题要求和预算内继续找结算的依赖者, 找到对账. 保存访问集合, 避免图中环导致无限遍历.
4. 回取 D3, D4 原文, 检查关系方向, 版本, 时间范围与访问权限.
5. 组织实体, 关系, 路径和原文证据, 生成“存在潜在依赖影响”的回答.

![图的离线准备与局部, 全局两条独立查询路径, 包含依据不足的出口](/images/rag-architectures/graph-flow.svg)

上半部分先把文本整理成实体关系, 再按 Microsoft 路线生成社区报告. 问题到来后, 两条查询从同一个入口分开, 不是先做完局部搜索才有资格做全局搜索. 沿左侧走 Q2: 定位支付, 反向查谁依赖它, 回取 D3 和 D4. 若实体没对齐或某条关系没有可核对的原文, 就走依据不足出口, 不能把猜测补成完整路径. 这条两跳遍历是教学案例, 不代表官方局部搜索只会执行两跳.

### 7.4 全局搜索: 不指定对象, 怎样总结整批资料? {#_7-4-在线-global-search-从整批语料的主题进入}

Q3 问的是“整批事故反映什么问题”, 没有给出一个足以定位所有资料的实体. Microsoft 的全局搜索 (Global Search) 主要利用已经准备好的社区报告, 分批提炼要点后再合并. 对 Q3:

1. 选择社区层级及报告范围, 确保使用者有权看到这些报告聚合的信息.
2. 将该范围内报告划分为上下文可容纳的批次.
3. Map (分批处理): 每批报告针对问题生成中间要点及重要性评分, 保留报告来源.
4. 排序, 过滤和合并中间要点, 处理重复或冲突.
5. Reduce (汇总处理): 综合保留的要点, 输出“资源容量类”“配置类”等主题, 附来源和覆盖范围.
6. 若问题要求“发生次数最多的类型”, 应使用完整结构化事故数据进行确定性统计, 不能把摘要强调程度当作频次.

回到上图右侧. 先选报告层级与范围, 每批报告分别回答这个问题, 再把相关要点合起来. 如果报告范围不完整或要点没有足够依据, 图中的判断同样走缺口出口. 和左侧一样, 这里不能默认“流程跑完”就代表资料齐全.

这种先分批处理, 再汇总的方式叫 Map-reduce. 这里是 Microsoft 官方社区报告机制的案例化解释. 并非每个 GraphRAG 都有 Global Search, 其输出也不保证精确覆盖全部原文细节. [来源: Global Search / Methodology](https://microsoft.github.io/graphrag/query/global_search/). 原论文重点是面向问题的全局语料总结, 不能简化为“图比向量更擅长所有问题”. [来源: From Local to Global](https://arxiv.org/abs/2404.16130).

### 7.5 两条查询路径怎样对应到代码? {#_7-5-两条路径的机制伪代码}

**教学伪代码, 不可直接运行**. `resolve_entities` 定位实体, `gather_graph_context` 汇集有范围约束的图上下文, `load_source_spans` 回取原文; 全局流程使用已构建的社区报告:

```python
entities = resolve_entities(question)
subgraph = gather_graph_context(entities, scope=access_scope, budget=graph_budget)
spans = load_source_spans(subgraph.source_ids)
local_answer = generate(question, context=[subgraph, spans])

reports = load_community_reports(level=chosen_level, scope=access_scope)
partials = [map_question(question, batch) for batch in batches(reports)]
global_answer = reduce_points(question, rank_and_filter(partials))
```

### 7.6 原文改了, 图和报告也都更新了吗? {#_7-6-增量更新与失败定位}

文档更新后, 不只重算文本向量. 应确认受影响的实体, 关系, 来源映射及派生报告是否需要更新; 图结构变化还可能影响社区. 不应假定局部文档变动永远只影响一个社区.

如果支付被错误合并到另一个“支付”系统, 是实体对齐问题; 结算与支付关系方向颠倒, 是抽取或建模问题; 图关系正确但丢了 D3 来源, 是溯源问题; 社区报告仍包含已失效事故结论, 是派生数据更新问题. 图中边能证明文档陈述过某关系, 不能自动证明因果真实性.

本文详细覆盖 Local / Global 两条机制, 没有复现全部查询模式. 官方还提供 DRIFT (Dynamic Reasoning and Inference with Flexible Traversal, 动态推理与灵活遍历), 将社区信息, 后续问题和局部搜索结合. 这也说明图结构与动态检索可以组合. [来源: DRIFT Search](https://microsoft.github.io/graphrag/query/drift_search/).

## 8. 技术组件如何对应到五条链路

下面是角色映射, 不是要求全部安装的依赖清单. 列出的引擎和框架是实现选项, 本文未执行其 SDK 示例或作兼容性组合验证.

| 角色 | 传统 RAG | 混合检索 RAG | Agentic RAG | Agent-as-retriever | GraphRAG |
| --- | --- | --- | --- | --- | --- |
| 数据入口 | 文档解析器 | 同左, 保留双路共用标识 | 复用索引或既有接口 | 可发现和可读取的来源 | 文档解析或现有结构化关系 |
| 表示 | 文本块 + 向量 | 词法索引 + 向量 | 由具体工具决定 | 路径, 目录, 文本位置, 可选索引 | 实体, 关系, 原文映射, 可选报告 |
| 检索组件示例 | Elasticsearch 向量检索 | Elasticsearch 词法与向量 + RRF; 或 Qdrant 多表示融合 | 将搜索接口封装为工具 | 搜索与定向读取工具 | Microsoft GraphRAG 查询引擎; 或业务关系查询 |
| 控制实现 | 顺序应用代码 | 双路查询与融合代码 | LangGraph 状态图或显式循环 | 带证据出口的检索循环 | 固定局部/全局路径或 Agent 调度 |
| 模型作用 | 编码与最终生成 | 编码, 可选重排与生成 | 工具决策与生成 | 检索决策, 上层另行综合 | 可选抽取与摘要, 查询表示和生成 |
| 非必需组件 | Agent 框架 | Agent, 图数据库 | 多 Agent, 向量库 | 向量库, 多 Agent | Agent, 特定图数据库 |

组件依据分别见 [Elastic 混合检索](https://www.elastic.co/docs/solutions/search/hybrid-search), [Qdrant 多阶段查询](https://qdrant.tech/documentation/search/hybrid-queries/), [LangGraph 检索 Agent](https://docs.langchain.com/oss/python/langgraph/agentic-rag) 和 [Microsoft GraphRAG 数据流](https://microsoft.github.io/graphrag/index/default_dataflow/).

### 8.1 可以组合的完整例子

```text
Agentic RAG 控制器
  → 对 Q1: 调用混合检索工具, 找 E1042 原因
  → 对 Q2: 调用 GraphRAG 局部关系工具, 找依赖链
  → 对缺失原文: 调用 Agent-as-retriever, 搜索并打开来源
  → 汇总统一证据包, 生成带出处的答案
```

该组合是教学架构, 不是已经运行的系统. 只有任务确实需要这些能力时才引入对应组件. 五种名称也没有“传统 → 混合 → Agentic → Agent-as-retriever → GraphRAG”的统一升级顺序.

## 9. 实操: 不调用模型, 验证关键中间机制

### 9.1 前置条件与输入

仅需 Python 3 标准库, 无账号, 付费接口或第三方包. 输入为上面的合成文档, 两路排名是**人工给定的固定输入**, 用于观察融合, 不冒充真实向量召回或 BM25 实测. 检索动作采用脚本化策略, 不冒充 LLM Agent. 图关系由明确事实手工录入, 不冒充模型自动抽取.

- <a href="/examples/rag-architectures/practice.py" download>下载练习 practice.py</a>
- [本次实际运行结果](/examples/rag-architectures/practice-results.txt)

```bash
python3 practice.py
```

练习关键融合代码, 完整脚本含输入, 证据检查和图路径:

```python
from collections import defaultdict

rankings = {"lexical": ["D1", "D2"], "dense": ["D2", "D3"]}
scores = defaultdict(float)
for ids in rankings.values():
    for rank, doc_id in enumerate(ids, start=1):
        scores[doc_id] += 1 / (60 + rank)
fused = sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))
print(fused)
```

预期为 `['D2', 'D1', 'D3']`. D2 被两路共同召回会排第一, 这并不代表它最能证明 Q1. **RRF 只融合排序信号, 不能理解“当次根因”的证据充分性.** 练习特意保留这个现象, 避免把“融合完成”误判为“答案有了充分依据”.

### 9.2 步骤, 结果与验收

| 步骤 | 执行内容 | 可观察验收 |
| --- | --- | --- |
| 1 | 使用固定语义候选 `[D2, D3]` | 不含 Q1 必需证据 D1 |
| 2 | 融合词法候选 `[D1, D2]` | 候选并集补入 D1, 但 D2 仍排第一 |
| 3 | 脚本化 search → open | 返回 D1 原文及位置, 用两次工具调用 |
| 4 | 脚本化两跳依赖查询 | 返回支付 → 结算 → 对账的潜在影响路径, 引用 D3, D4 |
| 5 | 限制只允许一次工具调用 | 第二跳无法完成, 状态为不足, 不能伪报证据齐全 |
| 6 | 手工图遍历及来源回取 | 反向沿依赖边得到同一路径, 每条边可回到原文 |
| 7 | 删掉 D4 再遍历 | 只保留直接依赖, 不推测缺失的对账关系 |

完整脚本中的断言检验这些教学不变量. 它不证明哪种系统在真实业务上更准确, 也不验证生成答案, 自动抽取, 全局社区总结和权限系统. 本次解释器和实际输出保存在结果文件.

### 9.3 后续接入真实组件时如何验收

这是复现实验边界, 不是声称本次已执行:

1. 固定同一语料快照, 访问范围和问答样本, 替换人工排名为真实词法与语义检索结果.
2. 保持生成模型, 提示和上下文预算可比, 分别记录单路, 双路融合, 可选重排的结果.
3. 将脚本决策替换为真实模型工具选择, 重复运行并记录工具轨迹与成本, 检查预算执行与未完成状态.
4. 将手工图换为目标数据的抽取图, 先验收实体与关系, 再验收局部与全局回答.
5. 根据业务要求设定验收标准, 不套用没有依据的通用准确率或延迟阈值.

## 10. 用同一批问题, 怎样比较效果才说得清? {#_10-如何用同一套证据比较效果}

以下指标定义属于本文实验设计, 不声称对应某个评测框架的默认实现.

| 维度 | 测什么 | 观测证据与判定 |
| --- | --- | --- |
| 必要证据覆盖 | 能否找到答案所需材料 | Q1 是否有 D1; Q2 是否同时有 D3, D4 |
| Recall@k (前 k 召回率) | 人工标注的相关项被找回多少 | 前 k 内相关项数 / 全部标注相关项数; 多跳任务另报告全部必需边是否齐全 |
| Context precision (上下文相关比例) | 装入上下文的片段有多少有用 | 对选入片段标注相关性, 按本文口径计数; 不混同所有框架的加权指标 |
| Claim support (结论证据支持) | 回答每个事实断言是否有依据 | 逐条对照原文, 尤其区分“潜在影响”和“实际波及” |
| 引用定位正确性 | 链接是否指向支持结论的原文 | 文档版本, 位置存在且文本支持对应断言 |
| Agent 过程完成度 | 动作是否补齐信息缺口 | 工具, 参数, 观察, 预算, 结束状态和中间证据 |
| 图质量 | 实体和边是否正确 | 别名对齐, 方向, 关系类型, 时间与来源正确 |
| 全局覆盖 | 是否只总结到局部热点 | 社区/报告范围和原始事故类型覆盖; 计数任务另做确定性核对 |
| 成本与延迟 | 资源代价是否可接受 | 同一硬件与负载下记录建库/更新成本, 模型用量, 工具次数, 延迟分布 |

没有一条必然的“性能从高到低”排序. 固定流程通常更易限制模型调用次数, 但具体延迟仍受检索和基础设施影响. GraphRAG 的离线抽取与摘要增加预处理成本, Global Search 的在线成本取决于报告范围与处理批次, 不能一概说查询都便宜.

### 10.1 答案不对时, 从哪一层开始查? {#_10-1-失败时沿证据链排查}

```text
原文有事实吗?
  → 解析是否保留?
  → 索引/图是否表示正确且版本有效?
  → 查询与权限范围是否正确?
  → 候选是否包含必需证据?
  → 排序与预算是否保留证据?
  → Agent 是否继续补齐缺口?
  → 最终断言与引用是否被证据支持?
```

检索文档中的指令只作为数据, 不覆盖工具策略. 访问控制必须落实在工具和存储层; GraphRAG 的社区报告可能聚合多份材料, 不能只过滤原文块而允许报告泄露受限内容.

## 11. 自测与参考答案

1. **混合检索能保证 Q2 的两跳关系齐全吗?** 不能. 它增加候选来源, 不自动遍历关系. 必须验证两份证据被召回, 或使用显式多跳查询/图遍历.
2. **固定流程调用一次检索 Agent, 算不算 Agentic RAG?** 检索内部具有 agentic 行为, 上层仍可保持固定流程. 说明作用层级比争论标签更准确.
3. **为什么 RRF 让 D2 排第一, 却不能用 D2 回答当次根因?** 融合只奖励排名信号, 不能替代问题与证据充分性判断.
4. **GraphRAG 中有支付 → 结算 → 对账的影响路径, 能证明三者当次都宕机吗?** 不能. 还需要当次运行状态或事故证据. 图中的依赖方向与展示的影响方向应分开.
5. **Q3 问“哪类事故最多”, 能直接看社区报告中哪个词出现最多吗?** 不能. 摘要会改变词频和粒度; 应先定义事故单位与分类口径, 再对完整记录统计.

最小练习: 把 Q1 的 D1 从词法输入中移除, 验证双路融合也无法恢复 D1; 把工具预算改为 1, 验证二跳结果标为不足; 移除图中的 D4 关系, 验证输出不再包含对账. 完成标准是解释每个变化发生在候选, 控制还是表示层, 并展示相应中间结果.

## 12. 术语表

| 英文名称与缩写 | 中文含义 | 本文具体作用 |
| --- | --- | --- |
| RAG, Retrieval-Augmented Generation | 检索增强生成 | 以外部证据支持回答 |
| 2-Step RAG | 两步 RAG | 固定先检索后生成的控制基线 |
| Hybrid retrieval / Hybrid RAG | 混合检索 / 混合架构 | 前者融合召回, 后者在特定文档指流程混合, 必须区分 |
| Agent / Agentic RAG | 智能体 / 智能体控制的 RAG | 根据观察选择工具和下一步 |
| Agent-as-retriever | 智能体承担检索职责 | 向上层交付原文证据与缺口 |
| GraphRAG | 图增强检索生成 | 用实体, 关系和派生上下文支持问答 |
| LLM, Large Language Model | 大语言模型 | 生成答案, 也可参与抽取, 摘要或决策 |
| SDK / API | 软件开发工具包 / 编程接口 | 区分真实框架接口与教学抽象 |
| Chunk / TextUnit | 文本块 / 文本单元 | 检索, 图抽取与来源定位单位 |
| Embedding / Dense retrieval | 向量表示 / 稠密向量检索 | 根据语义相似度召回片段 |
| Lexical retrieval / Inverted index | 词法检索 / 倒排索引 | 以词项查找候选, 保留错误码等线索 |
| BM25, Best Matching 25 | 词法相关性排序函数 | 为关键词一路提供排名 |
| Top-k / Recall@k | 前 k 项 / 前 k 召回率 | 分别控制候选数量和衡量相关项找回情况 |
| RRF, Reciprocal Rank Fusion | 倒数排名融合 | 不直接混合原始分值, 按排名合并候选 |
| Reranking / Cross-encoder | 重排 / 交叉编码器 | 对候选进行更细的相关性排序 |
| Prefetch / Query API | 候选预取 / 查询接口 | 表达引擎中先召回再融合的多阶段结构 |
| Just-in-time context | 按需上下文加载 | 搜索定位后才读取所需原文 |
| Entity / Relationship / Claim | 实体 / 关系 / 陈述 | 表示图中的对象, 连接和可选事实陈述 |
| Community / Community Report | 图社区 / 社区报告 | 组织连接紧密实体及其派生摘要 |
| Local Search / Global Search | 局部搜索 / 全局搜索 | 分别从具体实体和跨社区报告构建上下文 |
| Map-reduce | 分批处理再汇总 | 全局搜索处理中间要点与最终综合 |
| DRIFT | 动态推理与灵活遍历 | 官方将社区与局部探索结合的另一查询模式 |
| Context precision / Claim support | 上下文相关比例 / 结论证据支持 | 分别检查上下文质量与回答依据 |

## 13. 来源与读取边界 {#sources}

下表保留 2026-10-18 的链接核查记录. 2026-10-19 仅更新讲解与图解, 未把当日资料重新核查一遍. 在线文档可能继续变化. 本文不是指定仓库源码带读, 没有声称阅读完整源码或锁定某个提交; 未执行这些来源的服务示例.

| 一手来源 | 实际读取范围与作用 | 版本边界 |
| --- | --- | --- |
| [Lewis 等, Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) | 摘要, 用于区分原始模型论文与工程流程 | 2020 论文; 未复现训练 |
| [LangChain Retrieval](https://docs.langchain.com/oss/python/deepagents/retrieval) | Building blocks / RAG architectures / Hybrid RAG | 当日在线文档; 原 langchain/retrieval 路径重定向至此 |
| [LangGraph custom RAG agent](https://docs.langchain.com/oss/python/langgraph/agentic-rag) | 预处理, 检索工具, 决策, 判分, 改写与图连接章节 | 当日在线教程; SDK 示例未执行 |
| [Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) | RAG primer, BM25 与分块上下文缺失机制 | 2024 工程文章; 未引用性能提升为本文结果 |
| [Elastic Hybrid search](https://www.elastic.co/docs/solutions/search/hybrid-search) | 词法与向量融合说明 | 当日在线文档 |
| [Elastic RRF](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) | 排名公式, 等权子检索器, 排名窗口和常数 | 当日在线文档, 不混用旧版 API |
| [Qdrant Hybrid Queries](https://qdrant.tech/documentation/search/hybrid-queries/) | 多阶段查询, 预取与融合机制 | 在线页注明此类 Query API 自 v1.10.0 可用; 未检查安装版本 |
| [Anthropic Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Context retrieval and agentic search | 2025 工程文章; browser-act 抓取失败后使用网页工具读取 |
| [LlamaIndex Recursive Retriever + Document Agents](https://docs.llamaindex.ai/en/v0.10.17/examples/query_engine/recursive_retriever_agents.html) | 文档 Agent 与上层可组合检索器 | 明确为 v0.10.17 历史示例, 只解释架构 |
| [GraphRAG Dataflow](https://microsoft.github.io/graphrag/index/default_dataflow/) | Knowledge Model 与默认索引各阶段 | 当日在线说明; 不视为全部运行配置 |
| [GraphRAG Local Search](https://microsoft.github.io/graphrag/query/local_search/) | Entity-based Reasoning / Methodology | 当日在线说明 |
| [GraphRAG Global Search](https://microsoft.github.io/graphrag/query/global_search/) | Whole Dataset Reasoning / Methodology | 当日在线说明 |
| [From Local to Global](https://arxiv.org/abs/2404.16130) | 论文摘要, 全局问题导向总结的目标 | 2024 论文; 未复现实验 |
| [GraphRAG DRIFT](https://microsoft.github.io/graphrag/query/drift_search/) | Combining Local and Global Search / Methodology | 只说明扩展边界, 未实现 |

进入[同主题面试专题](../../interviews/rag/rag-architectures.md), 检验能否从开发与测试两个职责解释这些链路.
