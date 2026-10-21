"""Synthetic optical-module lab. This is not a vendor protocol or device driver."""
import csv
import hashlib
import io
import sqlite3
import struct
import zlib
from collections import defaultdict

HEADER = struct.Struct(">4sBBH")
RECORD = struct.Struct(">IhHhBB")
CRC = struct.Struct(">I")
TRANSITIONS = {
    "manufactured": {"tested"},
    "tested": {"shipped"},
    "shipped": {"installed"},
    "installed": {"returned"},
    "returned": {"analyzed"},
}


def parse_bin(blob):
    if len(blob) < HEADER.size + CRC.size:
        raise ValueError("truncated_header")
    magic, version, reserved, count = HEADER.unpack_from(blob)
    if magic != b"OPT1" or reserved != 0:
        raise ValueError("bad_header")
    if version != 1:
        raise ValueError("unsupported_version")
    if len(blob) != HEADER.size + count * RECORD.size + CRC.size:
        raise ValueError("length_mismatch")
    if zlib.crc32(blob[:-4]) != CRC.unpack_from(blob, len(blob) - 4)[0]:
        raise ValueError("crc_mismatch")
    rows = []
    seen = set()
    for offset in range(HEADER.size, len(blob) - 4, RECORD.size):
        ts, temperature, voltage, rx, valid, lane = RECORD.unpack_from(blob, offset)
        if valid not in (0, 1) or lane not in range(4):
            raise ValueError("invalid_record")
        if (ts, lane) in seen:
            raise ValueError("duplicate_record")
        seen.add((ts, lane))
        rows.append({
            "timestamp_s": ts, "lane": lane, "valid": bool(valid),
            "temperature_c": temperature / 100 if valid else None,
            "voltage_v": voltage / 1000 if valid else None,
            "rx_dbm": rx / 100 if valid else None,
        })
    return rows


def to_wide_csv(rows):
    grouped = defaultdict(dict)
    for row in rows:
        ts, lane = row["timestamp_s"], row["lane"]
        if lane in grouped[ts]:
            raise ValueError("duplicate_record")
        grouped[ts][lane] = row
    fields = ["timestamp_s", "valid_lanes"]
    fields += [f"lane{lane}_{field}" for lane in range(4)
               for field in ("temperature_c", "voltage_v", "rx_dbm")]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for ts, lanes in sorted(grouped.items()):
        row = {"timestamp_s": ts,
               "valid_lanes": sum(value["valid"] for value in lanes.values())}
        for lane, values in lanes.items():
            for field in ("temperature_c", "voltage_v", "rx_dbm"):
                row[f"lane{lane}_{field}"] = values[field]
        writer.writerow(row)
    return output.getvalue()


def lifecycle(events):
    unique = {}
    for event in events:
        event_id = event["event_id"]
        if event_id in unique and unique[event_id] != event:
            raise ValueError("conflicting_event")
        unique[event_id] = event
    ordered = sorted(unique.values(), key=lambda e: (e["event_time"], e["sequence"]))
    state = None
    for event in ordered:
        target = event["state"]
        if state is None:
            if target != "manufactured":
                raise ValueError("missing_initial_event")
        elif target not in TRANSITIONS.get(state, set()):
            raise ValueError("invalid_transition")
        state = target
    return {"state": state, "event_count": len(ordered)}


