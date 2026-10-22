---
title: "接口串联中的数据传递、隔离和清理"
category: 接口测试
contentType: 实践教程
pageClass: testing-notes
---

# 接口串联中的数据传递、隔离和清理

<p class="article-kicker">工作记录 · I4 · 设计思路与待验证方案</p>

如果把目前的 Postman 检查整理成接口串联测试, 我需要先解决数据归属. 创建接口返回的编号可以传给查询, 但它不能自动保证查到的是本次数据, 也不能保证更新和清理只影响本条用例.

我沿着“录入 → 查详情 → 修改标题 → 再查详情”设计数据传递、独立断言和失败收尾. [覆盖方案](api-coverage.md)中的固定预期保留下来, 后续 UI 自动化与 Agent 评测也可以使用相同的状态管理思路.

> 更新接口、数据管理入口、耗时与报告为方案推演, 不表示真实平台已有这些能力或我已落地自动化. Python 3.9 风格代码为伪代码.

## 连续场景与独立用例的边界

假设本例已经约定: 创建成功返回 201 和编号, 详情查询返回 200, 完整替换可编辑字段的 `PUT /api/v1/production-issues/{id}` 返回 200. 更新不改变编号、创建人和记录数量. 这些响应都表示同步操作已经完成, 不引入异步等待.

场景 A 的目的, 是验证这几个操作之间的数据能衔接. 它的四步应当属于同一条场景, 创建失败时, 后面三步没有有效输入, 应标记为“因前置失败未执行”. 不要拿一个共享的旧编号继续跑, 再报出三个看似独立的缺陷.

场景 B 的目的, 如果只是验证“无编辑权限不能修改标题”, 就不必等待场景 A 跑完. 它应准备自己拥有的记录, 使用无编辑权限的账号执行更新, 再核对没有变化. 复用的是准备方法, 不是上一条用例的成功结果.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-data-lifecycle/dependencies-mobile.svg"><img src="/images/api-data-lifecycle/dependencies.svg" alt="同一业务场景中编号从创建传到查询和更新; 独立场景A与B分别准备各自数据, B不依赖A执行成功."></picture>
<figcaption>图 1. 场景内部的业务依赖有意义, 跨场景共享上一次结果会让失败互相传播.</figcaption>
</figure>

沿图看两条独立泳道, 每条都从自己的准备开始. 改变执行顺序后, 如果 B 的预期仍然成立, 才说明它没有偷偷依赖 A 留下的状态. 这不是要求所有测试都毫无依赖, 而是把必需依赖放在明确的生命周期里.

## 响应编号与独立业务预期

为这次示例执行分配标记 `B02-20261022-R17`, 用例标记为 `B02-20261022-R17-C01`. 每次真实执行应由测试运行器生成不同标记; 固定示例字符串只是方便阅读. 运行前确认该标记下没有记录, 避免旧数据冒充本次结果.

初始输入仍是 SITE-A / CUSTOMER-X 的生产问题, 标题为“产测复测结果异常”. 更新后的标题为“产测复测结果异常-已补充证据”. 创建得到的编号是动态值, 从响应提取后传给查询和更新; 标题、局点、客户和创建人预期则保留在测试侧.

```python
# 教学伪代码, 不可直接运行. api 为授权测试账号的请求适配层.
original = {
    "siteId": "SITE-A", "customerId": "CUSTOMER-X",
    "title": "产测复测结果异常",
    "occurredAt": "2026-10-20T01:18:00Z",
    "clientReference": case_marker,
}
created = api.create_issue(original)
assert created.status == 201
assert created.body["code"] == "OK"
issue_id = created.body["data"]["id"]
assert isinstance(issue_id, str) and issue_id

detail = api.get_issue(issue_id)
assert detail.status == 200
assert detail.body["data"]["id"] == issue_id
assert detail.body["data"]["title"] == original["title"]
assert detail.body["data"]["customerId"] == original["customerId"]

updated = dict(original)
updated["title"] = "产测复测结果异常-已补充证据"
changed = api.replace_issue(issue_id, updated)
assert changed.status == 200
assert changed.body["code"] == "OK"

reloaded = api.get_issue(issue_id)
assert reloaded.status == 200
assert reloaded.body["data"]["id"] == issue_id
assert reloaded.body["data"]["title"] == updated["title"]
assert reloaded.body["data"]["siteId"] == original["siteId"]
assert reloaded.body["data"]["customerId"] == original["customerId"]
assert reloaded.body["data"]["createdBy"] == test_user_id
```

