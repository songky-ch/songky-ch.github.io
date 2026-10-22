---
title: Mock 测试
pageClass: testing-notes
---

# Mock 测试

从生产问题查询的教学案例出发, 先确定被测对象, 再控制依赖行为. 内容使用 Python 3.9 风格伪代码和完整示例, 不设练习任务.

| 文章 | 类型 | 阅读重点 |
| --- | --- | --- |
| [查询依赖不可用时, 我的 Mock 测试设计](./test-doubles.md) | 实践教程 | 理解 Stub、Fake、Mock 的用途与真实执行边界. |
| [Mock 没有生效时, 我会检查依赖引用位置](./patch-dependencies.md) | 实践教程 | 沿名字查找路径理解 patch、作用域和调用断言. |
| [查询超时和连续失败: 我的异常场景设计](./fault-sequences.md) | 实践教程 | 控制超时、错误结构和调用序列, 明确重试边界 |

前置: [接口判定](../api-testing/api-test-oracle.md). 第二批按 [I3](../api-testing/api-coverage.md) → [I4](../api-testing/api-data-lifecycle.md) → [查询依赖不可用时, 我的 Mock 测试设计](test-doubles.md) → [Mock 没有生效时, 我会检查依赖引用位置](patch-dependencies.md) 串联阅读.

[进入配套面试专题](../../interviews/mock-testing/).
