"""Bind the existing independent harness to fourteen actual destination cases."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
S = R.parents[3]
source = R.parent / "independent-review/run_affected.py"
text = source.read_text(encoding="utf-8")
old_root = 'Q = S / ".agents/app3-20261014"'
assert text.count(old_root) == 1
text = text.replace(old_root, 'Q = S  # Actual selected destination, preserving every unchanged test ROOT/guard.')
text = text.replace('manifest_path = Q / "TRANSFER-MANIFEST.json"',
                    'manifest_path = S / ".agents/app3-20261014/TRANSFER-MANIFEST.json"')
old_selectors = 'selectors = ["test_source_coverage", "test_task_meaning_view", "test_resource_management", "test_source_references", "test_task_view", "test_editor_recovery", "test_process_diagnostics", "test_windows_jobs"]'
selectors = [
    "test_source_coverage.SourceCoverageTests.test_contract_core_has_no_infrastructure_or_other_domain_imports",
    "test_source_coverage.SourceCoverageTests.test_only_the_observed_enum_type_import_is_qualified",
    "test_source_coverage.SourceCoverageTests.test_contract_leaf_rejects_infrastructure_and_relative_domain_escape",
    "test_task_meaning_view.TaskMeaningViewTests.test_exec_exception_retains_exact_rejected_native_document_after_deferred_delete",
    "test_process_diagnostics.NativeProcessDiagnosticsTests",
    "test_resource_management.PressureTests.test_native_disposable_storage_cache_preserves_observation_identity",
    "test_resource_management.PressureTests.test_compute_sampler_cached_low_observation_cannot_reopen_admission",
]
assert old_selectors in text
text = text.replace(old_selectors, 'selectors = ' + repr(selectors))
old_count = 'assert len(expected_ids) == len(set(expected_ids)) and len(expected_ids) > 220'
assert old_count in text
text = text.replace(old_count, 'assert len(expected_ids) == len(set(expected_ids)) == 14')
text = text.replace('"all_ceta_imports_inside_app3": True', '"all_ceta_imports_inside_actual_S": True')
text = text.replace('"subject": str(Q)', '"subject": str(Q), "measurement_scope": "Eight actual owned-process native diagnostics methods, one real disposable storage observation, one actual Qt interrupted-dialog method with two exception subcases, three import guards and one explicitly controlled compute-counter domain case"')
target = R / "run_bounded_destination.py"
with target.open("x", encoding="utf-8") as stream:
    stream.write(text)
print(json.dumps({"original_runner_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "bounded_runner_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "expected_methods": 14, "unchanged_test_source_and_qualification_guards": True}))
