---
title: 一个接口测试到底在验证什么?
category: 接口测试
contentType: 实践教程
pageClass: testing-notes
---

# 一个接口测试到底在验证什么?

<p class="article-kicker">第一批 · I1 · 从“请求成功”走到“业务正确”</p>

Postman 显示 `200 OK`, 响应用时 286 ms, 返回体里还有 `success`. 这次接口测试就能通过吗?

要看你发了什么请求, 以及这个请求本来应该发生什么. 如果测试的是“没有录入权限的账号应被拒绝”, 返回成功反而可能是问题. 接口测试需要把输入、身份、业务约定、响应和实际数据变化一起核对.

这一篇沿用[上一章](../web-testing/business-flow.md)的生产问题案例: 录入一条问题, 再查询列表. 你会看到同一接口的正向和反向情况怎样形成不同断言, 以及为什么“状态码对了”只是判定的一部分.

> 全部业务字段、状态约定、数量和耗时都是教学模拟. 例子接近维护平台的录入与查询场景, 不代表真实接口协议. 代码为 Python 3.9 风格伪代码, 不可直接运行.

## 先给接口写一份可以核对的约定

契约就是调用方和服务方对“什么输入、什么结果”的共同约定. 不必先有很复杂的工具, 先把必需条件写清楚即可.

本例定义两个接口. 所有地址都属于虚构服务, 域名使用不会指向真实业务的 `maintenance.example`.

| 操作 | 教学接口 | 正确结果 |
| --- | --- | --- |
| 录入问题 | `POST /api/v1/production-issues` | 有权限且字段有效时新增一条记录, 返回 201、业务码 `OK` 和编号 |
| 查询问题 | `GET /api/v1/production-issues` | 返回当前账号可见且满足条件的记录, HTTP 200, 业务码 `OK` |

录入规则约定: `siteId`、`customerId`、`title`、`occurredAt` 必填; 标题按本教学服务定义的 Unicode 码点数计算, 长度为 1 到 200; 时间必须能明确转换为时刻; 创建人从认证身份取得. 无录入权限返回 403, 字段不满足规则返回 422, 两者都不能新增记录. 不把浏览器隐藏按钮当作服务授权校验.

查询规则约定: 页码从 1 开始, `pageSize` 为 1 到 100; 时间条件使用起点包含、终点不包含; `total` 是账号可见且满足当前筛选条件的总数, `items` 仅是本页内容. 排序按发生时间倒序, 同时刻按编号倒序. 这些细节决定测试的预期, 不由测试人员临时猜测.

