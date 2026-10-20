# EvalScope 光模块维护架构实验

本目录为教学模拟, 无真实设备信息、账号或维修数据. 用真实 EvalScope 执行任务, 由固定回答模型返回人为设置的答案. 分数用于核验评测流程, 不代表真实模型能力.

- 源码提交: `3ff0a0c425cc89cec91a5d48141e22a61ce53a9b`.
- 实际环境: macOS arm64, Python 3.11.15, EvalScope 源码声明 `0.0.0_dev`.
- 框架完整运行与恢复: 2026-10-19. 发布前结构与练习校验: 2026-10-20.
- 配套学习文档: [架构详解](../../../learning/ai-evaluation/evalscope-architecture.md).
- 配套面试专题: [开发与测试视角](../../../interviews/ai-evaluation/evalscope-architecture.md).

## 下载文件

将以下文件保持目录结构保存到本地:

- [optics_eval.py](./optics_eval.py): 自定义任务、严格评分、报告与固定回答模型.
- [verify.py](./verify.py): 评分数据与错误变体的独立验收.
- [predictions.json](./predictions.json): baseline 与 candidate 两套固定回答.
- [data/diagnosis.jsonl](./data/diagnosis.jsonl): 4 条诊断模拟工单.
- [data/edge.jsonl](./data/edge.jsonl): 2 条边界模拟工单.
- [verification.json](./verification.json): 真实验证记录.
- [results/baseline-report.json](./results/baseline-report.json), [results/candidate-report.json](./results/candidate-report.json): 框架生成的原始报告.

## 运行

需要 Python 3.10 以上, 在独立环境安装固定提交:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "evalscope @ git+https://github.com/modelscope/evalscope.git@3ff0a0c425cc89cec91a5d48141e22a61ce53a9b"
python optics_eval.py baseline --output ./runs/baseline
python optics_eval.py candidate --output ./runs/candidate
python optics_eval.py candidate --output ./runs/candidate --resume
python optics_eval.py candidate --output ./runs/candidate --resume --rerun-review
python verify.py
```

验收: baseline 联合通过 2/6, candidate 5/6. 首跑各调用固定回答模型 6 次, candidate 两种恢复均调用 0 次. candidate 的 OM-003 因旧手册引用失败. 两轮首次运行执行摘要均为请求 6、完成 6、错误 0.

`--output` 首跑请使用新目录. 当前示例设 `no_timestamp=True`, 不要把多轮不同实验写进同一个旧目录; 恢复已有结果则明确使用 `--resume`.

## 验证的边界

已验证真实框架中的注册、加载、模型接口、单题评分、聚合、报告和缓存恢复. 未调用真实模型、裁判模型、检索器、设备工具或压测服务. `safe_action` 只约束本例输出字段, `evidence_valid` 只检查人工标注的支持引用集合, 均不等于生产系统全流程验收.
