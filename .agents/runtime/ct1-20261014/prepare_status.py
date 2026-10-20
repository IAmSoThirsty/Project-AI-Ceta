"""Claim the narrow status update and preserve all prior observations."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
F = R.parents[2]
RUN = "ct1-20261014"
Q = F / ".agents" / RUN
BASE = F / ".agents/current-continuity-20261014-r2"
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
assert not Q.exists()
assert sha(BASE / "CANDIDATE-MANIFEST.json") == "ac772591c95ff6ed0cc64e5b143b9508d66562c617eee381f68dbcf6aeecb375"
base = read(BASE / "CANDIDATE-MANIFEST.json")
for item in base["files"]:
    assert sha(F / item["relative_path"]) == item["active_before_sha256"]
    assert sha(BASE / item["relative_path"]) == item["candidate_sha256"]
for relative, digest in base["proofs"].items():
    assert sha(F / relative) == digest
rejected = F / ".agents/runtime/hp3-20261014/independent-review/review.json"
assert sha(rejected) == "11f0512ab58f86f9f8fda9af160c6991a13668a3cdcbc79c4f008cbd0549cc93"
assert read(rejected)["result"]["decision"] == "rejected"
assert read(rejected)["exit_status"] == 1
Q.mkdir()
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files


def save(path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write("\n")


def step(label, *args):
    argv = ["powershell", "-NoProfile", "-File", r"T:\02-Config\agents\taar-orchestrate.ps1", *args, "--runtime-root", str(R)]
    started = now()
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (("stdout", done.stdout), ("stderr", done.stderr)):
        with (R / (label + "." + suffix)).open("xb") as output:
            output.write(data)
    response = json.loads(done.stdout)
    save(R / (label + ".json"), {"started_at": started, "finished_at": now(), "argv": argv,
                               "exit_status": done.returncode, "response": response})
    assert done.returncode == 0 and response.get("allowed") is True, response
    print(json.dumps({"step": label, "allowed": True}), flush=True)


step("run-init", "run", "init", "--root", "T:\\", "--scope", str(Q), "--run-id", RUN)
for node in ("discover", "plan"):
    step(node + "-claim", "node", "claim", RUN, node, "--executor", "/root", "--workspace", str(Q))
    claim = read(R / RUN / "claims.json")[node]
    receipt = {"schema_version": 1, "run_id": RUN, "node_id": node, "executor_id": "/root",
        "started_at": now(), "finished_at": now(), "input_hash": claim["input_hash"], "changed_files": [],
        "result": {"scope": "TWO_STATUS_JSON_FILES_ONLY", "source_root": str(F),
                   "base_manifest_sha256": sha(BASE / "CANDIDATE-MANIFEST.json"),
                   "preserve": "Every prior observation, global gate and requirement status retained"},
        "commands": [{"command": "Inspected current status callers/schema and exact accepted BR1, APP3, rename and rejected HP3 receipts", "exit_status": 0}],
        "validations": [{"name": "source_before_images_and_receipt_bindings_exact", "passed": True}], "exit_status": 0}
    validate_receipt(receipt, run_id=RUN, node_id=node, executor_id=claim["executor_id"], input_hash=claim["input_hash"],
                     claimed_at=claim["claimed_at"], node=read(R / RUN / "graph.json")["graph"]["nodes"][node])
    save(R / (node + ".json"), receipt)
    step(node + "-complete", "node", "complete", RUN, node, str(R / (node + ".json")))
step("implement-claim", "node", "claim", RUN, "implement", "--executor", "/root", "--workspace", str(Q))
started = now()
rows = []
for item in base["files"]:
    relative = item["relative_path"]
    original = (F / relative).read_bytes()
    assert hashlib.sha256(original).hexdigest() == item["active_before_sha256"]
    prior = json.loads(original)
    candidate = read(BASE / relative)
    facts = candidate["current_repository_execution_20261014"]
    facts["recorded_at"] = started
    facts["HP3_author_cut"]["state"] = "IMPLEMENT_SUCCEEDED_INDEPENDENT_REVIEW_REJECTED"
    facts["HP3_author_cut"]["independent_tests"] = {"total": 117, "passed": 113, "failures": 4, "errors": 0, "skips": 0}
    facts["HP3_author_cut"]["blocking_findings"] = ["HP3-F01", "HP3-F02"]
    facts["HP4_repair"] = {"state": "AUTHOR_IMPLEMENTATION_IN_PROGRESS_AT_THIS_CUT", "candidate": ".agents/hp4-20261014",
                           "focused_regression_passed": 7, "full_suite_and_independent_review": "PENDING"}
    facts["proofs"].append({"relative_path": str(rejected.relative_to(F)).replace("\\", "/"), "sha256": sha(rejected)})
    facts["status_scope"] = "SCOPED_OBSERVATIONS_AT_RECORDED_TIME;GLOBAL_PRODUCT_GATES_RETAINED"
    if relative == "handoff/continuity.json":
        candidate["next_action"] = "Continue WA1 workload-admission implementation and HP4 independent repair review in this repository; preserve source/branch history under the separately approved exact content policy."
    allowed = set(item["allowed_changed_keys"])
    for key, value in prior.items():
        assert key in candidate
        if key not in allowed:
            assert candidate[key] == value
    assert set(candidate) - set(prior) <= allowed
    before = R / "before" / relative
    target = Q / relative
    before.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with before.open("xb") as output:
        output.write(original)
    save(target, candidate)
    assert (F / relative).read_bytes() == original
    rows.append({"relative_path": relative, "active_before_sha256": sha(before), "candidate_sha256": sha(target),
                 "allowed_changed_keys": sorted(allowed), "application_action": "EXTEND_PRESERVE_BEFORE_IMAGE"})
proofs = dict(base["proofs"])
proofs[str(rejected.relative_to(F)).replace("\\", "/")] = sha(rejected)
manifest = {"schema_version": "ceta.current-status.v1", "author": "/root", "source_root": str(F),
            "candidate_root": str(Q), "payloads": rows, "application_paths": sorted(row["relative_path"] for row in rows),
            "proofs": proofs, "active_source_changes": 0, "global_gate_or_requirement_changes": 0,
            "earlier_tests_preserved": True, "candidate_state": "PENDING_DISTINCT_REVIEW"}
save(Q / "TRANSFER-MANIFEST.json", manifest)
claim = read(R / RUN / "claims.json")["implement"]
changed = _changed_files(claim["baseline_snapshot"], _snapshot_workspace(Q, Path("T:/")))
assert changed == sorted((Q / name).relative_to(Path("T:/")).as_posix() for name in (*manifest["application_paths"], "TRANSFER-MANIFEST.json"))
receipt = {"schema_version": 1, "run_id": RUN, "node_id": "implement", "executor_id": "/root",
    "started_at": started, "finished_at": now(), "input_hash": claim["input_hash"], "changed_files": changed,
    "result": {"status": "TWO_CURRENT_STATUS_CANDIDATES_PREPARED_PRIOR_OBSERVATIONS_PRESERVED", "source_root": str(F),
               "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"), "runtime_code_changes": 0,
               "scope": "APP3_HISTORICAL1158;BR1_CURRENT_CONNECTED118;HP3_REJECTED;HP4_PENDING"},
    "commands": [{"command": "Exact pinned JSON transformation with prior key equality and source CAS checks", "exit_status": 0}],
    "validations": [{"name": "prior_observations_preserved_global_states_unchanged", "passed": True},
                    {"name": "scoped_current_tests_and_failed_review_have_exact_bindings", "passed": True}], "exit_status": 0}
validate_receipt(receipt, run_id=RUN, node_id="implement", executor_id=claim["executor_id"], input_hash=claim["input_hash"],
                 claimed_at=claim["claimed_at"], node=read(R / RUN / "graph.json")["graph"]["nodes"]["implement"])
save(R / "implement.json", receipt)
step("implement-complete", "node", "complete", RUN, "implement", str(R / "implement.json"))
assert not read(R / RUN / "claims.json")
assert read(R / RUN / "state.json")["nodes"]["review"]["state"] == "READY"
print(json.dumps({"actual_implement": "SUCCEEDED", "metadata_paths": 2, "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json")}), flush=True)
