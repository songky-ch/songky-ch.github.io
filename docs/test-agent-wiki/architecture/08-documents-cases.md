---
category: Agent
contentType: 架构设计
outline: [2, 3]
---

# 08. 文档、图片与用例生成

[返回目录](./index.md)

## 1. 输入输出边界

首期建议输入 PDF、DOCX、PNG、JPEG 与用户文字补充. 加密文件、旧 DOC、压缩项目包等不默认承诺支持; 支持矩阵在实现前确认. 用户上传并不自动发布到共享知识库.

输出包含规范化需求、流程结构、未解决问题、用例与覆盖映射. 不要求自动执行这些用例, 也不自动创建外部缺陷.

[![文档分型、OCR、图像理解、歧义处理和用例产出](/images/test-agent-wiki/07-documents.svg)](/images/test-agent-wiki/07-documents.svg)

从文件分型开始, 可提取文本和扫描页走不同处理路径. 流程图仍需关系理解. 所有路径汇总为带出处的需求, 关键歧义回到用户后才生成对应确定性预期.

## 2. 解析流水线

| 阶段 | 执行者 | 输出与依据 |
| --- | --- | --- |
| 文件校验 | 程序 | 文件签名、大小、页数、解压限制、哈希, 不只看扩展名 |
| 原生提取 | 解析子进程 | 段落、标题、表格和嵌入图片 |
| 页渲染/OCR | 解析子进程 | 页图、文字块、bbox、置信信息 |
| 版面重建 | 解析器 | 阅读顺序、表格关系、图文关联 |
| 视觉理解 | 获准多模态模型 | 图形节点、连线、条件、图例与不确定项 |
| 需求合并 | Agent + 规则 | 需求条目、冲突、来源与版本 |
| 用例生成 | 已激活 Skill | 结构化用例和需求映射 |
| 质量校验 | 规则 + 人工介入 | 缺失分支、重复项、无依据预期 |

PaddleOCR 的版面解析能力可以作为候选基础, 不等于自动保证流程图业务逻辑准确. 模型、语言、CPU/GPU、离线模型文件和复杂表格效果需要真实样本验证. [PP-StructureV3 官方文档](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html)

## 3. 流程图结构

FlowGraph 建议字段:

- nodes: id、label、kind(start/action/decision/end)、source_region.
- edges: id、from、to、condition、label、source_region、uncertainty.
- entry_nodes / exit_nodes, unresolved_items, source_version.

规则检查: 孤立节点、无入口、无终点、悬空连线、判断分支缺标签、互相矛盾条件、不可达节点、循环及并行汇合. 流程可能合法包含循环, 不能一概当错误.

路径爆炸时不声称“枚举所有路径”. 先明确覆盖准则: 节点/分支覆盖, 边界值与异常分支; 循环按零次、一次、多次等有界策略, 由业务条件决定是否适用. 对并行分支保留汇合条件, 不硬转成单线顺序.

遇到看不清的箭头或未标出的条件时, 保存 uncertainty 和具体区域引用, 触发 resolve_evidence. 用户可确认事实、补图或接受生成暂定用例; 暂定用例必须标记预期未确认, 不进入确定覆盖统计.

## 4. Skill 输入与输出契约

输入: document_version、requirements、flow_graphs、user_clarifications、coverage_policy、output_template_ref.

输出 TestCase 包含 case_id、title、requirement_refs、flow_edge_refs、preconditions、test_data、steps、expected_results、priority、case_type、assumptions、unresolved_refs、status.

核心质量规则:

- 每条业务预期有需求来源或用户补充依据.
- 每个关键判断的可行分支要有覆盖记录; 无法测试则解释原因.
- 操作步骤与预期对应, 不是只有“功能正常”.
- 不凭空生成未定义的业务错误码或权限规则.
- 不将排版错误、OCR 猜测升级为业务事实.
- 可导出 Markdown/JSON/CSV 作为首期提案; Excel 格式若需要后续单独确认.

## 5. 文档理解的异常出口

| 分支 | 处理 | 用户看到什么 |
| --- | --- | --- |
| 不支持/加密/损坏文件 | 停在文件校验 | 具体类型与重新提供要求 |
| 部分页可读, 部分页失败 | 保存部分结果, completeness=partial | 失败页码, 不宣称全文完成 |
| OCR/视觉不可用 | 阻塞依赖图片的步骤 | 缺少的模型或算力 |
| 文字与流程图冲突 | 请求用户确定 | 两处来源并列 |
| 流程无限路径 | 按有界覆盖方案生成 | 覆盖范围与排除项 |
| Skill 未激活/依赖不满足 | 不运行脚本 | 具体依赖与状态 |
| 用例结构不合法 | 限次修正或生成失败 | 保留可审阅草稿 |
| 文档中包含提示注入 | 作为文档内容 | 不执行其命令与扩权要求 |
| 用户取消 | 停止解析/模型请求, 保存已授权保留的部分产物 | CANCELLED, 部分产物标记 |

## 6. 验收样例

人工准备一个包含“通过/拒绝”分支和一条回路的脱敏文档, 标注节点、边、文字与页码. 分别测原生 PDF、扫描 PDF 和截图. 验收包括 OCR 文字错误率、节点/边提取正确性、需求引用准确性与可行分支覆盖, 不只看最终用例数量.

这一阶段不使用生成用例自己证明流程解析正确. 人工标注或已确认的业务结构才是参照.
