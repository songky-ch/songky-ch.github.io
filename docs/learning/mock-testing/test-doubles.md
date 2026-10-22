---
title: "查询依赖不可用时, 我的 Mock 测试设计"
category: Mock 测试
contentType: 实践教程
pageClass: testing-notes
---

# 查询依赖不可用时, 我的 Mock 测试设计

<p class="article-kicker">工作记录 · M1 · 设计思路与待验证方案</p>

Mock 是我目前需要补齐的薄弱项, 还没有形成实际项目经验. 我从熟悉的生产问题查询入手: 如果查询服务未就绪, 或返回数据不断变化, 我会怎样单独检查摘要逻辑对数量和编号的处理?

我的方案是保留真正要验证的摘要逻辑, 让可控的对象替代查询依赖. 我把这类替代对象记为测试替身 (Test Double), 再按固定返回、简化实现和调用记录区分用途. 它与[数据准备和隔离](../api-testing/api-data-lifecycle.md)处理的是不同边界.

> 摘要程序、依赖和三条简化记录均为方案设定, 不复用 I3 的日期快照. Python 3.9 风格代码为伪代码, 尚未执行 Mock 测试.

## 我保留的被测逻辑与替换边界

假设摘要逻辑如下. `fetch_issues` 是调用方传进来的查询函数, 约定接收局点、客户, 返回 `total` 和本页 `items`. 本篇只有三条小记录, 查询页大小为 20, 所以匹配项可以全部返回; 后续若有分页, 摘要数量仍应使用约定的 `total`, 不能自动换成 `len(items)`.

```python
# 教学伪代码, 不可直接运行.
def build_summary(site_id, customer_id, fetch_issues):
    data = fetch_issues(site_id=site_id, customer_id=customer_id)
    return {
        "text": "找到 {} 条生产问题".format(data["total"]),
        "first_ids": [row["id"] for row in data["items"]],
    }
```

本次被测对象是 `build_summary`, 要验证它传对条件、读对字段、组织对输出. 它不负责真实数据库如何筛选. 把 `fetch_issues` 换掉以后, 数据库、网络和认证链路就不在这条测试的证据范围内.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/test-doubles/boundary-mobile.svg"><img src="/images/test-doubles/boundary.svg" alt="真实链路为摘要程序调用查询适配器再访问服务; 替身测试保留摘要程序, 让调用转向可控替身, 真实网络和服务不在本条测试覆盖范围内."></picture>
<figcaption>图 1. 先画被测对象的边界. 替换边界右侧的依赖, 边界左侧的目标代码继续真实执行.</figcaption>
</figure>

这张图对应我需要避免的一种替换方式: 如果连 `build_summary` 本身也替换成固定字典, 再断言它返回这个字典, 检查到的只是替身中预设的答案. 我原本要验证的业务逻辑并未运行. 替身不是“哪里难测就把哪里变成成功”.

## 固定返回: Stub

我的固定返回方案只需要一个普通函数, 查询依赖返回以下两条记录:

```python
# 教学伪代码, 不可直接运行. 此函数有意不按参数筛选.
def fixed_query(*, site_id, customer_id):
    return {
        "total": 2,
        "items": [{"id": "PRD-0201"}, {"id": "PRD-0202"}],
    }

actual = build_summary("SITE-A", "CUSTOMER-X", fixed_query)
assert actual == {
    "text": "找到 2 条生产问题",
    "first_ids": ["PRD-0201", "PRD-0202"],
}
```

这类提供预设返回值的替身通常称为 Stub, 即桩. 它让摘要程序稳定收到同一份输入, 适合验证正常结果和空结果的转换. 若要看无结果时是否显示“找到 0 条”, 可以在另一条独立用例中提供 `{"total": 0, "items": []}`.

不过, 如果摘要程序把 CUSTOMER-X 错传成 CUSTOMER-Y, 这个函数仍会返回相同的两条记录. 输出断言可能照样通过. 这不是“Mock 工具没用”, 而是这个替身从未承诺检查参数.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/test-doubles/fixed-mobile.svg"><img src="/images/test-doubles/fixed.svg" alt="固定桩对正确的CUSTOMER-X和错误的CUSTOMER-Y都返回同样两条记录, 因此仅比较摘要输出无法发现传参错误."></picture>
<figcaption>图 2. 同样的输出可能来自不同输入. 要发现传错客户, 必须增加能区分这两种调用的证据.</figcaption>
</figure>

沿两条箭头看, 正确参数与错误参数都落到“返回 2 条”. 如果测试目标包含传参, 就需要让替身对参数作出不同反应, 或直接记录并核对调用. 这正是后面两种方式的用途.

## 按条件返回: 简化实现 Fake

现在改用三条独立示例记录. PRD-0201、PRD-0202 属于 SITE-A / CUSTOMER-X; PRD-0205 属于 SITE-A / CUSTOMER-Y. 我按固定表中顺序返回, 不模拟日期、权限、排序或数据库事务.

```python
# 教学伪代码, 不可直接运行. 简化实现只负责本例的两项筛选.
class InMemoryIssueQuery:
    def __init__(self):
        self.rows = [
            {"id": "PRD-0201", "siteId": "SITE-A", "customerId": "CUSTOMER-X"},
            {"id": "PRD-0202", "siteId": "SITE-A", "customerId": "CUSTOMER-X"},
            {"id": "PRD-0205", "siteId": "SITE-A", "customerId": "CUSTOMER-Y"},
        ]

    def fetch(self, *, site_id, customer_id):
        matched = [dict(row) for row in self.rows
                   if row["siteId"] == site_id
                   and row["customerId"] == customer_id]
        return {"total": len(matched), "items": matched}

fake = InMemoryIssueQuery()
assert build_summary("SITE-A", "CUSTOMER-X", fake.fetch)["text"] == "找到 2 条生产问题"
assert build_summary("SITE-A", "CUSTOMER-Y", fake.fetch)["first_ids"] == ["PRD-0205"]
assert build_summary("SITE-B", "CUSTOMER-X", fake.fetch)["text"] == "找到 0 条生产问题"
```

