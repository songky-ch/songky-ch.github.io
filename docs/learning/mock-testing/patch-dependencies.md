---
title: Python 中应该替换哪一处依赖?
category: Mock 测试
contentType: 实践教程
pageClass: testing-notes
---

# Python 中应该替换哪一处依赖?

<p class="article-kicker">第二批 · M2 · 沿名字查找路径理解 patch</p>

你把查询函数替换成 Mock, 执行测试时却仍然访问真实服务. 函数名没有拼错, 为什么替换没有生效?

因为“这个函数在哪里定义”和“被测代码执行时从哪里找到它”可以是两个位置. `patch` 临时改变的是某个位置上的名字指向, 不会自动追踪所有已经保存好的引用. 这一篇用两个模块把这句话拆开, 接续 [M1 的替身边界](test-doubles.md).

> 下面的 `issue_gateway`、`issue_summary` 和接口函数均为教学模块, 不存在于你的真实项目. `patch`、`Mock` 等名称是 Python 3.9 标准库真实 API, 代码整体仍是不可直接运行的教学伪代码. 本文不要求创建文件或连接服务.

## 两个名字, 可以指向同一个函数

先看查询函数的定义位置. 签名要求局点与客户作为关键字参数传入, 函数内部的网络实现本篇不展开.

```python
# issue_gateway.py, 教学伪代码, 不可直接运行.
def fetch_issues(*, site_id, customer_id):
    return query_remote_service(site_id=site_id, customer_id=customer_id)
```

摘要模块使用 `from ... import ...` 导入它. 除了依赖取得方式不同, 摘要逻辑与 M1 相同.

```python
# issue_summary.py, 教学伪代码, 不可直接运行.
from issue_gateway import fetch_issues

def build_summary(site_id, customer_id):
    data = fetch_issues(site_id=site_id, customer_id=customer_id)
    return {
        "text": "找到 {} 条生产问题".format(data["total"]),
        "first_ids": [row["id"] for row in data["items"]],
    }
```

导入完成后, 可以把它理解成两个抽屉里各放了一张指向同一函数的卡片: `issue_gateway.fetch_issues` 是一张, `issue_summary.fetch_issues` 是另一张. 运行摘要函数时, 它在自己模块里找 `fetch_issues`, 不会重新执行一次导入.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/patch-dependencies/names-mobile.svg"><img src="/images/patch-dependencies/names.svg" alt="from导入完成后, gateway和summary模块分别持有指向原函数的名字; 摘要执行时查找summary中的名字, 替换gateway的名字不改变summary已经保存的引用."></picture>
<figcaption>图 1. 同一对象可以有多个名字. patch 改一个绑定, 不代表其他绑定一起改变.</figcaption>
</figure>

