---
title: 接口测试
pageClass: testing-notes
---

# 接口测试

本系列以某光电维护平台的生产问题录入与查询为教学背景. 示例字段和数值均为模拟, 不代表真实项目成果.

| 文章 | 类型 | 阅读重点 |
| --- | --- | --- |
| [一个接口测试到底在验证什么](./api-test-oracle.md) | 实践教程 | 建立独立预期, 对照响应、数据与副作用. |
| [从浏览器请求定位到 Postman 复现](./browser-to-postman.md) | 实践教程 | 对齐请求条件, 用单变量对比定位日期边界差异. |
| [I3. 参数、权限、分页和过滤条件怎样系统覆盖?](./api-coverage.md) | 实践教程 | 从规则与小样本推导独立预期, 检查权限、分页和组合. |
| [I4. 多个接口串起来以后, 怎样管理数据和断言?](./api-data-lifecycle.md) | 实践教程 | 传递动态编号, 保留独立断言, 明确准备、隔离与清理. |

阅读顺序: [W1 业务链](../web-testing/business-flow.md) → [I1 接口判定](../api-testing/api-test-oracle.md) → [I2 请求复现](../api-testing/browser-to-postman.md) → [I3 系统覆盖](api-coverage.md) → [I4 数据关联](api-data-lifecycle.md) → [M1 测试替身](../mock-testing/test-doubles.md).

[进入配套面试专题](../../interviews/api-testing/).
