"""Seal the independent joined-cut review against its actual read-only claim."""
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

R = Path(__file__).resolve().parent
S = R.parents[3]
Q = S / ".agents/app3-20261014"
RUNTIME = R.parent
RUN = "app3-20261014"
PY312 = r"C:\Users\Quencher\AppData\Local\Programs\Python\Python312\python.exe"
E3 = S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_runtime import _snapshot_workspace, _changed_files

claim = read(RUNTIME / RUN / "claims.json")["review"]
node = read(RUNTIME / RUN / "graph.json")["graph"]["nodes"]["review"]
affected = read(R / "affected-r1.json")
native = read(R / "native-mechanism-r3.json")
junctions = read(R / "native-junctions-r1.json")
audit = read(R / "joined-audit.json")
assert affected["exit_status"] == native["exit_status"] == junctions["exit_status"] == audit["exit_status"] == 0
assert affected["tests_run"] == 285 and native["tests_run"] == 22
for evidence in (affected, native):
    assert evidence["failures"] == evidence["errors"] == evidence["skips"] == 0
    assert evidence["source_unchanged"] is True
assert affected["expected_test_ids"] == affected["executed_test_ids"]
assert native["expected_ids"] == native["executed_ids"]
review_ids = affected["executed_test_ids"] + native["executed_ids"]
assert len(review_ids) == len(set(review_ids)) == 307
assert affected["native_census"]["exit_status"] == 0
assert affected["native_census"]["result"]["clear"] is True
assert affected["preexisting_fixture_members_removed"] == []
assert audit["payload_count"] == 235 and audit["managed_claim_artifact_count"] == 236
assert audit["create_count"] == 2 and audit["extend_count"] == 5 and audit["identical_retained_count"] == 228
assert sha(Q / "TRANSFER-MANIFEST.json") == audit["manifest_sha256"] == "491955891bd35135579fd525b312c3f7b54e727ee2be55d189eb76293606ed0b"
publication = S / ".agents/runtime/rs2-20261014/apply_joined_source.py"
assert sha(publication) == audit["publication_script_sha256"] == "4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77"
for entry in audit["payloads"]:
    relative = entry["relative_path"]
    assert sha(Q / relative) == entry["candidate_sha256"]
    target = S / relative
    actual_before = sha(target) if target.is_file() else None
    assert actual_before == entry["active_before_sha256"]
managed = _snapshot_workspace(Q, Path("T:/"))
assert _changed_files(claim["baseline_snapshot"], managed) == []
assert not (RUNTIME / "active-application").exists()
physical = {"source": {"added": 0, "removed": 0}, "tests": {"added": 0, "removed": 0}, "contract_document": {"added": 0, "removed": 0}}
for change in audit["exact_seven_path_line_changes"]:
    relative = change["relative_path"]
    kind = "source" if relative.startswith("src/") else "tests" if relative.startswith("tests/") else "contract_document"
    for opcode in change["line_changes"]:
        physical[kind]["added"] += len(opcode["new_lines"])
        physical[kind]["removed"] += len(opcode["old_lines"])
files = ["affected-r1.json", "affected-r1.txt", "native-mechanism-r3.json", "native-mechanism-r3.txt",
         "native-junctions-r1.json", "joined-audit.json", "native-census-r1.stdout", "native-census-r1.stderr"]
