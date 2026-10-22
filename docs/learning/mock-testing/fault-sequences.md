---
title: 怎样稳定复现超时、错误和连续变化的返回?
category: Mock 测试
contentType: 实践教程
pageClass: testing-notes
---

# 怎样稳定复现超时、错误和连续变化的返回?

<p class="article-kicker">第四批 · M3 · 让失败按约定发生, 再检查程序怎样应对</p>

你想检查查询超时后的提示, 真实环境却一直正常; 好不容易超时一次, 又不知道下一次能否复现. 这时需要的不是等网络“碰巧坏掉”, 而是控制查询依赖在指定调用上返回什么或抛出什么异常.

[M2](patch-dependencies.md)解决替换位置, 本篇继续解决替换后的行为. 目标是看懂第一次失败、第二次成功、持续失败、空数据和错误结构怎样分别验证. 仍采用 Python 3.9 风格教学伪代码, 不要求运行.

> 这是独立的 D1 只读接口教学策略: 首次查询遇到指定超时异常时, 等待 200 ms 后重试一次, 总尝试上限为 2. 它不适用于写入, 也不修改 [A1](../agent/agent-request-map.md) 中 Agent 最多派发一次且不重试的约定. 所有工具名、返回和数值均为教学设计.

## 先确定你要制造哪一层故障

真实链路可以是“查询包装函数 → HTTP 适配器 → 网络 → 服务”. 在包装函数的依赖位置直接抛异常, 可以检查它怎样处理异常, 但没有验证真实 HTTP 客户端是否在规定时间取消请求.

<figure><picture><source media="(max-width: 600px)" srcset="/images/fault-sequences/boundary-mobile.svg"><img src="/images/fault-sequences/boundary.svg" alt="包装函数保持真实执行, 查询依赖替换为可控异常或返回值; 网络和服务没有执行, 因此只证明异常处理逻辑, 不证明真实超时机制."></picture><figcaption>图 1. 异常出现的位置决定结论范围. 直接抛出超时异常, 不等于真的等了几秒钟.</figcaption></figure>

本例约定查询适配器把它负责的超时转换成 `QueryTimeout`, 包装函数只重试这一种异常. 认证失败、业务拒绝、字段缺失不能因为“都不成功”就一起重试. 更不能捕获所有 `Exception` 后返回空列表, 那样服务故障会被误说成“没有生产问题”.

如果真实客户端抛的是自己的异常类型, 需要在真实适配器测试中检查转换关系. 本篇不会声称 Python 内置 `TimeoutError` 能自动覆盖所有网络库的超时.

## 先写清被测策略, 再配置替身

用 `query` 保存本次查询条件, 两次尝试必须使用相同条件. `fetch` 是查询依赖, `pause` 是等待依赖. `valid_payload` 是教学校验函数, 检查约定字段和类型; 本篇假定合法结果包含整数 `total` 和列表 `items`, 不在这里实现真实业务数据校验.

```python
# Python 3.9 风格教学伪代码, 不可直接运行.
class QueryTimeout(Exception):
    pass

def read_with_retry(fetch, pause, query):
    for attempt in (1, 2):
        try:
            data = fetch(**query)
        except QueryTimeout:
            if attempt == 2:
                return {"status": "unavailable", "data": None}
            pause(0.2)
            continue
        if not valid_payload(data):
            return {"status": "invalid_payload", "data": None}
        return {"status": "ok", "data": data}
```

这里的“重试一次”是总共最多两次尝试. 成功后立刻返回; 第二次超时后结束; 错误结构不重试; 未被列出的异常不会被这段代码吞掉. 这些路径都可以从代码走到明确出口.

<figure><picture><source media="(max-width: 600px)" srcset="/images/fault-sequences/retry-mobile.svg"><img src="/images/fault-sequences/retry.svg" alt="第一次查询成功则返回; 指定超时后等待200毫秒并进行第二次尝试; 第二次成功返回, 第二次超时进入不可用出口, 不再有第三次调用."></picture><figcaption>图 2. 重试由被测函数发起. side_effect 只决定每次被调用时发生什么, 不会主动触发下一次调用.</figcaption></figure>

## 第一次超时, 第二次成功, 要怎样配?

