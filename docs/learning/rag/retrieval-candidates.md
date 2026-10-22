---
title: "检索不到目标记录时, 我会检查哪些环节"
category: RAG
contentType: 实践教程
pageClass: testing-notes
---

# 检索不到目标记录时, 我会检查哪些环节

<p class="article-kicker">工作记录 · R2 · 设计思路与待验证方案</p>

面对“库里有 C102, 结果里却没有”的现象, 我的排查方案是保留每一步的候选集合. 客户字段被切掉、日期过滤用错、先取前两条再过滤, 都可能造成遗漏, 仅比较最终回答难以区分这些原因.

我继续使用 [R1 的六份 D3 合成资料](./rag-evidence-pipeline.md), 分别推演切分、过滤、混合检索、融合和重排改变了什么. 排名、数量和配置均为示例输入, 并非真实检索实测; Python 3.9 风格代码为伪代码, 这份方案尚未在公司系统实施.

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-candidates/map-mobile.svg"><img src="/images/retrieval-candidates/map.svg" alt="资料切分影响可检索单元; 权限和业务过滤限定范围; 关键词与向量两路检索并行后融合去重, 再重排和组织上下文. 空候选与异常返回各有出口."></picture><figcaption>图 1. 每一步改变的对象不同: 切分改资料单元, 过滤改范围, 检索取候选, 重排改候选顺序.</figcaption></figure>

## 切分后的记录完整性

C102 原记录同时包含局点、客户、发生时间、现象和处理状态. 若恰好在日期之后切开, 就可能出现:

```text
片段 A: C102, SITE-A, CUSTOMER-X, 2026-10-20 14:30.
片段 B: 复测告警. 已安排再次复测, 原因待确认.
```

只搜到 B, 模型知道现象, 却不知道时间和对象. 如果相邻记录 C104 也写“复测告警”, 还可能混淆两个局点. 解决思路是让片段保留父记录 ID 与必要元数据, 并按业务语义切分; 不是把全文一股脑塞进每个片段.

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-candidates/chunks-mobile.svg"><img src="/images/retrieval-candidates/chunks.svg" alt="机械切分将C102的身份日期与现象分到两段; 语义切分保留一条完整问题, 长文则给子片段保留父记录身份和必要元数据."></picture><figcaption>图 2. 检索到一个句子, 不代表拿到了判断它适用范围的条件.</figcaption></figure>

对于很短的结构化问题记录, 一条记录一个片段往往更容易理解和核对. 对长篇排查报告, 可以按标题与段落切分, 子片段继承资料 ID、版本、权限和日期. 本示例方案可先试“目标约 400 token、重叠约 60 token”, 但这只是待比较配置, 不是通用最佳值. 实际片段还需尊重句子、表格和字段边界, 并核对最终长度.

重叠能减少边界信息断裂, 也会产生重复证据. 两个片段都来自 C102, 不能算找到了两条生产问题. 如果改了切分策略导致片段 ID 全变, 后续评测应通过稳定资料 ID 或证据跨度重新映射标注, 不能把旧片段 ID 原封不动当新真值.

## 权限与业务范围的过滤位置

换一个更聚焦的问题: “查 SITE-A / CUSTOMER-X 在 2026-10-21 之前发生的复测告警.” 按 R1 的快照, 目标是 C102. C104 也有相同现象, 但局点不同; C103 在时间范围之外. “语义很像”不能覆盖这些限制.

关键词检索擅长利用问题编号、代号和原词匹配; 向量检索能补充“重新检测时报异常”与“复测告警”这类近义表达. 它们都不能天然代替授权或精确日期过滤. 关键词分词也可能把代号拆散, 精确 ID 查询应按字段契约选择精确匹配方式, 而非假定任意全文搜索都精确.

