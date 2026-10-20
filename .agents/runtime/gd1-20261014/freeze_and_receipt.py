"""Freeze GD1's exact source/test/doc cut with actual installed author evidence."""
import ast
from collections import Counter
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/gd1-20261014", F / ".agents/runtime/gd1-20261014"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
utc = lambda: datetime.now(timezone.utc).isoformat()
def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
def ref(path):
    return {"repository_relative_path": path.relative_to(F).as_posix(), "sha256": sha(path)}

claim = read(R / "gd1-20261014/claims.json")["implement"]
graph = read(R / "gd1-20261014/graph.json")["graph"]
assert claim["executor_id"] == "/root/pressure_writer" and claim["workspace"] == str(Q)
inputs = read(R / "input-copy.json")["payloads"]
before = {row["relative_path"]: row["sha256"] for row in inputs}
assert len(before) == 279
permitted = {"src/ceta/resource/diagnostics.py", "tests/contract/test_process_observation_timing.py", "contracts/PROCESS_DIAGNOSTICS_V1.md"}
new_paths = permitted - set(before)
assert new_paths == {"tests/contract/test_process_observation_timing.py"}
for relative, expected in before.items():
    assert sha(F / relative) == sha(R / "before-images" / relative) == expected, relative
    if relative not in permitted:
        assert sha(Q / relative) == expected, relative
assert not (F / next(iter(new_paths))).exists()
final = read(R / "final-connected-r3.json")
assert final["successful"] and final["tests_run"] == 314
assert final["failures"] == final["errors"] == final["skipped"] == 0
assert final["source_before_sha256"] == final["source_after_sha256"]
assert all(sha(Q / path) == value for path, value in final["source_after_sha256"].items())
ids = [row["id"] for row in final["cases"]]
assert len(set(ids)) == len(ids) == 314 and all(row["status"] == "PASS" for row in final["cases"])
raw_ids = re.findall(r"^test_[^\n]+\(([^)]+)\) \.\.\. ok\s*$", (R / "final-connected-r3.txt").read_text(), re.M)
assert set(raw_ids) == set(ids) and len(raw_ids) == 314
counts = dict(Counter(name.split(".")[0] for name in ids))
assert counts == {"test_process_observation_timing": 32, "test_process_diagnostics": 47,
                  "test_resource_management": 95, "test_hardware_observation": 52,
                  "test_workload_admission": 71, "test_temporal": 14, "test_source_coverage": 3}
assert all(Path(path).is_relative_to(Q / "src") for path in final["imports"].values())
baseline, closure = read(R / "baseline-r3.json"), read(R / "final-baseline-closure-r2.json")
assert (baseline["tests_run"], baseline["failures"], baseline["errors"]) == (1, 1, 0)
assert baseline["source_before_sha256"] == before["src/ceta/resource/diagnostics.py"]
assert closure["passed"] and closure["failures"] == closure["errors"] == closure["skips"] == 0
assert closure["source_after_sha256"] == sha(Q / "src/ceta/resource/diagnostics.py")
trials = [row for row in closure["native_observations"] if "attempt" in row]
assert len(trials) == 8 and all(not row["memory_measured"] and row["physical_elapsed_ns"] > row["configured_window_ns"] for row in trials)
assert any(row["public_clock_delta_ns"] == 0 for row in trials)
assert len([name for name in ids if name.startswith("test_process_observation_timing.Native")]) == 6
write(R / "native-observations.json", {"source": ref(Q / "src/ceta/resource/diagnostics.py"),
    "clock_info": final["clock_info"], "tests": final["native_observations"],
    "reproduced_baseline": ref(R / "baseline-r3.json"), "unchanged_oracle_closure": ref(R / "final-baseline-closure-r2.json"),
    "limits": ["Actual retained Windows handles plus declared scheduling delays; deterministic clocks are separate test-domain fixtures",
               "Native late returns are rejected; synchronous calls are not preempted"]})

