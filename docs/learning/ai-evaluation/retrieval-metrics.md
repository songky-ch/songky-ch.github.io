---
title: "我的检索评测口径: 召回、排序与证据覆盖"
category: AI 评测
contentType: 实践教程
pageClass: testing-notes
---

# 我的检索评测口径: 召回、排序与证据覆盖

<p class="article-kicker">工作记录 · R3 · 设计思路与待验证方案</p>

设计检索评测时, 我最需要先写清“这次应该找到什么”. 查询一条明确记录与列全两条生产问题, 即使返回相同资料, 任务完成情况也可能不同. 因此我的口径从预期证据出发, 再分别计算召回、排序与完整覆盖.

这份方案连接 [R2 的候选链](../rag/retrieval-candidates.md)和 [A3 的任务设计](./agent-benchmark-design.md), 使用 D3 合成快照. 返回顺序和统计均为手工推演, 未执行真实检索; Python 3.9 风格评分代码为伪代码. 当前只评价检索证据, 生成回答的忠实、正确与引用质量留在后续 R4 分析.

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-metrics/sets-mobile.svg"><img src="/images/retrieval-metrics/sets.svg" alt="预期相关资料是C101/C102, 返回前三项是G201/C101/C103, 交集只有C101. 命中1项除以相关总数2得到召回50%, 除以返回位置3得到精确率33.33%."></picture><figcaption>图 1. 同一个命中数, 换一个分母, 回答的问题就变了.</figcaption></figure>

## 相关标注与评价单元

主问题 Q1 是“列出 2026-10-21 之前 SITE-A / CUSTOMER-X 的生产问题, 包含标识、发生时间和现象”. 在冻结快照 `kb_d3_v1` 中, 预期相关资料集合 `G={C101,C102}`. C103 日期越界, G201 是指南, 都不满足这条任务. C104/C105 更不在账号允许范围, 任何返回未授权内容的情况需另记权限失败, 不能用较高召回抵消.

本例每个问题对应一份短资料, 一份资料只有一个足够完整的片段. 因此可以按资料 ID 计数. 真实长文多片段时应先定评测单元: 检查资料级找到没, 还是片段是否包含必要事实. 只有父文档 ID 命中, 但返回片段没有发生时间, 不应自动宣称回答证据已齐.

一条最小标注示意如下:

```json
{
  "query_id": "D3-Q1",
  "snapshot": "kb_d3_v1",
  "unit": "document_with_required_fields",
  "question": "列出2026-10-21之前SITE-A/CUSTOMER-X的生产问题及发生时间和现象",
  "relevant_ids": ["C101", "C102"],
  "required_evidence_groups": [["C101"], ["C102"]],
  "k": 3,
  "short_return_policy": "missing_slots_count_as_nonrelevant"
}
```

`required_evidence_groups` 是这份方案的自定义字段: 外层各组都要覆盖, 每组内部的任意一个证据即可满足该组. 这里两组分别只有一个 ID, 表示两条都必须找到. 如果后续有两份经核对的等价资料都能证明同一事实, 可以放同一组; 不要为了凑命中数随便认定等价.

标注应根据原文和任务口径建立, 不能从被测系统的返回直接反推“这些就是全部相关资料”. 大库无法穷尽标注时, 需要披露已标范围和未判资料. 否则所谓召回率只是对已知标注的覆盖, 不能声称是全库真实召回.

## 前 K 项的召回与精确率

为了展示缺陷, 假设一个**漏做类型/日期约束的待测版本**返回 `[G201,C101,C103,C102]`. 这是错误检索的合成快照, 不是 R2 正确过滤方案的正常输出. G201/C103 在账号允许范围内, 但不符合 Q1 的业务范围.

固定 K=3, 先取前三个, 只有 C101 相关:

- Recall@3 (召回率): `1/2=50%`, 应找到的两份中找回一份.
- Precision@3 (精确率): `1/3≈33.33%`, 三个位置中有一个有用.
- Hit@3 (是否命中): `1`, 至少有一份相关资料. 多问题平均后可称命中率.
- 完整证据覆盖: `0`, 必需的 C102 没有找到. 这是这份方案定义的任务级布尔检查.

这里 Precision@K 固定除以 K. 如果只返回 1 条相关结果而 K=3, 记为 `1/3`, 同时记录实际返回数 1. 有的实现会除以实际返回数得到 100%, 两者含义不同, 比较前必须确认. 本篇不把两种口径混用.