用户条件与账号范围要相交. 在本例先约束 SITE-A / CUSTOMER-X、`kind=production_issue` 和发生时间早于 21 日零点, 允许搜索的记录只有 C101/C102. 查询含义再决定 C102 比 C101 更相关. 日期字段不能误用资料更新时间; 时间换算与端点含义必须和 benchmark 一致.

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-candidates/filter-mobile.svg"><img src="/images/retrieval-candidates/filter.svg" alt="未过滤的模拟排名为C105、C103、C102等, 先截取前2再过滤会得到空集合; 在符合权限与日期的C101/C102中检索则有机会返回C102. 本例只解释候选不足, 不承诺所有前过滤都无损."></picture><figcaption>图 3. 空结果可能来自候选截断, 不代表符合条件的资料不存在.</figcaption></figure>

假设不加范围约束的合成排名前四是 `[C105, C103, C102, C101]`. 先取前 2 个再做完整范围检查, C105 客户不符、C103 日期不符, 结果为空. 如果在符合范围的 C101/C102 中检索, 就有机会拿到 C102. 增大最初候选数量可能缓解“后过滤不够”, 但不能替代权限控制, 也不能保证对所有输入都够用.

这是集合层面的解释. 不同引擎的“前过滤”“后过滤”可能发生在图遍历、分片合并或全局 Top-K 的不同位置. Azure 官方文档就明确区分这些位置及召回风险. 不能只看到参数名字便推断执行过程, 实际采用的引擎需要查对应版本. 无论过滤位置如何, 未授权内容不能交给重排模型、生成模型或用户; 返回边界仍需可信权限核对.

## 两路候选的融合与重排

BM25 一类关键词分数与向量相似度没有天然统一量纲. 将 `8.7 + 0.82` 相加并按总分排名, 数值大小本身没有解释力. 可以采用按名次融合的方法, 如倒数排名融合 (RRF), 或先校准再组合分数; 本篇只展开前者.

在前述合法的 C101/C102 范围里, 构造两路候选. 名次为示例输入, 不是运行结果:

| 资料 | 关键词名次 | 向量名次 | 本例 RRF 得分, 常数 c=60 |
| --- | ---: | ---: | ---: |
| C102 | 1 | 1 | `1/61 + 1/61 ≈ 0.03279` |
| C101 | 2 | 2 | `1/62 + 1/62 ≈ 0.03226` |

对每份资料, 每出现于一路就贡献 `1/(c+名次)`, 没出现不贡献. 常数 `c=60` 是本例选择, 不是候选数量 K. 这个值越大, 前后名次间的差距越平缓. 公式与常数含义可对照 [RRF 官方说明](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking). RRF 分数不是相关概率, 0.03279 也不是“3.279% 相关”.

为看懂分歧, 再保持同一个问题, 只把向量名次交换: C101 第一、C102 第二. 两者都得到 `1/61+1/62≈0.03252`, 此时需要明确稳定的平分处理或交给重排, 不能宣称融合一定知道哪条正确. 资料未出现在任何候选里时, 融合和普通重排都无法把它变出来.

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-candidates/ranking-mobile.svg"><img src="/images/retrieval-candidates/ranking.svg" alt="关键词和向量各给名次, 对相同资料汇总排名贡献并去重; 重排重新比较问题与候选, 只改变已有候选的顺序, 上下文预算决定最终保留项."></picture><figcaption>图 4. 融合利用两路名次, 重排重新判断候选; 两者都受候选集合约束.</figcaption></figure>

重排通常再看一次“问题 + 候选文本”, 比较候选是否真正回答该问题. 本例的成功预期是将发生复测告警的 C102 放在 C101 前, 但是否实现必须实测, 不能把预期填成真实模型结果. 若检索阶段漏掉 C102, 单纯重排 C101 无法补回它; 需要扩大或修正检索路径.

R1 的问题是“列出有哪些生产问题”, C101 和 C102 都相关; 本节问题缩小为“复测告警”, 此时 C101 是同范围的干扰项. **相关性必须绑定具体问题**, 同一份资料不能永久贴上“相关/不相关”的标签.