def meaningful(text):
    docs = set()
    for node in ast.walk(ast.parse(text)):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            docs.update(range(body[0].lineno, body[0].end_lineno + 1))
    return [line for index, line in enumerate(text.splitlines(), 1) if line.strip() and not line.lstrip().startswith("#") and index not in docs]
def delta(left, right):
    added = removed = 0
    for tag, i, j, k, l in difflib.SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
        if tag != "equal":
            added += l - k
            removed += j - i
    return {"added": added, "removed": removed, "net": added - removed}

(R / "diffs").mkdir(exist_ok=False)
payloads = []
for relative in sorted(set(before) | new_paths):
    path = Q / relative
    old = (R / "before-images" / relative).read_bytes() if relative in before else b""
    current = path.read_bytes()
    changed = old != current
    assert not changed or relative in permitted, relative
    row = {"relative_path": relative, "active_target_relative_to_repository": relative,
           "action": ("EXTEND" if relative in before else "CREATE") if changed else "REUSE",
           "kind": "functional_source" if relative.startswith("src/") else "test_source" if relative.startswith("tests/") and relative.endswith(".py") else "specification_or_tool_dependency",
           "active_before_sha256": before.get(relative), "candidate_sha256": sha(path), "bytes": len(current),
           "before_image": (R / "before-images" / relative).relative_to(F).as_posix() if relative in before else None}
    if changed:
        left, right = old.decode("utf-8-sig"), current.decode("utf-8-sig")
        diff = R / "diffs" / (relative.replace("/", "__") + ".diff")
        with diff.open("x", encoding="utf-8") as stream:
            stream.write("".join(difflib.unified_diff(left.splitlines(keepends=True), right.splitlines(keepends=True), fromfile="active-before/" + relative, tofile="GD1/" + relative)))
        row["diff"] = ref(diff)
        row["physical_LOC"] = delta(left.splitlines(), right.splitlines())
        row["meaningful_LOC"] = delta(meaningful(left), meaningful(right)) if relative.endswith(".py") else row["physical_LOC"]
        if relative.endswith(".py"):
            compile(right, str(path), "exec")
    payloads.append(row)
changed = [row for row in payloads if row["action"] != "REUSE"]
assert len(payloads) == 280 and {row["relative_path"] for row in changed} == permitted
source_fixture = F / ".agents/fixtures/windows-jobs-dd79a0fbc97549e786f288fb88fa31f0/primary.json"
scope_breach = {"classification": "HISTORICAL_GENERATED_FIXTURE_SCOPE_BREACH_PRESERVED; LATER_SCOPE_CORRECTION_FIXED",
    "metadata": ref(source_fixture), "own_lifetime_metadata": read(source_fixture),
    "initial_runner": ref(R / "baseline_probe_attempt_r1.py"), "initial_error": ref(R / "baseline-r1.json"),
    "exact_event": "Initial inherited Windows fixture helper used F/.agents/fixtures before its ROOT was rebound to R. All later baseline fixtures use R; candidate test fixtures use Q.",
    "cleanup_evidence": "Initial unittest execution has only the tuple-unpack error; inherited tearDown executed its owned wait/empty-job/close checks without another error. Root separately reported a fresh read-only ProcessId 18684 census absent.",
    "source_conservation_scope": "This generated artifact is outside Q/R and outside all 279 source payload conservation rows; it is preserved separately.",
    "removal_or_process_mutation": False}
