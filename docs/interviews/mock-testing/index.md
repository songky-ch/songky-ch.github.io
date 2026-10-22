---
title: Mock 测试
pageClass: testing-notes
---

# Mock 测试

从生产问题查询的教学案例出发, 先确定被测对象, 再控制依赖行为. 内容使用 Python 3.9 风格伪代码和完整示例, 不设练习任务.

| 文章 | 类型 | 阅读重点 |
| --- | --- | --- |
| [M1. 依赖还没准备好, 我怎样继续测试?](./test-doubles.md) | 面试专题 | 理解 Stub、Fake、Mock 的用途与真实执行边界. |
| [M2. Python 中应该替换哪一处依赖?](./patch-dependencies.md) | 面试专题 | 沿名字查找路径理解 patch、作用域和调用断言. |
| [M3 异常与连续返回](./fault-sequences.md) | 面试专题 | 控制超时、错误结构和调用序列, 明确重试边界 |

前置: [接口判定](../api-testing/api-test-oracle.md). 第二批按 [I3](../api-testing/api-coverage.md) → [I4](../api-testing/api-data-lifecycle.md) → [M1](test-doubles.md) → [M2](patch-dependencies.md) 串联阅读.

[进入配套学习教程](../../learning/mock-testing/).
