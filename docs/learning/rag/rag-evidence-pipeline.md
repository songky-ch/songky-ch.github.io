---
title: "从生产问题问答到检索证据: 我的排查思路"
category: RAG
contentType: 原理讲解
pageClass: testing-notes
---

# 从生产问题问答到检索证据: 我的排查思路

<p class="article-kicker">工作记录 · R1 · 设计思路与待验证方案</p>

生产问题知识库问答是我当前业务中的一个场景. 用户询问某个日期之前的问题, 需要的不只是流畅回答, 还包括正确的日期、局点、客户和记录范围. 我还没有 RAG 评测实践, 会先从自己熟悉的 SQL 数据核对出发, 沿资料进入回答的过程检查证据.

我的方案承接 [Agent 请求链路](../agent/agent-request-map.md): 目标记录是否进入索引、是否被检索到、是否进入上下文, 分别对应不同的排查位置. 检索增强生成 (RAG) 在生成前引入外部资料, 但不会因此自动保证结果正确, 也不会自动把知识永久写入模型参数.

> R1–R3 共用 D3 合成资料库. 字段、索引、日期、权限和处理方式为场景设定, 不代表公司架构或已完成工作. Python 3.9 风格代码为不可直接运行的伪代码.

<figure><picture><source media="(max-width: 600px)" srcset="/images/rag-evidence-pipeline/two-paths-mobile.svg"><img src="/images/rag-evidence-pipeline/two-paths.svg" alt="资料处理链将源记录解析、切分并建索引; 在线问答链按范围检索索引, 组织上下文后生成回答. 无结果和检索错误进入不同出口."></picture><figcaption>图 1. 先建好可查资料, 再回答用户. 两条链通过索引衔接, 不代表每次提问都重新处理全部文档.</figcaption></figure>

## 我的核对基线: 六份合成资料

合成快照叫 `kb_d3_v1`, 统一使用 Asia/Shanghai 时区, 账号只允许访问 SITE-A / CUSTOMER-X. 为了看清边界, 六份资料既包含目标记录, 也包含容易混淆的内容. 每份问题记录在本例恰好对应一个问题, 真实系统若一份文档含多个问题, 需要额外的问题标识, 不能直接按文档数统计问题数.

| 资料 ID | 类型 | 发生时间 / 文档日期 | 局点 / 客户 | 核心内容 |
| --- | --- | --- | --- | --- |
| C101 | 生产问题 | 2026-10-18 09:10 | SITE-A / CUSTOMER-X | 光功率波动, 已安排连接器检查, 原因待确认 |
| C102 | 生产问题 | 2026-10-20 14:30 | SITE-A / CUSTOMER-X | 复测告警, 已安排再次复测, 原因待确认 |
| C103 | 生产问题 | 2026-10-21 09:00 | SITE-A / CUSTOMER-X | 温度读数异常, 正在排查 |
| C104 | 生产问题 | 2026-10-19 11:00 | SITE-B / CUSTOMER-X | 复测告警, 正在排查 |
| C105 | 生产问题 | 2026-10-20 16:00 | SITE-A / CUSTOMER-Y | 光功率波动, 正在排查 |
| G201 | 操作指南 | 2026-10-17 | SITE-A / CUSTOMER-X | 复测告警排查步骤, 不记录实际问题发生 |

用户输入固定为:

```text
请列出 2026-10-21 之前, SITE-A 给 CUSTOMER-X 记录的生产问题,
包含问题标识、发生时间和现象. 不需要推断原因.
```

示例约定“21 日之前”指发生时间严格小于 `2026-10-21T00:00:00+08:00`. 不是文档更新时间, 也不包含 21 日当天. 预期是 C101 和 C102. C103 超过边界, C104/C105 范围不符, G201 是指南而非已发生事件. 如果用户只说“前几天”, 先澄清或使用已公布的时间规则, 不能在测试时临时猜一个口径.

## 源资料到检索片段的处理链

源资料可能来自业务记录或文档. 解析器提取文本与元数据, 切分器把长文变成可检索片段, 索引器保存关键词索引、向量和定位信息. 向量是文本的数值表示, 用于比较语义接近程度; 它不是一段可读答案, 相似也不是事实正确的证明.