将 K 调到 4, 同一排序中的 C102 被纳入, Recall@4 变成 100%, Precision@4 为 `2/4=50%`. 这个小例子里两项都上升, 所以“加 K 一定降低精确率”也不正确. 但增加候选会改变后续重排/上下文成本, 而且完整检索证据仍可能在拼上下文时被截掉. 大库中不能因为某个 K 的 Recall@K 高, 就承诺所有枚举任务都完整.

重复片段还会虚增统计. 本例按资料 ID 评价, 先取原始前 K 项, 重复 ID 只在首次出现处贡献一次, 后续位置不计命中, 也不向 K 之外补位. 如果产品本身先去重再取 K, 那是另一个明确的观测位置, 需要另存结果并标明.

## 首个命中与整体排序质量

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-metrics/ranks-mobile.svg"><img src="/images/retrieval-metrics/ranks.svg" alt="版本A前三项为G201/C101/C103, 首个相关在第2位; 版本B为C101/C102/G201, 首个相关在第1位且证据齐全. 首相关倒数排名只关注第一个, 不证明后续覆盖."></picture><figcaption>图 2. 尽早看到第一条有用资料, 和收集齐全部必需资料, 需要分别观察.</figcaption></figure>

倒数排名 RR 看第一条相关资料的位置. Q1 的首次相关出现在第 2 位, RR@3 为 `1/2=0.5`; 前 3 项无命中则为 0. 再设 Q2 是“C102 的发生时间”, 其相关集合只有 C102, 另一次合成返回把 C102 放在第一位, RR@3=1. 对这两条问题取平均, MRR@3=`(0.5+1)/2=0.75`. 它不是“第一条平均排在第 0.75 位”, 也不能对 0.75 取倒数来代替平均名次.

MRR 只看第一个相关项. 对 Q1, `[C101,G201,C103]` 的 RR@3 已是 1, 但仍漏 C102. 列表题与多证据题不能只靠 MRR 验收.

如果资料相关程度有等级, 可以用归一化折损累计增益 nDCG. 先给每个位置一个人工定义的相关等级 `rel_i`, 再让靠前的相关项贡献更多:

```text
DCG@K = sum((2^rel_i - 1) / log2(i + 1)), i 从 1 到 K
IDCG@K = 同一标注集合在理想排序下的 DCG@K
nDCG@K = DCG@K / IDCG@K
```

本例先用二值等级, 相关为 1、不相关为 0. 对 `[G201,C101,C103]`, DCG@3=`1/log2(3)≈0.63093`. 理想前三项应把两份相关资料排最前, IDCG@3=`1+1/log2(3)≈1.63093`, 所以 nDCG@3≈`0.38685`. 不是除以实际返回中已有的一份相关资料构造“理想值”, 否则会掩盖漏召回.

若使用 0/1/2 等级, 要先定义“部分有用”和“足以回答”分别意味着什么, 再复核标注一致性. nDCG 并不自动知道业务风险, 相关性高但越权仍应判权限失败. `IDCG=0` 的无相关资料题应按事先规则单列, 避免除零或悄悄记满分.

## 多份必需证据的完整覆盖

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-metrics/coverage-mobile.svg"><img src="/images/retrieval-metrics/coverage.svg" alt="列全生产问题要求分别覆盖C101和C102两个必需组. 只找到C101时命中成立但完整覆盖失败, 两组都覆盖才通过. 等价证据在同一组内任选一份, 不是所有资料都要找到."></picture><figcaption>图 3. 先定义必须满足的事实组, 再判断现有证据能否一起完成任务.</figcaption></figure>

Q1 要列出两个问题, 因此需要两组都满足. 如果另一条任务问“证明 C102 发生过复测告警”, 而经人工确认原记录和一份复盘纪要都完整证明这件事, 两者可以成为同组可替代证据. 此时只找到其中一份就可能够用. “必须找齐两份”与“任找一份都行”不能用同一条硬编码规则.

下面的评分器演示本章约定. `normalize_id` 将片段映射到本次评价的稳定资料 ID; 真正使用前必须验证映射以及必要事实字段. 无相关资料题转交单独流程, 不是自动认为检索完美.

```python
# 教学伪代码, 不可直接运行. k 为正整数, 标注已经复核.
def grade_retrieval(raw_hits, relevant_ids, required_groups, k):
    if not relevant_ids:
        return {"status": "no_answer_case"}
    seen = set()
    found = set()
    first_rank = None
    for rank, hit in enumerate(raw_hits[:k], start=1):
        doc_id = normalize_id(hit)
        if doc_id in seen:
            continue
        seen.add(doc_id)
        if doc_id in relevant_ids:
            found.add(doc_id)
            if first_rank is None:
                first_rank = rank
    full_coverage = (
        all(found.intersection(group) for group in required_groups)
        if required_groups else None
    )
    return {
        "precision_at_k": len(found) / k,
        "recall_at_k": len(found) / len(relevant_ids),
        "rr_at_k": 1 / first_rank if first_rank else 0,
        "full_coverage": full_coverage
    }
```

