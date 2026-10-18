import json
from pathlib import Path

root = Path(__file__).resolve().parent
cases = json.loads((root / "cases.json").read_text(encoding="utf-8"))
rows = []
for case in cases:
    required = set(case["required_evidence"])
    retrieved = set(case["retrieved_evidence"])
    evidence_ok = required <= retrieved and case["policy_current"]
    decision_ok = case["decision"] == case["expected_decision"]
    params_ok = all(
        call["order_id"] == case["order_id"]
        and call["amount_cents"] == case["expected_refund_cents"]
        for call in case["refund_calls"]
    )
    constraints_ok = len(case["refund_calls"]) <= 1 and all(
        case["confirmed_at"] is not None
        and case["confirmed_at"] < call["at"]
        for call in case["refund_calls"]
    )
    state_ok = None if case["observed_refund_cents"] is None else (
        case["observed_refund_cents"] == case["expected_refund_cents"]
        and case["other_order_refund_cents"] == 0
    )
    checks = {
        "evidence": evidence_ok,
        "decision": decision_ok,
        "parameters": params_ok,
        "constraints": constraints_ok,
        "state": state_ok,
        "communication": case["communication_ok"],
    }
    failed = [name for name, value in checks.items() if value is False]
    status = "failure" if failed else (
        "unknown" if any(value is None for value in checks.values()) else "success"
    )
    rows.append({
        "case_id": case["case_id"],
        "id_recall": len(required & retrieved) / len(required),
        "id_precision": len(required & retrieved) / len(retrieved),
        "checks": checks,
        "failed_checks": failed,
        "status": status,
    })

total = len(rows)
successes = sum(row["status"] == "success" for row in rows)
failures = sum(row["status"] == "failure" for row in rows)
unknown = sum(row["status"] == "unknown" for row in rows)
summary = {
    "planned_trials": total,
    "known_successes": successes,
    "known_failures": failures,
    "unknown": unknown,
    "observed_success_fraction": successes / total,
    "success_rate_on_judged": successes / (total - unknown),
    "judgment_coverage": (total - unknown) / total,
    "success_identification_bounds": [successes / total, (successes + unknown) / total],
}
result = {"data_type": "synthetic_annotated_traces", "summary": summary, "cases": rows}
(root / "results.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