每个片段至少能追溯到资料 ID、资料版本、片段 ID、原文范围和访问范围. 日期、客户、局点等精确条件尽量保留结构化字段. 举一个 C102 的片段, 这里不展示或伪造任何向量数值:

```json
{
  "chunk_id": "C102:v1:01",
  "document_id": "C102",
  "document_version": "v1",
  "kind": "production_issue",
  "occurred_at": "2026-10-20T14:30:00+08:00",
  "site": "SITE-A",
  "customer": "CUSTOMER-X",
  "text": "问题 C102, 复测告警. 已安排再次复测, 原因待确认."
}
```

<figure><picture><source media="(max-width: 600px)" srcset="/images/rag-evidence-pipeline/provenance-mobile.svg"><img src="/images/rag-evidence-pipeline/provenance.svg" alt="C102源记录经过解析成为带元数据的片段, 片段进入索引; 检索结果和最终引用保留同一资料及版本标识, 可反查原文."></picture><figcaption>图 2. 每层保留身份和版本, 才能解释模型究竟看了哪份资料.</figcaption></figure>

这里的知识库不等于向量数据库. 原文存储、元数据、关键词检索、向量检索都可能分别存在. 不同产品可以把它们合并, 也可以拆成多个服务. 测试先识别责任, 不根据一个组件名称想象实际部署.

若源记录 C102 已更新为 v2, 索引还是 v1, 模型忠实复述 v1 也可能不符合最新业务事实. 因此需要分别记录源版本、索引版本与同步时间. “同步任务成功”还要核对实际片段是否可见, 删除或权限撤销是否已生效. 本例冻结 v1 只是为了固定分析条件, 不能替代实际系统的新鲜度要求.

## 用户问题到上下文的查询链

在线处理先解析用户条件, 再与服务端可信权限相交. 用户写了 CUSTOMER-Y 不意味着账号获得 Y 的权限. 元数据过滤用于限定候选, 检索用于找相关内容, 重排用于重新比较候选和问题, 最后再按长度预算组织给模型看的上下文.

这些环节都不是必需的固定产品组件. 简单系统可以不用重排, 也可以使用结构化查询直接取得记录. 关键是明确“模型实际看到什么”, 而不是只保留搜索接口的返回.

<figure><picture><source media="(max-width: 600px)" srcset="/images/rag-evidence-pipeline/context-mobile.svg"><img src="/images/rag-evidence-pipeline/context.svg" alt="六份资料按日期、类型和权限筛选, 目标为C101和C102; 检索结果还要进入上下文才能供模型使用, 上下文若截掉C102会导致证据遗漏."></picture><figcaption>图 3. 源库有记录、索引能搜到、模型收到片段, 是三个不同的条件.</figcaption></figure>

本例的数据小, 可手工确认两份资料都符合范围. 若系统检索到了 C101/C102, 但拼上下文时只保留 C101, 问题就在检索之后. 提高检索数量无法自动修复上下文截断. 同样, 上下文有“原因待确认”, 最终回答却写“已确认由连接器污染导致”, 应检查生成是否编造了因果.

下面展示数据职责, 不是任何框架的真实 API. `retrieve_authorized` 按固定快照、用户条件和可信权限检索; `pack_context` 返回实际放入模型的内容和未放入清单; `generate_with_evidence` 通过已接入的模型服务生成, 本文没有调用它.

```python
# 教学伪代码, 不可直接运行.
scope = resolve_scope(question, clock, trusted_principal)
if scope.needs_clarification:
    answer = ask_for_missing_fields(scope)
else:
    search = retrieve_authorized(question, scope, snapshot="kb_d3_v1")
    if search.status != "ok":
        answer = explain_retrieval_error(search.status)
    elif not search.hits:
        answer = explain_no_evidence(scope)
    else:
        context = pack_context(search.hits, token_budget=1600)
        if not context.items:
            answer = explain_no_evidence(scope)
        else:
            answer = generate_with_evidence(question, context.items)
        save_evidence(search, context, answer)
```