## 保留中间结果的版本对比

方案设定可以采用关键词取 20、向量取 20、融合去重后最多 30、重排保留 6、上下文预算 1,600 token. 这用于说明各处 K 的不同含义, 不是六份小资料实际能返回 30 份, 更不是生产推荐参数. 小库只有两份合法候选时, 就应按实际数量记录, 不填充虚构结果.

```python
# 教学伪代码, 不可直接运行.
allowed_scope = intersect(query_filters, trusted_permissions)
lexical = keyword_search(question, allowed_scope, limit=20)
semantic = vector_search(question, allowed_scope, limit=20)
candidates = fuse_by_rank_and_deduplicate(lexical, semantic, limit=30)
if not candidates:
    result = no_evidence()
else:
    ranked = rerank(question, candidates)
    context = pack_context(ranked[:6], token_budget=1600)
    result = record_candidates_and_context(lexical, semantic, ranked, context)
```

`intersect` 返回不可越权的查询范围, `fuse_by_rank_and_deduplicate` 按本次选定的证据单元去重, `rerank` 只排序已有候选. 多片段长文是否合并到父文档, 要按任务决定: 问题数量统计需按问题 ID, 证据段落检索可保留多个不同片段. 本伪代码仅展开正常检索和空结果; 检索/重排服务错误必须记录为错误状态, 不能冒充空结果.

对比配置时保留问题集、原文快照、权限、模型版本和评分标准, 一次改变一个需要验证的因素. 例如先固定检索模型比较两种切分, 再固定切分比较关键词/向量/混合; 记录每路候选 ID、融合后 ID、重排顺序、最终上下文和耗时. 不只保存最终答案, 否则“回答变好了”无法解释是谁起的作用.

下列 demo 展示怎样读证据, 不提供虚构的性能提升:

| 可观察现象 | 先检查什么 | 不应直接得出的结论 |
| --- | --- | --- |
| C102 在索引中, 两路候选都没有 | 查询表达、过滤字段、检索配置 | “生成模型不行” |
| 两路有 C102, 融合后丢失 | 去重键、候选截断、融合规则 | “原文缺失” |
| 重排有 C102, 上下文没有 | 长度预算、顺序、删减记录 | “重排没找到” |
| 上下文有两段 C102, 却说两条问题 | 父记录映射与计数口径 | “召回很好, 答案自然正确” |

接下来 [R3](../ai-evaluation/retrieval-metrics.md)会把这些候选变成可手算的指标. 配套 [R2 面试专题](../../interviews/rag/retrieval-candidates.md).

## 术语与依据

| 英文名称与缩写 | 中文含义 | 本篇具体作用 |
| --- | --- | --- |
| Chunking / Overlap | 切分 / 重叠 | 保留语义边界, 同时控制重复证据 |
| BM25 / Embedding | 关键词相关性方法 / 向量表示 | 提供不同的候选查找路径 |
| Pre-filter / Post-filter | 前过滤 / 后过滤 | 约束范围, 执行位置因引擎而异 |
| Hybrid search / RRF | 混合检索 / 倒数排名融合 | 合并两路候选, 避免直接加不同量纲分数 |
| Reranking | 重排 | 重新比较问题和已有候选 |
| Candidate / Top-K | 候选 / 前 K 项 | 定义每层可处理的结果范围 |

核查日期: 2026-10-22. [Azure 混合检索概览](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview)用于核对并行全文/向量检索及 RRF 合并机制; [向量过滤说明](https://learn.microsoft.com/en-us/azure/search/vector-search-filters)用于核对过滤位置与遗漏风险. 这些是 Azure 的实现说明, 未把其 API 或默认值推广为通用标准, 未实际接入该服务. 本篇切分、候选、RRF 算例与参数为方案设定, 未取得真实召回、时延或效果提升数据.
