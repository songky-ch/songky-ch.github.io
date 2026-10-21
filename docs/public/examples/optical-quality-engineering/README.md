# 光模块质量工程实验

本目录使用合成数据与教学协议. Python 3.12, 无第三方依赖. 不连接企业平台、设备或真实模型. `run_agent` 是固定规则的可执行替身, 不是 LLM.

## 运行

```bash
NO_PROXY=127.0.0.1,localhost python run_lab.py --out results
```

预期: 65项自动测试通过, 17条样本确定性检查通过, 边界缺陷命中2条失败, 无依据自然语言根因不会被程序评分自动识别. 严格发布结论保持 REVIEW.

```bash
NO_PROXY=127.0.0.1,localhost python run_lab.py --out results --enforce-gate
```

第二条命令预期退出2, 表示语义证据缺失, 不表示实验代码异常. 0=实验执行成功(启用门禁时还需门禁通过), 1=自动测试失败, 2=门禁未通过.

本地 HTTP 契约测试需要允许回环端口. 有代理时设置上述 NO_PROXY; 不需访问互联网. 每次运行会重建 `data/` 合成数据并覆盖所选 `results/` 教学结果, 不要用这些路径存真实数据.

## 文件

| 文件 | 内容 |
| --- | --- |
| domain.py | 教学bin解析、宽表、生命周期、SQLite幂等、元数据检索与固定规则Agent |
| dashboard.py | 按完整历史确定首次测试后计算窗口内首测良率 |
| evaluation.py | 检索指标、确定性断言、门禁、Wilson区间、配对bootstrap和校准 |
| judge.py | Ollama真实HTTP适配器与结构验证, 本次未运行真实模型 |
| prepare_data.py | 显式编写的17条教学样本、文档和固定字节 |
| run_lab.py | 执行三种版本、保存轨迹、报告、宽表和JUnit, 运行自动测试 |
| test_lab.py / test_dashboard.py / test_deep_case.py | 65项测试, 含三轮HTTP工具契约、并发幂等和状态判据 |
| window_analysis.py / deep_case.py | 5秒×4通道完整案例, 连续点、迟滞、缺测与假恢复变异 |
| tool_agent.py | 实际模型工具循环与Ollama传输, 禁止动作和预算边界 |
| data/benchmark.jsonl | 输入与隐藏预期, 被测Agent只收到input |
| results/report.json | 本次实际运行状态与版本哈希 |
| results/unit-tests.txt | 自动测试记录 |
| results/traces.json | 参考执行轨迹与业务状态快照 |
| results/junit.xml | 仅确定性断言的JUnit结果, 不代表发布放行 |

## 真实模型实操: 未执行

前置条件: 已批准并可用的Ollama服务与模型. 使用合成输入, 将模型名改成服务已有的实际名称:

```bash
NO_PROXY=127.0.0.1,localhost python judge.py \
  --url http://localhost:11434 \
  --model YOUR_APPROVED_MODEL \
  --input data/judge-input.json \
  --output results/live-judge.json
```

本次只验证本机mock HTTP契约, 不代表Ollama或企业网关集成已验证. 接入企业平台时替换真实调用与状态读取, 保留标签隔离、评分器状态和审计证据. 真实模型输出还需要人工校准, 不能仅凭格式合法放行.

## 能力边界

此实验不实现真实CMIS/厂商协议、自然语言意图理解、向量索引、硬件控制、生产压测或完整分布式事务. 合成输入和固定规则用于把测试判据与评测链路做成可运行代码. 小样本统计只演示计算, 不估计真实模型/生产总体效果.

## 深入两条主链

运行 `python deep_case.py`, 检查 `results/window-analysis.json`: lane0参考状态为UNKNOWN, 缺测被误填为有效0的变异版为NORMAL. 两者CRC均合法, 但只有前者保留正确数据语义.

`tool_agent.py` 是多轮工具执行器, 本次用本机脚本化模型HTTP响应验证三轮调用与结果回传. 真实模型命令未执行:

```bash
NO_PROXY=127.0.0.1,localhost python tool_agent.py --url http://localhost:11434 --model YOUR_APPROVED_MODEL --out results
```

`live-agent.json`的answered仅表示输出了回答; hard_pass检查必要取证与禁止动作; 语义未评分时release_decision仍为REVIEW. 生产平台应读取门禁字段, 不能用模型命令的0退出码替代发布决策.
