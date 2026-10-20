"""Bind independent ER1 observations and complete one narrowly scoped review."""
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/er1-20261014", F / ".agents/runtime/er1-20261014"
V = R / "independent-review"
E3 = F / ".agents/source-assembly-20261014T021300Z/.agents/e3"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def write(path, data): path.open("x", encoding="utf-8").write(json.dumps(data, indent=2, allow_nan=False) + "\n")
def ref(path): return {"repository_relative_path": path.relative_to(F).as_posix(), "sha256": sha(path)}
started = datetime.now(timezone.utc).isoformat()
assert sha(Q / "TRANSFER-MANIFEST.json") == "7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83"
assert sha(R / "implement.json") == "34b94f4d8919f2e691bfde4f6df99f090e579a9201eb38bac4a97b9403e8db8f"
manifest = json.loads((Q / "TRANSFER-MANIFEST.json").read_text())
baseline = json.loads((V / "source-inventory-r1.json").read_text())
tests = json.loads((V / "review-tests-r3.json").read_text())
assert tests["successful"] and (tests["tests"], tests["failures"], tests["errors"], tests["skips"]) == (10, 0, 0, 0)
ids = [row["id"] for row in tests["cases"]]
assert len(ids) == len(set(ids)) == 10 and all(row["status"] == "PASS" for row in tests["cases"])
raw_ids = re.findall(r"^test_[^\n]+\(([^)]+)\) \.\.\. ok\s*$", (V / "review-tests-r3.txt").read_text(), re.M)
assert set(raw_ids) == set(ids) and len(raw_ids) == 10
assert tests["candidate_before"] == tests["candidate_after"]
assert all(sha(Q / relative) == expected for relative, expected in tests["candidate_after"].items())
assert len(tests["native_cli_invocations"]) == 7
assert all(row["lifetime_closed"] and row["observed_empty_job"] and row["image_sha256"] == row["retained_image_sha256"]
    and row["observed_exit"] == row["expected_exit"] for row in tests["native_cli_invocations"])
assert sum(row["expected_exit"] == 1 for row in tests["native_cli_invocations"]) == 2
assert len(manifest["payloads"]) == 30 and len({row["candidate_relative_path"] for row in manifest["payloads"]}) == 30
independent_sources = {row["source"]["relative_path"]: row["source"] for row in baseline["launchers"]}
independent_sources.update({row["RECORD"]["relative_path"]: row["RECORD"] for row in baseline["metadata"].values()})
applications = []
span_checks = 0
for row in manifest["payloads"]:
    source, candidate = Path(row["source_path"]), Q / row["candidate_relative_path"]
    assert source.is_relative_to(E3) and sha(source) == row["source_sha256"]
    assert sha(candidate) == row["candidate_sha256"] and candidate.stat().st_size == row["candidate_bytes"]
    observation = independent_sources[source.relative_to(F).as_posix()]
    assert observation["sha256"] == row["source_sha256"]
    identity = row["source_native_identity"]
    assert type(identity) is dict and identity["device"] == observation["native_identity"]["volume_serial"]
    assert identity["inode"] == observation["native_identity"]["file_id_low_64"]
    assert sha(F / row["before_image"]["repository_relative_path"]) == row["before_image"]["sha256"] == row["source_sha256"]
    applications.append({"source_path": str(source), "candidate_relative_path": row["candidate_relative_path"],
        "active_before_sha256": row["source_sha256"], "candidate_sha256": row["candidate_sha256"],
        "actual_source_native_identity": observation["native_identity"], "kind": row["kind"]})
    if row["kind"] == "EXACT_INSTALLED_RECORD_FIELD_CANDIDATE":
        before_lines, after_lines = source.read_bytes().splitlines(keepends=True), candidate.read_bytes().splitlines(keepends=True)
        assert len(before_lines) == len(after_lines) == row["row_count"]
        for change in row["exact_changed_rows"]:
            number = change["line_number"]
            original, revised = before_lines[number - 1], after_lines[number - 1]
            assert hashlib.sha256(original).hexdigest() == change["original_line_sha256"]
            assert hashlib.sha256(revised).hexdigest() == change["candidate_line_sha256"]
            offset = sum(len(line) for line in before_lines[:number - 1])
            original_bytes = source.read_bytes()
            for name, field_index in (("hash", 1), ("size", 2)):
                begin, end = change["original_byte_spans"][name]
                field = original_bytes[begin:end]
                assert list(csv.reader(io.StringIO(field.decode()), strict=True)) == [[change["original_row"][field_index]]]
                assert field.startswith(b'"') == change["original_field_quoting"][field_index - 1]
                assert offset <= begin < end <= offset + len(original)
                span_checks += 1
            assert list(csv.reader(io.StringIO(original.decode()))) == [change["original_row"]]
            assert list(csv.reader(io.StringIO(revised.decode()))) == [change["candidate_row"]]
            ending = bytes.fromhex(change["original_line_ending_hex"])
            assert original.endswith(ending) and revised.endswith(ending)
