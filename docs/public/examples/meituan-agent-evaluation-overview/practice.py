import json
import platform


cases = ["normal", "wrong_shop", "no_artifact", "valid_synonym", "missing_trace"]
expected = {
    "v1": [True, False, False, True, None],
    "v2": [True, True, False, True, None],
}
print(f"Python {platform.python_version()}; synthetic deterministic replay; no model/API")

for version in ("v1", "v2"):
    rows = []
    for case_id in cases:
        shop = "B" if version == "v1" and case_id == "wrong_shop" else "A"
        sales = 9 if shop == "B" else 100
        record = {
            "task_id": case_id,
            "session_id": f"session-{case_id}",
            "trace_id": f"{version}-{case_id}",
            "dataset_version": "d1",
            "rubric_version": "r2",
            "agent_version": version,
            "tool": {"name": "get_sales", "shop": shop, "sales": sales},
            "artifact": {"shop": shop, "sales": sales},
            "reply": "报告已生成" if case_id == "valid_synonym" else "已完成",
        }
        if case_id == "no_artifact":
            record["artifact"] = None
        if case_id == "missing_trace":
            record["tool"] = None

        old_pass = "已完成" in record["reply"]
        routes = []
        if record["tool"] is None:
            verdict = None
            routes.append("observability_fix")
        else:
            checks = {
                "tool_scope": record["tool"]["shop"] == "A",
                "artifact_exists": record["artifact"] is not None,
                "artifact_correct": record["artifact"] == {"shop": "A", "sales": 100},
            }
            verdict = all(checks.values())
            if not verdict:
                routes.append("agent_fix")
            if old_pass != verdict:
                routes.append("rubric_fix")
        rows.append({"id": case_id, "old_pass": old_pass, "pass": verdict, "routes": routes})

    assert [row["pass"] for row in rows] == expected[version]
    known = [row for row in rows if row["pass"] is not None]
    false_accept = sum(row["old_pass"] and not row["pass"] for row in known)
    false_reject = sum(not row["old_pass"] and row["pass"] for row in known)
    passed = sum(row["pass"] for row in known)
    summary = {
        "agent_version": version,
        "old_pass": f"{sum(row['old_pass'] for row in known)}/{len(known)}",
        "corrected_pass": f"{passed}/{len(known)}",
        "evidence_coverage": f"{len(known)}/{len(rows)}",
        "false_accept": false_accept,
        "false_reject": false_reject,
        "release": "ALLOW" if passed == len(rows) else "BLOCK",
        "rows": rows,
    }
    assert summary["release"] == "BLOCK"
    assert false_reject == 1
    assert false_accept == (2 if version == "v1" else 1)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

p, k = 0.75, 3
print(f"IID illustration: pass rate={p:.2%}; pass@{k}={1-(1-p)**k:.2%}; pass^{k}={p**k:.2%}")
print("Acceptance: scope error, missing artifact, rubric disagreement, unknown evidence and release gate verified.")
