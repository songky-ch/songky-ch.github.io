"""合成机制练习: 固定排名、脚本决策和手工图, 不调用真实模型."""

from collections import defaultdict, deque
import platform


docs = {
    "D1": {"text": "2026-10-01 支付服务出现 E1042, 当次原因为连接池耗尽.", "source": "incidents/payment-2026-10-01.md", "locator": "L1-L2"},
    "D2": {"text": "支付运行手册: 常规排查连接池和请求积压.", "source": "runbooks/payment.md", "locator": "L1"},
    "D3": {"text": "结算服务依赖支付服务.", "source": "dependencies/settlement.md", "locator": "L1"},
    "D4": {"text": "对账服务依赖结算服务.", "source": "dependencies/reconciliation.md", "locator": "L1"},
    "D5": {"text": "2026-10-03 通知服务出现模板配置错误.", "source": "incidents/notification-2026-10-03.md", "locator": "L1"},
}


def fuse(rankings):
    scores = defaultdict(float)
    for ids in rankings:
        for rank, doc_id in enumerate(ids, start=1):
            scores[doc_id] += 1 / (60 + rank)
    return sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))


def impact_paths(edges, max_calls):
    queue = deque([("支付", [])])
    seen = {"支付"}
    paths, trace = [], []
    while queue and len(trace) < max_calls:
        target, path = queue.popleft()
        hits = [(dependent, source) for dependent, dependency, source in edges if dependency == target]
        trace.append({"tool": "find_dependents", "target": target, "sources": [source for _, source in hits]})
        for dependent, source in hits:
            if dependent not in seen:
                seen.add(dependent)
                new_path = path + [source]
                paths.append({"service": dependent, "sources": new_path})
                queue.append((dependent, new_path))
    return {"status": "insufficient" if queue else "sufficient", "paths": paths, "trace": trace}


print("Python", platform.python_version())
print("合成输入: 固定召回排名, 脚本化决策, 手工图. 未调用模型/数据库.")
dense, lexical = ["D2", "D3"], ["D1", "D2"]
assert "D1" not in dense
hybrid = fuse([lexical, dense])
assert hybrid == ["D2", "D1", "D3"]
assert "D1" not in fuse([["D2"], dense])
print("传统候选:", dense, "; 缺少 Q1 必需证据 D1")
print("RRF 融合:", hybrid, "; 补入 D1, 但 D2 排第一, 不能据此证明当次根因")

trace = [{"tool": "search", "query": "E1042", "hits": ["D1"]}]
hit_id = trace[0]["hits"][0]
trace.append({"tool": "open", "doc_id": hit_id})
bundle = {"status": "sufficient", "evidence": [{"doc_id": hit_id, "version": "v1", **docs[hit_id]}], "missing": []}
assert len(trace) == 2
assert all(item["text"] and item["source"] and item["locator"] and item["version"] for item in bundle["evidence"])
assert "E1042" in bundle["evidence"][0]["text"]
print("脚本化检索组件:", [item["tool"] for item in trace], "; 原文:", bundle["evidence"][0]["text"])

edges = [("结算", "支付", "D3"), ("对账", "结算", "D4")]
full = impact_paths(edges, max_calls=3)
limited = impact_paths(edges, max_calls=1)
assert full["status"] == "sufficient"
assert full["paths"] == [{"service": "结算", "sources": ["D3"]}, {"service": "对账", "sources": ["D3", "D4"]}]
assert limited["status"] == "insufficient"
assert len(limited["trace"]) == 1 and len(limited["paths"]) == 1
print("脚本化两跳:", full["paths"], "; 调用数:", len(full["trace"]))
print("预算 1:", limited["status"], limited["paths"], "; 不宣称第二跳已完成")

for path in full["paths"]:
    assert all(source in docs for source in path["sources"])
print("手工图潜在影响: 支付 → 结算 → 对账; 每条关系均可回取 D3/D4 原文")
removed = impact_paths(edges[:1], max_calls=3)
assert [path["service"] for path in removed["paths"]] == ["结算"]
cycle = impact_paths(edges + [("支付", "对账", "cycle-fixture")], max_calls=4)
assert len(cycle["paths"]) == 2 and len(cycle["trace"]) == 3
print("移除 D4: 仅保留结算; 依赖环: 访问集合阻止重复遍历")
print("通过: 融合、缺失证据、原文契约、两跳来源、预算不足、删边与环检查")
print("未验证: 自动抽取、真实 Agent 决策、生成答案、社区全局总结与权限系统")