1,600 token 是本例用于解释上下文预算的配置, 不是推荐值, 也不等于 1,600 个汉字. 系统需要用真实模型的分词规则计算. 此代码只展示已有命中的取证流程; 完整评测还要记录澄清、空结果和错误分支的状态, 不能把未进入 `save_evidence` 的分支悄悄丢出报告.

## 列举与精确计数的证据边界

从前 5 条相关片段里看到 2 个问题, 不能推出全库只有 2 个问题. Top-K 检索解决的是候选相关性, 不天然保证穷尽整个集合. 本例能说“两条”, 是因为合成快照只有六份已完整核对的资料, 并明确过滤后只有 C101/C102.

真实平台需要完整名单或精确总数时, 若问题记录有结构化字段, 可以用具有完整分页/聚合语义的查询获得集合, 再让模型解释结果. 这种实现可能位于 Agent 的业务工具路径, 不必硬塞入文本检索. 如果系统只能提供相关片段, 回答应说明“本次检索找到以下记录”, 并避免声称这是全部. 是否允许这种部分回答应写进任务契约.

## 遗漏 C102 时的排查顺序

<figure><picture><source media="(max-width: 600px)" srcset="/images/rag-evidence-pipeline/diagnosis-mobile.svg"><img src="/images/rag-evidence-pipeline/diagnosis.svg" alt="依次检查源记录是否在快照、索引是否包含目标、检索是否返回目标、上下文是否包含目标和回答是否使用目标; 每个否分支分别指向源数据、索引、检索、上下文和生成问题."></picture><figcaption>图 4. 逐层确认 C102 首次在哪一步消失, 避免把所有失败都交给提示词.</figcaption></figure>

| 检查点 | 手里要拿到什么 | 本例的失败解释 |
| --- | --- | --- |
| 源记录 | 固定快照及真实字段 | C102 未入快照: 数据或测试准备问题 |
| 索引 | 文档/片段 ID、版本 | 源库有而索引没有: 解析、同步或索引链问题 |
| 检索 | 实际条件、候选 ID、顺序 | 索引有但未返回: 条件、检索或候选截断问题 |
| 上下文 | 最终片段与删减记录 | 命中了但没传给模型: 去重、预算或拼接问题 |
| 回答 | 文字、引用、证据对应 | 证据已给却遗漏/编造: 生成或任务理解问题 |

一次请求可能有多个故障, “首次消失”是排查起点, 不是未经验证就宣布唯一根因. 例如先修同步后还可能发现日期过滤错误. 固定其他条件再重放, 才能确认这次修复改变了哪个环节.

相关工作记录: [R2: 切分、过滤与重排](./retrieval-candidates.md), 再用 [R3: 检索结果评测](../ai-evaluation/retrieval-metrics.md)量化遗漏与排序. 配套 [R1 面试专题](../../interviews/rag/rag-evidence-pipeline.md).

## 术语与依据

| 英文名称与缩写 | 中文含义 | 本篇具体作用 |
| --- | --- | --- |
| RAG | 检索增强生成 | 检索资料后据此生成 |
| Chunk / Metadata | 片段 / 元数据 | 保存内容以及日期、范围和来源 |
| Embedding / Index | 向量表示 / 索引 | 支持相关内容查找, 不等于答案 |
| Context / Token | 上下文 / 模型处理单位 | 确认实际输入与长度预算 |
| Provenance / Snapshot | 来源追溯 / 快照 | 将回答关联到固定资料版本 |
| Top-K | 前 K 个结果 | 限定返回量, 不保证完整枚举 |

核查日期: 2026-10-22. [RAG 原始论文 v4 摘要](https://arxiv.org/abs/2005.11401v4)用于核对检索资料与生成结合的基本概念, 未复现其训练或实验, 本文流程不是论文架构复刻. [Azure AI Search 混合检索概览](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview)用于核对关键词和向量检索的不同职责, 未调用 Azure. D3 数据、权限和故障定位均为方案设定; 代码仅做静态语法检查, 未执行真实知识库问答.