write(R / "baseline-preparation-scope.json", scope_breach)
prior = [
    {"classification": "CONFIRMED_NATIVE_PRECISION_DEFECT_FIXED_IN_CANDIDATE", "failed": ref(R / "baseline-r3.json"), "raw": ref(R / "baseline-r3.txt"),
     "closure": ref(R / "final-baseline-closure-r2.json"), "issue": "6.1914 ms check admitted memory measurement under a 5 ms bound while public tick delta was zero"},
    {"classification": "PREPARATION_TUPLE_ERROR_AND_SCOPE_BREACH_PRESERVED", "failed": ref(R / "baseline-r1.json"), "raw": ref(R / "baseline-r1.txt"), "scope": ref(R / "baseline-preparation-scope.json")},
    {"classification": "SUPERSEDED_DENIAL_CACHE_ORACLE; PASS_DOES_NOT_CLOSE_DEFECT", "original": ref(R / "baseline-r2.json"), "raw": ref(R / "baseline-r2.txt"), "original_runner": ref(R / "baseline_probe_attempt_r2.py"),
     "repair": "Each native precision trial constructs a fresh sampler; a preceding unavailable cache cannot satisfy the next oracle"},
    {"classification": "FOCUSED_CODE_COMPATIBILITY_AND_NEW_TEST_CALL_ERRORS_CORRECTED", "failed": ref(R / "focused-r1.json"), "raw": ref(R / "focused-r1.txt"),
     "source_attempt": ref(R / "attempts/r1/diagnostics.py"), "test_attempt": ref(R / "attempts/r1/test_process_observation_timing.py"),
     "issues": ["Normalized rollback output changed the existing unavailable-cache recovery boundary; actual observation timestamps now remain unchanged while high-water persists", "Two new recorder.recent calls omitted the required scope_digest"], "closure": ref(R / "final-connected-r3.json")},
    {"classification": "INCORRECT_TEST_SELECTOR_CORRECTED; NO_SOURCE_FAILURE", "failed": ref(R / "connected-r1.json"), "raw": ref(R / "connected-r1.txt"),
     "issue": "Nonexistent test_resource_management_contract_is_pure_leaf; actual three leaf guard methods read and executed", "closure": ref(R / "final-connected-r3.json")},
    {"classification": "REUSED_RUNNER_LIMIT_TEXT_CORRECTED_WITH_FRESH_FINAL_EVIDENCE", "original_runner": ref(R / "run_tests_attempt_r1.py"),
     "issue": "Old reservation-only wording did not describe GD1's actual retained Windows process owner path", "closure": ref(R / "final-connected-r3.json")}]

spec = F / ".agents/cp1-20261014/independent-recovery/working-tree/20-RESOURCE-MANAGEMENT/20.05-OPERATIONAL-DIAGNOSTICS"
coverage = []
keywords = {1: ("bounds", "retention", "analyzer", "workload", "recorder"), 2: ("secret", "project", "redact", "privacy", "unqualified", "historical"),
            3: ("invalid", "typed", "malformed", "bounds", "wrong_types"), 4: ("stale", "future", "identity", "rollback", "epoch", "generation"),
            6: ("cancel", "interrupt", "slow", "occupancy", "window", "quantization", "resolution"),
            7: ("concurrent", "duplicate", "cache", "sequence"), 8: ("recover", "baseline", "rollback", "interruption")}
for unit, name in (("01", "resource-telemetry-recorder"), ("02", "performance-diagnostics-engine")):
    source = spec / (name + ".file.README.md")
    rows = re.findall(r"\| (AT-CETA-20\.05\." + unit + r"-[0-9]{2}) \| ([^|]+) \| ([^\n]+) \|", source.read_text())
    assert len(rows) == 10
    for acceptance_id, case, expected in rows:
        number = int(acceptance_id[-2:])
        supporting = [name for name in ids if name.startswith(("test_process_observation_timing.", "test_process_diagnostics.", "test_resource_management.")) and any(word in name for word in keywords.get(number, ()))]
        state = "BOUNDED_LOCAL_CODE_AND_NATIVE_PORTION_SELF_TESTED; FULL_ACCEPTANCE_OPEN"
        limitations = ["Canonical evidence/publication/principal scope and complete task/environment authenticity remain open"]
        if number == 5:
            supporting = []
            state = "BLOCKED_CANONICAL_PRINCIPAL_INTEGRATION"
            limitations = ["Unauthorized-principal isolation is not qualified by in-process role names or privacy projection"]
        elif number == 8:
            limitations.append("Recovery is process-local baseline/cache reconstruction; no durable owner cursor or restart authority claim")
        elif number == 9:
            supporting = [name for name in ids if name.startswith("test_process_observation_timing.Native") or name.startswith("test_process_diagnostics.Native")]
            state = "REAL_LOCAL_WINDOWS_PRODUCER_RECORDER_ANALYZER_PATH_SELF_TESTED; CANONICAL_FULL_INTEGRATION_OPEN"
        elif number == 10:
            supporting = []
            state = "AWAITING_DISTINCT_SOURCE_BOUND_REVIEW"
            limitations = ["Author evidence and self-review cannot satisfy independent acceptance"]
        if unit == "02":
            limitations += ["Workload latency/queueing, independent before/after qualification and causal diagnosis remain separate owner integration obligations"]
        coverage.append({"acceptance_id": acceptance_id, "source": ref(source), "original_case": case.strip(), "original_expected": expected.strip(),
                         "mapped_source": "src/ceta/resource/diagnostics.py", "writer": "/root/pressure_writer", "source_publication_owner": "/root",
                         "author_test_ids": supporting, "state": state, "remaining": limitations})
