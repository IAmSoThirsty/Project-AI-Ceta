"""Read-only exact-join, actual-receipt and native publication source audit."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

R = Path(__file__).resolve().parent
S = R.parents[3]
Q = S / ".agents/app3-20261014"
RUN = "app3-20261014"
RUNTIME = R.parent
MECHANISMS = S / ".agents/runtime/rs2-20261014"
PUBLICATION = MECHANISMS / "apply_joined_source.py"
PREPARE = MECHANISMS / "prepare_joined_application.py"
EXPECTED_SCRIPT = "4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77"
EXPECTED_RS3_MANIFEST = "864d9ab2842af8544ab69d44881ddc22a6f2ff3ec494aa3584c472ab3720e825"
EXPECTED_RS3_REVIEW = "c5f13e277cd8201dbf98ef82d4d928109cb8cdba9c46bd7017546d06398f1590"
EXPECTED_BASE = "cf76d204965d54eea8af3c226aa5b02d5b37cca4bf642e4d7fbb53fe5c3c1cce"
ALLOWED = frozenset({"tests/contract/test_source_coverage.py", "tests/contract/test_task_meaning_view.py",
                     "src/ceta/contracts/resource_management.py", "src/ceta/supervisor/windows_jobs.py",
                     "src/ceta/resource/diagnostics.py", "tests/contract/test_process_diagnostics.py",
                     "contracts/PROCESS_DIAGNOSTICS_V1.md"})
CREATE = frozenset({"tests/contract/test_process_diagnostics.py", "contracts/PROCESS_DIAGNOSTICS_V1.md"})
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
sys.path.insert(0, r"T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce")
from taar.orchestration_receipts import sha256_json
from taar.orchestration_runtime import _snapshot_workspace, _changed_files

spec = importlib.util.spec_from_file_location("app3_review_audit_io", S / ".agents/pr4-20261014/preserve_ceta_complete.py")
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)
assert sha(Path(spec.origin)) == "2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618"

def bytes_exact(path):
    with fs.open_source(fs.safe_components(path), exclusive=True) as stream:
        return stream.read()

def hash_exact(path):
    return hashlib.sha256(bytes_exact(path)).hexdigest()

def accepted_receipt(runtime, node):
    run = runtime.name
    state = read(runtime / run / "state.json")
    value = state["nodes"][node]
    assert value["state"] == "SUCCEEDED" and value["validation_passed"] is True
    stored_path = runtime / run / value["receipt_ref"]
    stored = read(stored_path)
    stored_hash = stored.pop("receipt_hash")
    assert sha256_json(stored) == stored_hash == value["receipt_hash"]
    raw_path = runtime / ("independent-review/review.json" if node == "review" else node + ".json")
    raw = read(raw_path)
    assert raw == stored, (run, node, "accepted and selected receipt content differs")
    assert raw["exit_status"] == 0
    if node == "review":
        assert raw["decision"] == "approved" and raw["changed_files"] == []
    return {"node": node, "state": value["state"], "executor": value["executor_id"],
            "receipt": str(raw_path), "receipt_sha256": sha(raw_path),
            "stored_receipt": str(stored_path), "normalized_receipt_hash": stored_hash,
            "state_sequence": state["sequence"], "value": raw}

started = now()
claim = read(RUNTIME / RUN / "claims.json")["review"]
assert claim["executor_id"] == "/root/pressure_review" and claim["workspace"] == str(Q)
assert read(RUNTIME / RUN / "state.json")["nodes"]["review"]["state"] == "RUNNING"
managed_before = _snapshot_workspace(Q, Path("T:/"))
assert _changed_files(claim["baseline_snapshot"], managed_before) == []
assert sha(PUBLICATION) == EXPECTED_SCRIPT
pub_text = bytes_exact(PUBLICATION).decode("utf-8")
pub_ast = ast.parse(pub_text)
pub_main = next(node for node in pub_ast.body if isinstance(node, ast.FunctionDef) and node.name == "main")
binding_line = next(node.lineno for node in ast.walk(pub_main) if isinstance(node, ast.Assert)
                    and "publication_script_sha256" in ast.unparse(node.test))
mutation_lines = [node.lineno for node in ast.walk(pub_main) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr in {"mkdir", "open", "replace"}]
assert binding_line < min(mutation_lines)
replace_call = next(node for node in ast.walk(pub_ast) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and node.func.attr == "ReplaceFileW")
assert len(replace_call.args) == 6 and ast.literal_eval(replace_call.args[3]) == 0
assert "backup" in ast.unparse(replace_call.args[2])
assert ast.literal_eval(replace_call.args[4]) is None and ast.literal_eval(replace_call.args[5]) is None
assert "PARTIAL_APPLICATION_PRESERVED_REQUIRES_FRESH_RECONCILIATION" in pub_text
assert "same-principal/privileged hostile ancestor replacement remains unqualified" in pub_text

manifest_path = Q / "TRANSFER-MANIFEST.json"
manifest = read(manifest_path)
assert manifest["source_root"] == str(S) and manifest["candidate_root"] == str(Q)
assert manifest["code_changes_authored_by_coordinator"] == 0
assert frozenset(manifest["application_paths"]) == ALLOWED and len(manifest["application_paths"]) == 7
entries = {item["relative_path"]: item for item in manifest["payloads"]}
assert len(entries) == len(manifest["payloads"]) == 235
bindings = {item["run_id"]: item for item in manifest["bindings"]}
assert set(bindings) == {"rs2-20261014", "rs3-20261014", "rd2-20261014"}
base_path = S / ".agents/rs2-20261014/TRANSFER-MANIFEST.json"
assert sha(base_path) == EXPECTED_BASE == bindings["rs2-20261014"]["manifest_sha256"]
base = read(base_path)
base_payloads = {item["active_target_relative_to_repository"]: item for item in base["payloads"]
                 if item["application_action"] != "HISTORICAL_ASSEMBLY_READBACK_EXCLUDED_FROM_APPLY"}
assert len(base_payloads) == 231
assert set(base_payloads) <= set(entries)
assert read(S / ".agents/runtime/rs2-20261014/rs2-20261014/state.json")["nodes"]["integrate"]["state"] == "FAILED"
base_failure = S / ".agents/runtime/rs2-20261014/integrate.json"
assert sha(base_failure) == bindings["rs2-20261014"]["failure_receipt_sha256"] == "7f75b4d9621855d38a8da811198ae20a1aebcf412ab5af309623ab7d224693bb"

reviews = []
ownership = {}
for run in ("rs3-20261014", "rd2-20261014"):
    runtime = S / ".agents/runtime" / run
    accepted = accepted_receipt(runtime, "review")
    producer = accepted_receipt(runtime, "implement")
    producer_manifest = S / ".agents" / run / "TRANSFER-MANIFEST.json"
    assert sha(producer_manifest) == bindings[run]["manifest_sha256"] == accepted["value"]["result"]["manifest_sha256"]
    assert sha(Path(bindings[run]["review"])) == accepted["receipt_sha256"] == bindings[run]["review_sha256"]
    assert producer["value"]["result"]["manifest_sha256"] == sha(producer_manifest)
    if run == "rs3-20261014":
        assert sha(producer_manifest) == EXPECTED_RS3_MANIFEST
        assert accepted["receipt_sha256"] == EXPECTED_RS3_REVIEW
    changed = set(bindings[run]["changed_paths"])
    assert changed and changed <= ALLOWED
    for relative in changed:
        assert relative not in ownership, ("overlapping producer ownership", relative)
        ownership[relative] = run
    producer_entries = {item["active_target_relative_to_repository"]: item
                        for item in read(producer_manifest)["payloads"]
                        if item["application_action"] != "HISTORICAL_ASSEMBLY_READBACK_EXCLUDED_FROM_APPLY"}
    for relative in changed:
        item = producer_entries[relative]
        assert entries[relative]["candidate_sha256"] == item["candidate_sha256"]
        assert entries[relative]["active_before_sha256"] == item["active_before_sha256"]
        producer_file = S / ".agents" / run / item["relative_path"]
        assert hash_exact(producer_file) == item["candidate_sha256"]
        assert bytes_exact(Q / relative) == bytes_exact(producer_file)
        assert Path(entries[relative]["input_path"]) == producer_file
    reviews.append({"run_id": run, "manifest_sha256": sha(producer_manifest), "changed_paths": sorted(changed),
                    "review": {key: value for key, value in accepted.items() if key != "value"},
                    "implement": {key: value for key, value in producer.items() if key != "value"}})
assert set(ownership) == ALLOWED
assert {relative for relative, run in ownership.items() if run == "rs3-20261014"} == {
    "tests/contract/test_source_coverage.py", "tests/contract/test_task_meaning_view.py"}

audit = []
changes = []
for relative, item in sorted(entries.items()):
    fs.relative_name(relative)
    assert relative == item["active_target_relative_to_repository"]
    assert item["candidate_relative_to_repository"] == str((Q / relative).relative_to(S)).replace("\\", "/")
    candidate = bytes_exact(Q / relative)
    assert hashlib.sha256(candidate).hexdigest() == item["candidate_sha256"]
    source = fs.safe_components(S / relative, allow_missing=item["active_before_sha256"] is None)
    before = bytes_exact(source) if fs.exists(source) else None
    before_hash = hashlib.sha256(before).hexdigest() if before is not None else None
    assert before_hash == item["active_before_sha256"], ("active before-source drift", relative)
    if relative in ALLOWED:
        expected_action = "CREATE" if relative in CREATE else "EXTEND_PRESERVE_BEFORE_IMAGE"
        assert item["application_action"] == expected_action
        assert (before is None) == (relative in CREATE)
        before_lines = (before or b"").decode("utf-8").splitlines(keepends=True)
        candidate_lines = candidate.decode("utf-8").splitlines(keepends=True)
        matcher = difflib.SequenceMatcher(a=before_lines, b=candidate_lines, autojunk=False)
        opcodes = [{"action": action, "old_start_line": left + 1, "old_stop_exclusive_line": stop + 1,
                    "new_start_line": right + 1, "new_stop_exclusive_line": finish + 1,
                    "old_lines": before_lines[left:stop], "new_lines": candidate_lines[right:finish]}
                   for action, left, stop, right, finish in matcher.get_opcodes() if action != "equal"]
        assert opcodes, relative
        changes.append({"relative_path": relative, "owner": ownership[relative], "action": expected_action,
                        "before_sha256": before_hash, "candidate_sha256": item["candidate_sha256"], "line_changes": opcodes})
    else:
        assert item["application_action"] == "IDENTICAL_RETAINED"
        assert before == candidate
    if relative in base_payloads and relative not in ALLOWED:
        assert item["candidate_sha256"] == base_payloads[relative]["candidate_sha256"]
    facts = os.lstat(fs.io_path(Q / relative))
    assert not fs.reparse(facts)
    audit.append({"relative_path": relative, "action": item["application_action"], "candidate_sha256": item["candidate_sha256"],
                  "active_before_sha256": before_hash, "candidate_bytes": facts.st_size,
                  "candidate_device": facts.st_dev, "candidate_inode": facts.st_ino})

original_core = [item for item in base_payloads.values() if item["application_action"] == "DEPENDENCY_ONLY_EXCLUDED_FROM_APPLY"]
for item in original_core:
    relative = item["active_target_relative_to_repository"]
    if relative not in ALLOWED:
        assert entries[relative]["candidate_sha256"] == item["candidate_sha256"]
assert len([path for path in entries if path.startswith("src/ceta/") and path.endswith(".py")]) == 72
assert hash_exact(Q / "tools/verify_source_coverage.py") == hash_exact(S / "tools/verify_source_coverage.py")
assert not (RUNTIME / "active-application").exists()
managed_after = _snapshot_workspace(Q, Path("T:/"))
assert managed_before == managed_after
assert _changed_files(claim["baseline_snapshot"], managed_after) == []
git = subprocess.run(["git", "-C", str(S), "status", "--short", "--untracked-files=no"], capture_output=True, text=True)
assert git.returncode == 0
path_lengths = [{"relative_path": relative,
                "target_characters": len(str(S / relative)),
                "native_backup_characters": len(str(RUNTIME / "active-application/native-backups" / (relative + ".original")))}
               for relative in sorted(ALLOWED)]
assert max(item["native_backup_characters"] for item in path_lengths) == 177
record = {"schema_version": 1, "started_at": started, "finished_at": now(), "run_id": RUN,
          "source_root": str(S), "candidate_root": str(Q), "review_claim": {key: claim[key] for key in ("executor_id", "input_hash", "claimed_at", "workspace")},
          "manifest_sha256": sha(manifest_path), "publication_script_sha256": sha(PUBLICATION),
          "prepare_script_sha256": sha(PREPARE), "publication_script_self_binding_line": binding_line,
          "native_replace_flags": 0, "first_output_mutation_line": min(mutation_lines),
          "actual_accepted_producer_reviews": reviews, "payload_count": len(entries), "applied_path_count": 7,
          "create_count": 2, "extend_count": 5, "identical_retained_count": len(entries) - 7,
          "product_module_count": 72, "managed_claim_artifact_count": len(managed_after),
          "managed_claim_unchanged": True, "payloads": audit, "exact_seven_path_line_changes": changes,
          "actual_active_path_lengths": path_lengths, "tracked_dirty_state": git.stdout.splitlines(),
          "source_application": "Not yet started; exact active before states verified",
          "shared_administration": "Same Windows principal and host; sibling reviewer, exact same-repository copies; privileged/concurrent ancestor replacement excluded from qualified scope",
          "api_documents": ["https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew",
                            "https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw"],
          "exit_status": 0}
with (R / "joined-audit.json").open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: record[key] for key in ("payload_count", "applied_path_count", "create_count", "extend_count", "identical_retained_count", "product_module_count", "managed_claim_artifact_count", "managed_claim_unchanged", "manifest_sha256", "publication_script_sha256", "exit_status")}))