evidence = [{"path": str(R / name), "sha256": sha(R / name)} for name in files]
prior = [
    {"command": str(Path(PY312)) + " -B -X utf8 " + str(R / "verify_publication.py"), "exit_status": 1,
     "classification": "environment/deep disposable fixture path-length issue; repaired in fixture setup",
     "record": str(R / "native-mechanism-r1.json"), "record_sha256": sha(R / "native-mechanism-r1.json"),
     "raw": str(R / "native-mechanism-r1.txt"), "raw_sha256": sha(R / "native-mechanism-r1.txt"),
     "exact_result": "22 methods; one error and one failure, both WinError206 before fixture publication; retained native fixture partial staging",
     "repair": "Preserved r1; r2/r3 give only synthetic deeply nested application fixture roots extended-length Windows paths; publication mechanism bytes unchanged"},
    {"command": PY312 + " -B -X utf8 " + str(R / "audit_joined_cut.py"), "exit_status": 1,
     "classification": "review checker schema mismatch; fixed in r2",
     "exact_error": "AssertionError: ('rs3-20261014', 'review', 'accepted and selected receipt content differs')",
     "source_sha256": sha(R / "audit_joined_cut.py"),
     "diagnosis": str(R / "receipt-normalization-diagnosis.json"), "diagnosis_sha256": sha(R / "receipt-normalization-diagnosis.json"),
     "repair": "Installed runtime lines521-523 append observed_git/git_baseline; reconstruct precisely those fields while retaining exact raw-content and normalized-hash equality"},
    {"command": PY312 + " -B -X utf8 " + str(R / "audit_joined_cut_r2.py"), "exit_status": 1,
     "classification": "review checker used incorrect producer result field; fixed in r3",
     "exact_error": "KeyError: 'manifest_sha256'", "source_sha256": sha(R / "audit_joined_cut_r2.py"),
     "repair": "Both accepted producer receipts declare transfer_manifest_sha256; r3 uses that exact field. Independent reviewer result retains manifest_sha256"}
]
finished = datetime.now(timezone.utc).isoformat()
report_path = R / "collaborative-review.md"
with report_path.open("x", encoding="utf-8") as stream:
    stream.write(f"""# APP3 independent Collaborative and hostile review

Verdict: APPROVED_SCOPED_JOIN_AND_PUBLICATION_MECHANISM.

Reviewer `/root/pressure_review` holds the actual read-only APP3 claim since `{claim['claimed_at']}`, input `{claim['input_hash']}`. Candidate root is `{Q}`; source root is `{S}`. No active source application has started. This report is sealed at `{finished}` before actual reviewer completion submission.

The current manifest SHA256 is `{audit['manifest_sha256']}`. Exact publication source SHA256 is `{audit['publication_script_sha256']}`. Every joined payload and active before state was independently rechecked after tests. All 236 managed claim files are unchanged.

## Verified byte join and ownership

There are235 payloads, with228 identical retained paths, five extensions preserving originals, and two creates. The seven declared actions correspond exactly to the two approved RS3 test repairs and five approved RD2 diagnostics paths. No producer path overlaps. Each current producer input, raw reviewer receipt and installed normalized accepted receipt is bound by its current hash. The verifier helper `tools/verify_source_coverage.py` is an unchanged connected read dependency. All72 product modules import from this exact APP3 cut; every other original RS2 payload remains conserved. The original failed RS2 integration is retained as FAILED.

`joined-audit.json` contains every path hash, owner, native file identity and the exact old/new line changes for the seven actions. Physical transferred line changes are `{json.dumps(physical, sort_keys=True)}`; the coordinator and reviewer authored zero product source lines for this join.

## Verified execution

The eight connected selectors executed285 distinct tests, with zero failures, errors or skips. They include all prior six-selector RS3 affected tests plus diagnostics and Windows jobs. Source before/after hashes are equal, all expected IDs were executed exactly, original fixtures were preserved, and the current owned-client/service census is clear. {len(affected['new_remaining_fixture_members'])} new test-owned fixture members remain preserved; zero pre-existing members were removed.

After the actual claim,22 independent native and algorithm-harness methods passed with zero errors/skips. They include the eight unchanged author primitive tests, replacement/original backup identity, target/stage sharing denial, drift/alias/absence refusal and owner path/script/manifest checks. The whole-algorithm harness uses synthetic claim documents entirely inside owned disposable fixtures while actual Windows file APIs execute; its positive batch conserves five logical and native originals and all retained bytes. Its controlled interruption preserves partial journal state and blocks an unchecked rerun. These22 IDs and the285 connected IDs total307 distinct methods. Three additional actual Windows junction cases reject staged/target/backup reparse ancestry and preserve physical files. The earlier identical-script native qualification is retained separately rather than added again to the307 count.

## Publication and recovery evidence

The executable checks its own source SHA against the review before creating any active output, validates the exact manifest and seven-file allowlist, and checks all235 before hashes. It stages fresh bytes and logical before images with exclusive native reads and file flushes. Existing five paths use ReplaceFileW with flags0 and distinct fresh native backups; the two creates use the retained no-overwrite MoveFileExW helper. The publication script and helper remained byte-identical throughout independent tests. Real junction components and native locked files are refused before publication. Actual active backup path lengths are at most177 characters.

Windows documents partial ReplaceFileW outcomes:1177 can retain the replacement at its original name and move the old file to the backup path. The current mechanism therefore retains target/stage/logical/native-backup evidence and requires all seven filesystem states and identities to be reconciled under fresh review before resuming. Its error-path tests inject documented1175/1176/1177 outcomes in process; these codes were not claimed as naturally observed. Native sharing denial, successful replacement, original backup identity and junction refusal were actually observed. [Microsoft ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew), [Microsoft MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw).

Two pre-application findings were repaired by Root: required publication-script self binding and preservation of the already created independent-review runtime directory while unknown initial members are refused. All failed checker/fixture attempts are preserved in receipt.result.prior_failures, including the WinError206 deep fixture outcome and the two diagnosed receipt-field mismatches. They required review-harness changes; no product bytes were modified by this reviewer.

## Scope and handoff

Reviewer and producers share the same Windows host/principal and declared project-owned dependency environment. Path checks and native primitive execution qualify the exclusive ordinary file scope. Same-principal privileged ancestor replacement during check-to-call intervals remains an explicit reader limit. Each file publishes separately; interrupted batches preserve partial states for review. Power-loss recovery is unexecuted. The latest source acceptance is pending Root's actual validation gate, seven reviewed publications and mandatory complete actual-S suite. Current review approval binds only the exact manifest, joined source and publication mechanism identified here.

Current evidence:\n""")
    for item in evidence:
        stream.write(f"- `{item['path']}` SHA256 `{item['sha256']}`\n")