assert len(coverage) == len({row["acceptance_id"] for row in coverage}) == 20
write(R / "acceptance-coverage.json", {"source": ref(Q / "src/ceta/resource/diagnostics.py"), "cases": coverage,
    "original_B_case_limit": "Bounded developer/native regression is not original B-case or installed/full product acceptance", "self_test_only": True})
self_review = {"author": "/root/pressure_writer", "reviewed_at": utc(), "independent": False,
    "source": ref(Q / "src/ceta/resource/diagnostics.py"), "tests": ref(R / "final-connected-r3.json"),
    "inspected": ["Complete 20.05.01/20.05.02 specifications and common timing/verification contracts", "Actual native owner, typed process port/counters and every sampler/collector/analyzer call site",
                  "Source and unified line diffs, public signature compatibility, unchanged original tests and all 277 reused payload hashes", "Clock/cache/CPU state transitions under lock, failed sampling interruption and recorder retry boundaries"],
    "public_interface_changes": [], "additional_canonical_owners": [],
    "clock_provenance": "Same-project qualified hardware.py _ObservationClock elapsed/high-water algorithm adapted narrowly in the existing process sampler; no copied library or replacement owner",
    "native_timing_limits": ["Observed runtime GetTickCount64 resolution 15.625 ms and QPC resolution 100 ns", "Native mean CPU rate is cumulative counter delta over precise accepted completion intervals with bounded counter-read jitter",
                             "Clock-resolution margin is conservative observational qualification, not trusted clock authentication or native preemption"],
    "prior_failures": prior, "acceptance": ref(R / "acceptance-coverage.json"), "ready_for_distinct_review": True,
    "active_source_application": False, "whole_product_completion": False}
write(R / "self-review.json", self_review)
manifest = {"schema_version": 1, "job": "GD1 bounded process observation timing and existing telemetry/performance integration",
    "author": "/root/pressure_writer", "frozen_at": utc(), "source_root": str(F), "candidate_root": str(Q),
    "state": "FROZEN_AUTHOR_CANDIDATE_FOR_DISTINCT_REVIEW", "baseline_payloads": 279, "payloads": payloads,
    "application_paths": sorted(permitted), "self_review": ref(R / "self-review.json"), "acceptance": ref(R / "acceptance-coverage.json"),
    "input_source_cut": read(R / "plan.json")["result"]["baseline_full_receipt"], "input_specification_bindings": read(R / "plan.json")["result"]["bindings"],
    "tests": ref(R / "final-connected-r3.json"), "raw_tests": ref(R / "final-connected-r3.txt"), "native": ref(R / "native-observations.json"),
    "test_counts": counts, "prior_failures": prior, "reuse_new_LOC": 0,
    "count_method": "SequenceMatcher autojunk=False; meaningful Python excludes blank/comment/docstring lines; reused source/test bytes count zero new LOC",
    "excluded": ["Virtual environments", "Generated native fixture trees", "__pycache__", "Historical evidence/ledgers", "Unrelated repositories"],
    "pending": ["Distinct Collaborative Review", "Root current-source guarded publication", "Root integration/full regression", "All remaining canonical/physical/principal/original acceptance obligations"]}
