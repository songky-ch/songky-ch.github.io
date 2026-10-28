---
category: Agent
contentType: 技术学习
---

# Agent 技术学习 Wiki

以文档理解技术, 以交互模拟理解机制, 以后有可核验记录再加入真实回放. 不再以交付完整企业项目为目标.

## 从这里开始

- [学习路线与隔离概念纠正](./architecture/19-learning-guide.md)
- <a href="/demos/agent-lab/index.html" target="_self">打开动态 HTML 实验室</a>
- [完整章节目录](./architecture/)

**v0.3** 包含 19 个章节. 原 18 章保留为架构案例, 无 Docker、Windows 等条件不再是必须落地的约束. 用户身份与数据隔离、执行环境和资源限制要分开看, 并非每人必须长期占用一个 Docker 容器.

## 三个可操作演示

| 演示 | 可以操作和观察什么 |
| --- | --- |
| Agent 执行与审批 | 逐步运行、批准、拒绝、变参、取消、业务失败与 UNKNOWN |
| RAG 评测 | 改变 Top K、排序、故障和可见证据, 查看逐样本计算与汇总 |
| Agent 评测 | 对照合成轨迹、环境结果与安全规则, 比较两个样例版本 |

这些页面使用合成数据, 没有真实模型、检索器或业务服务调用. 状态转换和指标由页面程序实际计算. [查看检查记录](/demos/agent-lab/verification.json).

## 文档与下载

[进入全部章节](./architecture/) · [下载 v0.3 完整包](/downloads/test-agent-wiki-v0.3.zip).

旧版架构案例仍在原链接, 不删除既有内容. 后续按学习需要逐项补充演示, 不承诺本版已覆盖全部技术的动态实现.
