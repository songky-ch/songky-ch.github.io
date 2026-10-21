---
title: 参数、权限、分页和过滤条件怎样系统覆盖?
category: 接口测试
contentType: 实践教程
pageClass: testing-notes
---

# 参数、权限、分页和过滤条件怎样系统覆盖?

<p class="article-kicker">第二批 · I3 · 把一条正确请求展开成有依据的覆盖</p>

你已经能用 Postman 发出查询, 也知道不能只看 200. 接下来容易遇到另一个问题: 参数很多, 到底该测哪些组合? 改几个值似乎太少, 把所有组合列出来又很快失控.

先把查询想成一道逐层筛选的题: 当前账号能看哪些记录, 业务条件留下哪些记录, 按什么顺序排列, 最后截取哪一页. 测试用例就是有意改变其中一层, 检查结果是否按约定变化. 输入非法时, 则在约定的校验位置停止, 不进入正常查询.

本文接续 [I1 的接口判定](api-test-oracle.md)和 [I2 的请求复现](browser-to-postman.md), 不重新讲等价类与边界值定义, 直接把它们放进生产问题查询.

> 以下权限、字段、返回码和记录均为教学模拟. 为便于手算, 本篇单独构造 8 条记录, 不与上一批的 18,427 条台账混为同一个数据快照. Python 3.9 风格代码均为伪代码, 不需要运行.

## 把预期写成一条可以手算的流水线

沿用 `GET /api/v1/production-issues`. 本篇补足教学契约: `page` 缺省为 1, `pageSize` 缺省为 20, 显式传值时分别要求正整数及 1–100 的整数; `category` 可省略, 省略表示不限制类别, 空字符串不是省略. 时间采用起点包含、终点不包含. 非法查询参数返回 400 和 `INVALID_QUERY`, 不自动偷偷纠正.