write(Q / "TRANSFER-MANIFEST.json", manifest)
snapshot = _snapshot_workspace(Q, Path("T:/"))
observed_changes = _changed_files(claim["baseline_snapshot"], snapshot)
assert len(snapshot) == len(observed_changes) == 281
assert all(path.startswith("00-Active/Project-AI-CETA/.agents/gd1-20261014/") for path in observed_changes)
write(R / "source-freeze.json", {"candidate": str(Q), "manifest": ref(Q / "TRANSFER-MANIFEST.json"), "snapshot": snapshot,
    "source_before": before, "current_source_after": {path: sha(F / path) for path in before},
    "source_unchanged": all(sha(F / path) == value for path, value in before.items()), "unchanged_reused_payloads": 277,
    "generated_scope_breach": ref(R / "baseline-preparation-scope.json")})
receipt = {"schema_version": 1, "run_id": "gd1-20261014", "node_id": "implement", "executor_id": "/root/pressure_writer",
    "started_at": claim["claimed_at"], "finished_at": utc(), "input_hash": claim["input_hash"], "changed_files": observed_changes,
    "result": {"status": "BOUNDED_EXECUTABLE_CANDIDATE_READY_FOR_DISTINCT_REVIEW", "manifest": ref(Q / "TRANSFER-MANIFEST.json"),
        "self_review": ref(R / "self-review.json"), "source_freeze": ref(R / "source-freeze.json"), "tests": ref(R / "final-connected-r3.json"),
        "tests_run": 314, "failures": 0, "errors": 0, "skips": 0, "new_methods": 32, "new_native_methods": 6,
        "source_added": next(row["meaningful_LOC"]["added"] for row in changed if row["kind"] == "functional_source"),
        "source_removed": next(row["meaningful_LOC"]["removed"] for row in changed if row["kind"] == "functional_source"),
        "test_added": next(row["meaningful_LOC"]["added"] for row in changed if row["kind"] == "test_source"),
        "reuse_new_LOC": 0, "prior_failures": prior, "active_source_application": False, "independent_acceptance": False},
    "commands": [read(R / "final-connected-r3-command.json"),
        {"command": "Own E3 Python -B -X utf8 baseline_probe.py Q final-baseline-closure-r2; unchanged corrected native oracle", "exit_status": 0},
        {"command": "Own Python -B freeze_and_receipt.py: all 279 current Source inputs, 277 reuse payloads, exact raw IDs and actual installed snapshot/validator", "exit_status": 0}],
    "validations": [{"name": name, "passed": True} for name in ("actual314_zero_skip_connected_tests_and_raw_IDs", "six_new_actual_native_owned_process_cases_and_8_sub_tick_recovery_trials",
        "unchanged_public_interfaces_and_all_original47_95_52_71_14_3_regressions", "exact279_current_source_277_reuse_and_only_three_allowed_payload_deltas",
        "complete20_acceptance_IDs_with_explicit_remaining_obligations", "actual_claim_input_hash_and_installed_snapshot_changes_with_full_validator_keywords")], "exit_status": 0}
keywords = {"run_id": "gd1-20261014", "node_id": "implement", "executor_id": "/root/pressure_writer", "input_hash": claim["input_hash"], "claimed_at": claim["claimed_at"], "node": graph["nodes"]["implement"]}
validate_receipt(receipt, **keywords)
write(R / "implement.json", receipt)
validate_receipt(load_receipt(R / "implement.json"), **keywords)
write(R / "implement-validation.json", {"receipt": ref(R / "implement.json"), "validator": "installed taar.orchestration_receipts.validate_receipt", "full_keywords": keywords,
    "changed_files": observed_changes, "snapshot_members": len(snapshot), "passed": True})
print(json.dumps({"manifest": ref(Q / "TRANSFER-MANIFEST.json"), "receipt": ref(R / "implement.json"),
    "snapshot_members": len(snapshot), "tests_run": 314, "LOC": [{"path": row["relative_path"], "meaningful": row["meaningful_LOC"]} for row in changed]}), flush=True)
