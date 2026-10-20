"""Recover evidence-only command encoding; preserve the already frozen GD1 cut."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/gd1-20261014", F / ".agents/runtime/gd1-20261014"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
def ref(path):
    return {"repository_relative_path": path.relative_to(F).as_posix(), "sha256": sha(path)}
now = lambda: datetime.now(timezone.utc).isoformat()
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt
claim = read(R / "gd1-20261014/claims.json")["implement"]
graph = read(R / "gd1-20261014/graph.json")["graph"]
assert claim["executor_id"] == "/root/pressure_writer" and claim["workspace"] == str(Q)
manifest_path = Q / "TRANSFER-MANIFEST.json"
manifest, frozen = read(manifest_path), read(R / "source-freeze.json")
assert sha(manifest_path) == frozen["manifest"]["sha256"]
assert len(manifest["payloads"]) == 280
assert len(frozen["snapshot"]) == 281
for item in manifest["payloads"]:
    relative = item["relative_path"]
    assert sha(Q / relative) == item["candidate_sha256"]
    if item["active_before_sha256"] is None:
        assert not (F / relative).exists()
    else:
        assert sha(F / relative) == item["active_before_sha256"]
current = _snapshot_workspace(Q, Path("T:/"))
assert current == frozen["snapshot"]
changed = _changed_files(claim["baseline_snapshot"], current)
final = read(R / "final-connected-r3.json")
assert final["tests_run"] == 314 and final["successful"] and final["failures"] == final["errors"] == final["skipped"] == 0
failure = {"classification": "RECEIPT_COMMAND_ENCODING_ERROR_CORRECTED_WITHOUT_CANDIDATE_CHANGE",
           "observed_at": now(), "original_finalizer": ref(R / "freeze_and_receipt.py"),
           "command": "Python312 -B -X utf8 freeze_and_receipt.py", "exit_status": 1,
           "observed_exception": "taar.errors.TransitionDenied: Receipt command 0 requires command and exit_status",
           "exact_conflict": "Runner command JSON uses argv list; installed validate_receipt requires nonempty command string. Original source/raw-ID/native assertions and frozen snapshot succeeded before the validator rejected the receipt.",
           "repair": "Preserve argv in its existing raw command receipt; encode it using subprocess.list2cmdline for the strict command field.",
           "frozen_manifest": ref(manifest_path), "frozen_candidate_changes": []}
write(R / "freeze-r1-failure.json", failure)
prior = manifest["prior_failures"] + [{"classification": failure["classification"], "failure": ref(R / "freeze-r1-failure.json")}]
command_record = read(R / "final-connected-r3-command.json")
assert command_record["exit_status"] == 0
rows = [item for item in manifest["payloads"] if item["action"] != "REUSE"]
assert {item["relative_path"] for item in rows} == set(manifest["application_paths"])
source_loc = next(item["meaningful_LOC"] for item in rows if item["kind"] == "functional_source")
test_loc = next(item["meaningful_LOC"] for item in rows if item["kind"] == "test_source")
receipt = {"schema_version": 1, "run_id": "gd1-20261014", "node_id": "implement", "executor_id": "/root/pressure_writer",
    "started_at": claim["claimed_at"], "finished_at": now(), "input_hash": claim["input_hash"], "changed_files": changed,
    "result": {"status": "BOUNDED_EXECUTABLE_CANDIDATE_READY_FOR_DISTINCT_REVIEW", "manifest": ref(manifest_path),
        "self_review": ref(R / "self-review.json"), "source_freeze": ref(R / "source-freeze.json"), "tests": ref(R / "final-connected-r3.json"),
        "tests_run": 314, "failures": 0, "errors": 0, "skips": 0, "new_methods": 32, "new_native_methods": 6,
        "source_added": source_loc["added"], "source_removed": source_loc["removed"], "test_added": test_loc["added"],
        "reuse_new_LOC": 0, "prior_failures": prior, "active_source_application": False, "independent_acceptance": False},
    "commands": [{"command": subprocess.list2cmdline(command_record["command"]), "exit_status": 0, "raw_command_evidence": ref(R / "final-connected-r3-command.json")},
        {"command": "Own E3 Python -B -X utf8 baseline_probe.py Q final-baseline-closure-r2; unchanged corrected native oracle", "exit_status": 0},
        {"command": "Own Python -B finish_receipt.py: exact unchanged frozen 281-member cut, current 279 Source bindings, strict installed snapshot/full-keyword validation", "exit_status": 0}],
    "validations": [{"name": name, "passed": True} for name in ("actual314_zero_skip_connected_tests_and_raw_IDs", "six_new_actual_native_owned_process_cases_and_8_sub_tick_recovery_trials",
        "unchanged_public_interfaces_and_all_original47_95_52_71_14_3_regressions", "exact279_current_source_277_reuse_and_only_three_allowed_payload_deltas",
        "complete20_acceptance_IDs_with_explicit_remaining_obligations", "actual_claim_input_hash_and_installed_snapshot_changes_with_full_validator_keywords")], "exit_status": 0}
kwargs = {"run_id": "gd1-20261014", "node_id": "implement", "executor_id": "/root/pressure_writer", "input_hash": claim["input_hash"], "claimed_at": claim["claimed_at"], "node": graph["nodes"]["implement"]}
validate_receipt(receipt, **kwargs)
write(R / "implement.json", receipt)
validate_receipt(load_receipt(R / "implement.json"), **kwargs)
write(R / "implement-validation.json", {"receipt": ref(R / "implement.json"), "validator": "installed taar.orchestration_receipts.validate_receipt", "full_keywords": kwargs,
    "changed_files": changed, "snapshot_members": len(current), "passed": True})
print(json.dumps({"manifest": ref(manifest_path), "receipt": ref(R / "implement.json"), "tests_run": 314,
                  "candidate_changed": False, "source_LOC": source_loc, "test_LOC": test_loc}), flush=True)