这种能够做少量实际工作的简化替身通常称为 Fake. 它比固定返回更能支持连贯场景, 例如创建后查询、不同筛选得到不同结果; 代价是我需要维护它的行为, 防止把自己的过滤错误写进替身.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/test-doubles/filter-mobile.svg"><img src="/images/test-doubles/filter.svg" alt="三条内存记录经局点与客户筛选后, A/X留下0201和0202, A/Y留下0205, B/X为空; 每次测试有独立的替身实例."></picture>
<figcaption>图 3. Fake 用一小段逻辑响应输入变化. 真实系统的权限、SQL 与事务没有因此被验证.</figcaption>
</figure>

这里返回字典副本, 是为了避免摘要代码意外修改返回行后污染后续读取. 如果后面要测试多步骤状态变化, 还需明确每条用例是否创建新实例. 不是把一个 Fake 放到全局, 就自动获得了隔离.

## 调用过程的记录与断言

现在目标变为: 摘要必须向查询函数传入 SITE-A、CUSTOMER-X, 且本示例逻辑只查询一次. 我的方案可以同时提供固定结果, 并检查调用发生的方式.

```python
# 教学伪代码, 不可直接运行. Mock 为 Python 3.9 标准库 API.
from unittest.mock import Mock

query_double = Mock(return_value={
    "total": 2,
    "items": [{"id": "PRD-0201"}, {"id": "PRD-0202"}],
})
actual = build_summary("SITE-A", "CUSTOMER-X", query_double)

assert actual["text"] == "找到 2 条生产问题"
assert actual["first_ids"] == ["PRD-0201", "PRD-0202"]
query_double.assert_called_once_with(site_id="SITE-A", customer_id="CUSTOMER-X")
```

结果断言回答“输出对不对”, 调用断言回答“是否按约定使用依赖”. 此处一次调用是这段摘要逻辑的明确约定, 不是所有软件都应该只调用一次. 若真实实现允许缓存命中时不查询, 就要为不同路径分别定义预期, 不能为了省事把次数写死.

Python 中的 `Mock` 是工具类名, 不意味着使用它时一定在做严格术语中的 Mock. 只设置 `return_value` 的时候, 它主要扮演桩; 再检查调用参数时, 才承担交互验证. 常见术语区分参考 [Martin Fowler 的测试替身说明](https://martinfowler.com/articles/mocksArentStubs.html#TheDifferenceBetweenMocksAndStubs); 真实 API 行为参考 [Python 3.9 unittest.mock](https://docs.python.org/3.9/library/unittest.mock.html).

## 替身测试仍然无法证明的部分

假设这三种 demo 都符合预期, 仍不能得出真实服务“鉴权正确、日期筛选正确、能处理 100 并发”之类结论. 这条测试没有经过那些路径, 更没有采集相应证据.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/test-doubles/proof-mobile.svg"><img src="/images/test-doubles/proof.svg" alt="摘要转换由输出断言提供证据, 调用方式由参数和次数断言提供证据, 真实服务权限与数据库行为需要真实集成验证; 替身通过不能跨越到未执行路径."></picture>
<figcaption>图 4. 把结论写到实际执行过的边界, 能避免替身测试产生过度信心.</figcaption>
</figure>

一个具体反例: 真实服务把 `total` 改成了 `count`, 替身还在返回 `total`. 摘要测试仍然全绿, 联调却发生字段错误. 问题在于替身契约已经过时, 需要检查契约一致性并保留真实集成验证; 不是简单增加十倍相同的 Mock 用例.

再看耗时. 假设一次替身测试的示例计时是 8 ms, 真实依赖调用曾有一个 286 ms 样例, 不能把差值写成“查询性能优化”. 测试路径已经变了, 真实网络与服务被移除. 这只说明该测试可以更快地得到局部反馈, 两个值也都不是本文实测结果.

本章真正建立的是三个选择问题: 只需要稳定输入, 用固定桩; 需要少量随输入或状态变化的行为, 用简化实现; 需要检查交互, 记录并断言调用. 这些能力可以组合, 不必先背术语再勉强套用.

继续 [M2: Python 中应该替换哪一处依赖](patch-dependencies.md), 看已有代码没有把查询函数作为参数传入时如何替换. [M1 面试专题](../../interviews/mock-testing/test-doubles.md)聚焦替身选择与证据边界.

## 术语与依据

| 名称 | 中文含义 | 本篇作用 |
| --- | --- | --- |
| Test Double | 测试替身的总称 | 让依赖在测试中变得可控 |
| Stub | 提供预设回答的桩 | 给摘要代码稳定的输入 |
| Fake | 可工作的简化实现 | 按小型数据集响应不同筛选 |
| Mock | 交互验证用替身; 也指库中的类 | 记录并核对参数及调用次数 |
| Dependency injection | 依赖注入 | 把查询函数作为参数交给被测逻辑 |
| System under test / SUT | 被测对象 | 本篇实际执行的摘要逻辑 |

核查日期: 2026-10-22. 术语参考 Fowler 原文 (2007-01-02), Python API 按 3.9 文档核对. 业务代码、三条记录和耗时对比均为本文方案设定. 只进行了代码表达及图文核对, 没有执行程序或证明真实服务质量.