这里传的是完整的可编辑输入, 避免把本例的 PUT 当成“只发送一个字段就一定可以更新”的通用规则. 方法语义参考 [RFC 9110 §9.3.4](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.4), 具体允许字段与响应结构仍由平台定义.

一个常见的错误写法是: 从更新响应里取出 `title`, 再断言详情里的 `title` 与它相同. 如果两个接口都错误返回了旧标题, 这种检查仍会通过. 它只能说明两处一致, 无法证明更新符合用户输入. **关联值可以来自响应, 关键业务预期不能全部由被测系统自己生成.**

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-data-lifecycle/data-flow-mobile.svg"><img src="/images/api-data-lifecycle/data-flow.svg" alt="创建响应中的动态编号进入后续请求, 测试侧保留的原始及更新输入独立进入断言; 响应之间相等不能替代与输入预期的比较."></picture>
<figcaption>图 2. 一条线传“查哪条记录”, 另一条线回答“它应该变成什么”.</figcaption>
</figure>

还应按用例标记核对记录数量从 0 变成 1, 更新后仍是 1, 避免服务把更新实现成新增. 在大家共用的测试库里, 不要用全表数量“刚好加一”作为唯一证据, 其他人的写入也会改变它. 用例自己的数据范围更稳定.

## 准备、清理和断言的边界

准备阶段先确认账号权限、环境版本、可追踪标记和初始数据. 若需要测试更新, 可以通过已验证的准备接口创建数据, 或通过明确允许的测试数据工具准备; 这两种方式覆盖的路径不同. 本例的关联场景刻意使用业务创建接口, 以便把创建本身纳入检查.

清理只处理本次执行拥有的记录. 假设示例环境提供测试管理入口, 能按精确的运行标记和所有者定位、删除本次创建的数据. 它不是面向生产用户的业务接口, 也不是让测试程序执行“清空生产问题表”. 没有这种能力时, 应采用实际允许的回滚、测试租户或到期回收方式, 不编造万能清理函数.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-data-lifecycle/lifecycle-mobile.svg"><img src="/images/api-data-lifecycle/lifecycle.svg" alt="准备成功后执行场景, 主检查通过或失败都进入限定范围的清理; 主失败证据和清理失败证据分别保留, 准备失败则记录未执行."></picture>
<figcaption>图 3. 主检查与收尾分别记结果. 收尾失败不能把原始断言失败替换掉.</figcaption>
</figure>

下面把异常处理单独展开. `run_business_checks` 表示前面的四步; `cleanup_owned_records` 只能删除这次标记下且所有者匹配的数据, 返回未清理条目及原因. 如果服务已写入但响应没有返回编号, 它仍可按运行前确认不存在的唯一标记核对. 本例假设请求已结束, 不处理后台仍可能继续写入的异步场景.

```python
# 教学伪代码, 不可直接运行. 全部为测试运行器的抽象接口.
primary_error = None
cleanup_error = None
cleanup_allowed = False
try:
    assert test_data.find_exact(case_marker, owner=test_user_id) == []
    cleanup_allowed = True
    run_business_checks(case_marker)
except Exception as error:
    primary_error = error
finally:
    if cleanup_allowed:
        try:
            leftovers = test_data.cleanup_owned_records(
                case_marker, owner=test_user_id
            )
            if leftovers:
                cleanup_error = leftovers
        except Exception as error:
            cleanup_error = error

report.finish(primary_error=primary_error, cleanup_error=cleanup_error)
```

