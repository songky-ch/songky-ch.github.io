"""Explicit teaching KPI: first-test yield, not final yield or field reliability."""
from collections import defaultdict


def first_test_yield(events, start, end):
    unique = {}
    for event in events:
        if event["event_id"] in unique and unique[event["event_id"]] != event:
            raise ValueError("conflicting_event")
        unique[event["event_id"]] = event
    first = {}
    for event in unique.values():
        if event["result"] not in {"pass", "fail"}:
            raise ValueError("unknown_result")
        key = event["family"], event["module_id"]
        if key not in first or (event["at"], event["sequence"]) < (
                first[key]["at"], first[key]["sequence"]):
            first[key] = event
    groups = defaultdict(list)
    for event in first.values():
        if start <= event["at"] < end:
            groups[event["family"]].append(event["result"] == "pass")
    return {family: {"first_pass": sum(values), "first_tested": len(values),
                     "yield": sum(values) / len(values)}
            for family, values in sorted(groups.items())}
