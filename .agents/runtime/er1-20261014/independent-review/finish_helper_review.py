"""Freeze the separately authorized ER1 publication-helper review evidence."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json
import os

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/er1-20261014", F / ".agents/runtime/er1-20261014"
V = R / "independent-review"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
utc = lambda: datetime.now(timezone.utc).isoformat()
manifest_sha = "7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83"
helper_sha = "f25e7967d5cfba5e90819490ec0f2f19320b2d5ebc8df95e2a8d9020064b8cec"
old_sha = "33b0f64a38f7c02e51d9b495fcce791471b886d936331c47bc25c5a9855184dd"
second_sha = "806fc0b8a34a9d2bcddd0f27374ca23e6c99eec697c676aa25d4ec6b4de8de9b"
assert sha(Q / "TRANSFER-MANIFEST.json") == manifest_sha
assert sha(R / "apply_reviewed_environment.py") == helper_sha
assert sha(R / "apply_reviewed_environment_attempt_r1.py") == old_sha
assert sha(R / "apply_reviewed_environment_attempt_r2.py") == second_sha
assert sha(V / "review.json") == "8322051dbf2b0efac25a46ea2af47ce1fcab2cf62f42d41776a28e677a94e0b3"
test_path = V / "publication-helper-tests-f25e7967d5cf-r2.json"
assert sha(test_path) == "59a7d72295886f5bb6d0351073aa998db9e63fbd5d469453ed69447357c343cd"
tests = read(test_path)
assert tests["tests_run"] == 12 and tests["passed"] and tests["helper_source_unchanged"]
assert not tests["failures"] and not tests["errors"] and not tests["skips"]
assert not tests["helper_main_executed"] and not tests["active_E3_writes"]
assert tests["native_replacements_executed"] == 0
assert len(tests["current_source_and_candidate_bindings"]) == 30

def ref(path):
    return {"repository_relative_path": path.relative_to(F).as_posix(), "sha256": sha(path)}

def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())

first_findings = [
    {"id": "ER1-PH-F01", "classification": "FIXED_IN_REVISED_HELPER",
     "evidence_kind": "SOURCE_GUARD_ABSENCE; NO_LIVE_PUBLICATION_REPRODUCTION",
     "source": ref(R / "apply_reviewed_environment_attempt_r1.py"),
     "observed": "Only initial native path identity was checked. Logical original preservation and native replacement backup retention lacked expected original handle identity checks.",
     "required_repair": "Check expected original descriptor identity during preservation, recheck full path identity before replacement, and verify backup bytes plus descriptor identity after replacement."},
    {"id": "ER1-PH-F02", "classification": "FIXED_IN_REVISED_HELPER",
     "evidence_kind": "SOURCE_GUARD_ABSENCE; NO_LIVE_PUBLICATION_REPRODUCTION",
     "source": ref(R / "apply_reviewed_environment_attempt_r1.py"),
     "observed": "The approval decision was read without its frozen receipt hash or approved result-manifest binding, and the manifest self-review reference was not validated.",
     "required_repair": "Pin the existing distinct review receipt, require its manifest binding, and validate the frozen manifest's exact author self-review reference."},
    {"id": "ER1-PH-F03", "classification": "FIXED_IN_REVISED_HELPER",
     "evidence_kind": "EXACT_EXCEPTION_HANDLER_FRAGMENT_REPRODUCTION; NO_LIVE_PUBLICATION",
     "source": ref(R / "apply_reviewed_environment_attempt_r1.py"),
     "observed": "A diagnostic save exception replaced the primary publication exception as the propagated failure.",
     "reproduction_id": "__main__.PublicationHelperReview.test_first_helper_journal_masking_is_retained_as_rejected_evidence",
     "required_repair": "Guard the diagnostic save, retain a note when it fails, and bare-raise the original exception."}]
first = {"schema_version": 1, "reviewer": "/root/pressure_writer", "recorded_at": utc(),
         "decision": "rejected", "exit_status": 1, "manifest_sha256": manifest_sha,
         "publication_script_sha256": old_sha, "findings": first_findings,
         "superseded_by_publication_script_sha256": helper_sha,
         "live_helper_execution": False, "active_environment_writes": False,
         "exact_isolated_fragment_evidence": ref(test_path)}
save(V / "publication-helper-review-r1.json", first)
fourth = {"id": "ER1-PH-F04", "classification": "FIXED_IN_REVISED_HELPER",
          "evidence_kind": "SOURCE_GUARD_ABSENCE; NO_LIVE_PUBLICATION_REPRODUCTION",
          "source": ref(R / "apply_reviewed_environment_attempt_r2.py"),
          "observed": "The whole-environment precondition read E3-after-tests.json without validating the frozen manifest to conservation proof to comparison-snapshot reference chain.",
          "required_repair": "Validate both exact frozen references and scope facts before live observation/comparison; journal their hashes."}
second = {"schema_version": 1, "reviewer": "/root/pressure_writer", "recorded_at": utc(),
          "decision": "rejected", "exit_status": 1, "manifest_sha256": manifest_sha,
          "publication_script_sha256": second_sha, "findings": [fourth],
          "earlier_three_findings_closed": True, "superseded_by_publication_script_sha256": helper_sha,
          "live_helper_execution": False, "active_environment_writes": False}
save(V / "publication-helper-review-r2.json", second)
manifest = read(Q / "TRANSFER-MANIFEST.json")
pinned = [(R / "er1_support.py", "38721b1fa0c112f568a4e957b5ae3a1ecd747645c83ec5882228947805a198d5"),
          (F / ".agents/runtime/rs2-20261014/apply_joined_source.py", "4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77"),
          (F / ".agents/pr4-20261014/preserve_ceta_complete.py", "2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618")]
for path, expected in pinned:
    assert sha(path) == expected
conservation_path = F / manifest["source_conservation"]["repository_relative_path"]
assert sha(conservation_path) == manifest["source_conservation"]["sha256"]
historical_path = F / read(conservation_path)["after"]["repository_relative_path"]
assert sha(historical_path) == read(conservation_path)["after"]["sha256"]
for row in manifest["payloads"]:
    assert sha(Path(row["source_path"])) == row["source_sha256"]
    assert sha(Q / row["candidate_relative_path"]) == row["candidate_sha256"]
claim = read(V / "claim.json")["response"]["claim"]
assert len(claim["baseline_snapshot"]) == 33
for key, expected in claim["baseline_snapshot"].items():
    relative = Path(key).relative_to(Q) if Path(key).is_absolute() else Path(key)
    # The installed snapshot keys are T:/-relative rather than Q-relative.
    if not (Q / relative).is_file():
        relative = Path("T:/") / key
        relative = relative.relative_to(Q)
    actual = sha(Q / relative)
    expected_sha = expected["sha256"] if isinstance(expected, dict) else expected
    assert actual == expected_sha, str(relative)
report = {"schema_version": 1, "reviewer": "/root/pressure_writer", "reviewed_at": utc(),
          "decision": "approved", "exit_status": 0, "manifest_sha256": manifest_sha,
          "publication_script_sha256": helper_sha, "candidate_review": ref(V / "review.json"),
          "author_self_review": manifest["self_review"], "tests": ref(test_path),
          "raw_tests": ref(V / "publication-helper-tests-f25e7967d5cf-r2.txt"),
          "test_runner": ref(V / "review_publication_helper.py"),
          "dependencies": [ref(path) for path, _ in pinned],
          "source_conservation": ref(conservation_path), "comparison_snapshot": ref(historical_path),
          "prior_rejected_helpers": [ref(V / "publication-helper-review-r1.json"), ref(V / "publication-helper-review-r2.json")],
          "closed_findings": [finding["id"] for finding in first_findings] + [fourth["id"]],
          "verified": [
              "Exact thirty allowed E3 destinations and candidate mappings; current source hashes and native stat identities remain frozen before application",
              "Pinned distinct candidate review receipt, approved result-manifest binding, author self-review, installed reader/primitive and P4 dependencies",
              "Expected original handle identity checked during preservation; full path identity checked immediately before controlled native replacement",
              "Native backup hash and original device/inode/mode/size/mtime verification precede each completed event",
              "Exclusive new staging/original/journal paths and per-file fsync events; failure journal cannot replace primary exception in tested handler fragments",
              "Exact frozen conservation reference chain before comparison, ordinary 3601-file precondition and all 3571 unrelated ordinary-file postconditions present",
              "All 33 frozen candidate members match actual review claim baseline; no candidate changes"],
          "tests_run": 12, "failures": 0, "errors": 0, "skips": 0,
          "execution_scope": tests["execution_scope"], "helper_main_executed": False,
          "native_replacements_executed": 0, "active_E3_writes": False,
          "separate_review_authority": "Root expressly authorized a bound publication-helper review after the distinct candidate review; this report is not another TAAR node transition",
          "limits": [
              "Only the exact pinned helper and frozen candidate qualify; change to either reopens review",
              "Actual E3 publication and destination verification remain unexecuted in this review and belong to Root under a fresh exclusive integrate claim",
              "Twelve helper tests execute isolated guard/handler/save fragments; native ReplaceFileW execution was not performed by this reviewer",
              "Thirty replacements are individually native; group atomicity is not provided; any interruption requires reconciliation of every target, stage and original",
              "Controlled coordinator-owned paths qualify; same-principal privileged hostile ancestor replacement and uninterrupted custody remain outside established evidence",
              "This helper's conservation assertions cover ordinary file rows; directory stat sizes and OS-internal metadata equality are not claimed",
              "Live fresh review observations cover the thirty destinations; full 3601-file evidence is pinned recorded comparison until the helper performs its own live censuses"]}
assert sha(R / "apply_reviewed_environment.py") == helper_sha
save(V / "publication-helper-review.json", report)
print(json.dumps({"review": ref(V / "publication-helper-review.json"), "decision": "approved",
                  "publication_script_sha256": helper_sha, "tests_run": 12,
                  "active_E3_writes": False}), flush=True)
