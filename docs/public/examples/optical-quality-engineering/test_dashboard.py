import unittest
from dashboard import first_test_yield


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            {"event_id": "a", "module_id": "S1", "family": "F1", "at": 100, "sequence": 1, "result": "fail"},
            {"event_id": "b", "module_id": "S1", "family": "F1", "at": 101, "sequence": 2, "result": "pass"},
            {"event_id": "c", "module_id": "S2", "family": "F1", "at": 100, "sequence": 1, "result": "pass"},
            {"event_id": "d", "module_id": "S3", "family": "F2", "at": 100, "sequence": 1, "result": "pass"},
        ]

    def test_retest_not_first_pass(self):
        self.assertEqual(first_test_yield(self.events, 100, 102)["F1"],
                         {"first_pass": 1, "first_tested": 2, "yield": .5})

    def test_product_families_separate(self):
        self.assertEqual(first_test_yield(self.events, 100, 102)["F2"]["yield"], 1)

    def test_duplicates_and_arrival_order(self):
        self.assertEqual(first_test_yield(self.events, 100, 102),
                         first_test_yield(self.events[::-1] + [self.events[0]], 100, 102))

    def test_no_denominator_means_no_rate(self):
        self.assertEqual(first_test_yield(self.events, 500, 600), {})

    def test_first_test_outside_window_excludes_retest(self):
        self.assertEqual(first_test_yield(self.events, 101, 102), {})