`Mock.side_effect` 可以接收一个序列. 每发生一次调用, 消耗下一个元素: 普通值作为返回值, 异常作为抛出的异常. 这是 [Python 3.9 的 side_effect 语义](https://docs.python.org/3.9/library/unittest.mock.html#unittest.mock.Mock.side_effect), 不是我们给业务函数新增的接口.

```python
# 教学伪代码, 不可直接运行. read_with_retry 为上面的被测逻辑.
from unittest.mock import Mock, call

query = {"site_id": "SITE-A", "customer_id": "CUSTOMER-X"}
ok_data = {"total": 2, "items": [{"id": "PRD-0401"}, {"id": "PRD-0402"}]}
fetch = Mock(side_effect=[QueryTimeout("模拟超时"), ok_data])
pause = Mock()

actual = read_with_retry(fetch, pause, query)
assert actual == {"status": "ok", "data": ok_data}
assert fetch.call_args_list == [call(**query), call(**query)]
pause.assert_called_once_with(0.2)
```

按顺序理解: 第一次 `fetch` 抛出异常, 包装函数捕获它; `pause` 记录了一次 0.2 的参数, 但测试替身没有真的等待; 包装函数再调 `fetch`, 此时得到两条记录. 最后既检查结果, 也检查两次调用的条件以及等待次数.

只写 `assert_has_calls` 不一定能排除多余调用, 因为该断言允许指定序列前后存在额外调用. 本例直接比较完整 `call_args_list`, 同时约束数量、顺序和参数. 即使一次调用抛异常, Mock 仍会记录那次调用. 这些细节可查官方 [调用断言](https://docs.python.org/3.9/library/unittest.mock.html#unittest.mock.Mock.assert_has_calls)与 [Calling](https://docs.python.org/3.9/library/unittest.mock.html#calling) 章节.

## 持续失败与一次就成功, 都要能讲清楚

下面是四个独立 demo. 每行都重新创建 `fetch` 和 `pause`, 再调用同一个被测函数. 不在行与行之间共享已消耗的序列.

| 查询替身配置 | 预期输出 | 查询次数 | 等待次数 |
| --- | --- | ---: | ---: |
| `side_effect=[QueryTimeout(), QueryTimeout()]` | unavailable, data 为 None | 2 | 1, 参数 0.2 |
| `return_value=ok_data` | ok, 返回两条记录 | 1 | 0 |
| `return_value={"total": 0, "items": []}` | ok, 业务上没有匹配记录 | 1 | 0 |
| `return_value={"count": 2}` | invalid_payload, 不当成空数据 | 1 | 0 |

持续失败用例应检查第二次之后没有第三次调用, 也没有第二次等待. 正常首次成功则检查 `pause.assert_not_called()`. 空列表是合法业务结果, 不应该触发“直到查到记录才停止”的循环.

<figure><picture><source media="(max-width: 600px)" srcset="/images/fault-sequences/outcomes-mobile.svg"><img src="/images/fault-sequences/outcomes.svg" alt="合法空结果、错误结构和指定超时分开: 空结果返回ok且数量零, 错误结构返回invalid_payload, 连续两次超时返回unavailable; 不能统一折叠为空列表."></picture><figcaption>图 3. “没有数据”和“没有取得数据”是不同结论. 合并它们会让错误处理掩盖业务风险.</figcaption></figure>

如果给序列只放两个元素, 程序却调用了第三次, Mock 会抛出 `StopIteration`. 这是序列耗尽, 不是远端服务的新业务错误. 它能暴露次数不符, 但排查时要回到配置与调用轨迹, 不把它归类为真实服务故障.

默认 `reset_mock()` 清理调用记录, 不会把已消耗的 `side_effect` 迭代序列重新倒带. 即使清除了 side_effect, 也不等于重新安装了原来的失败脚本. 本篇每个场景新建替身, 让初始状态直接可见. 官方默认行为见 [reset_mock](https://docs.python.org/3.9/library/unittest.mock.html#unittest.mock.Mock.reset_mock).

## 立即抛异常, 能不能证明 3 秒超时有效?

不能. 假设真实客户端配置 3,000 ms 超时, 当前测试立即抛出 `QueryTimeout`, 只证明异常发生后代码选择了哪条处理路径. `pause` 收到 0.2, 只证明代码请求等待 200 ms. 两者都没有验证墙钟等待时间、网络取消、连接释放或超时后服务端是否继续执行.

<figure><picture><source media="(max-width: 600px)" srcset="/images/fault-sequences/time-mobile.svg"><img src="/images/fault-sequences/time.svg" alt="逻辑测试用立即异常和等待替身核对分支及参数; 真实时间机制测试需要可控的慢响应依赖和实际时钟测量, 两条证据支持不同结论."></picture><figcaption>图 4. 控制返回行为和验证真实时间机制是两类测试. 不将替身执行很快写成系统性能提升.</figcaption></figure>

同样, 给替身加一次 `sleep(3)` 也不自动等价于网络超时. 如果睡眠绕过了真正负责计时的客户端, 它只是拖慢测试. 真正要测超时机制, 应让请求穿过真实客户端, 对连接或响应施加可控延迟, 再测终止时间与资源行为. 本篇只解释这个边界, 不要求搭建服务器.

把这件事迁移到上一批 Agent 时, 如果约定是一次业务派发且不重试, 就配置一次超时, 检查调用数为 1、没有额外动作、回答说明未取得结果. **不能因为这里演示了两次查询, 就给 Agent 用例放宽成两次也通过.** 写操作超时更不能照搬只读重试策略, 因为没有响应不代表没有提交.

接下来读 [A3: 从测试用例到 Agent benchmark](../ai-evaluation/agent-benchmark-design.md), 把这些可控行为放进有初始状态和成功条件的任务中. [M3 面试专题](../../interviews/mock-testing/fault-sequences.md)帮助解释故障注入的证据边界.

## 术语与依据

| 英文名称与缩写 | 中文含义 | 本篇具体作用 |
| --- | --- | --- |
| Fault injection | 故障注入 | 在指定依赖位置制造可重复失败 |
| side_effect | 调用时的行为配置 | 连续返回、抛异常或按参数处理 |
| Retry / Attempt | 重试 / 尝试 | 一次重试对应最多两次尝试 |
| call_args_list | 完整调用参数列表 | 核对次数、顺序和参数 |
| StopIteration | 迭代结束异常 | 识别测试序列被额外消耗 |
| Wall-clock time | 实际流逝时间 | 区分参数断言与真实计时 |

核查日期: 2026-10-22. Python API 按 3.9 官方 `unittest.mock` 核对. 重试策略、数据与等待值为教学约定. 代码仅做静态语法和机制核查, 未运行故障注入或真实超时测试.
