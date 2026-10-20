"""Fresh governed attempt reuses exact CT1 without rewriting failed evidence."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
F = R.parents[2]
RUN = "ct2-20261014"
Q = F / ".agents/ct1-20261014"
OLD = F / ".agents/runtime/ct1-20261014"
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
assert sha(Q / "TRANSFER-MANIFEST.json") == "6ebe98c39182233943bdce6ff26ea2ab878397abc04ed35d74a09b972e466ea9"
assert read(OLD / "ct1-20261014/state.json")["nodes"]["review"]["state"] == "FAILED"
assert not read(OLD / "ct1-20261014/claims.json")
assert sha(OLD / "independent-review/review.json") == "d5b99f1b37c955d090c9c7413b7d8d86b0b0bb3f3699a56cbf0999bd5af1cb69"
assert read(OLD / "ct1-20261014/state.json")["nodes"]["implement"]["state"] == "SUCCEEDED"
manifest = read(Q / "TRANSFER-MANIFEST.json")
for item in manifest["payloads"]:
    assert sha(Q / item["relative_path"]) == item["candidate_sha256"]
    assert sha(F / item["relative_path"]) == item["active_before_sha256"]
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files


def save(path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2)
        output.write("\n")


def step(label, *args):
    argv = ["powershell", "-NoProfile", "-File", r"T:\02-Config\agents\taar-orchestrate.ps1", *args, "--runtime-root", str(R)]
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (("stdout", done.stdout), ("stderr", done.stderr)):
        with (R / (label + "." + suffix)).open("xb") as output:
            output.write(data)
    response = json.loads(done.stdout)
    save(R / (label + ".json"), {"argv": argv, "exit_status": done.returncode, "response": response})
    assert done.returncode == 0 and response.get("allowed") is True, response
    print(json.dumps({"step": label, "allowed": True}), flush=True)


publisher = OLD / "apply_reviewed_status.py"
assert sha(publisher) == "a6adef68d3debf3153f969eaf9f70d5c0f434d4033912d4e68e2644f42a1496b"
text = publisher.read_text(encoding="utf-8")
text = text.replace("R / 'ct1-20261014/claims.json'", "R / 'ct2-20261014/claims.json'")
text = text.replace("R / 'ct1-20261014/state.json'", "R / 'ct2-20261014/state.json'")
assert "F / '.agents/ct1-20261014'" in text
with (R / "apply_reviewed_status.py").open("x", encoding="utf-8") as output:
    output.write(text)
step("run-init", "run", "init", "--root", "T:\\", "--scope", str(Q), "--run-id", RUN)
for node in ("discover", "plan", "implement"):
    step(node + "-claim", "node", "claim", RUN, node, "--executor", "/root", "--workspace", str(Q))
    claim = read(R / RUN / "claims.json")[node]
    changed = _changed_files(claim["baseline_snapshot"], _snapshot_workspace(Q, Path("T:/")))
    assert changed == []
    for item in manifest["payloads"]:
        assert sha(Q / item["relative_path"]) == item["candidate_sha256"]
        assert sha(F / item["relative_path"]) == item["active_before_sha256"]
    receipt = {"schema_version": 1, "run_id": RUN, "node_id": node, "executor_id": "/root",
        "started_at": now(), "finished_at": now(), "input_hash": claim["input_hash"], "changed_files": [],
        "result": {"status": "REUSE_EXACT_PREVIOUSLY_IMPLEMENTED_CT1_CANDIDATE", "source_root": str(F),
                   "candidate_root": str(Q), "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"),
                   "prior_implement_receipt_sha256": sha(OLD / "implement.json"),
                   "publication_script_sha256": sha(R / "apply_reviewed_status.py"),
                   "prior_failed_review_sha256": sha(OLD / "independent-review/review.json"),
                   "prior_failure": "CT1 review command list included the preserved initial parser failure; fresh final checks and distinct review required",
                   "new_source_or_LOC_claimed": 0},
        "commands": [{"command": "Fresh exact candidate/source-before hash inspection and real unchanged workspace snapshot", "exit_status": 0}],
        "validations": [{"name": "reuse_exact_three_frozen_members_no_source_changes", "passed": True},
                        {"name": "failed_previous_ledger_and_receipt_preserved", "passed": True}], "exit_status": 0}
    validate_receipt(receipt, run_id=RUN, node_id=node, executor_id=claim["executor_id"], input_hash=claim["input_hash"],
                     claimed_at=claim["claimed_at"], node=read(R / RUN / "graph.json")["graph"]["nodes"][node])
    save(R / (node + ".json"), receipt)
    step(node + "-complete", "node", "complete", RUN, node, str(R / (node + ".json")))
assert not read(R / RUN / "claims.json")
assert read(R / RUN / "state.json")["nodes"]["review"]["state"] == "READY"
print(json.dumps({"actual_reuse_implement": "SUCCEEDED", "candidate_root": str(Q),
                  "publisher_sha256": sha(R / "apply_reviewed_status.py"), "prior_failed_ledger_preserved": True}), flush=True)
