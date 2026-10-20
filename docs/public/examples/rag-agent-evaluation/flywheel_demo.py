"""Run a synthetic admission and release exercise using only Python's standard library."""
import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parent
source = json.loads((root / "flywheel-input.json").read_text(encoding="utf-8"))
protected_families = set(source["protected_families"])
seen, routes, admitted = set(), [], []
for event in source["events"]:
    key = (event["event_id"], event["rule_version"])
    if key in seen:
        route = "duplicate"
    elif not event["privacy_approved"]:
        route = "restricted"
    elif not event["evidence_complete"]:
        route = "awaiting_evidence"
    elif event["review"] == "pending":
        route = "pending_review"
    elif event["review"] == "rejected":
        route = "dismissed"
    elif event["task_family"] in protected_families:
        route = "protected_holdout"
    else:
        assert event["review"] == "approved"
        route = "admitted_regression"
        admitted.append({
            "case_id": event["event_id"],
            "source_trace_id": event["trace_id"],
            "source_observation_id": event["observation_id"],
            "task_family": event["task_family"],
            "input": event["public_input"],
            "expected_output": event["reviewed_expected"],
            "snapshot_id": event["snapshot_id"],
            "review_version": event["review_version"],
            "rule_version": event["rule_version"],
            "split": "regression",
        })
    seen.add(key)
    routes.append({"event_id": event["event_id"], "route": route})

required = ("mteb", "ragas", "state", "performance")
releases = []
for candidate in source["candidates"]:
    states = [candidate["jobs"].get(name, "missing") for name in required]
    if "fail" in states:
        decision = "blocked_failure"
    elif any(state != "pass" for state in states):
        decision = "blocked_incomplete"
    else:
        decision = "eligible_for_canary"
    releases.append({"release_id": candidate["release_id"], "decision": decision})

counts = dict(Counter(item["route"] for item in routes))
assert counts == dict.fromkeys((
    "admitted_regression", "duplicate", "restricted", "awaiting_evidence",
    "pending_review", "protected_holdout", "dismissed",
), 1)
assert len(admitted) == 1
assert all(item["task_family"] not in protected_families for item in admitted)
assert [item["decision"] for item in releases] == [
    "blocked_failure", "eligible_for_canary", "blocked_incomplete",
]
result = {
    "notice": "Synthetic routing only; no real framework, reviewer or business execution.",
    "route_counts": counts, "routes": routes,
    "dataset": {"version": source["dataset_version"], "items": admitted},
    "releases": releases, "checks": "passed",
}
(root / "flywheel-results.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
)
print(json.dumps({"routes": counts, "releases": releases, "checks": "passed"}, indent=2))
