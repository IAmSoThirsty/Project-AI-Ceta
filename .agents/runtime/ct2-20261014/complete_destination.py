"""Verify the actual two-file status destination and close its real claim."""
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
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
claim = read(R / RUN / "claims.json")["integrate"]
assert claim["executor_id"] == "/root" and claim["workspace"] == str(F)
manifest_path = Q / "TRANSFER-MANIFEST.json"
review_path = R / "independent-review/review.json"
journal_path = R / "active-application/APPLIED.json"
assert sha(manifest_path) == "6ebe98c39182233943bdce6ff26ea2ab878397abc04ed35d74a09b972e466ea9"
assert sha(review_path) == "2c7a930f9361b83c47483eef9436546a4a92f892084432394574d6be550192b5"
assert sha(journal_path) == "35d244ca4bda7602e28213b93439c05f5afab073bd0a80844ff62c924a4d669c"
manifest, review, journal = [read(p) for p in (manifest_path, review_path, journal_path)]
assert review["decision"] == "approved" and review["exit_status"] == 0
assert review["result"]["publication_script_sha256"] == sha(R / "apply_reviewed_status.py")
assert journal["claim_input_hash"] == claim["input_hash"] and len(journal["completed"]) == 2
for item in manifest["payloads"]:
    relative = item["relative_path"]
    assert sha(F / relative) == sha(Q / relative) == item["candidate_sha256"]
    native = R / "active-application/native-backups" / (relative + ".original")
    logical = R / "active-application/before" / (relative + ".source")
    assert sha(native) == sha(logical) == item["active_before_sha256"]
    descriptor = next(v for v in journal["before_images"] if v["relative_path"] == relative)
    facts = native.stat()
    assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
        descriptor["device"], descriptor["inode"], descriptor["mode"], descriptor["bytes"], descriptor["mtime_ns"])
    before, after = read(logical), read(F / relative)
    for key, value in before.items():
        if key not in item["allowed_changed_keys"]:
            assert after[key] == value
    if relative == "handoff/continuity.json":
        assert after["historical_latest_source_tests_before_repository_consolidation_20261014"] == before["latest_source_tests"]
        assert after["latest_source_tests"]["passed"] == 118 and after["latest_source_tests"]["complete_contract_suite"] is False
base_path = F / ".agents/br1-20261014/TRANSFER-MANIFEST.json"
assert sha(base_path) == "12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040"
for item in read(base_path)["payloads"]:
    assert sha(F / item["relative_path"]) == item["candidate_sha256"]
observed = {"recorded_at": now(), "executor": "/root", "source_root": str(F),
    "manifest_sha256": sha(manifest_path), "independent_candidate_review_sha256": sha(review_path),
    "application_journal_sha256": sha(journal_path), "actual_metadata_paths": 2,
    "source_payload_hashes_retained": 235, "logical_and_native_originals_exact": 2,
    "prior_observations_and_global_axes_preserved": True,
    "scope": "Root destination verification following distinct candidate and publication review"}
with (R / "destination-verification.json").open("x", encoding="utf-8") as output:
    json.dump(observed, output, indent=2)
    output.write("\n")
print(json.dumps({"stage": "real_source_snapshot", "metadata_paths": 2, "unchanged_source_payloads": 235}), flush=True)
changed = _changed_files(claim["baseline_snapshot"], _snapshot_workspace(F, Path("T:/")))
assert changed == sorted((F / name).relative_to(Path("T:/")).as_posix() for name in manifest["application_paths"])
receipt = {"schema_version": 1, "run_id": RUN, "node_id": "integrate", "executor_id": "/root",
    "started_at": journal["started_at"], "finished_at": now(), "input_hash": claim["input_hash"], "changed_files": changed,
    "result": {"status": "TWO_STATUS_FILES_APPLIED_AND_SOURCE_BOUND", "source_root": str(F),
               "manifest_sha256": sha(manifest_path), "application_journal_sha256": sha(journal_path),
               "destination_verification_sha256": sha(R / "destination-verification.json"),
               "independent_review_sha256": sha(review_path), "runtime_code_changes": 0,
               "previous_failed_review_preserved": True, "retained_source_payloads": 235},
    "commands": [{"command": "Reviewed exact two-path native publication with fresh preserved logical and native originals", "exit_status": 0},
                 {"command": "Actual destination JSON equality/prior observations/global states/source235 and original identity checks", "exit_status": 0},
                 {"command": "Actual installed source snapshot equals exactly the two approved metadata paths", "exit_status": 0}],
    "validations": [{"name": "actual_destination_matches_distinct_reviewed_candidate", "passed": True},
                    {"name": "historical707_and_source_scoped118_preserved_without_global_gate_promotion", "passed": True},
                    {"name": "source235_and_native_originals_unchanged", "passed": True}], "exit_status": 0}
validate_receipt(receipt, run_id=RUN, node_id="integrate", executor_id=claim["executor_id"], input_hash=claim["input_hash"],
                 claimed_at=claim["claimed_at"], node=read(R / RUN / "graph.json")["graph"]["nodes"]["integrate"])
receipt_path = R / "integrate.json"
with receipt_path.open("x", encoding="utf-8") as output:
    json.dump(receipt, output, indent=2)
    output.write("\n")
argv = ["powershell", "-NoProfile", "-File", r"T:\02-Config\agents\taar-orchestrate.ps1", "node", "complete", RUN,
        "integrate", str(receipt_path), "--runtime-root", str(R)]
done = subprocess.run(argv, capture_output=True)
for suffix, data in (("stdout", done.stdout), ("stderr", done.stderr)):
    with (R / ("integrate-complete." + suffix)).open("xb") as output:
        output.write(data)
response = json.loads(done.stdout)
assert done.returncode == 0 and response.get("allowed") is True, response
state = read(R / RUN / "state.json")
assert set(state["nodes"]) == {"discover", "plan", "implement", "review", "validate", "integrate"}
assert all(node["state"] == "SUCCEEDED" for node in state["nodes"].values())
assert not read(R / RUN / "claims.json")
with (R / "actual-acceptance.json").open("x", encoding="utf-8") as output:
    json.dump({"recorded_at": now(), "source_root": str(F), "sequence": state["sequence"], "claims": {},
               "actual_states": {name: node["state"] for name, node in state["nodes"].items()},
               "integrate_receipt_sha256": sha(receipt_path), "metadata_paths": 2, "retained_source_payloads": 235}, output, indent=2)
    output.write("\n")
print(json.dumps({"actual_integration": "SUCCEEDED", "sequence": state["sequence"], "receipt_sha256": sha(receipt_path)}), flush=True)