assert span_checks == 54

for key in ("current_inventory", "superseded_native_identity_bug_inventory", "source_conservation", "generation", "self_review"):
    value = manifest[key]
    assert sha(F / value["repository_relative_path"]) == value["sha256"]
for value in manifest["prior_failures"]:
    assert sha(F / value["repository_relative_path"]) == value["sha256"]
conservation = json.loads((R / "source-conservation.json").read_text())
snapshots = {}
for key in ("historical_before", "bounded_before", "after"):
    value = conservation[key]
    path = F / value["repository_relative_path"]
    assert sha(path) == value["sha256"]
    snapshots[key] = json.loads(path.read_text())
    ordinary = [member for member in snapshots[key]["members"] if member["kind"] == "ordinary_file"]
    assert len(ordinary) == 3601 and sum(member["bytes"] for member in ordinary) == 231026958
reference_files = {row["relative_path"]: row for row in snapshots["historical_before"]["members"] if row["kind"] == "ordinary_file"}
for key in ("bounded_before", "after"):
    assert {row["relative_path"]: row for row in snapshots[key]["members"] if row["kind"] == "ordinary_file"} == reference_files
    assert {row["relative_path"] for row in snapshots[key]["members"]} == {row["relative_path"] for row in snapshots["historical_before"]["members"]}
directories = json.loads((R / "directory-observation-proof.json").read_text())
assert directories["directory_count"] == len(directories["directories"]) == 101
assert directories["native_directory_identity_matches"] and directories["ordinary_file_changes"] == 0
for row in directories["directories"]:
    left, right = row["historical_before"], row["historical_after"]
    assert {key: value for key, value in left.items() if key != "bytes"} == {key: value for key, value in right.items() if key != "bytes"}
    assert row["fresh_native_handle"]["file_id_low_64"] == left["inode"]
    assert row["fresh_native_handle"]["volume_serial"] == left["device"]

sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt
claim = json.loads((R / "er1-20261014/claims.json").read_text())["review"]
assert claim["executor_id"] == "/root/pressure_writer"
snapshot = _snapshot_workspace(Q, Path("T:/"))
changed_files = _changed_files(claim["baseline_snapshot"], snapshot)
assert len(snapshot) == 33 and not changed_files and snapshot == claim["baseline_snapshot"]
limitations = ["Only this frozen preparation cut is accepted; active E3 publication and destination verification belong to Root",
    "All 23 Qt GUI/server/deployment functions remain unexecuted; all 27 callable imports and wrapper byte bindings are qualified",
    "Independent live source hashing/native IDs cover exact 30 targets and generator metadata; full 3601-file evidence was independently compared as recorded snapshots, not freshly rehashed in this review",
    "Directory-only stat byte variations do not establish whole raw metadata equality; their OS-internal cause remains unresolved",
    "Native endpoint identity/hash equality does not establish uninterrupted custody between observations",
    "Existing unavailable aggregate PySide6 distribution metadata remains unchanged",
    "Original copied launcher exited 1 with empty stdout/stderr; exact native internal error cause was not exposed",
    "Shared installed dependency/runtime and existing WindowsOwnedProcess custody code are reused; no claim of independent implementation of those dependencies"]