这段伪代码还有一个前置: `case_marker` 已由运行器保证本轮独占, 不是可能撞名的用户输入. `report.finish` 必须把主失败与清理失败记录为非全绿结果, 不可以吞掉异常后报告成功. 为突出记录思路, 准备失败归类、步骤计时和测试框架的抛错机制没有在此展开.

若原始数据检查意外发现旧记录, 应停止本用例并报告隔离条件不满足, 不应顺手删除来源不明的数据. 代码中的 `cleanup_allowed` 只在独占标记的初始检查通过后打开, 清理入口仍需核对所有者. 下面的结果表也将这种情况与“本次执行创建的数据未清理”分开.

## 用失败报告复核数据生命周期

构造一次场景: 创建 184 ms, 首次详情 96 ms, 更新 162 ms, 再查详情 91 ms. 四次请求观测值合计 533 ms, 不包括准备、断言、清理和步骤间开销, 因而不等于完整场景耗时, 更不是系统 P95. 本例的用意是让报告能够对应到步骤.

| 阶段 | 模拟证据 | 应如何记录 |
| --- | --- | --- |
| 创建 | 201, 得到本次编号 | 创建检查通过 |
| 首次详情 | 原标题与客户正确 | 首次查询检查通过 |
| 更新 | 200 / OK | 仅证明响应符合约定, 继续核对数据 |
| 再查详情 | 仍然是旧标题 | 更新结果失败, 保存编号、输入与实际值 |
| 清理 | 本次编号已移除 | 清理通过, 不能把主失败改成成功 |

另一种情况是创建成功, 第二步查询断言失败, 清理又返回权限错误. 报告应同时保留“详情字段不正确”和“本次记录残留”, 不让 finally 中的新异常掩盖原始问题. 若准备阶段账号未就绪, 则报告场景未执行, 不把它计为业务断言失败.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-data-lifecycle/report-mobile.svg"><img src="/images/api-data-lifecycle/report.svg" alt="执行结果分成主检查和清理两列: 主失败且清理成功仍是失败, 主通过而清理失败也不是全绿, 两者失败需保留两个证据."></picture>
<figcaption>图 4. 结果是两个维度. 清理成功不抵消产品问题, 主检查通过也不消除残留风险.</figcaption>
</figure>

为了检查独立性, 可在场景推演中交换两个场景的顺序, 或分别单独执行它们, 看是否仍有明确预期. 每个场景使用不同标记、独立记录, 共享的只读参考字典则可以复用. 不要把所有准备都重复一遍当成隔离, 也不要把共享可变状态当成省事的默认选择.

下一篇 [M1: 依赖没准备好时怎样继续测试](../mock-testing/test-doubles.md)会进一步区分“准备数据”和“替换依赖”. [I4 面试专题](../../interviews/api-testing/api-data-lifecycle.md)聚焦关联、隔离与失败证据.

## 术语与依据

| 名称 | 中文含义 | 本篇作用 |
| --- | --- | --- |
| Correlation | 接口数据关联 | 把创建编号传给后续请求 |
| Setup / Teardown | 准备与收尾 | 明确运行前提和数据回收职责 |
| Test isolation | 用例隔离 | 避免顺序及残留数据影响判断 |
| Fixture | 用例所需固定条件 | 账号、数据与可复现的初始状态 |
| Primary failure | 主失败 | 保留最先发现的业务断言或执行问题 |

核查日期: 2026-10-22. PUT 方法语义参考 RFC 9110 (2022-06); 生命周期和报告为本文方案设定. 仅做数据流、算术、异常路径与伪代码静态核对. 未执行接口调用或数据删除, 未构建实际自动化框架.
