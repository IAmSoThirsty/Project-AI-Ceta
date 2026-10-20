"""Independently inspect completed actual-S raw IDs, source seals and custody."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

R = Path(__file__).resolve().parent
S = R.parents[3]
FULL = S / ".agents/runtime/rs2-20261014/active-application"
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
started = datetime.now(timezone.utc).isoformat()
full_path = FULL / "destination-full-r2.json"
raw_path = FULL / "destination-full-r2.txt"
preflight_path = FULL / "destination-full-r2-preflight.json"
assert full_path.is_file(), "Completed full-suite result is not yet available"
full = read(full_path)
preflight = read(preflight_path)
discovery = read(R / "actual-suite-discovery.json")
applied = read(R / "applied-source-audit.json")
raw = raw_path.read_text(encoding="utf-8")
raw_ids = re.findall(r"^test[^\s]* \(([A-Za-z0-9_.]+)\)", raw, re.MULTILINE)
expected = discovery["discovered_ids"]
checks = {}
def check(name, value):
    checks[name] = bool(value)

check("exact1158_ids_in_fresh_discovery_preflight_execution_and_raw", len(raw_ids) == len(set(raw_ids)) == len(expected) == 1158
      and raw_ids == expected == full["expected_ids"] == full["executed_ids"] == preflight["expected_ids"])
check("raw_output_hash_exact", sha(raw_path) == full["output_sha256"])
check("actual_source_and_interpreter", full["root"] == str(S) and full["python_executable"] == preflight["python_executable"])
check("zero_failures_errors_skips_and_exit0", full["failures"] == full["errors"] == full["skips"] == full["exit_status"] == 0
      and full["failed_ids"] == [] and full["skip_details"] == [])
check("full_tests_run_matches_declared_and_raw_summary", full["tests_run"] == 1158 and re.search(r"^Ran 1158 tests in [0-9.]+s$", raw, re.MULTILINE)
      and raw.rstrip().endswith("OK"))
expected_payloads = applied["before_current_hashes"]
current = {relative: sha(S / relative) for relative in expected_payloads}
check("all235_current_source_hashes_match_frozen_cut_and_full_before_after", len(current) == 235
      and current == expected_payloads == full["expected_payload_hashes"] == full["before_hashes"] == full["after_hashes"]
      and full["source_unchanged"] is True)
check("root_full_preflight_exact_from_independent_discovery", sha(preflight_path) == discovery["preflight_sha256"])
check("journal_and_manifests_unchanged", sha(R.parent / "active-application/APPLICATION.json") == applied["application_journal_sha256"]
      and sha(S / ".agents/app3-20261014/TRANSFER-MANIFEST.json") == applied["manifest_sha256"])
native_stdout = FULL / "destination-native-census-r2.stdout"
native_stderr = FULL / "destination-native-census-r2.stderr"
native = read(native_stdout)
check("actual_root_native_census_clear_and_raw_matches_result", native == full["native_census"]["result"]
      and native["clear"] is True and native["children"] == [] and full["native_census"]["exit_status"] == 0
      and native_stderr.read_bytes() == b"")
check("all72_full_run_imports_actual_S_and_hashes_current", len(full["imports"]) == 72
      and all(Path(item["actual_path"]).resolve().is_relative_to(S / "src") and sha(Path(item["actual_path"])) == item["sha256"]
              for item in full["imports"]))
check("all_dependency_modules_current_and_preflight_bound", full["dependencies"] == preflight["dependencies"]
      and all(sha(Path(item["actual_path"])) == item["module_file_sha256"] for item in full["dependencies"]))
required_ids = [
    "test_source_coverage.SourceCoverageTests.test_contract_core_has_no_infrastructure_or_other_domain_imports",
    "test_task_meaning_view.TaskMeaningViewTests.test_exec_exception_retains_exact_rejected_native_document_after_deferred_delete",
    "test_process_diagnostics.NativeProcessDiagnosticsTests.test_actual_owned_cpu_memory_io_collector_and_analyzer",
    "test_process_diagnostics.NativeProcessDiagnosticsTests.test_actual_delayed_lifetime_check_rejects_stale_cache_and_recovers",
    "test_process_diagnostics.NativeProcessDiagnosticsTests.test_actual_concurrent_collection_retains_native_order_and_analyzes",
]
check("original_two_failure_methods_and_actual_native_diagnostics_executed", all(item in raw_ids for item in required_ids))
result = {"schema_version": 1, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
          "source_root": str(S), "full_suite": str(full_path), "full_suite_sha256": sha(full_path),
          "full_raw": str(raw_path), "full_raw_sha256": sha(raw_path), "full_suite_tests_run": full["tests_run"],
          "raw_test_ids": raw_ids, "checks": checks, "failed_checks": [name for name, passed in checks.items() if not passed],
          "failures": full["failures"], "errors": full["errors"], "skips": full["skips"],
          "failed_ids": full["failed_ids"], "required_cases": required_ids, "expected_payload_hashes": expected_payloads,
          "current_source_hashes": current, "native_census": native,
          "native_census_stdout_sha256": sha(native_stdout), "native_census_stderr_sha256": sha(native_stderr),
          "dependency_metadata": full["dependencies"], "decision": "approved" if all(checks.values()) else "rejected",
          "exit_status": 0 if all(checks.values()) else 1}
with (R / "full-result-audit.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: result[key] for key in ("decision", "full_suite_tests_run", "failures", "errors", "skips", "failed_checks", "exit_status")}))
raise SystemExit(result["exit_status"])
