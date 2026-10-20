"""Read actual rejected state, then close this review evidence scope."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import stat

V = Path(__file__).resolve().parent
R, F = V.parent, V.parents[3]
Q, RUN = F / ".agents/gd2-20261014", "gd2-20261014"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
def save(path, value):
    path.open("x", encoding="utf-8").write(json.dumps(value, indent=2, allow_nan=False) + "\n")
state, claims = read(R / RUN / "state.json"), read(R / RUN / "claims.json")
persisted = R / RUN / "receipts/review.json"
assert state["sequence"] == 9 and state["nodes"]["review"]["state"] == "FAILED"
assert state["nodes"]["review"]["claim"] is None and claims == {}
assert read(persisted)["decision"] == "rejected" and read(persisted)["exit_status"] == 1
assert sha(Q / "TRANSFER-MANIFEST.json") == "cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a"
record = {"observed_at": datetime.now(timezone.utc).isoformat(), "sequence": state["sequence"],
          "actual_review_state": state["nodes"]["review"], "claims": claims,
          "submitted_review_sha256": sha(V / "review.json"), "persisted_review_sha256": sha(persisted),
          "persisted_decision": read(persisted)["decision"], "persisted_exit_status": read(persisted)["exit_status"],
          "actual_completion_response": read(V / "complete.json"),
          "state_decision_field": state["nodes"]["review"]["decision"],
          "state_decision_limit": "State decision null on failed-execution branch; submitted and persisted decisions rejected",
          "disposition": "WITHHELD_PENDING_FRESH_CORRECTED_CUT; PRODUCT327_PASS_WITH_ZERO_FAIL_ERROR_SKIP",
          "whole_joined_unit_independent_acceptance": "OPEN", "candidate_Source_E3_writes": []}
save(V / "actual-review-readback.json", record)
tool = F / ".agents/pr4-20261014/preserve_ceta_complete.py"
assert sha(tool) == "2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618"
spec = importlib.util.spec_from_file_location("gd2_seal_fs", tool)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)
def extended_sha(path):
    result = hashlib.sha256()
    with fs.open_source(path, exclusive=True) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()
rows, stack = [], [V]
while stack:
    parent = stack.pop()
    with os.scandir(fs.io_path(parent)) as items:
        children = sorted(items, key=lambda item: item.name)
    for item in children:
        path = parent / item.name
        facts = fs.lstat(path)
        row = {"relative_path": path.relative_to(V).as_posix(), "device": facts.st_dev, "inode": facts.st_ino,
               "mode": facts.st_mode, "mtime_ns": facts.st_mtime_ns, "attributes": facts.st_file_attributes}
        if fs.reparse(facts):
            row.update(kind="inert_reparse", target=os.readlink(fs.io_path(path)))
        elif stat.S_ISDIR(facts.st_mode):
            row.update(kind="directory")
            stack.append(path)
        else:
            assert stat.S_ISREG(facts.st_mode)
            row.update(kind="ordinary_file", bytes=facts.st_size, sha256=extended_sha(path))
        rows.append(row)
rows.sort(key=lambda row: row["relative_path"])
save(V / "SCOPE-SEAL.json", {"schema_version": 1, "reviewer": "/root/pressure_writer",
    "sealed_at": datetime.now(timezone.utc).isoformat(), "review_sha256": sha(V / "review.json"),
    "report_sha256": sha(V / "REPORT.json"), "readback_sha256": sha(V / "actual-review-readback.json"),
    "members": rows, "ordinary_files": sum(row["kind"] == "ordinary_file" for row in rows),
    "ordinary_bytes": sum(row.get("bytes", 0) for row in rows), "self_excluded": True,
    "reparse_links_followed": False, "actual_review_state": "FAILED", "claims": {},
    "further_reviewer_writes": "CLOSED", "whole_unit_independent_acceptance": "OPEN"})
print(json.dumps({"actual_state": "FAILED", "sequence": 9, "claims": {},
                  "readback_sha256": sha(V / "actual-review-readback.json"), "seal_sha256": sha(V / "SCOPE-SEAL.json")}), flush=True)
