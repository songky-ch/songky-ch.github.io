import argparse
import hashlib
import json
import platform
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from domain import IssueStore, parse_bin, run_agent, to_wide_csv
from evaluation import calibration, paired_bootstrap, release_gate, summarize
from prepare_data import prepare
from deep_case import build_deep_case


def execute(cases, corpus, variant):
    rows, traces = [], []
    from evaluation import score_trial
    with tempfile.TemporaryDirectory() as work:
        for case in cases:
            store = IssueStore(str(Path(work) / (case["id"] + ".sqlite")))
            before = store.snapshot()
            start = time.perf_counter()
            result = run_agent(case["input"], corpus, store, variant)
            if case["id"] == "draft-retry":
                run_agent(case["input"], corpus, store, variant)
            row = score_trial(case, result, before, store.snapshot())
            row["duration_ms"] = (time.perf_counter() - start) * 1000
            rows.append(row)
            traces.append({"case_id": case["id"], "result": result,
                           "state_before": before, "state_after": store.snapshot()})
    return rows, traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--enforce-gate", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).parent
    cases, corpus = prepare(root / "data")
    rows, traces = execute(cases, corpus, "reference")
    broken, _ = execute(cases, corpus, "boundary_bug")
    unsafe, _ = execute(cases, corpus, "unsupported_cause")
    expected = [case["id"] for case in cases]
    gate = release_gate(rows, expected)
    deep_case = build_deep_case(args.out)
    report = {
        "environment": {"python": platform.python_version(), "os": platform.system()},
        "scope": "synthetic offline tools + scripted agent, no LLM or enterprise platform",
        "deep_case": deep_case["comparison"],
        "versions": {"dataset": "optical-teaching-v1", "rubric": "optical-r1",
                     "parser": "OPT1-v1", "model": "not_used",
                     "benchmark_sha256": hashlib.sha256(
                         (root / "data/benchmark.jsonl").read_bytes()).hexdigest(),
                     "code_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(root.glob("*.py"))}},
        "reference": {"passed": sum(r["hard_pass"] for r in rows), "total": len(rows),
                      "slices": summarize(rows), "release_gate": gate},
        "boundary_bug": {"failed_ids": [r["case_id"] for r in broken if not r["hard_pass"]],
                         "release_gate": release_gate(broken, expected)},
        "semantic_blind_spot": {
            "hard_passed": sum(r["hard_pass"] for r in unsafe),
            "meaning": "Hard checks cannot judge an unsupported natural-language root cause.",
            "release_gate": release_gate(unsafe, expected)},
        "paired_teaching_statistics": paired_bootstrap(
            {r["case_id"]: int(r["hard_pass"]) for r in broken},
            {r["case_id"]: int(r["hard_pass"]) for r in rows}),
        "synthetic_judge_calibration": calibration(
            [1, 1, 1, 1, 0, 0, 0, 0], [1, 1, 0, 1, 0, 1, 0, 0]),
        "statistics_warning": "Teaching cases are purposive and correlated, not production population estimates.",
    }
    for name, value in (("report.json", report), ("traces.json", traces),
                        ("case-results.json", rows)):
        (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))
    (args.out / "wide.csv").write_text(to_wide_csv(parse_bin((root / "data/one-record.bin").read_bytes())))
    junit = ET.Element("testsuite", name="optical-scripted-eval", tests=str(len(rows)),
                      failures=str(sum(not row["hard_pass"] for row in rows)))
    for row in rows:
        node = ET.SubElement(junit, "testcase", name=row["case_id"], classname=row["slice"],
                             time=str(row["duration_ms"] / 1000))
        if not row["hard_pass"]:
            ET.SubElement(node, "failure", message="hard checks failed").text = json.dumps(row["checks"])
    ET.ElementTree(junit).write(args.out / "junit.xml", encoding="utf-8", xml_declaration=True)
    suite = unittest.defaultTestLoader.discover(str(root), pattern="test_*.py")
    with (args.out / "unit-tests.txt").open("w") as stream:
        tests = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report["unit_tests"] = {"run": tests.testsRun, "failures": len(tests.failures),
                            "errors": len(tests.errors), "passed": tests.wasSuccessful()}
    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({"unit_tests": report["unit_tests"],
                      "reference": report["reference"], "boundary_bug": report["boundary_bug"],
                      "semantic_blind_spot": report["semantic_blind_spot"]},
                     ensure_ascii=False, indent=2))
    if not tests.wasSuccessful():
        return 1
    return 2 if args.enforce_gate and gate["decision"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