无答案题要区分“快照确实没有支持资料”“用户无权获取”和“检索服务出错”. 第一类可测空结果处理与无依据回答, 第二类检查权限, 第三类检查错误反馈; 不混成一个 Recall=0. 已检索到的未标注资料也不能静默当不相关, 应进入补标或保留未知, 报告标注覆盖情况.

## 百条问题的分组与汇总口径

构造另一份 **100 条问题的合成报告**, 不是本次交付了完整百题数据集. 固定 K=3、资料 ID 计数、同一快照与权限. 为突出分母, 这里只汇总有相关资料且标注完整的题:

| 任务组 | 题数 | 返回相关资料情况 | 命中题数 | 完整覆盖题数 |
| --- | ---: | --- | ---: | ---: |
| 只需一份证据 | 80 | 72 题找到, 8 题没找到 | 72 | 72 |
| 需两份证据 | 20 | 12 题找齐, 6 题只找一份, 2 题没找到 | 18 | 12 |
| 合计 | 100 | 共找到 102 份相关资料, 应找 120 份 | 90 | 84 |

<figure><picture><source media="(max-width: 600px)" srcset="/images/retrieval-metrics/report-mobile.svg"><img src="/images/retrieval-metrics/report.svg" alt="100题中90题至少命中, 84题完整覆盖. 单证据组完整覆盖72/80为90%, 双证据组12/20为60%. 总平均会掩盖双证据任务较弱."></picture><figcaption>图 4. 90% 命中率, 不代表 90% 的问题已经有足够证据.</figcaption></figure>

总体命中率 `90/100=90%`, 完整覆盖率 `84/100=84%`. 单证据组完整覆盖 `72/80=90%`, 双证据组只有 `12/20=60%`. 如果只报总体, 就看不出组合任务是弱项.

对每题召回率等权平均, 即宏平均, 为 `(72+12+6×0.5)/100=87%`. 把所有题的命中数和相关总数相加后再除, 即微平均, 为 `(72+12×2+6)/(80+20×2)=102/120=85%`. 微平均让相关资料更多的题拥有更大权重; 不能把 87% 与 85% 当作不同版本效果来比较.

报告还需带上实际返回数量、未知/无答案/权限失败分组、候选层与上下文层的观测位置, 以及检索耗时与输入规模. 本例没有真实时延数据, 不填造 P95. 两个版本比较时同时看逐题差异, 避免平均相同却一批关键任务退化. 召回改善只是证据条件改善, 不等于生成答案已经正确.

配套 [R3 面试专题](../../interviews/ai-evaluation/retrieval-metrics.md). 后续 R4 将继续检查“证据齐了, 回答是否忠实和完整”, R5 再系统组织 RAG benchmark, 不把本章的局部算例冒充完整评测集.

## 术语与依据

| 英文名称与缩写 | 中文含义 | 本篇具体作用 |
| --- | --- | --- |
| Relevance / Ground truth | 相关性 / 参考标注 | 固定问题、快照、权限和评价单元 |
| Recall@K / Precision@K | 前 K 项召回率 / 精确率 | 分别看找全与候选有用程度 |
| Hit@K | 前 K 项是否命中 | 只要求至少一个相关项 |
| RR / MRR | 倒数排名 / 平均倒数排名 | 观察首个相关结果的位置 |
| DCG / nDCG | 折损累计增益 / 归一化值 | 用相关等级和位置评价排序 |
| Macro / Micro average | 宏平均 / 微平均 | 区分逐题等权与汇总计数 |
| Evidence coverage | 证据覆盖 | 这份方案定义的必需事实组满足情况 |

核查日期: 2026-10-22. 定义参考 Stanford《Introduction to Information Retrieval》的 [Precision 与 Recall](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html)、[排序评测及 nDCG 公式](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html). [TorchMetrics 1.9.0 MRR 文档](https://lightning.ai/docs/torchmetrics/stable/retrieval/mrr.html)用于核对按问题聚合及空标注处理需显式选择, 未运行该库. 本文缺位计数、去重、证据分组和合成统计是明确的示例约定, 不宣称是所有框架默认行为.
