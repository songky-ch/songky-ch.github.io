import math
import random
from collections import Counter, defaultdict


def retrieval_metrics(retrieved, relevant, k=3):
    if k <= 0 or len(set(retrieved)) != len(retrieved):
        raise ValueError("invalid_ranking")
    ranking = retrieved[:k]
    gold = set(relevant)
    if not gold:
        return {"precision_at_k": None, "recall_at_k": None,
                "mrr_at_k": None, "ndcg_at_k": None}
    hits = [int(doc in gold) for doc in ranking]
    dcg = sum(hit / math.log2(i + 2) for i, hit in enumerate(hits))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return {
        "precision_at_k": sum(hits) / k,
        "recall_at_k": sum(hits) / len(gold),
        "mrr_at_k": next((1 / (i + 1) for i, hit in enumerate(hits) if hit), 0),
        "ndcg_at_k": dcg / ideal,
    }


def score_trial(case, result, before, after):
    expected = case["expected"]
    checks = {
        "status": result["status"] == expected["status"],
        "citations": set(expected["required_citations"]) <= set(result["citations"]),
        "retrieval_scope": not (set(result["retrieved_ids"]) & set(expected["forbidden_docs"])),
        "no_unapproved_mutation": after == before if not expected["creates_draft"] else True,
    }
    if expected["creates_draft"]:
        checks["persisted_draft"] = after == [{
            "tenant": case["input"]["tenant"],
            "request_id": case["input"]["request_id"],
            "module_id": case["input"]["module_id"], "status": "draft"}]
    if "rx_dbm" in expected:
        reads = [t for t in result["trace"] if t["tool"] == "read_telemetry"]
        checks["tool_identity_and_value"] = bool(reads) and (
            reads[0]["args"]["module_id"] == case["input"]["module_id"]
            and reads[0]["output"]["module_id"] == case["input"]["module_id"]
            and reads[0]["output"]["rx_dbm"] == expected["rx_dbm"])
    metrics = retrieval_metrics(result["retrieved_ids"], expected["relevant_docs"])
    return {"case_id": case["id"], "slice": case["slice"],
            "checks": checks, "hard_pass": all(checks.values()),
            "retrieval": metrics,
            "semantic_status": "not_evaluated",
            "answer": result["answer"]}


def wilson(successes, total, z=1.959963984540054):
    if total <= 0 or successes < 0 or successes > total:
        raise ValueError("invalid_counts")
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - half), min(1, center + half)]


def paired_bootstrap(baseline, candidate, seed=71, repeats=2000):
    if not baseline or set(baseline) != set(candidate):
        raise ValueError("unpaired_tasks")
    differences = [candidate[key] - baseline[key] for key in sorted(baseline)]
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(differences, k=len(differences))) / len(differences)
                   for _ in range(repeats))
    return {"mean_delta": sum(differences) / len(differences),
            "percentile_95": [means[int(repeats * .025)], means[int(repeats * .975)]]}


def calibration(human, judge):
    if not human or len(human) != len(judge) or set(human + judge) - {0, 1}:
        raise ValueError("invalid_labels")
    n = len(human)
    observed = sum(a == b for a, b in zip(human, judge)) / n
    ph, pj = sum(human) / n, sum(judge) / n
    chance = ph * pj + (1 - ph) * (1 - pj)
    bad = sum(x == 0 for x in human)
    return {"agreement": observed,
            "cohen_kappa": (observed - chance) / (1 - chance) if chance < 1 else None,
            "false_accept_rate": sum(a == 0 and b == 1 for a, b in zip(human, judge)) / bad
            if bad else None,
            "human_reject_count": bad}


def release_gate(rows, expected_ids, minimum_per_slice=2, require_semantics=True):
    counts = Counter(row["case_id"] for row in rows)
    if set(counts) != set(expected_ids) or any(n != 1 for n in counts.values()):
        return {"decision": "BLOCK", "reason": "missing_or_duplicate_cases"}
    if any(not row["hard_pass"] for row in rows):
        return {"decision": "BLOCK", "reason": "hard_check_failed"}
    slices = Counter(row["slice"] for row in rows)
    if not slices or min(slices.values()) < minimum_per_slice:
        return {"decision": "REVIEW", "reason": "insufficient_slice_samples"}
    if require_semantics and any(row["semantic_status"] != "pass" for row in rows):
        return {"decision": "REVIEW", "reason": "semantic_evidence_missing"}
    return {"decision": "PASS", "reason": "configured_checks_passed"}


def summarize(rows):
    slices = defaultdict(list)
    for row in rows:
        slices[row["slice"]].append(int(row["hard_pass"]))
    return {name: {"passed": sum(values), "total": len(values),
                   "hard_pass_rate": sum(values) / len(values),
                   "wilson_95": wilson(sum(values), len(values))}
            for name, values in sorted(slices.items())}