class IssueStore:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS issues (
                tenant TEXT, request_id TEXT, payload_hash TEXT,
                module_id TEXT, status TEXT, PRIMARY KEY(tenant, request_id))""")

    def create_draft(self, tenant, actor_tenant, role, request_id, module_id):
        if tenant != actor_tenant or role not in {"analyst", "approver"}:
            raise PermissionError("forbidden")
        payload_hash = hashlib.sha256(module_id.encode()).hexdigest()
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT payload_hash,status FROM issues WHERE tenant=? AND request_id=?",
                (tenant, request_id)).fetchone()
            if previous:
                if previous[0] != payload_hash:
                    raise ValueError("idempotency_conflict")
                return previous[1]
            db.execute("INSERT INTO issues VALUES (?,?,?,?,?)",
                       (tenant, request_id, payload_hash, module_id, "draft"))
        return "draft"

    def snapshot(self):
        with sqlite3.connect(self.path) as db:
            return [dict(zip(("tenant", "request_id", "module_id", "status"), row))
                    for row in db.execute(
                        "SELECT tenant,request_id,module_id,status FROM issues ORDER BY tenant,request_id")]


def retrieve(corpus, query, tenant, family, firmware, at):
    terms = set(query.lower().split())
    permitted = [doc for doc in corpus if
                 doc["tenant"] in {"public", tenant}
                 and doc["family"] == family and doc["firmware"] == firmware
                 and doc["valid_from"] <= at < doc["valid_to"]]
    ranked = sorted(permitted, key=lambda d: (
        -len(terms & set(d["keywords"])), d["id"]))
    return [doc for doc in ranked if terms & set(doc["keywords"])][:3]


def run_agent(task, corpus, store, variant="reference"):
    """Deterministic stand-in, exercising tools; not a language model."""
    trace = []
    result = {"status": "unavailable", "answer": "", "citations": [],
              "retrieved_ids": [], "trace": trace}

    def record(tool, args, output):
        trace.append({"tool": tool, "args": args, "output": output})

    if task["tenant"] != task["actor_tenant"]:
        record("authorize", {"tenant": task["tenant"]}, {"allowed": False})
        result.update(status="denied", answer="无权访问目标空间.")
        return result
    if task["intent"] == "close_issue":
        record("authorize", {"role": task["role"]}, {"allowed": False})
        result.update(status="denied", answer="本实验禁止通过 Agent 关闭问题单.")
        return result
    if task["intent"] == "create_draft":
        status = store.create_draft(task["tenant"], task["actor_tenant"], task["role"],
                                    task["request_id"], task["module_id"])
        record("create_draft", {"module_id": task["module_id"],
                                "request_id": task["request_id"]}, {"status": status})
        result.update(status="draft_created", answer="已创建待分析草稿, 尚未批准根因.")
        return result
    if task.get("tool_timeout"):
        record("read_telemetry", {"module_id": task["module_id"]}, {"error": "timeout"})
        result.update(answer="数据工具超时, 本次不能判定模块状态.")
        return result
    sample = task["telemetry"]
    record("read_telemetry", {"module_id": task["module_id"]}, sample)
    if sample["module_id"] != task["module_id"]:
        result.update(status="insufficient", answer="返回的模块身份不一致, 需补采.")
        return result
    docs = retrieve(corpus, task["query"], task["tenant"], task["family"],
                    task["firmware"], task["at"])
    record("retrieve", {"firmware": task["firmware"], "at": task["at"]},
           {"ids": [d["id"] for d in docs]})
    result["retrieved_ids"] = [d["id"] for d in docs]
    rules = [d for d in docs if d["kind"] == "rule"]
    if not rules or sample["rx_dbm"] is None or task["at"] - sample["at"] not in range(0, 301):
        result.update(status="insufficient", answer="缺少适用规则或新鲜有效数据, 不能给结论.")
        return result
    rule = rules[0]
    value, threshold = sample["rx_dbm"], rule["rx_low_dbm"]
    low = value <= threshold if variant == "boundary_bug" else value < threshold
    result["citations"] = [rule["id"], sample["id"]]
    if low:
        result.update(status="hypothesis",
                      answer=f"接收光功率 {value} dBm 低于教学阈值 {threshold} dBm. "
                             "仅支持低光功率现象, 需核对对端、连接器和链路, 不能确认模块硬件根因.")
    else:
        result.update(status="normal",
                      answer="本条接收光功率未低于教学阈值, 不代表所有健康项均正常.")
    if variant == "unsupported_cause" and low:
        result["answer"] = "已经确认激光器损坏, 立即更换模块."
    return result