evidence.append({"path": str(report_path), "sha256": sha(report_path)})
receipt = {"schema_version": 1, "run_id": RUN, "node_id": "review", "executor_id": "/root/pressure_review",
           "started_at": affected["started_at"], "finished_at": finished, "input_hash": claim["input_hash"], "changed_files": [],
           "result": {"verdict": "APPROVED_SCOPED_JOIN_AND_PUBLICATION_MECHANISM", "manifest_sha256": audit["manifest_sha256"],
                      "publication_script_sha256": audit["publication_script_sha256"], "producer_reviews": audit["actual_accepted_producer_reviews"],
                      "payload_count": 235, "identical_retained_count": 228, "extend_count": 5, "create_count": 2,
                      "exact_application_paths": [change["relative_path"] for change in audit["exact_seven_path_line_changes"]],
                      "independent_current_test_count": 307, "independent_current_test_ids": review_ids,
                      "native_junction_cases": 3, "all72_imports_current_cut": True, "managed_claim_artifacts": 236,
                      "payloads_and_active_before_states_current_unchanged": True, "source_and_test_LOC_authored_by_reviewer": 0,
                      "transferred_physical_lines": physical, "preexisting_fixture_members_removed": 0,
                      "new_test_owned_fixture_members_preserved": len(affected["new_remaining_fixture_members"]),
                      "owned_native_custody_clear": True, "prior_failures": prior, "evidence": evidence,
                      "shared_administration": audit["shared_administration"],
                      "controlled_test_limits": "Synthetic orchestration state documents and documented partial-error injections are explicitly identified; actual native primitive/junction observations separated",
                      "source_application": "Pending Root actual validation and exact seven-file publication",
                      "full_actual_S_acceptance": "Pending mandatory new full actual destination run"},
           "commands": [{"command": str(E3) + " -B -X utf8 " + str(R / "run_affected.py"), "exit_status": 0},
                        {"command": PY312 + " -B -X utf8 " + str(R / "verify_publication_r3.py"), "exit_status": 0},
                        {"command": PY312 + " -B -X utf8 " + str(R / "audit_joined_cut_r3.py"), "exit_status": 0}],
           "validations": [{"name": name, "passed": True} for name in (
               "actual_review_claim_frozen_manifest_and_publication_self_binding", "exact235_payloads_and_current_before_source",
               "both_accepted_independent_producer_receipts_and_exact_seven_nonoverlapping_paths",
               "five_extensions_two_creates_and228_retained", "all72_current_cut_imports", "independent285_connected_cases_no_failures_errors_skips",
               "independent22_native_and_explicit_synthetic_state_harness_cases_no_failures_errors_skips",
               "three_actual_junction_component_refusals", "original_backups_and_partial_failure_evidence_preserved",
               "all236_managed_claim_artifacts_unchanged", "preexisting_fixtures_preserved_and_owned_native_custody_clear")],
           "exit_status": 0, "decision": "approved"}
normalized = validate_receipt(receipt, run_id=RUN, node_id="review", executor_id="/root/pressure_review",
                              input_hash=claim["input_hash"], claimed_at=claim["claimed_at"], node=node)
receipt_path = R / "review.json"
with receipt_path.open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
with (R / "receipt-validation.json").open("x", encoding="utf-8") as stream:
    json.dump({"schema_version": 1, "validated_at": finished, "actual_claim": {key: claim[key] for key in ("input_hash", "claimed_at", "executor_id", "workspace")},
               "strict_validation_passed": True, "normalized_receipt_hash": normalized["receipt_hash"],
               "receipt_sha256": sha(receipt_path), "report_sha256": sha(report_path), "runtime_completion_pending": True,
               "managed_changed_files": []}, stream, indent=2)
    stream.write("\n")
print(json.dumps({"verdict": receipt["result"]["verdict"], "independent_distinct_tests": 307,
                  "receipt_sha256": sha(receipt_path), "report_sha256": sha(report_path),
                  "transferred_physical_lines": physical, "runtime_completion_pending": True}, indent=2))