因此, 在摘要模块**已经导入**的前提下, 只 patch `issue_gateway.fetch_issues` 不会改变摘要实际使用的名字. 官方将这个原则表述为在查找依赖的命名空间替换它, 见 [Python 3.9: Where to patch](https://docs.python.org/3.9/library/unittest.mock.html#where-to-patch). 导入与名字绑定的基础可查 [import 语句说明](https://docs.python.org/3.9/reference/simple_stmts.html#the-import-statement).

## 对本例, 替换摘要模块实际查找的位置

这里先导入摘要模块, 再在 `with` 范围内替换它的 `fetch_issues`. 在这段范围内, `build_summary` 仍是真实函数; 唯独查询依赖指向我们配置的对象.

```python
# 教学伪代码, 不可直接运行. 依赖的业务模块是上面的示意模块.
from unittest.mock import patch
import issue_summary

with patch("issue_summary.fetch_issues", autospec=True) as query_double:
    query_double.return_value = {
        "total": 2,
        "items": [{"id": "PRD-0201"}, {"id": "PRD-0202"}],
    }
    actual = issue_summary.build_summary("SITE-A", "CUSTOMER-X")
    assert actual == {
        "text": "找到 2 条生产问题",
        "first_ids": ["PRD-0201", "PRD-0202"],
    }
    query_double.assert_called_once_with(
        site_id="SITE-A", customer_id="CUSTOMER-X"
    )
```

按代码走一遍: 进入 `with` 时替换目标, 配置调用后的返回值, 执行摘要, 检查输出和调用, 最后退出作用域并恢复原绑定. `actual` 必须由真实摘要逻辑算出来, 不能直接等于 `query_double.return_value` 就算测试完成.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/patch-dependencies/patched-mobile.svg"><img src="/images/patch-dependencies/patched.svg" alt="进入with后summary.fetch_issues指向替身, 摘要调用它获得两条模拟记录并生成输出, 再验证调用参数; 退出with恢复原绑定."></picture>
<figcaption>图 2. 替换依赖后, 结果检查与调用检查仍然是两条独立证据.</figcaption>
</figure>

如果输出断言通过了, 但 `query_double.assert_called_once_with` 报“调用次数为 0”, 整条用例仍然失败. 这是一条定位线索: 可能 patch 错了位置, 也可能实际走了无需查询的分支, 或被测函数根本没有执行. 先沿控制流查, 不要直接删掉调用断言来获得通过.

## 换一种导入方式, 查找路径也会改变

如果摘要模块改成下面这样, 它保存的是模块引用, 调用时再从模块取函数:

```python
# 替代版本 issue_summary.py, 与前一版本二选一理解, 不叠加执行.
# 教学伪代码, 不可直接运行.
import issue_gateway

def build_summary(site_id, customer_id):
    data = issue_gateway.fetch_issues(site_id=site_id, customer_id=customer_id)
    return {"text": "找到 {} 条生产问题".format(data["total"])}
```

这时可以 patch `issue_gateway.fetch_issues`. 因为摘要执行时正是通过这个模块对象查找函数. 也可沿 `issue_summary.issue_gateway.fetch_issues` 到达同一个模块属性, 但没有必要同时 patch 两个路径. 关键是按实际表达式找名字, 不是背下“永远替换定义处”或“永远替换当前文件”这样的口诀.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/patch-dependencies/imports-mobile.svg"><img src="/images/patch-dependencies/imports.svg" alt="from导入的调用在summary.fetch_issues查找; import模块形式的调用先从summary取得gateway模块, 再查gateway.fetch_issues; 两种路径决定不同替换位置."></picture>
<figcaption>图 3. 顺着实际调用表达式走, 比看函数最初写在哪个文件更可靠.</figcaption>
</figure>

还有一种引用会让人困惑: `def build(fetch=fetch_issues)` 这样的默认参数会在函数定义时保存对象. 之后只 patch 模块同名变量, 不会自动改掉已保存的默认参数. 这类代码可在调用时显式传替身, 就像 M1 那样. 不要为一个测试随意改写函数的内部属性来强行替换.

## return_value、签名约束和调用断言各管什么?

`query_double` 是替代的可调用对象, `query_double.return_value` 是它被调用后交出的结果. 给前者随便添加一个 `total=2` 属性, 不等于调用后会返回 `{"total": 2}`. 要按真实依赖的返回层次设置数据, 才能把它正确送进摘要程序.

`autospec=True` 根据被替换对象建立接口约束. 本例若把 `customer_id` 错拼成 `customer`, 或遗漏必需参数, 签名检查会阻止这次错误调用. 但传入格式正确、业务值错误的 `customer_id="CUSTOMER-Y"`, 签名仍然合法, 需要调用参数断言才能发现.

更进一步, 即使签名正确且参数正确, 返回字典缺少 `total` 仍可能使摘要失败. `autospec` 不验证字典字段、业务权限或数据真实性. 它约束的是可见接口, 不能成为“替身和真实服务完全一致”的证明. 对动态创建的属性也有识别限制, 不能把它理解成执行了一遍真实对象.

| 工具 | 本例能检查什么 | 单独使用时还缺什么 |
| --- | --- | --- |
| `return_value` | 给调用提供明确数据 | 不检查调用参数是否正确 |
| `autospec=True` | 参数名字和调用签名 | 不知道 CUSTOMER-Y 在本用例里是错值 |
| `assert_called_once_with` | 一次调用且参数符合预期 | 不证明输出格式或真实服务可用 |
| 输出断言 | 摘要内容、编号与顺序 | 固定桩可能让错参数也得到相同输出 |

`assert_called_with` 只针对最近一次调用, 不能单独证明只调用一次. 此处选择 `assert_called_once_with` 正是因为“只查一次”属于本例约定. 如果未来允许多次查询, 应重新定义调用序列及次数约束, 不机械沿用这个断言. 这些 API 语义见 [Python 3.9 调用断言](https://docs.python.org/3.9/library/unittest.mock.html#unittest.mock.Mock.assert_called_once_with).

## 替换需要结束, 否则会污染下一条测试

`with patch(...)` 正常退出或因异常退出时, 都会撤销该范围的替换. 你仍需保证目标调用发生在这个范围内. 在 `with` 里配置好替身, 退出后才调用摘要函数, 会重新使用原依赖.

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/patch-dependencies/scope-mobile.svg"><img src="/images/patch-dependencies/scope.svg" alt="时间线分为替换前、with内部和退出后; 只在with内部调用目标才使用替身, 正常或异常退出都会恢复原绑定, 不影响范围外原有引用的独立行为."></picture>
<figcaption>图 4. 替换有明确的时间范围. 它不是线程隔离机制, 也不自动等待异步任务完成.</figcaption>
</figure>

模块级 patch 会影响同一进程内查找该名字的其他调用. `with` 能控制恢复时机, 并不意味着同一进程并发执行的其他测试看不到这个替身. 如果场景要并发, 可以通过独立进程或显式注入独立依赖来控制隔离; 本篇只讨论同步、串行的教学调用.

如果用了手动 `start()` 却忘记 `stop()`, 后续用例可能接着得到上一条的固定返回. 本篇选择 `with` 是为了让范围直接可见, 不是要求读者先学习所有装饰器和 patcher 写法. 下一阶段的 M3 会在此基础上展开异常和连续返回, 这里不提前加入自动重试策略.

将本篇方法迁移到工具调用时也是同样的边界问题: 固定某个工具执行函数的返回, 可以帮助检查上层怎样使用它, 但不会因此验证真实工具的鉴权或副作用. 先找上层实际查找工具函数的位置, 再明确哪些部分仍然真实执行.

[M2 面试专题](../../interviews/mock-testing/patch-dependencies.md)提供命名空间、作用域和调用约束的完整问答. 本批阅读链至此为“接口覆盖 → 数据关联 → 替身边界 → 依赖替换”, 继续 [A1 的 Agent 请求地图](../agent/agent-request-map.md), 再进入路由与工具选择测试.

## 术语与依据

| 名称 | 中文含义 | 本篇作用 |
| --- | --- | --- |
| Namespace | 命名空间 | 确定摘要运行时到哪里查函数 |
| Name binding | 名字绑定 | 解释两个名字为何可指向同一对象 |
| Patch | 临时替换绑定 | 让指定名字在测试范围内指向替身 |
| Return value | 调用返回值 | 配置替身交给摘要的数据 |
| Autospec | 自动接口约束 | 发现不符合真实函数签名的调用 |
| Context manager | 上下文管理器 | 通过 with 明确替换与恢复范围 |

核查日期: 2026-10-22. 按 Python 3.9 官方 `unittest.mock` 的 Where to patch、patch、autospeccing 及调用断言章节核对; 默认参数的绑定时机参考 [函数定义说明](https://docs.python.org/3.9/reference/compound_stmts.html#function-definitions). 业务模块和断言场景为本文教学设计. 代码只做静态语法与机制核对, 没有实际访问服务或运行测试.

继续阅读 [M3: 超时、错误和连续返回](./fault-sequences.md).
