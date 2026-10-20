"""Bounded nested-frame recovery and publication gates; never publish Source."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

V = Path(__file__).resolve().parent
R, F = V.parent, V.parents[3]
Q = F / ".agents/gd2-20261014"
E3 = F / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
read = lambda path: json.loads(path.read_text(encoding="utf-8"))
if len(sys.argv) == 1:
    command = [str(E3), "-B", "-X", "utf8", str(Path(__file__)), "worker"]
    started = now()
    with (V / "hostile-r1.txt").open("x", encoding="utf-8") as raw:
        result = subprocess.run(command, cwd=r"T:\00-Active", stdout=raw, stderr=subprocess.STDOUT,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    (V / "hostile-r1-command.json").open("x", encoding="utf-8").write(json.dumps({"command": command,
        "started_at": started, "finished_at": now(), "cwd": r"T:\00-Active", "exit_status": result.returncode,
        "raw_sha256": sha(V / "hostile-r1.txt")}, indent=2) + "\n")
    print((V / "hostile-r1.txt").read_text(encoding="utf-8")[-2400:], flush=True)
    sys.exit(result.returncode)

assert Path(sys.executable) == E3
sys.dont_write_bytecode = True
sys.path[:0] = [str(Q / "src"), str(Q / "tests/contract")]
import test_process_observation_timing as timing
import test_process_diagnostics as process_tests
from ceta.contracts.resource_management import ObservationState
from ceta.contracts.wire import ContractError
from ceta.resource.diagnostics import ResourceTelemetryRecorder

HELPER = R / "apply_reviewed_observation.py"
assert sha(HELPER) == "f6a9dcbbada985fc5495c7af3b46c46039bcbd8c5c5fa668e39e1c4732230599"
(V / "publication-helper-at-review.py").open("xb").write(HELPER.read_bytes())
spec = importlib.util.spec_from_file_location("gd2_publication_review", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
native = helper.native
manifest = read(Q / "TRANSFER-MANIFEST.json")
candidate_before = {row["relative_path"]: sha(Q / row["relative_path"]) for row in manifest["payloads"]}
active_before = {row["relative_path"]: sha(F / row["relative_path"]) for row in manifest["payloads"] if row["active_before_sha256"] is not None}
rows = []


class StopBeforeMutation(RuntimeError):
    pass


class NestedRecoveryChallenges(unittest.TestCase):
    def fixture(self):
        return timing.ProcessObservationTimingTests.fixture(self)

    @staticmethod
    def quantities(frame):
        return (frame.working_set_bytes, frame.usage.cpu_time_100ns, frame.usage.private_bytes,
                frame.usage.read_io_bytes, frame.usage.write_io_bytes)

    def test_each_nested_boolean_before_and_after_baseline_preserves_order_and_recorder(self):
        for initial in (True, False):
            for index in range(5):
                with self.subTest(initial=initial, index=index):
                    public, precise, port, sampler = self.fixture()
                    recorder = ResourceTelemetryRecorder(maximum_samples=3)
                    if not initial:
                        sampler.collect(recorder)
                    accepted = sampler._accepted_time, tuple(sampler._counter_high_water), sampler._sequence
                    public[0], precise[0] = 110, 1010
                    bad = process_tests.counters(110, cpu=50_000, read=50_000, write=50_000)
                    object.__setattr__(self.quantities(bad)[index], "value", True)
                    port.next = bad
                    with self.assertRaises(ContractError) as caught:
                        sampler.collect(recorder)
                    self.assertEqual(caught.exception.code, "RESOURCE_MEASUREMENT_INVALID")
                    self.assertEqual((sampler._accepted_time, tuple(sampler._counter_high_water), sampler._sequence), accepted)
                    self.assertEqual(len(recorder._samples), 0 if initial else 1)
                    self.assertIsNone(sampler._cached)
                    self.assertIsNone(sampler._cpu_baseline)
                    self.assertIsNone(sampler._cpu_elapsed_baseline)
                    public[0], precise[0], port.next = 120, 1020, process_tests.counters(120, cpu=110)
                    baseline = sampler.collect(recorder)
                    self.assertEqual(baseline.cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
                    public[0], precise[0], port.next = 130, 1030, process_tests.counters(130, cpu=110)
                    recovered = sampler.collect(recorder)
                    self.assertTrue(recovered.cpu_milli.measured)
                    self.assertEqual(recovered.cpu_milli.value, 0)
                    rows.append({"case": "nested_bool_recovery", "index": index, "initial": initial,
                                 "error": caught.exception.code, "preserved_sequence": accepted[2],
                                 "recovered_sequence": recovered.source.sequence, "recovered_cpu_milli": 0})

    def test_oversized_method_reason_and_scalar_types_reject_before_adoption(self):
        changes = (("method", "m" * 161), ("method", False), ("value", 2**63),
                   ("value", float("inf")), ("state", True), ("reason", "unavailable"))
        for index in range(5):
            for field, invalid in changes:
                with self.subTest(index=index, field=field):
                    public, precise, port, sampler = self.fixture()
                    frame = process_tests.counters(100)
                    object.__setattr__(self.quantities(frame)[index], field, invalid)
                    port.next = frame
                    with self.assertRaises(ContractError):
                        sampler.sample()
                    self.assertEqual((sampler._accepted_time, sampler._sequence, sampler._counter_high_water),
                                     (-1, 0, [None, None, None]))
                    self.assertIsNone(sampler._cached)

    def test_unavailable_zero_has_valid_separate_recovery_without_boolean_adoption(self):
        public, precise, port, sampler = self.fixture()
        frame = process_tests.counters(100)
        for observation in self.quantities(frame):
            object.__setattr__(observation, "state", ObservationState.UNAVAILABLE)
            object.__setattr__(observation, "value", None)
            object.__setattr__(observation, "reason", "NOT_OBSERVED")
        port.next = frame
        unavailable = sampler.sample()
        self.assertIsNone(unavailable.memory_bytes.value)
        self.assertEqual(sampler._counter_high_water, [None, None, None])
        public[0], precise[0], port.next = 110, 1010, process_tests.counters(110, cpu=0, memory=0, private=0, read=0, write=0)
        self.assertEqual(sampler.sample().cpu_milli.reason, "PROCESS_CPU_BASELINE_REQUIRED")
        public[0], precise[0], port.next = 120, 1020, process_tests.counters(120, cpu=0, memory=0, private=0, read=0, write=0)
        measured = sampler.sample()
        self.assertTrue(measured.cpu_milli.measured)
        self.assertEqual(measured.cpu_milli.value, 0)


class PublicationChallenges(unittest.TestCase):
    def intercepted_read(self, path, *, altered=None):
        if path == R / helper.RUN / "claims.json":
            return {"integrate": {"executor_id": "/root", "workspace": str(F), "input_hash": "synthetic-owner-gate"}}
        if path == R / helper.RUN / "state.json":
            return {"nodes": {"review": {"state": "SUCCEEDED"}, "validate": {"state": "SUCCEEDED"}}}
        if path == R / "independent-review/review.json":
            return {"decision": "approved", "exit_status": 0,
                    "result": {"manifest_sha256": "0" * 64, "scope": "unrelated-synthetic-approval"}}
        if path == R / "independent-review/publication-helper-review.json":
            return {"decision": "approved", "exit_status": 0, "publication_script_sha256": sha(HELPER),
                    "manifest_sha256": "1" * 64}
        return read(path)

    def test_wrong_manifest_and_unpersisted_review_reach_intercepted_publication_boundary(self):
        destination = V / "publication-gate-wrong-review"
        called = []
        def fence(*args):
            called.append(str(args[1]))
            raise StopBeforeMutation("Own test intercept: actual Source publication forbidden")
        with patch.object(helper, "read", side_effect=self.intercepted_read), patch.object(helper, "OUT", destination), \
                patch.object(native, "publish_prepared", side_effect=fence):
            with self.assertRaises(StopBeforeMutation):
                helper.main()
        self.assertEqual(len(called), 1)
        self.assertTrue(called[0].startswith(str(F)))
        rows.append({"case": "publication_unbound_review", "stimulus": "Synthetic read-only approvals carry wrong manifest and no persisted receipt",
                     "outcome": "Reached intercepted native publication boundary", "Source_mutations": 0,
                     "retained_staging_scope": str(destination)})

    def test_same_byte_native_identity_substitution_is_accepted_by_hash_only_primitive(self):
        scope = V / "native-identity-fixture"
        scope.mkdir(exist_ok=False)
        target, first, second = (scope / name for name in ("target", "first-stage", "second-stage"))
        target.write_bytes(b"owned-original")
        first.write_bytes(target.read_bytes())
        second.write_bytes(b"owned-candidate")
        expected = os.stat(target)
        before_hash = sha(target)
        native.publish_prepared(first, target, scope / "original-native-backup", before_hash, before_hash)
        replaced = os.stat(target)
        self.assertNotEqual(expected.st_ino, replaced.st_ino)
        native.publish_prepared(second, target, scope / "second-native-backup", before_hash, sha(second))
        backup = os.stat(scope / "second-native-backup")
        self.assertNotEqual(expected.st_ino, backup.st_ino)
        self.assertEqual(replaced.st_ino, backup.st_ino)
        self.assertEqual(expected.st_ino, os.stat(scope / "original-native-backup").st_ino)
        rows.append({"case": "native_original_identity_not_gated", "fixture_scope": str(scope),
                     "initial_identity": [expected.st_dev, expected.st_ino], "substituted_identity": [replaced.st_dev, replaced.st_ino],
                     "eventual_backup_identity": [backup.st_dev, backup.st_ino], "same_before_bytes_sha256": before_hash,
                     "original_also_retained": True, "actual_fixture_ReplaceFile_calls": 2, "Source_mutations": 0})

    def test_control_exception_survives_failure_journal_exception(self):
        for index, primary in enumerate((KeyboardInterrupt("owned-test-control"), SystemExit(23))):
            destination = V / ("publication-primary-control-" + str(index))
            real_save = helper.save
            def failed_journal(path, value):
                if path.name == "FAILED.json":
                    raise OSError("explicit owned-fixture journal failure")
                return real_save(path, value)
            with patch.object(helper, "read", side_effect=self.intercepted_read), patch.object(helper, "OUT", destination), \
                    patch.object(helper, "save", side_effect=failed_journal), patch.object(native, "publish_prepared", side_effect=primary):
                with self.assertRaises(type(primary)) as caught:
                    helper.main()
            self.assertIs(caught.exception, primary)
            self.assertEqual(primary.__notes__, ["Publication failure journal could not be written: OSError"])
            rows.append({"case": "primary_control_retained", "primary_type": type(primary).__name__,
                         "same_primary_instance": True, "Source_mutations": 0})


suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                           for cls in (NestedRecoveryChallenges, PublicationChallenges))
expected = [test.id() for group in suite for test in group]
executed = []
class Result(unittest.TextTestResult):
    def startTest(self, test):
        executed.append(test.id())
        super().startTest(test)
started, begin = now(), time.perf_counter()
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(suite)
candidate_after = {row["relative_path"]: sha(Q / row["relative_path"]) for row in manifest["payloads"]}
active_after = {relative: sha(F / relative) for relative in active_before}
passed = (result.wasSuccessful() and not result.skipped and expected == executed
          and candidate_before == candidate_after and active_before == active_after)
record = {"reviewer": "/root/pressure_writer", "started_at": started, "finished_at": now(),
          "manifest_sha256": sha(Q / "TRANSFER-MANIFEST.json"), "publication_script_sha256": sha(HELPER),
          "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
          "seconds": time.perf_counter() - begin, "expected_ids": expected, "executed_ids": executed,
          "failure_details": [{"id": test.id(), "traceback": trace} for test, trace in result.failures + result.errors],
          "observations": rows, "candidate_payloads_unchanged": candidate_before == candidate_after,
          "active_Source_payloads_unchanged": active_before == active_after, "fixture_ReplaceFile_calls": 2,
          "actual_Source_writes": [], "native_children_launched": 0,
          "classification": "Nested malformed-port inputs are synthetic. Approval metadata substitution is an isolated read injection and native identity replacements affect owned fixtures only. Tests confirm observed defects; passing these tests does not approve the helper.",
          "source_functional_closure": True if result.wasSuccessful() else False,
          "helper_approval": "WITHHELD_PENDING_EXACT_BINDING_AND_NATIVE_IDENTITY_REPAIR", "exit_status": 0 if passed else 1}
(V / "hostile-r1.json").open("x", encoding="utf-8").write(json.dumps(record, indent=2, allow_nan=False) + "\n")
print(json.dumps({key: record[key] for key in ("tests_run", "failures", "errors", "skips", "helper_approval", "exit_status")}), flush=True)
sys.exit(record["exit_status"])
