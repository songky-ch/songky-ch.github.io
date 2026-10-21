import copy
import csv
import io
import json
import math
import struct
import tempfile
import threading
import unittest
import zlib
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from domain import IssueStore, lifecycle, parse_bin, retrieve, run_agent, to_wide_csv
from evaluation import calibration, paired_bootstrap, release_gate, retrieval_metrics, score_trial, wilson
from judge import judge_answer, validate_judgment
from prepare_data import prepare


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.body = bytes.fromhex("4f5054310100000100000064ff9c0ce4fb500100")
        self.blob = self.body + struct.pack(">I", zlib.crc32(self.body))

    def test_independent_known_bytes(self):
        self.assertEqual(parse_bin(self.blob), [{
            "timestamp_s": 100, "lane": 0, "valid": True,
            "temperature_c": -1, "voltage_v": 3.3, "rx_dbm": -12}])

    def test_every_truncation_rejected(self):
        for length in range(len(self.blob)):
            with self.subTest(length=length), self.assertRaises(ValueError):
                parse_bin(self.blob[:length])

    def test_crc_corruption(self):
        for offset in range(8, len(self.blob)):
            damaged = bytearray(self.blob)
            damaged[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, "crc_mismatch"):
                parse_bin(damaged)

    def test_unknown_version(self):
        damaged = bytearray(self.blob)
        damaged[4] = 2
        with self.assertRaisesRegex(ValueError, "unsupported_version"):
            parse_bin(damaged)

    def test_trailing_bytes(self):
        with self.assertRaisesRegex(ValueError, "length_mismatch"):
            parse_bin(self.blob + b"x")

    def test_invalid_flag(self):
        body = self.body[:-2] + bytes([2, 0])
        with self.assertRaisesRegex(ValueError, "invalid_record"):
            parse_bin(body + struct.pack(">I", zlib.crc32(body)))

    def test_invalid_lane(self):
        body = self.body[:-1] + bytes([4])
        with self.assertRaisesRegex(ValueError, "invalid_record"):
            parse_bin(body + struct.pack(">I", zlib.crc32(body)))

    def test_missing_measurement_stays_missing(self):
        body = self.body[:-2] + bytes([0, 0])
        rows = parse_bin(body + struct.pack(">I", zlib.crc32(body)))
        row = next(csv.DictReader(io.StringIO(to_wide_csv(rows))))
        self.assertIsNone(rows[0]["rx_dbm"])
        self.assertEqual(row["lane0_rx_dbm"], "")
        self.assertEqual(row["valid_lanes"], "0")

    def test_duplicate_rejected(self):
        body = self.body[:6] + b"\x00\x02" + self.body[8:] * 2
        with self.assertRaisesRegex(ValueError, "duplicate_record"):
            parse_bin(body + struct.pack(">I", zlib.crc32(body)))

    def test_wide_column_alignment(self):
        rows = parse_bin(self.blob)
        other = dict(rows[0], lane=3, rx_dbm=-9)
        wide = next(csv.DictReader(io.StringIO(to_wide_csv(rows + [other]))))
        self.assertEqual(wide["lane0_rx_dbm"], "-12.0")
        self.assertEqual(wide["lane3_rx_dbm"], "-9")
        self.assertEqual(wide["lane2_rx_dbm"], "")
        self.assertEqual(wide["valid_lanes"], "2")

    def test_permutation_invariance(self):
        rows = parse_bin(self.blob)
        rows += [dict(rows[0], lane=1, timestamp_s=101)]
        self.assertEqual(to_wide_csv(rows), to_wide_csv(list(reversed(rows))))

    def test_signed_and_scale_boundaries(self):
        for raw in (-32768, -1, 0, 1, 32767):
            body = self.body[:12] + struct.pack(">h", raw) + self.body[14:]
            actual = parse_bin(body + struct.pack(">I", zlib.crc32(body)))[0]["temperature_c"]
            self.assertEqual(actual, raw / 100)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.path = str(Path(self.work.name) / "issues.db")
        self.store = IssueStore(self.path)

    def test_idempotency(self):
        for _ in range(3):
            self.store.create_draft("A", "A", "analyst", "r1", "SYN-1")
        self.assertEqual(len(self.store.snapshot()), 1)

    def test_concurrent_idempotency(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(lambda _: self.store.create_draft(
                "A", "A", "analyst", "r1", "SYN-1"), range(12)))
        self.assertEqual(values, ["draft"] * 12)
        self.assertEqual(len(self.store.snapshot()), 1)

    def test_idempotency_payload_conflict(self):
        self.store.create_draft("A", "A", "analyst", "r1", "SYN-1")
        with self.assertRaisesRegex(ValueError, "idempotency_conflict"):
            self.store.create_draft("A", "A", "analyst", "r1", "SYN-2")

    def test_tenant_isolation(self):
        with self.assertRaises(PermissionError):
            self.store.create_draft("A", "B", "analyst", "r1", "SYN-1")
        self.assertEqual(self.store.snapshot(), [])

    def test_viewer_cannot_write(self):
        with self.assertRaises(PermissionError):
            self.store.create_draft("A", "A", "viewer", "r1", "SYN-1")

    def test_parameter_binding(self):
        module = "'; DROP TABLE issues; --"
        self.store.create_draft("A", "A", "analyst", "r1", module)
        self.assertEqual(self.store.snapshot()[0]["module_id"], module)

    def test_event_time_not_arrival_order(self):
        events = [{"event_id": str(i), "event_time": i, "sequence": i, "state": state}
                  for i, state in enumerate(
                      ["manufactured", "tested", "shipped", "installed", "returned", "analyzed"])]
        self.assertEqual(lifecycle(list(reversed(events)) + [events[1]]),
                         {"state": "analyzed", "event_count": 6})

    def test_invalid_lifecycle_transition(self):
        with self.assertRaisesRegex(ValueError, "invalid_transition"):
            lifecycle([{"event_id": "1", "event_time": 1, "sequence": 1, "state": "manufactured"},
                       {"event_id": "2", "event_time": 2, "sequence": 2, "state": "installed"}])

    def test_conflicting_event(self):
        event = {"event_id": "1", "event_time": 1, "sequence": 1, "state": "manufactured"}
        with self.assertRaisesRegex(ValueError, "conflicting_event"):
            lifecycle([event, dict(event, state="tested")])


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.cases, self.corpus = prepare(Path(self.work.name) / "data")
        self.store = IssueStore(str(Path(self.work.name) / "issues.db"))

    def test_rank_metrics_hand_calculated(self):
        metrics = retrieval_metrics(["x", "a", "b"], ["a", "b"], 3)
        self.assertAlmostEqual(metrics["precision_at_k"], 2 / 3)
        self.assertEqual(metrics["recall_at_k"], 1)
        self.assertEqual(metrics["mrr_at_k"], .5)
        self.assertAlmostEqual(metrics["ndcg_at_k"], (1 / math.log2(3) + .5) /
                               (1 + 1 / math.log2(3)))

    def test_no_relevant_documents_is_not_perfect(self):
        self.assertIsNone(retrieval_metrics([], [])["recall_at_k"])

    def test_empty_retrieval_with_answerable_task(self):
        self.assertEqual(retrieval_metrics([], ["a"])["recall_at_k"], 0)

    def test_duplicate_rank_is_error(self):
        with self.assertRaises(ValueError):
            retrieval_metrics(["a", "a"], ["a"])

    def test_metadata_filters(self):
        docs = retrieve(self.corpus, "rx low", "A", "DEMO", "F1", 2000)
        self.assertEqual([d["id"] for d in docs], ["RULE-F1"])

    def test_rule_effective_time_boundary(self):
        docs = retrieve(self.corpus, "rx low", "A", "DEMO", "F1", 999)
        self.assertEqual([d["id"] for d in docs], ["RULE-OLD"])
        docs = retrieve(self.corpus, "rx low", "A", "DEMO", "F1", 1000)
        self.assertEqual([d["id"] for d in docs], ["RULE-F1"])

    def test_freshness_boundary(self):
        task = copy.deepcopy(self.cases[0]["input"])
        task["telemetry"]["at"] = 1700
        self.assertEqual(run_agent(task, self.corpus, self.store)["status"], "hypothesis")
        task["telemetry"]["at"] = 1699
        self.assertEqual(run_agent(task, self.corpus, self.store)["status"], "insufficient")

    def test_boundary_mutation_detected(self):
        case = self.cases[1]
        result = run_agent(case["input"], self.corpus, self.store, "boundary_bug")
        self.assertFalse(score_trial(case, result, [], [])["hard_pass"])

    def test_unsupported_cause_needs_semantic_review(self):
        case = self.cases[0]
        result = run_agent(case["input"], self.corpus, self.store, "unsupported_cause")
        scored = score_trial(case, result, [], [])
        self.assertTrue(scored["hard_pass"])
        self.assertEqual(scored["semantic_status"], "not_evaluated")
        self.assertEqual(release_gate([scored], [case["id"]], 1)["decision"], "REVIEW")

    def test_incorrect_tool_argument_detected(self):
        case = self.cases[0]
        result = run_agent(case["input"], self.corpus, self.store)
        result["trace"][0]["args"]["module_id"] = "SYN-WRONG"
        self.assertFalse(score_trial(case, result, [], [])["hard_pass"])

    def test_unapproved_write_detected(self):
        case = self.cases[0]
        result = run_agent(case["input"], self.corpus, self.store)
        self.assertFalse(score_trial(case, result, [], [{"status": "closed"}])["hard_pass"])

    def test_gate_missing_and_duplicates(self):
        row = {"case_id": "a", "slice": "s", "hard_pass": True, "semantic_status": "pass"}
        self.assertEqual(release_gate([row], ["a", "b"])["decision"], "BLOCK")
        self.assertEqual(release_gate([row, row], ["a"])["decision"], "BLOCK")

    def test_gate_zero_cases(self):
        self.assertNotEqual(release_gate([], [])["decision"], "PASS")

    def test_gate_small_slice(self):
        row = {"case_id": "a", "slice": "s", "hard_pass": True, "semantic_status": "pass"}
        self.assertEqual(release_gate([row], ["a"])["decision"], "REVIEW")

    def test_wilson_not_100_percent_certainty(self):
        low, high = wilson(10, 10)
        self.assertAlmostEqual(low, .7224672, places=6)
        self.assertAlmostEqual(high, 1)

    def test_bootstrap_pairing(self):
        with self.assertRaises(ValueError):
            paired_bootstrap({"a": 1}, {"b": 1})
        self.assertEqual(paired_bootstrap({"a": 1}, {"a": 1})["percentile_95"], [0, 0])

    def test_judge_calibration(self):
        result = calibration([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual(result["agreement"], .5)
        self.assertEqual(result["cohen_kappa"], 0)
        self.assertEqual(result["false_accept_rate"], .5)


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.valid = {"verdict": "pass", "grounding": 2, "completeness": 2,
                      "evidence_ids": ["E1"], "reason": "有证据且说明了限制."}

    def test_valid_structure(self):
        self.assertEqual(validate_judgment(self.valid, ["E1"]), self.valid)

    def test_fabricated_evidence(self):
        with self.assertRaisesRegex(ValueError, "invented_evidence"):
            validate_judgment(self.valid, [])

    def test_boolean_is_not_score(self):
        with self.assertRaisesRegex(ValueError, "invalid_score"):
            validate_judgment(dict(self.valid, grounding=True), ["E1"])

    def test_contradictory_pass(self):
        with self.assertRaisesRegex(ValueError, "contradictory_pass"):
            validate_judgment(dict(self.valid, grounding=0), ["E1"])

    def test_http_adapter_contract_without_model(self):
        valid = self.valid
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                body = json.dumps({"message": {"content": json.dumps(valid)},
                                   "eval_count": 20}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = judge_answer(f"http://127.0.0.1:{server.server_port}", "mock-only",
                                  {"answer": "合成回答", "evidence": [{"id": "E1", "text": "合成证据"}]})
            self.assertEqual(result["status"], "scored", result)
            self.assertFalse(captured[0]["stream"])
            self.assertEqual(captured[0]["format"]["type"], "object")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
