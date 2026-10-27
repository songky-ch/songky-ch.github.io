---
category: Agent
contentType: 项目 Wiki
---

# 测试 Agent 项目 Wiki

从零设计面向测试团队的内部 Agent. 本栏目完整保留架构评审稿, 先确认方案, 再进入开发.

**当前版本: v0.2, 设计评审稿.** 已整理 18 个设计章节、12 张图解和 110 条分支检查项. 公司认证、Linux 隔离和实际容量仍需验证, 尚未开始业务开发.

## 架构设计

[进入完整 Wiki 与章节目录](./architecture/)

涵盖 Windows + WebView2、Linux 单主服务与任务子进程、Agent 工具调用、HITL、长短期记忆、Agentic RAG、图片需求理解、专项测试、评测、API 和部署.

建议先读 [目标与决策](./architecture/01-scope-decisions.md), 再读 [技术底座](./architecture/02-stack-architecture.md), 之后逐章确认.

[![系统架构全景](/images/test-agent-wiki/01-architecture.svg)](/images/test-agent-wiki/01-architecture.svg)

## 本次新增

- [上下文工程与压缩](./architecture/16-context-engineering.md)
- [Prompt 工程与版本管理](./architecture/17-prompt-engineering.md)
- [Harness 运行机制](./architecture/18-harness-runtime.md)

## 完整下载

[下载 Wiki v0.2 压缩包](/downloads/test-agent-wiki-v0.2.zip), 包含 Markdown、离线 HTML 阅读版、SVG/PNG 图解与检查记录.

本文档经用户明确授权公开发布. 文档中的例子不包含真实凭证或公司内网地址.
