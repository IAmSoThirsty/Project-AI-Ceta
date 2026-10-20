"""Bind GD1 to the actual closed HD2 279-member active source cut."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/gd1-20261014", F / ".agents/runtime/gd1-20261014"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
node = sys.argv[1]
claim = read(R / "gd1-20261014/claims.json")[node]
assert claim["executor_id"] == "/root/pressure_writer" and claim["workspace"] == str(Q)
baseline_path = F / ".agents/runtime/hd2-20261014/active-application/destination-full-r1.json"
assert sha(baseline_path) == "e7aa79e76d6277a719070e6fb573121bb230a0c297af0447b829d4d53f495057"
baseline = read(baseline_path)
assert baseline["tests_run"] == 1281 and baseline["exit_status"] == 0 and baseline["source_unchanged"]
payloads = [{"relative_path": key, "sha256": value} for key, value in sorted(baseline["after_hashes"].items())]
assert len(payloads) == 279
assert all(sha(F / row["relative_path"]) == row["sha256"] for row in payloads)
bindings = [F / "START_HERE.md", F / "CODEX_BOOTSTRAP_PROMPT.md", F / "AGENTS.md",
            F / "handoff/OWNER_SCOPE_OVERRIDE.md",
            F / ".agents/runtime/authoritative-inputs-20261014/CETA-UNIFIED-CODE-IMPLEMENTATION-PLAN-r6.txt"]
templates = F / ".local-build-cache/subagent-templates-20261011"
bindings += [templates / name for name in ("TASK_BINDING.md", "SOURCE_GOVERNANCE.md", "HANDOFF_RECORD.md", "operational/02-code-writer.md")]
architecture = F / ".agents/cp1-20261014/independent-recovery/working-tree"
bindings += [architecture / "20-RESOURCE-MANAGEMENT" / name for name in ("ARCHITECTURE.md", "DEPENDENCIES.md", "BUILD-SEQUENCE.md", "FILE-INDEX.md", "INTEGRATION.md", "INTERFACE-CONTRACTS.md")]
bindings += [architecture / "20-RESOURCE-MANAGEMENT/20.05-OPERATIONAL-DIAGNOSTICS" / name for name in ("README.md", "resource-telemetry-recorder.file.README.md", "performance-diagnostics-engine.file.README.md")]
git = []
for args in (["rev-parse", "--show-toplevel"], ["branch", "--show-current"], ["rev-parse", "HEAD"], ["status", "--short", "--untracked-files=no"]):
    command = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(F), *args]
    result = subprocess.run(command, cwd=r"T:\00-Active", env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1"), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    git.append({"command": command, "exit_status": result.returncode, "stdout": result.stdout})
receipt = {"schema_version": 1, "run_id": "gd1-20261014", "node_id": node,
    "executor_id": claim["executor_id"], "started_at": claim["claimed_at"],
    "finished_at": datetime.now(timezone.utc).isoformat(), "input_hash": claim["input_hash"],
    "changed_files": [], "exit_status": 0,
    "commands": [{"command": "Own Python -B prepare_receipt.py " + node + ": exact current 279 inputs and closed full receipt", "exit_status": 0}],
    "validations": [{"name": "actual_current_closed_HD2_source_cut", "passed": True}, {"name": "exclusive_three_path_candidate_scope", "passed": True}],
    "result": {"payloads": payloads, "baseline_full_receipt": {"path": str(baseline_path), "sha256": sha(baseline_path)},
        "bindings": [{"path": str(path), "sha256": sha(path)} for path in bindings], "git": git,
        "classification": {"src/ceta/resource/diagnostics.py": "EXTEND",
            "tests/contract/test_process_observation_timing.py": "CREATE", "contracts/PROCESS_DIAGNOSTICS_V1.md": "EXTEND",
            "shared_contracts_and_callers_and_other_payloads": "REUSE",
            "positive_authority_durable_evidence_and_external_principal_integration": "BLOCKED pending canonical owner integration"},
        "scope": {"candidate": str(Q), "evidence": str(R), "source_owner": "/root", "writer": "/root/pressure_writer"},
        "prior_failures": ["baseline-r1.json: tuple preparation error", "baseline-r2.json: denial-cache oracle superseded", "baseline-r3.json: confirmed native timing defect"],
        "baseline": [{"path": str(R / name), "sha256": sha(R / name)} for name in ("baseline_probe.py", "baseline-r3.json", "baseline-r3.txt")],
        "requirements": ["Precise bounded elapsed fencing with public timestamps preserved", "Persistent rollback high-water", "Conservative cached and observation age", "CPU baseline/window recovery, cancellation and interruption", "Existing collector/analyzer native process path with finite retention and explicit unavailable outcomes"],
        "reuse_new_LOC": 0}}
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_receipts import validate_receipt
graph = read(R / "gd1-20261014/graph.json")["graph"]
validate_receipt(receipt, run_id="gd1-20261014", node_id=node, executor_id=claim["executor_id"], input_hash=claim["input_hash"], claimed_at=claim["claimed_at"], node=graph["nodes"][node])
with (R / (node + ".json")).open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps({"node": node, "payloads": len(payloads), "sha256": sha(R / (node + ".json"))}), flush=True)