prior_failures = [{"classification": "REVIEWER_DIAGNOSTIC_ORACLE_ERROR_CORRECTED", "failed": ref(V / "review-tests-r1.json"),
    "raw": ref(V / "review-tests-r1.txt"), "original_runner": ref(V / "review_candidate_r1.py"),
    "issue": "Expected literal fatal-launcher diagnostic text was absent; old copied launcher exit 1 and closed empty job were measured",
    "closure": ref(V / "review-tests-r3.json")},
    {"classification": "NONBLOCKING_REVIEW_PREPARATION_LOOKUP_ERRORS", "issues": [
        "Incorrect role basename 04-collaborative-reviewer.md; actual 05-collaborative-reviewer.md was read",
        "Optional runtime README.md lookup was absent; actual candidate README.md was read"], "source_or_environment_changes": False}]
prior_failures.append({"classification": "REVIEW_FINALIZER_FIELD_LOOKUP_ERROR_CORRECTED",
    "failure": ref(V / "finish-r1-failure.json"), "original_finalizer": ref(V / "finish_review_r1.py"),
    "repair": "Read exact manifest keys and use its existing exact_changed_rows array; no source/candidate/metadata modification"})
prior_failures.append({"classification": "REVIEW_RECEIPT_DECISION_SCHEMA_ERROR_CORRECTED",
    "failure": ref(V / "finish-r2-failure.json"), "original_finalizer": ref(V / "finish_review_r2.py"),
    "provisional_evidence": ref(V / "evidence.json"),
    "repair": "Actual installed validator requires approved/rejected; final receipt uses approved; prior provisional report retained"})
evidence = {"schema_version": 1, "actor": "/root/pressure_writer", "author": "/root/history_preservation", "decision": "accepted",
    "review_standard": "Current Source authority, exact ER1 assignment, preserved collaborative/hostile role templates and PyPA installed RECORD format",
    "scope": "33 frozen candidate members; 27 launcher and 3 RECORD application targets; own fresh native fixtures only",
    "manifest": ref(Q / "TRANSFER-MANIFEST.json"), "author_implement": ref(R / "implement.json"),
    "source_inventory": ref(V / "source-inventory-r1.json"), "tests": ref(V / "review-tests-r3.json"), "raw": ref(V / "review-tests-r3.txt"),
    "applications": applications, "RECORD_raw_field_span_checks": span_checks, "source_snapshot_before_after": snapshot,
    "verified_strengths": ["Exact 26 declarations plus standard pip3.12 alias and original source RECORD bindings",
        "Installed t64 AMD64 console stub and exact original entry-point body retained; current shebang and strict one-member ZIP proven",
        "Exactly 27 hash/size row changes across three RECORD files; all other raw bytes, names, row order, quoting and line endings preserved",
        "Actual staged pip/schema positive and negative outputs plus all callable targets qualify through observed Windows job custody",
        "Emission hook refuses unexpected, duplicate and nonbyte outputs; malformed/altered CSV and artifact bodies are rejected in bounded tests",
        "All failed parser, mislabeled identity, native diagnostic and finalizer attempts remain preserved and qualified",
        "Generated stubs/wrappers contribute zero new functional product LOC; hand-written builder remains preparation-tool code"],
    "confirmed_candidate_defects": [], "unsupported_claims": [], "missing_evidence": limitations,
    "risks": [{"classification": "PUBLISH_ONLY_WITH_CURRENT_BEFORE_HASH_AND_NATIVE_ID_RECHECK", "severity": "MATERIAL_AT_PUBLICATION",
              "reason": "Source drift between review and replacement must reopen acceptance; publish launchers and their corresponding RECORD changes together"}],
    "threat_model": "Accidental stale interpreter, mismatched module/entry point, modified PE/main/ZIP artifact, out-of-scope or malformed metadata changes and lost CLI custody",
    "techniques": "Exact-byte/native-ID reconciliation, independent CSV raw reconstruction and 54 span checks, in-memory negative artifact/emission/parser tests, retained-handle actual Windows CLI children",
    "cleanup": "Seven native invocations exited, jobs were observed empty and owners closed; fixtures and raw outputs retained under independent-review",
    "ambiguities": "Native old-launcher diagnostic text and OS directory stat-size variation cause remain unexposed; neither is attributed to installed metadata corruption",
    "required_remediation": "No additional candidate repair established; Root must recheck all 30 exact source targets before any reviewed publication",
    "optional_improvements": [], "reopening_conditions": ["Any candidate, installed source, generator/entry-point/metadata byte or native identity change",
        "Any live/unknown owned child, a changed destination or scope, or a request to qualify previously unexecuted Qt functions"],
    "limitations": limitations, "prior_failures": prior_failures, "product_completion": False, "active_application": False,
    "observed_at": datetime.now(timezone.utc).isoformat()}
