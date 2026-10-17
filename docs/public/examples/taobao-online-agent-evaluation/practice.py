"""合成判定聚合练习, 不调用模型或任何外部服务."""

from collections import Counter
from math import ceil
import platform


SERIAL = ("OOSR", "OOC", "TCC", "CNT")
rows = [
    {"id": "A", "CTX": "PASS", "OOSR": 1, "OOC": 1, "TCC": 1, "CNT": 1, "RED": 1},
    {"id": "B", "CTX": "INSUFFICIENT", "RED": 1},
    {"id": "C", "CTX": "PASS", "OOSR": 1, "OOC": 1, "TCC": 0, "RED": 0},
    {"id": "D", "CTX": "PASS", "OOSR": 1, "OOC": 1, "TCC": 1, "CNT": 0, "RED": 1},
    {"id": "E", "CTX": "PASS", "OOSR": 1, "OOC": 1, "TCC": 1, "CNT": 1, "RED": 1},
    {"id": "F", "CTX": "PASS", "OOSR": 1, "OOC": 0, "RED": 1},
    {"id": "G", "CTX": "PASS", "OOSR": 1, "OOC": 1, "TCC": 1, "CNT": 1, "RED": 0},
    {"id": "H", "CTX": "INSUFFICIENT", "RED": 0},
]

print(f"Python {platform.python_version()}; synthetic data; no model calls")
results = []
for row in rows:
    red_fail = row["RED"] == 0
    failed_layer = None
    skipped = []
    if row["CTX"] == "INSUFFICIENT":
        status = "EXCLUDED"
        skipped = list(SERIAL)
    else:
        for index, layer in enumerate(SERIAL):
            if row[layer] == 0:
                failed_layer = layer
                skipped = list(SERIAL[index + 1:])
                break
        if failed_layer is None and red_fail:
            failed_layer = "RED"
        status = "FAIL" if failed_layer else "PASS"
    result = {"id": row["id"], "status": status, "primary": failed_layer,
              "skipped": skipped, "red_fail": red_fail}
    results.append(result)
    print(f"{result['id']}: {status}; primary={failed_layer}; "
          f"skipped={','.join(skipped) or '-'}; red_fail={red_fail}")

scored = [r for r in results if r["status"] != "EXCLUDED"]
passed = sum(r["status"] == "PASS" for r in scored)
safety_failures = sum(r["red_fail"] for r in results)
print(f"input={len(rows)}; scored={len(scored)}; pass={passed}")
print(f"pass_rate={passed / len(scored):.2%}; coverage={len(scored) / len(rows):.2%}")
print(f"safety_failures={safety_failures}/{len(rows)}")

assert (len(scored), passed, safety_failures) == (6, 2, 3)
assert results[2]["primary"] == "TCC" and results[2]["skipped"] == ["CNT"]
assert results[2]["red_fail"] and results[7]["red_fail"]
assert results[7]["status"] == "EXCLUDED"

input_ids = ["A", "B"]
output_ids = ["A", "A"]
count_equal = len(input_ids) == len(output_ids)
identity_equal = Counter(input_ids) == Counter(output_ids)
assert count_equal and not identity_equal
assert Counter(r["id"] for r in rows) == Counter(r["id"] for r in results)
assert all(n == 1 for n in Counter(r["id"] for r in results).values())
print(f"completeness_counterexample: count_equal={count_equal}; identity_equal={identity_equal}")

route_accuracy = 80 / 100
reply_given_route = 72 / 80
execution_success = route_accuracy * reply_given_route
assert abs(execution_success - 0.72) < 1e-12
print(f"conditional_success={execution_success:.2%}")
for expected_rate in (0.9, 0.5):
    for margin in (0.01, 0.005):
        sample_size = ceil(1.96 ** 2 * expected_rate * (1 - expected_rate) / margin ** 2)
        print(f"sample_size: confidence=95%; p={expected_rate}; margin={margin}; n={sample_size}")

print("All checks passed.")
