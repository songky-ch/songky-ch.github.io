import json
from pathlib import Path

from optics_eval import METRICS, score_response


def main():
    here = Path(__file__).resolve().parent
    records = [
        json.loads(line)
        for subset in ["diagnosis", "edge"]
        for line in (here / "data" / f"{subset}.jsonl").read_text().splitlines()
    ]
    predictions = json.loads((here / "predictions.json").read_text())
    totals = {}
    for variant in ["baseline", "candidate"]:
        rows = []
        for record in records:
            ticket = record["metadata"]["ticket_id"]
            values = score_response(
                json.dumps(predictions[variant][ticket]),
                json.dumps(record["target"]),
                record["metadata"],
            )
            rows.append({"ticket_id": ticket, **values})
        totals[variant] = {key: sum(row[key] for row in rows) for key in METRICS}
        assert totals[variant]["joint_pass"] == {"baseline": 2, "candidate": 5}[variant]
        print(variant, json.dumps(totals[variant], sort_keys=True))

    record = records[0]
    answer = predictions["candidate"]["OM-001"]
    target = json.dumps(record["target"])
    metadata = record["metadata"]
    invalid_values = [
        "not json",
        "[]",
        json.dumps({**answer, "extra": "field"}),
        json.dumps({**answer, "escalate": "false"}),
        json.dumps({**answer, "citations": "KB-PATH@3"}),
    ]
    for value in invalid_values:
        assert score_response(value, target, metadata) == dict.fromkeys(METRICS, 0.0)
    for change, failed_metric in [
        ({"diagnosis": "local_module_failed"}, "diagnosis_correct"),
        ({"next_action": "reset_port"}, "safe_action"),
        ({"escalate": True}, "action_correct"),
        ({"citations": []}, "evidence_valid"),
        ({"citations": ["KB-THERMAL@2"]}, "evidence_valid"),
    ]:
        values = score_response(json.dumps({**answer, **change}), target, metadata)
        assert values["schema_valid"] == 1
        assert values[failed_metric] == 0
        assert values["joint_pass"] == 0
    print("PASS: 12 fixture scores and 10 malformed or business-error mutations.")


if __name__ == "__main__":
    main()