这与上一批“录入字段错误返回 422”不冲突: 两个操作的错误约定分别定义. HTTP 标准并没有规定所有平台都必须这样映射, 本例的具体状态与业务码由教学契约确定. 状态语义参考 [RFC 9110 §15](https://www.rfc-editor.org/rfc/rfc9110.html#section-15).

账号 `reader_ax` 有列表和详情读取权限, 数据范围只包括 `SITE-A / CUSTOMER-X`. 合法筛选超出它的数据范围时, 列表返回 200 和空集合; 直接按编号访问范围外记录, 本例返回 403 且不包含记录详情. 这里刻意区分“列表的集合交集”与“单条记录的授权拒绝”, 其他项目可以有不同约定.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-coverage/pipeline-mobile.svg"><img src="/images/api-coverage/pipeline.svg" alt="参数合法时, 记录集合依次经过账号权限范围、业务过滤、稳定排序和分页; 参数非法独立返回400, 不进入正常查询."></picture>
<figcaption>图 1. 测试预期的推导顺序. 这是逻辑关系, 不要求数据库内部必须按这个物理顺序执行.</figcaption>
</figure>

沿图向下看, `total` 在分页之前确定. 权限范围与业务条件共同限制返回集合; 分页只取其中一段, 不能重新扩大可见范围. 实现可能通过一条 SQL 完成, 测试仍可分层推导独立预期.

## 先看 8 条记录, 再决定每条用例应返回谁

表中时间全部是上海时间 `+08:00`, 编号用固定宽度后缀. 各字段都有效, 没有后台新增或删除.

| 编号 | 局点 | 客户 | 类别 | 发生时间 |
| --- | --- | --- | --- | --- |
| PRD-0201 | SITE-A | CUSTOMER-X | 产测 | 10-20 10:00:00 |
| PRD-0202 | SITE-A | CUSTOMER-X | 产测 | 10-20 09:00:00 |
| PRD-0203 | SITE-A | CUSTOMER-X | 软件 | 10-20 09:00:00 |
| PRD-0204 | SITE-A | CUSTOMER-X | 产测 | 10-19 23:59:59.999 |
| PRD-0205 | SITE-A | CUSTOMER-Y | 产测 | 10-20 11:00:00 |
| PRD-0206 | SITE-B | CUSTOMER-X | 产测 | 10-20 12:00:00 |
| PRD-0207 | SITE-A | CUSTOMER-X | 产测 | 10-21 00:00:00 |
| PRD-0208 | SITE-A | CUSTOMER-X | 产测 | 10-20 00:00:00 |

基线请求使用 `reader_ax`, 时间范围为 `[2026-10-20 00:00, 2026-10-21 00:00)`, 类别为“产测”, 每页 2 条. 先排除其他客户和局点的 0205、0206; 再排除范围外的 0204、0207; 最后排除“软件”类别的 0203. 剩下 0201、0202、0208, 所以 `total=3`.

按 `occurredAt desc, id desc` 排序, 第 1 页应为 `[0201, 0202]`, 第 2 页为 `[0208]`, 第 3 页为空. 本篇把每页数从常用的 20 调到 2, 是为了让分页错误在小样本里直接可见, 不是建议真实平台统一采用 2 条一页.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-coverage/windows-mobile.svg"><img src="/images/api-coverage/windows.svg" alt="过滤后有序集合为0201、0202、0208, 每页2条时前两条属于第一页, 最后一条属于第二页, 第三页为空; total始终为3."></picture>
<figcaption>图 2. 先有完整的有序集合, 才有分页窗口. 比较编号比只比较条数更有判断力.</figcaption>
</figure>

若第一页变成 `[0201, 0208]`, 条数仍是 2, 但成员和顺序已经不对. 若每页都返回同样两条, 每一页的“长度检查”也可能通过, 完整拼接后却会暴露重复和遗漏.

## 一次改变一个条件, 先让失败容易解释

从同一合法基线出发, 每行是一条独立用例. “没有传字段”和“传了一个表示空的值”必须分开; URL 查询参数本来是文本, 下面的整数指服务约定如何解析这些文本.

| 变化 | 教学预期 | 能暴露的问题 |
| --- | --- | --- |
| 不传 `pageSize` | 使用 20, 返回全部 3 条 | 缺省值没有生效 |
| `pageSize=1` / `100` | 合法, 分别返回 1 / 3 条 | 合法边界误拒绝 |
| `pageSize=0` / `101` | 400, `INVALID_QUERY` | 越界值被悄悄接受 |
| `pageSize=2.5` / `abc` / 空字符串 | 400 | 解析或类型校验错误 |
| 不传 `category` | `total=4`, 顺序 0201、0203、0202、0208 | 可选条件或同刻排序错误 |
| `category=` 空字符串 | 400 | 把空值误当“不过滤” |
| 起点等于终点 | 本例约定 400 | 空区间语义不明确 |
| 起点晚于终点 | 400 | 日期关系未校验 |
| 合法范围内没有匹配记录 | 200, `total=0`, `items=[]` | 把无结果误当异常 |

不传类别后, 0203 与 0202 发生时间相同. 因为编号倒序, 0203 必须排在 0202 前. 这条样例特意让次级排序有机会影响结果, 而不是放一批时间全不相同的数据后声称测过稳定排序.

字符串 `"null"` 也不天然等于 JSON 的 `null`. 如果接口接收 JSON 查询体, 缺字段、`null`、`""`、`[]` 要按该契约分别设计. 不能把 Postman 界面显示为空的所有情况合成一个用例.

## 权限测试同时问“能做什么”和“能看谁”

把身份分成三个教学角色: `reader_ax` 可读取 A/X; `editor_ax` 可读取和编辑 A/X; `reader_ay` 只能读取 A/Y. 两个 reader 的功能权限相同, 可见对象不同. 页面是否显示编辑按钮, 无法替代服务端的这两类判断.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-coverage/permissions-mobile.svg"><img src="/images/api-coverage/permissions.svg" alt="权限矩阵区分reader_ax、editor_ax和reader_ay对A/X及A/Y记录的读取与编辑能力, 不能只检查角色名或按钮可见性."></picture>
<figcaption>图 3. 一列验证操作权限, 另一列验证对象范围. 相同角色也可能拥有不同数据范围.</figcaption>
</figure>

具体可以这样推演: 用 `reader_ax` 查询列表, 不应包含 0205; 再用同一账号请求 0205 的详情, 按本例应返回 403; 用可编辑 A/X 的 `editor_ax` 尝试更新 A/Y 的 0205, 也应拒绝, 并确认原记录未改变. 知道编号不代表拥有权限, 这是 [OWASP 对对象级授权的说明](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)强调的边界.

不要只查 `items` 有没有泄露. `total`、聚合数量和导出入口如果存在, 也可能采用另一条查询路径. 本例列表的 `total` 必须基于相同授权范围, 不能内容只有 3 条, 总数却包含其他客户的数据. 这些场景限于获准测试的账号和模拟数据, 不枚举真实业务编号.

## 组合测试围绕规则相遇的位置展开

单参数正常不代表组合正确. 本例优先把日期、类别、账号范围和分页一起放入基线, 再针对相互作用增加少量对照. 例如“取消类别后仍只在账号可见范围内返回 4 条”, 可以同时检查可选过滤与权限约束没有互相覆盖.

但若同时使用无权限账号、非法日期和非法页码, 返回 403 并不能证明日期和页码校验正确. 如果契约没有规定多种错误的优先级, 就不能要求所有实现都先返回某一个错误. 先用其他条件合法的反向用例验证各项规则, 再在确有需求时检查组合优先级.

对固定样例, 跨页断言可以写得很直接:

```python
# 教学伪代码, 不可直接运行. api 是请求适配层.
expected_pages = [["PRD-0201", "PRD-0202"], ["PRD-0208"], []]
seen_ids = []
for page_number, expected_ids in enumerate(expected_pages, start=1):
    response = api.query_issues(user="reader_ax", page=page_number,
                                page_size=2, filters=baseline_filters)
    assert response.status == 200
    data = response.body["data"]
    actual_ids = [row["id"] for row in data["items"]]
    assert data["total"] == 3
    assert actual_ids == expected_ids
    seen_ids.extend(actual_ids)

assert seen_ids == ["PRD-0201", "PRD-0202", "PRD-0208"]
assert len(seen_ids) == len(set(seen_ids))
```

这里预期写自那张 8 行表, 没有再次调用被测查询来生成“标准答案”. 对大样本可以独立构造参考集合, 但仍要防止把同一个错误查询复制进判定逻辑. 数据若持续变化, 则应换成受控快照或依据真实产品的一致性约定测试, 不直接套用这份静态断言.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-coverage/evidence-mobile.svg"><img src="/images/api-coverage/evidence.svg" alt="规则确定预期, 固定数据提供独立答案, 执行产生响应证据, 最终按编号顺序、总数和数据范围比较; 没有有效执行证据的用例单列阻塞."></picture>
<figcaption>图 4. 覆盖需要连接规则、数据与证据. 只增加用例数量不会自动增加判断力.</figcaption>
</figure>

如果计划 32 条, 实际执行 28 条, 其中 26 条通过、2 条失败, 另有 4 条因账号未就绪而阻塞, 则已执行通过率为 `26/28 ≈ 92.86%`, 计划完成率为 `28/32 = 87.5%`. 不能把阻塞算成产品通过, 也不能把 92.86% 写成接口覆盖率. 覆盖还要回答哪些规则有正向、反向和组合证据. 这些数值是报告示例, 不是实际测试成绩.

下一篇 [I4: 接口关联与测试数据](api-data-lifecycle.md)将把独立查询接到录入和更新之后. [配套面试专题](../../interviews/api-testing/api-coverage.md)帮助你讲清测试选择的依据.

## 术语与依据

| 名称 | 中文含义 | 本篇作用 |
| --- | --- | --- |
| Test fixture | 测试固定条件与数据 | 让 8 条记录形成可重复推导的基准 |
| Invariant | 不变量 | 检查分页前后总数、范围等应保持的规则 |
| Object-level authorization | 对象级授权 | 证明账号只能访问允许的具体记录 |
| Stable ordering | 稳定排序 | 用次级排序消除同刻记录的顺序歧义 |
| Offset pagination | 偏移分页 | 理解页码与每页数截取的集合窗口 |

核查日期: 2026-10-22. 协议参考 RFC 9110 (2022-06), 授权边界参考 OWASP API Security Top 10 2023. 所有业务规则、小表、比例和代码为原创教学设计. 已核对手算结果与伪代码语法, 未执行真实接口或权限测试.
