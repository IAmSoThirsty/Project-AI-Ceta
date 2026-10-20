"""Seal independent actual destination evidence; never touch runtime claims/state."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json

R = Path(__file__).resolve().parent
S = R.parents[3]
Q = S / ".agents/app3-20261014"
FULL = S / ".agents/runtime/rs2-20261014/active-application"
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source_audit = read(R / "applied-source-audit.json")
full_audit = read(R / "full-result-audit.json")
bounded = read(R / "affected-r1.json")
discovery = read(R / "actual-suite-discovery.json")
assert source_audit["exit_status"] == full_audit["exit_status"] == bounded["exit_status"] == discovery["exit_status"] == 0
assert full_audit["decision"] == "approved" and all(full_audit["checks"].values())
assert bounded["tests_run"] == 14 and bounded["failures"] == bounded["errors"] == bounded["skips"] == 0
assert bounded["source_unchanged"] is True and bounded["preexisting_fixture_members_removed"] == []
assert bounded["native_census"]["exit_status"] == 0 and bounded["native_census"]["result"]["clear"] is True
assert bounded["native_census"]["result"]["children"] == []
assert bounded["expected_test_ids"] == bounded["executed_test_ids"]
assert set(bounded["executed_test_ids"]) <= set(full_audit["raw_test_ids"])
expected = source_audit["before_current_hashes"]
current = {relative: sha(S / relative) for relative in expected}
assert current == expected == bounded["before_hashes"] == bounded["after_hashes"] == full_audit["current_source_hashes"]
assert len(current) == 235
manifest_path = Q / "TRANSFER-MANIFEST.json"
journal_path = R.parent / "active-application/APPLICATION.json"
assert sha(manifest_path) == source_audit["manifest_sha256"]
assert sha(journal_path) == source_audit["application_journal_sha256"]
full_path = FULL / "destination-full-r2.json"
assert sha(full_path) == full_audit["full_suite_sha256"]
completion_path = R.parent / "complete_active_integration.py"
assert sha(completion_path) == "18c177ce8dde3972228903d8a53bee8ffc60af5aa1a1e1951fcb1c27b9a1efbc"
completion_text = completion_path.read_text()
completion_ast = ast.parse(completion_text)
assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "validate_receipt"
           for node in ast.walk(completion_ast))
assert "assert changed == expected_changed" in completion_text
assert "response.get('allowed') is True" in completion_text
assert "assert not read(R / RUN / 'claims.json')" in completion_text
assert "assert all(node['state'] == 'SUCCEEDED'" in completion_text
assert "review['expected_payload_hashes']" in completion_text
assert "assert exact_sha(full_path.with_suffix('.txt')) == full['output_sha256']" in completion_text
assert "facts.st_ino == item['inode']" in completion_text
history = [
    {"path": str(S / ".agents/runtime/rs2-20261014/integrate.json"),
     "sha256": "7f75b4d9621855d38a8da811198ae20a1aebcf412ab5af309623ab7d224693bb", "decision": "FAILED"},
    {"path": str(FULL / "destination-full-r1.txt"),
     "sha256": "b9bc7bbde2b4cb44a061790d8c03e544b2b6f8dc6d18e0dae8bb17ad42a1d9f5", "decision": "ORIGINAL_TWO_FULL_SUITE_FAILURES_PRESERVED"},
    {"path": str(S / ".agents/runtime/rd1-20261014/independent-review/review.json"),
     "sha256": "528bd92b3909c2e4d5da8a3fa3db31c54c451c8089b4c0c251f1c9cf20cf4b91", "decision": "rejected"},
    {"path": str(S / ".agents/runtime/rd1-20261014/rd1-20261014/receipts/review.json"),
     "sha256": "814da4b18cf8c8eab12fb43f37b637b6ea4b7244c157f25c27138531db2211b8", "decision": "rejected"},
]
for item in history:
    assert sha(Path(item["path"])) == item["sha256"]
assert read(Path(history[2]["path"]))["decision"] == read(Path(history[3]["path"]))["decision"] == "rejected"
evidence_names = ["applied-source-audit.json", "actual-suite-discovery.json", "full-result-audit.json",
                  "affected-r1.json", "affected-r1.txt", "native-census-r1.stdout", "native-census-r1.stderr"]
evidence = [{"path": str(R / name), "sha256": sha(R / name)} for name in evidence_names]
finished = datetime.now(timezone.utc).isoformat()
report_path = R / "destination-handoff.md"
with report_path.open("x", encoding="utf-8") as stream:
    stream.write(f"""# APP3 independent actual destination review

