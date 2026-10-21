import copy
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import Mock
from deep_case import make_fixture
from tool_agent import OllamaChat, RULE, run_tool_agent
from window_analysis import inspect_window


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.blob, self.manifest = make_fixture()

    def inspect(self):
        return inspect_window(self.blob, self.manifest, "SYN-WINDOW-1", 100, 105)

    def test_every_state_transition(self):
        lane = self.inspect()["lanes"]["0"]
        self.assertEqual([p["state"] for p in lane["timeline"]],
                         ["UNKNOWN", "ALERT", "ALERT", "UNKNOWN", "UNKNOWN"])
        self.assertEqual(lane["events"], [{"at": 101, "from": "UNKNOWN", "to": "ALERT"},
                                          {"at": 103, "from": "ALERT", "to": "UNKNOWN"}])

    def test_expected_grid_denominator(self):
        lane = self.inspect()["lanes"]["0"]
        self.assertEqual((lane["valid_samples"], lane["expected_samples"]), (4, 5))
        self.assertFalse(lane["complete"])

    def test_other_lanes_not_contaminated(self):
        for lane in ("1", "2", "3"):
            self.assertEqual(self.inspect()["lanes"][lane]["last_state"], "NORMAL")

    def test_missing_to_zero_mutation_creates_false_recovery(self):
        blob, manifest = make_fixture(missing_as_zero=True)
        bad = inspect_window(blob, manifest, "SYN-WINDOW-1", 100, 105)
        self.assertEqual(bad["lanes"]["0"]["last_state"], "NORMAL")
        self.assertEqual(self.inspect()["lanes"]["0"]["last_state"], "UNKNOWN")

    def test_wrong_module_rejected(self):
        with self.assertRaisesRegex(ValueError, "module_mismatch"):
            inspect_window(self.blob, self.manifest, "SYN-OTHER", 100, 105)

    def test_wrong_blob_rejected(self):
        with self.assertRaisesRegex(ValueError, "file_mismatch"):
            inspect_window(self.blob + b"x", self.manifest, "SYN-WINDOW-1", 100, 105)

    def test_no_samples_is_unknown_not_healthy(self):
        result = inspect_window(self.blob, self.manifest, "SYN-WINDOW-1", 200, 205)
        self.assertEqual(result["lanes"]["0"]["last_state"], "UNKNOWN")
        self.assertIsNone(result["lanes"]["0"]["mean_power_dbm"])

    def test_power_mean_is_not_arithmetic_dbm_mean(self):
        lane = self.inspect()["lanes"]["0"]
        self.assertNotAlmostEqual(lane["mean_power_dbm"], (-13 -13 -11.5 -10.5) / 4)
        self.assertEqual(self.inspect()["root_cause"], "not_determined")


class ToolLoopTests(unittest.TestCase):
    def setUp(self):
        blob, manifest = make_fixture()
        self.window = inspect_window(blob, manifest, "SYN-WINDOW-1", 100, 105)
        self.read = {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "read_window", "arguments": {"module_id": "SYN-WINDOW-1"}}}]}
        self.rule = {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "read_rule", "arguments": {"rule_id": RULE["id"]}}}]}
        self.final = {"role": "assistant", "content": "历史告警成立, 当前恢复证据不足; 根因未确定."}

    def test_multi_turn_observation_reaches_next_request(self):
        snapshots = []
        replies = iter([self.read, self.rule, self.final])
        def chat(messages, tools):
            snapshots.append(copy.deepcopy(messages))
            return next(replies)
        result = run_tool_agent(chat, self.window)
        self.assertTrue(result["hard_pass"])
        self.assertEqual(result["release_decision"], "REVIEW")
        self.assertEqual(snapshots[1][-1]["role"], "tool")
        self.assertIn('"id": "WINDOW-1"', snapshots[1][-1]["content"])

    def test_answer_without_tools_fails_evidence_gate(self):
        result = run_tool_agent(Mock(return_value=self.final), self.window)
        self.assertFalse(result["hard_pass"])

    def test_forbidden_write_attempt_is_recorded(self):
        bad = {"role": "assistant", "tool_calls": [
            {"function": {"name": "close_issue", "arguments": {}}}]}
        result = run_tool_agent(Mock(side_effect=[bad, self.final]), self.window)
        self.assertEqual(result["trace"][0]["output"]["error"], "tool_or_scope_forbidden")
        self.assertEqual(result["release_decision"], "BLOCK")

    def test_wrong_object_is_not_read(self):
        bad = copy.deepcopy(self.read)
        bad["tool_calls"][0]["function"]["arguments"]["module_id"] = "SYN-OTHER"
        result = run_tool_agent(Mock(side_effect=[bad, self.final]), self.window)
        self.assertNotIn("data", result["trace"][0]["output"])

    def test_tool_budget_prevents_execution(self):
        result = run_tool_agent(Mock(return_value=self.read), self.window, max_calls=1)
        self.assertEqual(result["execution_status"], "tool_budget_exhausted")
        self.assertEqual(result["tool_calls_used"], 1)

    def test_turn_budget_is_not_success(self):
        result = run_tool_agent(Mock(return_value=self.read), self.window, max_turns=1)
        self.assertEqual(result["execution_status"], "turn_budget_exhausted")
        self.assertFalse(result["hard_pass"])

    def test_model_service_error_is_not_answer(self):
        result = run_tool_agent(Mock(side_effect=TimeoutError), self.window)
        self.assertEqual(result["execution_status"], "execution_error")

    def test_valid_tools_do_not_certify_natural_language(self):
        wrong = {"role": "assistant", "content": "已经确认激光器损坏."}
        result = run_tool_agent(Mock(side_effect=[self.read, self.rule, wrong]), self.window)
        self.assertTrue(result["hard_pass"])
        self.assertEqual(result["semantic_status"], "not_evaluated")

    def test_real_http_tool_roundtrips_with_scripted_responses(self):
        replies = iter([self.read, self.rule, self.final])
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                body = json.dumps({"message": next(replies)}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = run_tool_agent(OllamaChat(f"http://127.0.0.1:{server.server_port}", "mock-only"),
                                    self.window)
            self.assertTrue(result["hard_pass"])
            self.assertEqual(len(requests), 3)
            self.assertEqual(requests[2]["messages"][-1]["tool_name"], "read_rule")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
