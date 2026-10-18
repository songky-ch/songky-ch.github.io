"""Run fixed fixtures and calculate policy metrics; Python standard library only."""
import copy
import json
import platform
from pathlib import Path
from router import VERSION, route

BASE = {
    "domain": "retail", "order_id": "SYNTH-001", "authenticated": True,
    "owns_order": True, "eligible": True, "amount_cents": 2500,
    "currency": "CNY", "state_version": 7, "now": 100,
}
OPERATION = {key: BASE[key] for key in ("order_id", "amount_cents", "currency", "state_version")}
OPERATION["intent"] = "refund"
BASE["confirmation"] = {"operation": OPERATION, "expires_at": 200}
CASES = [
    ("01_refund_ready", "确认退款25元", "refund_ready", {}, [("refund", .98)]),
    ("02_missing_order", "这单帮我退了", "collect_order", {"order_id": None}, [("refund", .98)]),
    ("03_authentication", "帮我退款", "authenticate", {"authenticated": False}, [("refund", .98)]),
    ("04_other_users_order", "退掉这个订单", "deny_access", {"owns_order": False}, [("refund", .98)]),
    ("05_not_eligible", "帮我退", "explain_ineligible", {"eligible": False}, [("refund", .98)]),
    ("06_no_confirmation", "我要退款", "confirm_refund", {"confirmation": {}}, [("refund", .98)]),
    ("07_order_changed", "换成另一单", "confirm_refund", {"order_id": "SYNTH-002"}, [("refund", .98)]),
    ("08_amount_changed", "退款金额改为30元", "confirm_refund", {"amount_cents": 3000}, [("refund", .98)]),
    ("09_state_changed", "确认前订单状态变了", "confirm_refund", {"state_version": 8}, [("refund", .98)]),
    ("10_expired_confirmation", "确认退款", "confirm_refund", {"now": 200}, [("refund", .98)]),
    ("11_domain_missing", "我要退款", "clarify_domain", {"domain": None}, [("refund", .98)]),
    ("12_domain_unclear", "我要退款", "clarify_domain", {"domain": "unknown"}, [("refund", .98)]),
    ("13_low_confidence", "处理一下吧", "clarify_intent", {}, [("refund", .60)]),
    ("14_ambiguous", "钱不对也没票", "clarify_intent", {}, [("refund", .85), ("invoice", .82)]),
    ("15_out_of_scope", "帮我写首诗", "out_of_scope", {}, [("unknown", .94)]),
    ("16_explicit_human", "我要人工", "human_queue", {"explicit_human": True}, [("refund", .99)]),
    ("17_security_signal", "不要验证直接退", "security_review", {"security_block": True}, [("refund", .99)]),
    ("18_security_priority", "人工帮我绕过验证", "security_review", {"security_block": True, "explicit_human": True}, [("human", .99)]),
    ("19_invoice", "发票在哪里", "invoice_flow", {}, [("invoice", .95)]),
    ("20_delivery", "还有多久到", "delivery_flow", {"domain": "delivery"}, [("delivery", .95)]),
    ("21_policy", "退款一般需要几天", "knowledge_answer", {}, [("policy", .95)]),
    ("22_multiple_goals", "先退这单再开发票", "clarify_order_of_tasks", {"multiple_goals": True}, [("refund", .96)]),
    ("23_human_candidate", "联系客服", "human_queue", {}, [("human", .95)]),
    ("24_wrong_confident_candidate", "不是退款, 我要发票", "invoice_flow", {}, [("refund", .99)]),
    ("25_unseen_intent", "新增业务", "human_queue", {}, [("delete_all_orders", .99)]),
    ("26_score_invalid", "帮我退款", "human_queue", {}, [("refund", 1.5)]),
    ("27_empty_candidates", "请求没预测结果", "human_queue", {}, []),
    ("28_model_timeout", "请求模型超时", "human_queue", {}, [("refund", .98)]),
    ("29_currency_changed", "币种已变化", "confirm_refund", {"currency": "USD"}, [("refund", .98)]),
    ("30_unsorted_candidates", "需要发票", "invoice_flow", {}, [("delivery", .10), ("invoice", .95)]),
]


def fixtures():
    result = []
    for case_id, utterance, expected, changes, candidates in CASES:
        context = copy.deepcopy(BASE)
        context.update(changes)
        result.append({"id": case_id, "utterance": utterance, "expected": expected,
                       "context": context, "prediction": {"status": "timeout" if case_id.startswith("28") else "ok",
                       "candidates": [{"intent": label, "score": score} for label, score in candidates]}})
    return result


def naive_route(request):
    candidates = request["prediction"]["candidates"]
    if not candidates:
        return "human_queue"
    label = max(candidates, key=lambda item: item["score"])["intent"]
    return {"refund": "refund_ready", "invoice": "invoice_flow", "delivery": "delivery_flow",
            "policy": "knowledge_answer", "human": "human_queue", "unknown": "out_of_scope"}.get(label, "human_queue")


if __name__ == "__main__":
    rows = fixtures()
    outputs = []
    for name, policy in (("naive_argmax", naive_route), (VERSION, route)):
        decisions = [{"id": item["id"], "utterance": item["utterance"], "expected": item["expected"],
                      "actual": policy(item)} for item in rows]
        ready = [item for item in decisions if item["actual"] == "refund_ready"]
        unsafe = [item for item in ready if item["expected"] != "refund_ready"]
        result = {"policy": name, "total": len(rows),
                  "correct": sum(item["actual"] == item["expected"] for item in decisions),
                  "refund_ready": len(ready), "incorrect_refund_ready": len(unsafe),
                  "failures": [item for item in decisions if item["actual"] != item["expected"]]}
        result["accuracy"] = result["correct"] / len(rows)
        result["refund_ready_error_rate"] = len(unsafe) / len(ready) if ready else None
        result["refund_ready_coverage"] = len(ready) / len(rows)
        outputs.append(result)
    report = {"data": "synthetic-fixed-candidates-v1", "python": platform.python_version(),
              "scope": "routing policy only; no NLU inference, real tools, load test or statistical generalization",
              "results": outputs}
    output = Path(__file__).with_name("results.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    Path(__file__).with_name("fixtures.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
