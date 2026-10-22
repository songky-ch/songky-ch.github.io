---
title: 接口测试
pageClass: testing-notes
---

# 接口测试

本系列以某光电维护平台的生产问题录入与查询为教学背景. 示例字段和数值均为模拟, 不代表真实项目成果.

| 文章 | 类型 | 阅读重点 |
| --- | --- | --- |
| [我判断接口结果时, 不只看 HTTP 200](./api-test-oracle.md) | 实践教程 | 建立独立预期, 对照响应、数据与副作用. |
| [从页面异常到 Postman: 我的请求复现思路](./browser-to-postman.md) | 实践教程 | 对齐请求条件, 用单变量对比定位日期边界差异. |
| [生产问题查询的参数、权限与分页覆盖](./api-coverage.md) | 实践教程 | 从规则与小样本推导独立预期, 检查权限、分页和组合. |
| [接口串联中的数据传递、隔离和清理](./api-data-lifecycle.md) | 实践教程 | 传递动态编号, 保留独立断言, 明确准备、隔离与清理. |

阅读顺序: [W1 业务链](../web-testing/business-flow.md) → [I1 接口判定](../api-testing/api-test-oracle.md) → [I2 请求复现](../api-testing/browser-to-postman.md) → [生产问题查询的参数、权限与分页覆盖](api-coverage.md) → [接口串联中的数据传递、隔离和清理](api-data-lifecycle.md) → [M1 测试替身](../mock-testing/test-doubles.md).

[进入配套面试专题](../../interviews/api-testing/).
