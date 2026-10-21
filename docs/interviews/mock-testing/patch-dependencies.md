---
title: 怎样解释 patch 位置、作用域与调用断言?
category: Mock 测试
contentType: 面试专题
pageClass: testing-notes
---

# 怎样解释 patch 位置、作用域与调用断言?

<p class="article-kicker">第二批 · M2 面试专题</p>

配套学习: [Python 中应该替换哪一处依赖](../../learning/mock-testing/patch-dependencies.md). 业务模块为教学设计, Python API 按 3.9 文档核对, 不是实际排障经历.

## 开发视角: patch 了函数定义处, 为什么仍然调用真实函数?

考察名字绑定与查找路径. 可以先说明导入方式, 再沿运行时表达式解释替换目标.

### 可以这样回答

“要看被测代码从哪里取函数. 如果摘要模块已经执行了 `from issue_gateway import fetch_issues`, 它自己就保存了一个名字. 后来只替换 gateway 模块里的名字, 不会改变摘要模块已经保存的引用. 对这个版本应 patch `issue_summary.fetch_issues`.

“如果摘要采用 `import issue_gateway`, 运行时调用 `issue_gateway.fetch_issues`, 那么替换这个模块属性就能影响调用. 所以我会顺着真实调用表达式定位, 不仅看函数定义文件.”

<figure>
<picture><source media="(max-width: 600px)" srcset="/images/patch-dependencies/imports-mobile.svg"><img src="/images/patch-dependencies/imports.svg" alt="两种导入方式形成不同的函数查找路径, patch目标取决于运行时使用的名字."></picture>
<figcaption>先确定查找路径, 再确定替换位置.</figcaption>
</figure>

### 追问: 函数把依赖放在默认参数里呢?

默认参数在函数定义时就已经求值. 之后只替换模块变量, 不会自动更新那个保存好的参数对象. 这类调用可显式传入替身, 并确认被测函数确实使用这个参数. 不应该把“patch 路径正确”误当成所有已保存引用都会跟着变化.

易错回答是“永远 patch 定义处”或“永远 patch 测试文件”. 判断依据应是实际运行时的名字查找位置和导入时机.

## 测试视角: autospec 开启后, 还需要调用参数断言吗?

考察接口形状与业务值的区别. 可以按签名错误、值错误和输出错误三个层次回答.

### 可以这样回答

“需要. autospec 能帮助发现参数名字或数量不符合真实签名, 但它不知道这个场景应该查哪个客户. `customer_id="CUSTOMER-Y"` 可能完全符合签名, 只是与本用例预期不一致.

“所以我会检查输出, 同时根据需求核对调用参数和次数. 如果要求只调用一次, 用 `assert_called_once_with`; 只用 `assert_called_with` 不能排除之前多调用过. 这些检查仍然不能验证真实服务的鉴权或返回数据契约.”

### 追问: 返回字典缺少 total, autospec 会提前拒绝吗?

不会自动替你校验这个业务字典. 函数签名与返回内容约定是两件事. 要提供真实形状的教学返回并检查消费逻辑, 同时通过适当的契约或集成验证确认替身没有过时.

## 开发与测试交叉: with patch 能保证用例互不影响吗?

它能在退出范围时恢复绑定, 包括因异常退出. 但模块级名字在同一进程内可能被其他并发调用使用, 所以 with 不是线程隔离机制. 目标调用还必须发生在替换有效期间; 在范围外执行, 或异步任务晚于退出才查找依赖, 行为就可能与预期不同.

追问“如何避免污染”时, 应先让同步场景使用明确的替换范围和独立替身, 再根据并发模型采用显式依赖注入或进程隔离. 不应靠无条件扩大 patch 的全局持续时间来掩盖错误.

## 术语与依据

| 名称 | 含义与用途 |
| --- | --- |
| Namespace / Name binding | 定位名字及其当前指向 |
| Patch | 在指定范围临时改变绑定 |
| Autospec | 约束可见接口与调用签名 |
| Context manager | 控制替换生效及恢复时间 |

核查日期: 2026-10-22. 参考 [Where to patch](https://docs.python.org/3.9/library/unittest.mock.html#where-to-patch)、[patch](https://docs.python.org/3.9/library/unittest.mock.html#unittest.mock.patch)与 [Python 函数定义](https://docs.python.org/3.9/reference/compound_stmts.html#function-definitions). 未执行真实业务测试.
