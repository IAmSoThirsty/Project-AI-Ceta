"""Read back the frozen GD2 author cut before the actual independent claim."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

V = Path(__file__).resolve().parent
R, F = V.parent, V.parents[3]
Q, RUN = F / ".agents/gd2-20261014", "gd2-20261014"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
assert sha(Q / "TRANSFER-MANIFEST.json") == "cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a"
assert sha(R / "implement.json") == "7f76cf5e45dd8726bbf66bbfb398651205a277bf7aa52141a3cbd688027ce98a"
assert sha(R / "actual-implementation-readback.json") == "0c2dedfe267a64780157653b20dfe2eb8f2c38e1f3379142af21cc1df20b02cc"
state = read(R / RUN / "state.json")
assert state["sequence"] == 7 and state["nodes"]["implement"]["state"] == "SUCCEEDED"
assert state["nodes"]["review"]["state"] == "READY" and read(R / RUN / "claims.json") == {}
manifest = read(Q / "TRANSFER-MANIFEST.json")
assert len(manifest["payloads"]) == 281
native = {}
source = {}
for row in manifest["payloads"]:
    relative = row["relative_path"]
    assert sha(Q / relative) == row["candidate_sha256"]
    target = F / relative
    if row["active_before_sha256"] is None:
        assert not target.exists()
    else:
        assert sha(target) == row["active_before_sha256"]
        facts = target.stat()
        source[relative] = row["active_before_sha256"]
        native[relative] = {"device": facts.st_dev, "inode": facts.st_ino,
                           "mode": facts.st_mode, "bytes": facts.st_size, "mtime_ns": facts.st_mtime_ns}
assert len(source) == 279
specifications = []
for item in manifest["input_specification_bindings"]:
    path = Path(item["path"])
    assert sha(path) == item["sha256"]
    specifications.append(item)
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_runtime import _snapshot_workspace
from taar.orchestration_receipts import load_receipt, validate_receipt
snapshot = _snapshot_workspace(Q, Path("T:/"))
assert snapshot == read(R / "source-freeze.json")["snapshot"] and len(snapshot) == 282
implement = read(R / "implement.json")
validate_receipt(load_receipt(R / "implement.json"), run_id=RUN, node_id="implement", executor_id="/root",
                 input_hash=implement["input_hash"], claimed_at=implement["started_at"],
                 node=read(R / RUN / "graph.json")["graph"]["nodes"]["implement"])
environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1")
git = {}
for tag, args in (("branch", ["branch", "--show-current"]), ("head", ["rev-parse", "HEAD"]),
                  ("status", ["status", "--short"])):
    command = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(F), *args]
    output = subprocess.run(command, env=environment, cwd=r"T:\00-Active", capture_output=True)
    assert output.returncode == 0
    (V / ("git-" + tag + ".txt")).open("xb").write(output.stdout)
    git[tag] = output.stdout.decode("utf-8-sig").strip() if tag != "status" else {
        "raw": "git-status.txt", "sha256": sha(V / "git-status.txt"),
        "tracked_modified": [line[3:] for line in output.stdout.decode("utf-8-sig").splitlines() if not line.startswith("??")],
        "untracked_rows": sum(line.startswith("??") for line in output.stdout.decode("utf-8-sig").splitlines())}
final = read(R / "final-connected-r4.json")
ids = [row["id"] for row in final["cases"]]
assert len(ids) == len(set(ids)) == final["tests_run"] == 327
record = {"observed_at": datetime.now(timezone.utc).isoformat(), "reviewer": "/root/pressure_writer",
          "author": "/root", "source_root": str(F), "candidate_root": str(Q),
          "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"), "implement_sha256": sha(R / "implement.json"),
          "author_readback_sha256": sha(R / "actual-implementation-readback.json"),
          "actual_state_sequence": state["sequence"], "actual_implement_state": "SUCCEEDED",
          "actual_review_state": "READY", "actual_claims": {}, "snapshot": snapshot,
          "source_before_sha256": source, "source_before_native": native, "specification_bindings": specifications,
          "author_test_cohort": dict(Counter(item.split('.')[0] for item in ids)), "author_expected_ids": ids,
          "git": git,
          "independence": {"distinct": ["Root three-line nested validation", "Root six new tests", "discovery/reuse wiring", "publication helper"],
                           "shared_authorship": "Reviewer authored the retained GD1 72-line timing change and 32 timing methods",
                           "prior_independent_timing_review": ".agents/runtime/gd1-20261014/independent-review",
                           "whole_unit_independent_acceptance": "OPEN: further reviewer without GD1/GD2 authorship required for joined Source and final1326 evidence"},
          "application_performed": False}
with (V / "preflight.json").open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"preflight_sha256": sha(V / "preflight.json"), "candidate_members": len(snapshot),
                  "current_source_payloads": len(source), "author_test_cohort": record["author_test_cohort"],
                  "specification_bindings": specifications}), flush=True)
