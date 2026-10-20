"""Bind exact passing evidence and the withheld GD2 disposition to the real claim."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re
import subprocess
import sys

V = Path(__file__).resolve().parent
R, F = V.parent, V.parents[3]
Q, BASE, RUN = F / ".agents/gd2-20261014", F / ".agents/gd1-20261014", "gd2-20261014"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
def ref(path):
    return {"repository_relative_path": path.relative_to(F).as_posix(), "sha256": sha(path)}

preflight = read(V / "preflight.json")
manifest = read(Q / "TRANSFER-MANIFEST.json")
assert sha(Q / "TRANSFER-MANIFEST.json") == preflight["manifest_sha256"]
assert sha(R / "implement.json") == preflight["implement_sha256"]
claim = read(R / RUN / "claims.json")["review"]
assert claim["executor_id"] == "/root/pressure_writer" and claim["workspace"] == str(Q)
connected = read(V / "connected-r1.json")
assert connected["successful"] and connected["tests_run"] == 327
assert connected["failures"] == connected["errors"] == connected["skips"] == 0
assert connected["executed_ids"] == connected["expected_ids"] == preflight["author_expected_ids"]
raw = (V / "connected-r1.txt").read_text(encoding="utf-8")
raw_ids = re.findall(r"^test_[^\n]+\(([^)]+)\) \.\.\. ok\s*$", raw, re.M)
assert len(raw_ids) == len(set(raw_ids)) == 327 and raw_ids == connected["executed_ids"]
hostile = read(V / "hostile-r2.json")
assert hostile["exit_status"] == 0 and hostile["tests_run"] == 6
assert hostile["failures"] == hostile["errors"] == hostile["skips"] == 0
assert hostile["candidate_payloads_unchanged"] and hostile["active_Source_payloads_unchanged"]
assert hostile["actual_Source_writes"] == []
assert len([row for row in hostile["observations"] if row["case"] == "nested_bool_recovery"]) == 10
assert hostile["publication_script_sha256"] == "f6a9dcbbada985fc5495c7af3b46c46039bcbd8c5c5fa668e39e1c4732230599"
source = Q / "src/ceta/resource/diagnostics.py"
left = ast.parse((BASE / "src/ceta/resource/diagnostics.py").read_text())
right = ast.parse(source.read_text())
sampler = next(node for node in right.body if isinstance(node, ast.ClassDef) and node.name == "OwnedProcessTelemetrySampler")
sample = next(node for node in sampler.body if isinstance(node, ast.FunctionDef) and node.name == "sample")
counter_try = next(node for node in ast.walk(sample) if isinstance(node, ast.Try)
                   and any(isinstance(child, ast.For) for child in node.body))
validator = next(node for node in counter_try.body if isinstance(node, ast.For))
assert ast.unparse(validator.iter) == "(counters.working_set_bytes, counters.usage.cpu_time_100ns, counters.usage.private_bytes, counters.usage.read_io_bytes, counters.usage.write_io_bytes)"
assert len(validator.body) == 1 and ast.unparse(validator.body[0]) == "observation.__post_init__()"
counter_try.body.remove(validator)
assert ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)
parent_oracles = (F / ".agents/runtime/gd1-20261014/independent-review/hostile_timing_probes.py").read_text()
prior_class = next(node for node in ast.parse(parent_oracles).body if isinstance(node, ast.ClassDef) and node.name == "IndependentTimingBoundaryTests")
test_path = Q / "tests/contract/test_process_observation_validation.py"
test_text = test_path.read_text()
classes = [node for node in ast.parse(test_text).body if isinstance(node, ast.ClassDef)]
assert ast.dump(classes[0], include_attributes=False) == ast.dump(prior_class, include_attributes=False)
assert sha(Q / "tests/contract/test_process_observation_timing.py") == sha(BASE / "tests/contract/test_process_observation_timing.py")
appends = [node for node in ast.walk(classes[1]) if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
           and ast.unparse(node.value.func) == "observations.append"]
assert len(appends) == 1
last_append = appends[0]
first_append = next(node for node in ast.walk(classes[0]) if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                    and ast.unparse(node.value.func) == "observations.append")
assert ast.dump(last_append, include_attributes=False) == ast.dump(first_append, include_attributes=False)
assert last_append.end_lineno - last_append.lineno + 1 == 2
bindings = {row["relative_path"]: sha(Q / row["relative_path"]) for row in manifest["payloads"]}
assert bindings == {row["relative_path"]: row["candidate_sha256"] for row in manifest["payloads"]}
active_after = {relative: sha(F / relative) for relative in preflight["source_before_sha256"]}
assert active_after == preflight["source_before_sha256"]
for relative in ("tests/contract/test_process_observation_timing.py", "tests/contract/test_process_observation_validation.py"):
    assert not (F / relative).exists()
prior = F / ".agents/runtime/gd1-20261014/independent-review"
findings = [
    {"id": "GD2-R-F01", "priority": "P2", "classification": "blocking current handoff per coordinator decision",
     "title": "New unavailable-mutation test appends a duplicate inaccurately labelled rollback observation",
     "path": str(test_path), "source_sha256": sha(test_path), "start_line": last_append.lineno, "end_line": last_append.end_lineno,
     "actual_subject": "Unavailable value/reason mutations", "displayed_case_label": "asymmetric_precise_rollback",
     "runtime_test_assertions": "PASS; author runner does not export this observations list",
     "LOC": {"reported_new": 133, "reused_duplicate_credit": 0, "deduct_duplicate_lines": 2, "qualified_new": 131},
     "next_executable_repair": "Fresh successor removes these two lines, preserves all 327 exact method IDs and reruns bound evidence"},
    {"id": "GD2-PUB-F01", "priority": "P1", "classification": "blocking publication-helper approval",
     "title": "Approved local metadata is not bound to the persisted review and exact manifest",
     "publication_script_sha256": hostile["publication_script_sha256"], "evidence": ref(V / "hostile-r2.json"),
     "counterexample": "Own fixture runtime has approved JSON with wrong manifest hashes and no persisted review receipt. It passes helper gates and reaches intercepted first native publication call.",
     "limits": "Synthetic metadata in an owned fixture; Source publication intercepted, no actual owner/runtime state tampering or Source write",
     "next_executable_repair": "Compare exact local strict receipt with actual persisted receipt and bind both candidate/helper approvals to the exact manifest"},
    {"id": "GD2-PUB-F02", "priority": "P1", "classification": "blocking publication-helper approval",
     "title": "Recorded original native identities do not gate replacement or qualify retained backup identities",
     "evidence": ref(V / "hostile-r2.json"), "counterexample": "Actual same-byte substitution in own native fixture changes target inode; hash-only primitive still accepts replacement and its second backup has substituted identity instead of initially recorded identity.",
     "limits": "Two owned fixture ReplaceFileW operations; first native original remains preserved; no Source operation or uninterrupted-custody claim",
     "next_executable_repair": "Check captured fstat identity at preservation, immediately before replacement, on retained native backup, and at final verification"},
    {"id": "GD2-RUNNER-F01", "priority": "P2", "classification": "requires successor runtime repair before Source validation",
     "title": "Normal exit is inside a BaseException handler and would be labelled a writer failure",
     "path": str(R / "run_destination_full.py"), "sha256": sha(R / "run_destination_full.py"),
     "evidence_type": "Direct source inspection; runner not executed against Source",
     "source_fact": "sys.exit(record['exit_status']) is within the try, and the following except BaseException records writer-failure exit_status1",
     "inference": "SystemExit(0) on a passing run would enter that error branch",
     "next_executable_repair": "Move normal exit after try/except, retaining real interruption/crash evidence and primary exception"}]
evidence = {"schema_version": 1, "reviewer": "/root/pressure_writer", "observed_at": now(), "decision": "rejected",
    "disposition": "WITHHELD_GD2_SUPERSEDED_BY_FRESH_CORRECTED_CUT", "manifest": ref(Q / "TRANSFER-MANIFEST.json"),
    "implement": ref(R / "implement.json"), "author_readback": ref(R / "actual-implementation-readback.json"),
    "claim": {key: claim[key] for key in ("executor_id", "workspace", "claimed_at", "input_hash")},
    "findings": findings, "verified_product_results": {"methods": 327, "failures": 0, "errors": 0, "skips": 0,
        "raw_ID_order_and_uniqueness_exact": True, "cohort": connected["cohort"], "evidence": ref(V / "connected-r1.json"),
        "raw": ref(V / "connected-r1.txt"), "native_lifetimes": len(connected["native_lifetimes"]),
        "all_observed_process_and_job_handles_closed": True,
        "currentness_native_trials": [row for row in connected["native_timing_observations"] if row.get("case") == "currentness"]},
    "source_fix": {"added_functional_lines_this_successor": 3, "entire_GD1_AST_exact_after_removing_only_validation_loop": True,
        "all_five_quantities_validated_before_order_counter_baseline_adoption": True,
        "public_signatures_shared_contracts_and_all_other_payloads_retained": True,
        "original_GD1_failure_oracle": ref(prior / "nested-shape-candidate.json"),
        "original_seven_oracle_class_AST_exact": True, "original32_timing_test_bytes_exact": True,
        "extra_hostile_methods": 6, "extra_hostile": ref(V / "hostile-r2.json"),
        "extra_hostile_limit": "Three malformed/recovery methods plus three publication/control probes; passing confirms observed defect or closure conditions, not helper approval"},
    "source_conservation": {"candidate_payloads": 281, "candidate_members_with_manifest": 282, "active_payloads": 279,
        "candidate_payloads_unchanged": True, "active_source_payloads_unchanged": True, "active_source_writes": [],
        "E3_writes": [], "external_repository_reads_or_writes_this_job": []},
    "independence": preflight["independence"], "whole_joined_unit_independent_acceptance": "OPEN",
    "pending": manifest["pending"],
    "prior_failures": [{"classification": "Reviewer r1 preparation fault: synthetic read approval was not physically present for later hash; FileNotFoundError, no Source publication",
                        "code": ref(V / "hostile_review.py"), "result": ref(V / "hostile-r1.json"), "raw": ref(V / "hostile-r1.txt"),
                        "successor": ref(V / "hostile_review_r2.py")}],
    "qualification": "No product test failure is fabricated. Rejection is the coordinator's requested handoff disposition for inaccurate test evidence and unqualified publication/runtime tooling.",
    "executed_publication_operations": "Only two native replacements per hostile run in fresh owned fixtures; Source operations intercepted"}
save(V / "REPORT.json", evidence)
save(V / "publication-helper-review.json", {"schema_version": 1, "reviewer": "/root/pressure_writer", "reviewed_at": now(),
    "decision": "rejected", "exit_status": 1, "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"),
    "publication_script_sha256": hostile["publication_script_sha256"], "finding_ids": ["GD2-PUB-F01", "GD2-PUB-F02"],
    "evidence": ref(V / "hostile-r2.json"), "report": ref(V / "REPORT.json"), "actual_Source_publication": False})
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt
snapshot = _snapshot_workspace(Q, Path("T:/"))
assert snapshot == preflight["snapshot"]
changed = _changed_files(claim["baseline_snapshot"], snapshot)
assert changed == []
commands = []
for name in ("connected-r1-command.json", "hostile-r1-command.json", "hostile-r2-command.json"):
    item = read(V / name)
    commands.append({"command": subprocess.list2cmdline(item["command"]), "exit_status": item["exit_status"]})
receipt = {"schema_version": 1, "run_id": RUN, "node_id": "review", "executor_id": "/root/pressure_writer",
    "started_at": claim["claimed_at"], "finished_at": now(), "input_hash": claim["input_hash"], "changed_files": changed,
    "decision": "rejected", "exit_status": 1, "result": {"decision": "rejected", "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"),
        "report": ref(V / "REPORT.json"), "publication_helper_review": ref(V / "publication-helper-review.json"),
        "findings": [item["id"] for item in findings], "methods": 327, "product_failures": 0, "product_errors": 0, "product_skips": 0,
        "source_functional_fix_verified": True, "extra_hostile_methods": 6, "extra_hostile_failures": 0,
        "extra_hostile_errors": 0, "shared_authorship_limit": preflight["independence"], "whole_unit_acceptance": "OPEN",
        "qualified_new_test_LOC": 131, "prior_failures": evidence["prior_failures"]},
    "commands": commands, "validations": [
        {"name": "exact_frozen_cut_claim_and_readonly_conservation", "passed": True},
        {"name": "327_unique_raw_discovered_executed_methods_zero_skips", "passed": True},
        {"name": "all5_nested_validation_and_recovery_before_sampler_adoption", "passed": True},
        {"name": "test_observation_label_and_new_LOC_credit_exact", "passed": False},
        {"name": "publication_receipt_manifest_and_native_identity_binding", "passed": False},
        {"name": "whole_joined_unit_has_independent_non_author_acceptance", "passed": False}]}
kwargs = {"run_id": RUN, "node_id": "review", "executor_id": "/root/pressure_writer", "input_hash": claim["input_hash"],
          "claimed_at": claim["claimed_at"], "node": read(R / RUN / "graph.json")["graph"]["nodes"]["review"]}
validate_receipt(receipt, **kwargs)
save(V / "review.json", receipt)
validate_receipt(load_receipt(V / "review.json"), **kwargs)
print(json.dumps({"decision": "rejected", "review_sha256": sha(V / "review.json"), "report_sha256": sha(V / "REPORT.json"),
                  "helper_review_sha256": sha(V / "publication-helper-review.json"), "methods": 327, "product_failures": 0,
                  "malformed_label_lines": [last_append.lineno, last_append.end_lineno], "qualified_new_test_LOC": 131}), flush=True)