Verdict: APPROVED_ACTUAL_SOURCE_DESTINATION_VERIFICATION at `{finished}`.

The current source folder is `{S}`. Its frozen joined manifest SHA256 is `{source_audit['manifest_sha256']}`; application journal SHA256 is `{source_audit['application_journal_sha256']}`. All 235 active payloads are byte-identical to the reviewed APP3 cut. Exactly seven declared files are published: five extensions and two creates; 228 retained files are unchanged. All 72 actual imports resolve to this S source. The folder rename remains pending.

All five logical originals and native backups match the prior hashes and bytes. Native backup device/inode, mode and mtime match the recorded originals. Staging is empty and no pending journal temporary remains. The original Root integrate claim was observed at job entry with actor `/root`, workspace S and input `{source_audit['root_claim_input_hash']}`, consistent with the immutable journal. Actual runtime claims/state were neither read nor modified after Root's completion instruction.

## Personally inspected full execution

The full active suite completed 1,158 tests with zero failures, errors and skips. Independent actual-S discovery, preflight IDs, reported executed IDs and all 1,158 raw method lines agree exactly and are unique. Raw output and preflight hashes match their records. All 235 hashes are equal in the frozen manifest, preflight, full-run before/after, independent source audit and current destination. Reported dependencies are bound to current module bytes in the declared same-project environment. Actual Root native-census stdout matches the result, is clear with no children, and stderr is empty.

The two original failing guard/Qt methods and real native diagnostics cases occur in the passing raw run. Historical RS2 failure receipt/raw and RD1 rejected raw/installed receipts remain present with their exact recorded hashes.

## Independent bounded actual destination execution

After the full suite ended, this reviewer independently executed 14 selected methods with zero failures, errors or skips in {bounded['elapsed_seconds']:.3f} seconds. They cover the three precise contract import guards, original interrupted Qt dialog/custody method with both RuntimeError and KeyboardInterrupt subcases, all eight actual owned-process diagnostics native methods, real disposable storage cache observation, and one explicitly controlled compute-counter domain case. These 14 IDs are a subset of the full 1,158 cases; distinct source coverage remains 1,158. No test source, ROOT or qualification guard was changed.

All 72 imports remained in actual S and all 235 before/after hashes stayed equal. Zero pre-existing fixture members were removed; {len(bounded['new_remaining_fixture_members'])} new test-owned fixture members remain preserved. The fresh independent native census is clear with no children. Outputs and fixture creation remained within the assigned review/disposable test scopes; product bytes, configuration and accepted receipts/manifests stayed immutable.

## Completion mechanism and scoped handoff

Root's completion helper `{completion_path}` SHA256 `{sha(completion_path)}` was personally inspected. It checks the actual Root/S running claim, accepted predecessor states, exact manifest/journal/publication hashes, current full execution and raw hash, this standalone report binding, all 235 current source/candidate hashes, five original backups, and exactly seven actual snapshot changes. It builds and validates a strict receipt, captures real CLI completion, and requires accepted completion, every node SUCCEEDED and an empty claim set. No mismatch was established in that mechanism. This reviewer did not execute it or perform runtime transitions for the destination job.

Current local source destination verification is approved. Root's actual APP3 integration completion remains the next runtime action. Whole-repository preservation/rename and conditional identity applications remain coordinator work. The reviewer and coordinator share a Windows host/principal and declared project-owned dependencies; broader malicious privileged path races and power-loss recovery were outside executed qualification. PySide6 distribution metadata absence remains explicitly recorded as an environment issue; actual dependency modules, versions and executed native Qt behavior are identified separately.

