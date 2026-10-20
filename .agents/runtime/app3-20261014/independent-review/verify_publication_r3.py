"""Independent native publication checks; every mutation is an owned fixture."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout
import ctypes
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest

R = Path(__file__).resolve().parent
S = R.parents[3]
MECHANISM = S / ".agents/runtime/rs2-20261014"
PUBLICATION = MECHANISM / "apply_joined_source.py"
ORIGINAL_TESTS = MECHANISM / "test_joined_publication.py"
digest = lambda data: hashlib.sha256(data).hexdigest()
sha = lambda path: digest(path.read_bytes())
now = lambda: datetime.now(timezone.utc).isoformat()

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

pub = load("app3_independent_native_publication", PUBLICATION)
original = load("app3_unchanged_original_native_tests", ORIGINAL_TESTS)
# The original test bodies are unmodified. Only their fresh fixture parent is
# redirected to this review's explicit disposable output scope.
original.R = R
original.publication = pub
FIXTURES = R / "native-publication-fixtures"
FIXTURES.mkdir(exist_ok=True)
observations = []

class NativeBoundaryTests(original.NativeJoinedPublicationTests):
    # Inherit the eight exact author test bodies and add independent cases.
    def test_create_racing_destination_is_refused_by_actual_nooverwrite_api(self):
        real = pub.fs.publish_new
        def create_racing(stage, target):
            target.write_bytes(b"racing destination must be retained\n")
            return real(stage, target)
        pub.fs.publish_new = create_racing
        try:
            with self.assertRaisesRegex(pub.fs.PreservationError, "overwrite refused"):
                self.call(None)
        finally:
            pub.fs.publish_new = real
        self.assertEqual(self.target.read_bytes(), b"racing destination must be retained\n")
        self.assertEqual(self.stage.read_bytes(), self.new)
        self.assertFalse(self.backup.exists())

    def test_actual_staged_deny_delete_share_refuses_preserving_both_files(self):
        self.target.write_bytes(self.old)
        with pub.fs.open_source(self.stage, exclusive=True):
            with self.assertRaisesRegex(OSError, "WINDOWS_EXACT_FILE_REPLACEMENT_FAILED"):
                self.call(digest(self.old))
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertEqual(self.stage.read_bytes(), self.new)
        self.assertFalse(self.backup.exists())

    def test_lexical_parent_escape_is_rejected_before_read_or_write(self):
        self.target.write_bytes(self.old)
        escaped = self.root / ".." / self.root.name / "target.py"
        with self.assertRaisesRegex(pub.fs.PreservationError, "parent traversal"):
            pub.publish_prepared(self.stage, escaped, self.backup, digest(self.old), digest(self.new))
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertEqual(self.stage.read_bytes(), self.new)

    def test_missing_existing_target_never_degrades_to_create(self):
        with self.assertRaisesRegex(pub.fs.PreservationError, "declared path is missing"):
            self.call(digest(self.old))
        self.assertFalse(self.target.exists())
        self.assertEqual(self.stage.read_bytes(), self.new)

    def test_native_backup_cannot_alias_stage(self):
        self.target.write_bytes(self.old)
        with self.assertRaises(AssertionError):
            pub.publish_prepared(self.stage, self.target, self.stage, digest(self.old), digest(self.new))
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertEqual(self.stage.read_bytes(), self.new)

    def _controlled_partial(self, error, move_original):
        self.target.write_bytes(self.old)
        real_kernel = pub.KERNEL
        def partial(target, stage, backup, flags, exclude, reserved):
            self.assertEqual(flags, 0)
            self.assertIsNone(exclude)
            self.assertIsNone(reserved)
            if move_original:
                pub.fs.publish_new(self.target, self.backup)
            ctypes.set_last_error(error)
            return 0
        pub.KERNEL = SimpleNamespace(ReplaceFileW=partial)
        try:
            with self.assertRaisesRegex(OSError, "WINDOWS_EXACT_FILE_REPLACEMENT_FAILED"):
                self.call(digest(self.old))
        finally:
            pub.KERNEL = real_kernel
        self.assertEqual(self.stage.read_bytes(), self.new)
        if move_original:
            self.assertFalse(self.target.exists())
            self.assertEqual(self.backup.read_bytes(), self.old)
        else:
            self.assertEqual(self.target.read_bytes(), self.old)
            self.assertFalse(self.backup.exists())
        observations.append({"case": self.id(), "scope": "controlled documented-error injection, not an observed native error code",
                             "injected_error": error, "target_exists": self.target.exists(),
                             "stage_sha256": sha(self.stage), "backup_exists": self.backup.exists()})

    def test_controlled_1175_preserves_original_and_stage_without_retry(self):
        self._controlled_partial(1175, False)

    def test_controlled_1176_with_backup_argument_preserves_original_and_stage(self):
        self._controlled_partial(1176, False)

    def test_controlled_1177_keeps_absent_target_and_original_backup_for_reconciliation(self):
        self._controlled_partial(1177, True)

class OwnedApplicationHarnessTests(unittest.TestCase):
    """Synthetic claim/state documents, actual Windows file publication in R only."""
    def setUp(self):
        self.root = Path(pub.fs.io_path(Path(tempfile.mkdtemp(prefix="application-owned-", dir=FIXTURES))))
        self.q = self.root / ".agents/app3-20261014"
        self.runtime = self.root / ".agents/runtime/app3-20261014"
        self.q.mkdir(parents=True)
        (self.runtime / "app3-20261014").mkdir(parents=True)
        (self.runtime / "independent-review").mkdir()
        self.out = self.runtime / "active-application"
        self.old_root = pub.S
        pub.S = self.root
        self.old = b"fixture original preserved\r\n"
        self.new = b"fixture reviewed candidate\n"
        self.creates = {"contracts/PROCESS_DIAGNOSTICS_V1.md", "tests/contract/test_process_diagnostics.py"}
        self.entries = []
        for relative in sorted(pub.ALLOWED):
            target, candidate = self.root / relative, self.q / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(self.new)
            before = None if relative in self.creates else digest(self.old)
            if before is not None:
                target.write_bytes(self.old)
            self.entries.append({"relative_path": relative, "active_target_relative_to_repository": relative,
                                 "candidate_sha256": digest(self.new), "active_before_sha256": before,
                                 "application_action": "CREATE" if before is None else "EXTEND_PRESERVE_BEFORE_IMAGE"})
        retained = "contracts/unchanged_fixture.md"
        for base in (self.root, self.q):
            (base / retained).write_bytes(b"fixture retained dependency\n")
        self.entries.append({"relative_path": retained, "active_target_relative_to_repository": retained,
                             "candidate_sha256": sha(self.root / retained), "active_before_sha256": sha(self.root / retained),
                             "application_action": "IDENTICAL_RETAINED"})
        self.manifest = {"application_paths": sorted(pub.ALLOWED), "payloads": self.entries}
        self.manifest_path = self.q / "TRANSFER-MANIFEST.json"
        self.write_json(self.manifest_path, self.manifest)
        self.review_path = self.runtime / "independent-review/review.json"
        self.review = {"decision": "approved", "exit_status": 0,
                       "result": {"manifest_sha256": sha(self.manifest_path), "publication_script_sha256": sha(PUBLICATION)}}
        self.write_json(self.review_path, self.review)
        self.write_json(self.runtime / "app3-20261014/claims.json",
                        {"integrate": {"executor_id": "/root", "workspace": str(self.root), "input_hash": "synthetic-owned-fixture"}})
        self.write_json(self.runtime / "app3-20261014/state.json",
                        {"nodes": {"review": {"state": "SUCCEEDED"}, "validate": {"state": "SUCCEEDED"}}})

    def tearDown(self):
        pub.S = self.old_root
        # Preserve all generated fixture states, including partial failures.

    def write_json(self, path, value):
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")

    def call(self):
        with redirect_stdout(io.StringIO()):
            pub.main()

    def assert_before_state(self):
        for entry in self.entries:
            target = self.root / entry["relative_path"]
            if entry["active_before_sha256"] is None:
                self.assertFalse(target.exists())
            else:
                self.assertEqual(sha(target), entry["active_before_sha256"])

    def test_all_seven_native_publications_preserve_five_originals_and_retained_dependency(self):
        self.call()
        journal = json.loads((self.out / "APPLICATION.json").read_text())
        self.assertEqual(journal["status"], "SEVEN_REVIEWED_PATHS_APPLIED_AWAITING_FULL_DESTINATION_VERIFICATION")
        self.assertEqual(len(journal["completed"]), 7)
        self.assertEqual(len(journal["before_images"]), 5)
        for entry in self.entries:
            relative = entry["relative_path"]
            self.assertEqual(sha(self.root / relative), entry["candidate_sha256"])
            if relative in pub.ALLOWED and entry["active_before_sha256"] is not None:
                self.assertEqual(sha(self.out / "before" / (relative + ".source")), entry["active_before_sha256"])
                self.assertEqual(sha(self.out / "native-backups" / (relative + ".original")), entry["active_before_sha256"])

    def test_unreviewed_publication_script_hash_refuses_before_output_creation(self):
        self.review["result"]["publication_script_sha256"] = "0" * 64
        self.write_json(self.review_path, self.review)
        with self.assertRaisesRegex(AssertionError, "publication script differs"):
            self.call()
        self.assertFalse(self.out.exists())
        self.assert_before_state()

    def test_manifest_drift_refuses_before_output_creation(self):
        with self.manifest_path.open("a") as stream:
            stream.write(" ")
        with self.assertRaises(AssertionError):
            self.call()
        self.assertFalse(self.out.exists())
        self.assert_before_state()

    def test_unowned_eighth_application_path_refuses_before_output_creation(self):
        self.manifest["application_paths"].append("contracts/unchanged_fixture.md")
        self.write_json(self.manifest_path, self.manifest)
        self.review["result"]["manifest_sha256"] = sha(self.manifest_path)
        self.write_json(self.review_path, self.review)
        with self.assertRaises(AssertionError):
            self.call()
        self.assertFalse(self.out.exists())
        self.assert_before_state()

    def test_changed_retained_dependency_refuses_before_any_native_application(self):
        target = self.root / "contracts/unchanged_fixture.md"
        target.write_bytes(b"new owner dependency bytes\n")
        with self.assertRaisesRegex(AssertionError, "destination drift"):
            self.call()
        self.assertFalse(self.out.exists())
        self.assertEqual(target.read_bytes(), b"new owner dependency bytes\n")

    def test_after_first_publish_failure_preserves_every_stage_original_and_partial_journal(self):
        real = pub.publish_prepared
        calls = []
        def injected(stage, target, backup, before, candidate):
            calls.append(target)
            if len(calls) == 2:
                raise OSError("controlled application interruption before second native call")
            return real(stage, target, backup, before, candidate)
        pub.publish_prepared = injected
        try:
            with self.assertRaisesRegex(OSError, "controlled application interruption"):
                self.call()
        finally:
            pub.publish_prepared = real
        journal = json.loads((self.out / "APPLICATION.json").read_text())
        self.assertEqual(journal["status"], "PARTIAL_APPLICATION_PRESERVED_REQUIRES_FRESH_RECONCILIATION")
        self.assertEqual(len(journal["completed"]), 1)
        self.assertEqual(len(journal["before_images"]), 5)
        for entry in self.entries:
            relative = entry["relative_path"]
            if relative not in pub.ALLOWED:
                continue
            if self.root / relative == calls[0]:
                self.assertEqual(sha(self.root / relative), entry["candidate_sha256"])
            else:
                self.assertEqual(sha(self.out / "staged" / relative), entry["candidate_sha256"])
        # An automatic rerun is refused and cannot silently overwrite evidence.
        with self.assertRaises((FileExistsError, AssertionError)):
            self.call()
        self.assertEqual(json.loads((self.out / "APPLICATION.json").read_text())["status"],
                         "PARTIAL_APPLICATION_PRESERVED_REQUIRES_FRESH_RECONCILIATION")

class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = []
    def startTest(self, test):
        self.executed_ids.append(test.id())
        super().startTest(test)

def flatten(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite):
            yield from flatten(case)
        else:
            yield case.id()

started = now()
before = {str(path): sha(path) for path in (PUBLICATION, ORIGINAL_TESTS, MECHANISM / "prepare_joined_application.py", pub.TOOL)}
suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(NativeBoundaryTests),
                          unittest.defaultTestLoader.loadTestsFromTestCase(OwnedApplicationHarnessTests)])
expected_ids = list(flatten(suite))
with (R / "native-mechanism-r3.txt").open("x", encoding="utf-8") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
after = {path: sha(Path(path)) for path in before}
files = [{"path": str(path.relative_to(R)), "bytes": path.stat().st_size, "sha256": sha(path)}
         for path in sorted(FIXTURES.rglob("*")) if path.is_file()]
passed = result.wasSuccessful() and not result.skipped and expected_ids == result.executed_ids and before == after
record = {"schema_version": 1, "started_at": started, "finished_at": now(), "tests_run": result.testsRun,
          "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
          "expected_ids": expected_ids, "executed_ids": result.executed_ids,
          "failed_ids": [case.id() for case, _ in result.failures + result.errors],
          "source_before": before, "source_after": after, "source_unchanged": before == after,
          "test_source_sha256": sha(Path(__file__)), "output_sha256": sha(R / "native-mechanism-r3.txt"),
          "preserved_owned_fixture_files": files, "controlled_partial_outcomes": observations,
          "scope": "Actual native Windows file APIs in explicit independent-review fixtures; synthetic orchestration state documents in algorithm harness are not an actual TAAR integration",
          "partial_error_scope": "1175/1176/1177 documented outcomes injected in process; no claim these Windows error codes occurred naturally",
          "exit_status": 0 if passed else 1}
with (R / "native-mechanism-r3.json").open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps({key: record[key] for key in ("tests_run", "failures", "errors", "skips", "source_unchanged", "failed_ids", "exit_status")}))
raise SystemExit(record["exit_status"])
