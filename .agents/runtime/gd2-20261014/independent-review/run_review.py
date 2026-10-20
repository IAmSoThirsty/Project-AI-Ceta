"""Independent execution of the exact frozen cohort in reviewer-owned fixtures."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import time
import unittest

V = Path(__file__).resolve().parent
R, F = V.parent, V.parents[3]
Q = F / ".agents/gd2-20261014"
E3 = F / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
now = lambda: datetime.now(timezone.utc).isoformat()
stem = sys.argv[2] if sys.argv[1] == "worker" else sys.argv[1]
if sys.argv[1] != "worker":
    command = [str(E3), "-B", "-X", "utf8", str(Path(__file__)), "worker", stem]
    temporary = V / (stem + "-temporary")
    temporary.mkdir(exist_ok=False)
    started = now()
    with (V / (stem + ".txt")).open("x", encoding="utf-8") as raw:
        result = subprocess.run(command, cwd=r"T:\00-Active", stdout=raw, stderr=subprocess.STDOUT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TEMP=str(temporary), TMP=str(temporary)))
    (V / (stem + "-command.json")).open("x", encoding="utf-8").write(json.dumps({"command": command,
        "cwd": r"T:\00-Active", "started_at": started, "finished_at": now(), "exit_status": result.returncode,
        "raw_log_sha256": sha(V / (stem + ".txt"))}, indent=2) + "\n")
    print((V / (stem + ".txt")).read_text(encoding="utf-8")[-2000:], flush=True)
    sys.exit(result.returncode)

assert Path(sys.executable) == E3
sys.dont_write_bytecode = True
sys.path[:0] = [str(Q / "src"), str(Q / "tests/contract"), str(V)]
preflight = read(V / "preflight.json")
manifest = read(Q / "TRANSFER-MANIFEST.json")
before = {row["relative_path"]: sha(Q / row["relative_path"]) for row in manifest["payloads"]}
active_before = {relative: sha(F / relative) for relative in preflight["source_before_sha256"]}
assert before == {row["relative_path"]: row["candidate_sha256"] for row in manifest["payloads"]}
assert active_before == preflight["source_before_sha256"]
modules = ["test_process_observation_timing", "test_process_observation_validation", "test_process_diagnostics",
           "test_resource_management", "test_hardware_observation", "test_workload_admission", "test_temporal",
           "test_source_coverage.SourceCoverageTests.test_contract_core_has_no_infrastructure_or_other_domain_imports",
           "test_source_coverage.SourceCoverageTests.test_only_the_observed_enum_type_import_is_qualified",
           "test_source_coverage.SourceCoverageTests.test_contract_leaf_rejects_infrastructure_and_relative_domain_escape"]
jobs = importlib.import_module("test_windows_jobs")
fixtures = importlib.import_module("fixture_paths")
hardware = importlib.import_module("test_hardware_observation")
diagnostics = importlib.import_module("test_process_diagnostics")
timing = importlib.import_module("test_process_observation_timing")
jobs.ROOT = fixtures.ROOT = hardware.ROOT = V
lifetimes = []
original_teardown = jobs.WindowsJobTests.tearDown


def observed_teardown(self):
    rows = [{"test_id": self.id(), "pid": owned.pid, "creation_time": owned.creation_time,
             "closed_before_teardown": owned.lifetime_closed,
             "exit_code_before_teardown": owned.poll()} for owned in self.owned]
    try:
        original_teardown(self)
    finally:
        for row, owned in zip(rows, self.owned):
            row.update(closed_after_teardown=owned.lifetime_closed,
                       retained_process_handle=owned._process, retained_job_handle=owned._job)
            lifetimes.append(row)


diagnostics.NativeProcessDiagnosticsTests.tearDown = observed_teardown
timing.NativeProcessObservationTimingTests.tearDown = observed_teardown
suite = unittest.defaultTestLoader.loadTestsFromNames(modules)


def ids(value):
    if isinstance(value, unittest.TestSuite):
        for child in value:
            yield from ids(child)
    else:
        yield value.id()


expected = list(ids(suite))
assert expected == preflight["author_expected_ids"] and len(expected) == len(set(expected)) == 327
cases = []


class Result(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.begin, self.status = time.perf_counter(), "PASS"
    def addFailure(self, test, error):
        self.status = "FAIL"
        super().addFailure(test, error)
    def addError(self, test, error):
        self.status = "ERROR"
        super().addError(test, error)
    def addSkip(self, test, reason):
        self.status = "SKIP"
        super().addSkip(test, reason)
    def addSubTest(self, test, subtest, error):
        if error is not None:
            self.status = "FAIL" if issubclass(error[0], test.failureException) else "ERROR"
        super().addSubTest(test, subtest, error)
    def stopTest(self, test):
        cases.append({"id": test.id(), "status": self.status, "seconds": time.perf_counter() - self.begin})
        super().stopTest(test)


started, begin = now(), time.perf_counter()
print(json.dumps({"started_at": started, "source_root": str(Q), "fixture_root": str(V),
                  "expected_methods": len(expected)}), flush=True)
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(suite)
after = {row["relative_path"]: sha(Q / row["relative_path"]) for row in manifest["payloads"]}
active_after = {relative: sha(F / relative) for relative in preflight["source_before_sha256"]}
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if (name == "ceta" or name.startswith("ceta.")) and getattr(module, "__file__", None)}
actual_ids = [row["id"] for row in cases]
passed = (result.wasSuccessful() and not result.skipped and before == after and active_before == active_after
          and actual_ids == expected and len(set(actual_ids)) == 327
          and bool(imports) and all(Path(path).is_relative_to(Q / "src") for path in imports.values())
          and all(row["closed_after_teardown"] and row["retained_process_handle"] is None
                  and row["retained_job_handle"] is None for row in lifetimes))
record = {"reviewer": "/root/pressure_writer", "started_at": started, "finished_at": now(),
          "candidate_root": str(Q), "candidate_manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"),
          "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
          "skips": len(result.skipped), "successful": passed, "seconds": time.perf_counter() - begin,
          "expected_ids": expected, "executed_ids": actual_ids, "cases": cases,
          "cohort": dict(Counter(row.split('.')[0] for row in actual_ids)),
          "failure_details": [{"id": test.id(), "traceback": trace} for test, trace in result.failures + result.errors],
          "source_before_sha256": before, "source_after_sha256": after,
          "active_before_sha256": active_before, "active_after_sha256": active_after,
          "imports": imports, "native_lifetimes": lifetimes,
          "native_timing_observations": timing.NATIVE_OBSERVATIONS,
          "native_hardware_observations": hardware.NATIVE_OBSERVATIONS,
          "clock_info": {name: vars(time.get_clock_info(name)) for name in ("monotonic", "perf_counter")},
          "fixture_adjustment": "Only test-global jobs.ROOT, fixture_paths.ROOT and hardware.ROOT point to reviewer V. Source guard ROOT remains Q. Original test bytes, guards and IDs are unchanged.",
          "independence": preflight["independence"], "whole_unit_acceptance": "OPEN", "exit_status": 0 if passed else 1}
(V / (stem + ".json")).open("x", encoding="utf-8").write(json.dumps(record, indent=2, allow_nan=False) + "\n")
print(json.dumps({key: record[key] for key in ("tests_run", "failures", "errors", "skips", "successful", "seconds", "exit_status")}), flush=True)
sys.exit(record["exit_status"])
