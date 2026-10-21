import hashlib
import math
from domain import parse_bin


def inspect_window(blob, manifest, module_id, start, stop):
    if manifest["module_id"] != module_id:
        raise ValueError("module_mismatch")
    if hashlib.sha256(blob).hexdigest() != manifest["sha256"]:
        raise ValueError("file_mismatch")
    if start >= stop:
        raise ValueError("empty_window")
    rows = parse_bin(blob)
    indexed = {(row["timestamp_s"], row["lane"]): row for row in rows}
    lanes = {}
    for lane in range(4):
        state, low_run, recovery_run = "UNKNOWN", 0, 0
        timeline, events, powers = [], [], []
        for ts in range(start, stop):
            row = indexed.get((ts, lane))
            value = row["rx_dbm"] if row and row["valid"] else None
            previous = state
            if value is None:
                state, low_run, recovery_run = "UNKNOWN", 0, 0
            elif value < -12:
                low_run, recovery_run = low_run + 1, 0
                if low_run >= 2:
                    state = "ALERT"
            elif value >= -11:
                low_run, recovery_run = 0, recovery_run + 1
                if recovery_run >= 2:
                    state = "NORMAL"
            else:
                low_run, recovery_run = 0, 0
            if value is not None:
                powers.append(10 ** (value / 10))
            if state != previous:
                events.append({"at": ts, "from": previous, "to": state})
            timeline.append({"at": ts, "rx_dbm": value, "low_run": low_run,
                             "recovery_run": recovery_run, "state": state})
        lanes[str(lane)] = {
            "last_state": state, "valid_samples": len(powers),
            "expected_samples": stop - start, "complete": len(powers) == stop - start,
            "mean_power_dbm": 10 * math.log10(sum(powers) / len(powers)) if powers else None,
            "events": events, "timeline": timeline,
        }
    return {"module_id": module_id, "source_sha256": manifest["sha256"],
            "window": [start, stop], "sample_period_s": 1,
            "rule_version": "synthetic-hysteresis-v1", "lanes": lanes,
            "root_cause": "not_determined"}