write(V / "evidence-r3.json", evidence)
graph = json.loads((R / "er1-20261014/graph.json").read_text())["graph"]
receipt = {"schema_version": 1, "run_id": "er1-20261014", "node_id": "review", "executor_id": claim["executor_id"],
    "started_at": claim["claimed_at"], "finished_at": datetime.now(timezone.utc).isoformat(), "input_hash": claim["input_hash"],
    "changed_files": changed_files, "decision": "approved", "exit_status": 0,
    "result": {"evidence": ref(V / "evidence-r3.json"), "manifest": ref(Q / "TRANSFER-MANIFEST.json"),
        "tests": ref(V / "review-tests-r3.json"), "tests_run": 10, "native_cli_invocations": 7,
        "candidate_changed_files": [], "prior_failures": prior_failures, "limitations": limitations, "active_application": False, "product_completion": False},
    "commands": [{"command": str(E3 / "Scripts/python.exe") + " -B -X utf8 " + str(V / "inventory.py"), "exit_status": 0},
                 {"command": str(E3 / "Scripts/python.exe") + " -B -X utf8 " + str(V / "review_candidate.py"), "exit_status": 0},
                 {"command": "Python312 -B finish_review.py: current 30 source bindings, 33 member installed snapshot, exact raw IDs, 54 RECORD field spans, retained census/directory proof and full-keyword receipt validation", "exit_status": 0}],
    "validations": [{"name": value, "passed": True} for value in ("Ten independent checks, seven actual native invocations and all 27 callable imports; zero skips",
        "Exact 27 launcher and 3 RECORD bindings; source preimages and 54 raw-field spans match",
        "Original stub/body and standard current shebang generation verified; malformed artifact/emission/parser cases rejected",
        "All owned CLI exits and empty jobs observed; candidate and limited active source unchanged",
        "Recorded 3601 ordinary-file identities/bytes and 101 directory-only differences verified with explicit scope/resolution limits",
        "Actual installed snapshot equals review claim baseline for all 33 members; only independent evidence/fixtures written")]
}
kwargs = {"run_id": "er1-20261014", "node_id": "review", "executor_id": claim["executor_id"],
    "input_hash": claim["input_hash"], "claimed_at": claim["claimed_at"], "node": graph["nodes"]["review"]}
validate_receipt(receipt, **kwargs)
write(V / "review.json", receipt)
validate_receipt(load_receipt(V / "review.json"), **kwargs)
assert _snapshot_workspace(Q, Path("T:/")) == snapshot
print(json.dumps({"decision": "approved", "review_sha256": sha(V / "review.json"), "evidence_sha256": sha(V / "evidence-r3.json"),
    "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"), "candidate_unchanged": True, "source_application": False}))