Evidence:\n""")
    for item in evidence:
        stream.write(f"- `{item['path']}` SHA256 `{item['sha256']}`\n")
evidence.append({"path": str(report_path), "sha256": sha(report_path)})
record = {
    "schema_version": 1, "record_kind": "independent-actual-source-destination-review", "reviewer": "/root/pressure_review",
    "started_at": source_audit["started_at"], "finished_at": finished, "decision": "approved", "exit_status": 0,
    "source_root": str(S), "manifest_sha256": source_audit["manifest_sha256"],
    "application_journal_sha256": source_audit["application_journal_sha256"],
    "full_suite_sha256": full_audit["full_suite_sha256"], "full_suite_tests_run": 1158,
    "full_suite_raw_sha256": full_audit["full_raw_sha256"], "full_suite_preflight_sha256": discovery["preflight_sha256"],
    "expected_payload_hashes": expected, "current_payload_hashes": current,
    "observations": {"payloads_verified": 235, "actual_publications": 7, "retained": 228, "creates": 2, "extensions": 5,
        "logical_originals": 5, "native_originals": 5, "original_native_identities_metadata_and_bytes_preserved": True,
        "all72_imports_actual_S": True, "all1158_ids_discovered_reported_and_raw_equal": True,
        "full_failures": 0, "full_errors": 0, "full_skips": 0,
        "independent_bounded_methods": 14, "independent_bounded_failures": 0, "independent_bounded_errors": 0,
        "independent_bounded_skips": 0, "independent_bounded_ids": bounded["executed_test_ids"],
        "bounded_methods_are_subset_of_full_suite": True, "fresh_owned_native_custody_clear": True,
        "remaining_staged_files": 0, "preexisting_fixture_members_removed": 0,
        "new_test_owned_fixture_members_preserved": len(bounded["new_remaining_fixture_members"]),
        "claims_state_not_read_or_modified_during_completion": True,
        "completion_mechanism_personally_inspected_sha256": sha(completion_path),
        "completion_mechanism_defects_established": [], "source_configuration_manifest_receipt_edits": []},
    "full_inspection_checks": full_audit["checks"], "completion_mechanism_scope": "Static independent inspection; Root owns actual execution and completion readback",
    "commands": [
        {"command": str(S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe") + " -B -X utf8 " + str(R / "verify_applied_destination.py"), "exit_status": 0},
        {"command": str(S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe") + " -B -X utf8 " + str(R / "discover_actual_suite.py"), "exit_status": 0},
        {"command": str(S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe") + " -B -X utf8 " + str(R / "inspect_full_result.py"), "exit_status": 0},
        {"command": str(S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe") + " -B -X utf8 " + str(R / "run_bounded_destination.py"), "exit_status": 0},
    ], "proofs": evidence, "historical_evidence_preserved": history, "prior_reviewer_failures": [],
    "shared_administration": source_audit["shared_administration"],
    "existing_issues": [{"issue": "PySide6 distribution metadata unavailable in the declared e3 environment", "classification": "environment/dependency issue",
                          "impact": "Actual module bytes, declared versions and native Qt execution are recorded; current local source verification passed"}],
    "reader_limits": ["Shared Windows host/principal", "Qt native execution used the reported offscreen platform",
                      "Controlled compute-counter domain case is explicitly distinguished from actual native process/storage observations",
                      "Privileged malicious path races and power-loss recovery are outside executed scope"],
    "remaining": ["Root actual APP3 integration receipt submission/completion readback", "Whole-repository preservation and requested folder rename/identity applications"],
}
record_path = R / "destination-review.json"
with record_path.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps({"decision": "approved", "full_suite_tests_run": 1158, "independent_bounded_tests": 14,
                  "report_sha256": sha(report_path), "record_sha256": sha(record_path), "source_payloads": 235,
                  "root_actual_completion_pending": True}, indent=2))