HTTP 的 200、201、202 分别用于成功、创建成功和接受处理但尚未完成等语义; 401 与 403 也不是同一个含义. 状态码的基础定义见 [RFC 9110 §15](https://www.rfc-editor.org/rfc/rfc9110.html#section-15). 业务码、字段和持久化承诺仍由项目契约规定, 标准不会替平台定义 `OK` 或某个业务编号.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-test-oracle/contract-mobile.svg"><img src="/images/api-test-oracle/contract.svg" alt="接口判定从请求和身份出发, 依据独立契约检查响应状态、字段和持久化结果; 实际返回不能反过来定义预期."></picture>
<figcaption>图 1. 先确定预期, 再检查实际返回. 接口自己的回答不能成为唯一标准答案.</figcaption>
</figure>

## 正常录入: 为什么既要看编号, 也要查记录?

发送一条生产问题, 使用 `DEMO-20261020-A17` 作为本次样例的唯一标记. 以下是请求体, 身份凭证不在正文展示.

```json
{
  "siteId": "SITE-A",
  "customerId": "CUSTOMER-X",
  "title": "产测复测结果异常",
  "occurredAt": "2026-10-20T01:18:00Z",
  "clientReference": "DEMO-20261020-A17"
}
```

预期响应采用下面的教学结构. 这里的 `requestId` 关联一次请求, 业务编号关联一条记录. 列表查询是另一请求, 会有自己的请求标识, 不要要求两次请求的标识相同.

```json
{
  "code": "OK",
  "message": "created",
  "requestId": "demo-req-create-a17",
  "data": {
    "id": "PRD-20261020-0143",
    "clientReference": "DEMO-20261020-A17"
  }
}
```

响应状态为 201, `Content-Type` 表示 JSON. 接下来仍要核对编号存在、关键字段正确, 并确认当前请求确实新增了一条记录. 如果服务提前返回成功但保存失败, 单看响应无法发现问题.

```python
# 教学伪代码, 不可直接运行.
# api 表示测试请求适配层, records 表示获准核对的数据访问层.
before = records.find(client_reference=payload["clientReference"])
assert before == []

response = api.post("/api/v1/production-issues", json=payload)
assert response.status == 201
assert response.is_json
assert response.body["code"] == "OK"
issue_id = response.body["data"]["id"]
assert isinstance(issue_id, str) and issue_id

after = records.find(client_reference=payload["clientReference"])
assert len(after) == 1
assert after[0]["id"] == issue_id
assert after[0]["siteId"] == payload["siteId"]
assert after[0]["customerId"] == payload["customerId"]
assert after[0]["occurredAtUtc"] == payload["occurredAt"]
```

这组检查来自业务契约, 不是为了把所有字段都机械断言一遍. 不稳定的请求标识通常检查格式与存在性, 不写死每次必须等于同一值; 业务关联标记则要对应这次输入. 如果只能访问详情接口而不能查询数据库, 就记录自己的验证范围, 不宣称已经验证底层事务行为.

## 错误输入: 正确拒绝也算测试通过

将标题改成 201 个 ASCII 字符, 其他业务条件保持相同. 为区分前一条记录, 换用新的追踪标记; 它只用于定位样例, 不改变校验规则. 因为这组字符的码点计数明确, 可以避免先把精力放在 emoji 或组合字符计数上. 本例期望 422, 业务码 `INVALID_TITLE_LENGTH`, 且没有新增记录.

```python
# 教学伪代码, 不可直接运行.
invalid = dict(payload)
invalid["title"] = "A" * 201
invalid["clientReference"] = "DEMO-20261020-A18"

before = records.find(client_reference=invalid["clientReference"])
assert before == []
response = api.post("/api/v1/production-issues", json=invalid)

assert response.status == 422
assert response.body["code"] == "INVALID_TITLE_LENGTH"
assert records.find(client_reference=invalid["clientReference"]) == []
```

如果接口返回 422 但数据库已经插入记录, 仍然失败. 如果返回 201 且记录保存成功, 也失败, 因为规则不允许这个输入. 测试是否通过取决于“实际行为是否符合本条预期”, 不是“接口有没有报错”.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-test-oracle/outcomes-mobile.svg"><img src="/images/api-test-oracle/outcomes.svg" alt="有效输入预期201且新增一条; 标题超长预期422且不写入; 无权限预期403且不写入. 状态与数据变化必须同时符合预期."></picture>
<figcaption>图 2. 正向与反向用例有不同预期, 都需要检查数据变化.</figcaption>
</figure>

再把账号换成“可查询、不可录入”的教学角色, 使用有效输入测试 403. 这样只改变授权条件, 能区分权限错误与字段错误. 如果同时换账号又把标题改坏, 两条规则都可能拒绝请求, 很难判断权限校验是否实际生效.

本篇只用几个代表性样例解释判定方法. 完整的参数边界、跨角色越权和组合覆盖放在 I3 展开, 不因为三条用例通过就认为接口已经覆盖充分.

## 查询接口: 143、20 和 3 为什么都可能正确?

沿用 W1 的隔离样例: 总台账 18,427 条, 当前账号及筛选条件匹配 143 条, 每页 20 条. 第一页应返回 20 条, 第八页返回 3 条, 第九页返回空列表; 本教学契约约定越过末页仍返回 200, `total` 保持 143. 如果实际产品契约不同, 就按其约定测试.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-test-oracle/pagination-mobile.svg"><img src="/images/api-test-oracle/pagination.svg" alt="全台账18427条, 筛选匹配143条, 每页20条; 第1到7页各20条, 第8页3条, 第9页0条. total不能误写为本页数量."></picture>
<figcaption>图 3. 全表数、筛选总数、本页数是不同统计范围.</figcaption>
</figure>

第八页的模拟响应可以完整展示为三条摘要. 它们是教学记录, 不需要展示 143 条才能讲清分页规则.

```json
{
  "code": "OK",
  "data": {
    "page": 8,
    "pageSize": 20,
    "total": 143,
    "items": [
      {"id": "PRD-20261001-0003", "occurredAt": "2026-10-01T02:15:00Z"},
      {"id": "PRD-20261001-0002", "occurredAt": "2026-10-01T01:20:00Z"},
      {"id": "PRD-20261001-0001", "occurredAt": "2026-09-30T16:30:00Z"}
    ]
  }
}
```

最后一条看起来是“9 月 30 日”, 换到上海时间却是 10 月 1 日 00:30, 应落入条件范围. 所以检查日期不能只取 ISO 字符串前十位.

```python
# 教学伪代码, 不可直接运行. reference 是独立构造的预期集合.
expected_ids = reference.filtered_and_sorted_ids(query, user_scope)
assert len(expected_ids) == 143

data = response.body["data"]
offset = (query["page"] - 1) * query["pageSize"]
expected_page = expected_ids[offset:offset + query["pageSize"]]
actual_ids = [item["id"] for item in data["items"]]

assert data["total"] == len(expected_ids)
assert actual_ids == expected_page
assert len(actual_ids) == len(set(actual_ids))
```

`reference` 由规则和已知样例独立推导, 不直接调用同一个被测查询来生成答案. 对比有序编号同时覆盖了本页成员和顺序, 但其他返回字段仍需要相应断言. 完整分页遍历还应检查跨页遗漏或重复, 并控制数据在翻页期间是否变化, 不能拿持续写入的数据集当静态快照比较.

## 100 次里有 98 次返回 2xx, 能说明质量是 98% 吗?

不能, 除非先定义分母和成功条件. 我们构造一批 100 次接口用例执行: 80 次有效请求, 20 次应该被拒绝的请求. 如果 80 次正确完成、20 次正确拒绝, 测试通过率就是 100%, HTTP 2xx 比例却只有 80%.

再构造另一个结果: 有效请求中 78 次符合全部断言, 2 次保存字段错误; 无效请求 20 次都正确拒绝. 那么这批**用例执行通过率**为 `98 / 100 = 98%`, 有效请求的业务完成比例为 `78 / 80 = 97.5%`. 两个指标都没有资格直接代表生产环境的用户成功率, 因为样本分布是我们设计的.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/api-test-oracle/rates-mobile.svg"><img src="/images/api-test-oracle/rates.svg" alt="100次教学执行包含80次有效请求和20次应拒绝请求; 78次有效请求正确、2次错误、20次正确拒绝, 所以用例通过率98%, 有效请求完成比例97.5%."></picture>
<figcaption>图 4. 先写清统计对象和分母, 再计算比例. 数值来自模拟执行分类, 不是实测.</figcaption>
</figure>

如果某次执行因测试数据准备失败而根本没发出请求, 还应单列为未完成或环境问题, 说明统计时是否计入分母. 静默丢掉这类记录, 可能让报告看起来更好, 却让结果难以复核.

同样, 286 ms 是单次观测. 这篇没有加压、没有指定并发、没有采集足够的时间分布, 因此不会给出接口性能达标结论. 当前最值得建立的习惯是: 每一个“成功率”和“耗时”, 都紧跟统计对象和范围.

## 遇到矛盾时, 把结论收在证据能支持的范围内

返回体写着 `OK`, 数据却没有保存, 应分别记录“响应声称成功”和“持久化验证不成立”. 状态码 200 加业务码失败的老系统, 也要依据它自己的契约分别判断, 不把 200 自动解释为所有业务动作已经完成.

如果本例录入接口返回 202, 则与我们“同步完成后返回 201”的约定不符. 如果另一个真实接口本来就是异步提交, 202 可以是合法结果, 后续应查询任务状态. 不同实现可以成立, 关键是测试基于已确认的契约.

下一篇 [I2: 从浏览器请求定位到 Postman 复现](browser-to-postman.md)会用同一查询场景展示如何获取真实请求、建立等价复现并定位差异. [I1 面试专题](../../interviews/api-testing/api-test-oracle.md)用于练习表达这些判定依据, 没有独立练习任务.

## 术语与资料

| 名称 | 含义 | 本文具体用途 |
| --- | --- | --- |
| HTTP / Hypertext Transfer Protocol | HTTP 协议 | 理解请求、响应和状态码的基础语义 |
| API contract | 接口契约 | 明确输入、响应及数据变化的约定 |
| Test oracle | 测试判定依据 | 在看到实际结果前确定什么算正确 |
| Assertion | 断言 | 把业务预期写成可核对的条件 |
| JSON | 结构化数据格式 | 表达请求体和响应体 |
| Pagination | 分页 | 区分筛选总数与当前页内容 |
| Request ID | 请求标识 | 定位一次请求, 不等同业务记录编号 |

核查日期: 2026-10-21. 协议事实参考 [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), 2022 年 6 月版本, 重点为 §15 状态码与 §9.3 方法语义. 其余业务契约、样本、断言、数量和比例均为教学设计. 未访问公司接口或数据库; 算术与代码表达做静态核对, 没有执行接口测试或性能测试.
