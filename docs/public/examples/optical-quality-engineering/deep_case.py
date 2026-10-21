import hashlib
import json
import struct
import zlib
from pathlib import Path
from domain import parse_bin, to_wide_csv
from window_analysis import inspect_window


def make_fixture(missing_as_zero=False):
    sequence = [-13, -13, -11.5, None, -10.5]
    records = []
    for offset, value in enumerate(sequence):
        for lane in range(4):
            rx = value if lane == 0 else -10
            if missing_as_zero and rx is None:
                rx = 0
            records.append(struct.pack(">IhHhBB", 100 + offset, 2500, 3300,
                                       round(rx * 100) if rx is not None else 0,
                                       int(rx is not None), lane))
    body = struct.pack(">4sBBH", b"OPT1", 1, 0, len(records)) + b"".join(records)
    blob = body + struct.pack(">I", zlib.crc32(body))
    return blob, {"module_id": "SYN-WINDOW-1", "sha256": hashlib.sha256(blob).hexdigest()}


def build_deep_case(directory):
    directory.mkdir(parents=True, exist_ok=True)
    blob, manifest = make_fixture()
    bad_blob, bad_manifest = make_fixture(missing_as_zero=True)
    reference = inspect_window(blob, manifest, "SYN-WINDOW-1", 100, 105)
    corrupted = inspect_window(bad_blob, bad_manifest, "SYN-WINDOW-1", 100, 105)
    (directory / "window.bin").write_bytes(blob)
    (directory / "window-manifest.json").write_text(json.dumps(manifest, indent=2))
    (directory / "window-wide.csv").write_text(to_wide_csv(parse_bin(blob)))
    output = {"reference": reference, "missing_as_zero": corrupted,
              "comparison": {"reference_lane0_state": reference["lanes"]["0"]["last_state"],
                             "corrupted_lane0_state": corrupted["lanes"]["0"]["last_state"],
                             "meaning": "Invalid measurement relabeled as valid zero creates false recovery."}}
    (directory / "window-analysis.json").write_text(json.dumps(output, ensure_ascii=False, indent=2))
    return output


if __name__ == "__main__":
    print(json.dumps(build_deep_case(Path("results")), ensure_ascii=False, indent=2))
