"""Independent ER1 helper guard review; never import or execute its main."""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import ast
import copy
import hashlib
import json
import os
import sys
import unittest
import uuid

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/er1-20261014", F / ".agents/runtime/er1-20261014"
V = R / "independent-review"
E3 = F / ".agents/source-assembly-20261014T021300Z/.agents/e3"
HELPER = R / "apply_reviewed_environment.py"
EXPECTED = sys.argv[1]
MANIFEST_SHA = "7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83"
REVIEW_SHA = "8322051dbf2b0efac25a46ea2af47ce1fcab2cf62f42d41776a28e677a94e0b3"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
utc = lambda: datetime.now(timezone.utc).isoformat()
assert os.name == "nt" and sys.flags.optimize == 0
assert sha(HELPER) == EXPECTED
SOURCE = HELPER.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
MAIN = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "main")
MANIFEST = read(Q / "TRANSFER-MANIFEST.json")
FIXTURE = V / ("helper-fixture-" + uuid.uuid4().hex)
FIXTURE.mkdir(exist_ok=False)
OBSERVATIONS = []


def condition(reason, tree=TREE):
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "require"
             and len(n.args) == 2 and isinstance(n.args[1], ast.Constant)
             and n.args[1].value == reason]
    assert len(calls) == 1, reason
    return calls[0]


def evaluate(reason, values):
    return eval(compile(ast.Expression(copy.deepcopy(condition(reason).args[0])),
                        str(HELPER), "eval"), values)


def code_function(function):
    module = ast.Module(body=[copy.deepcopy(function)], type_ignores=[])
    ast.fix_missing_locations(module)
    return compile(module, str(HELPER), "exec")


def failure_probe(tree, incoming, journal_fault):
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    handler = next(n for n in main.body if isinstance(n, ast.Try)).handlers[0]
    block = ast.Try(body=[ast.Raise(exc=ast.Name(id="incoming", ctx=ast.Load()), cause=None)],
                    handlers=[copy.deepcopy(handler)], orelse=[], finalbody=[])
    function = ast.FunctionDef(name="probe", args=ast.arguments(posonlyargs=[], args=[],
        kwonlyargs=[], kw_defaults=[], defaults=[]), body=[block], decorator_list=[])
    calls = []
    def save(path, value):
        calls.append((str(path), value))
        if journal_fault is not None:
            raise journal_fault
    env = {"incoming": incoming, "save": save, "OUT": FIXTURE, "started": {},
           "completed": [], "now": utc}
    exec(code_function(function), env)
    try:
        env["probe"]()
    except BaseException as observed:
        return observed, calls
    raise AssertionError("Primary failure was swallowed")


class PublicationHelperReview(unittest.TestCase):
    def test_frozen_approval_and_author_self_review_links_match_real_bytes(self):
        self.assertEqual(sha(Q / "TRANSFER-MANIFEST.json"), MANIFEST_SHA)
        self.assertEqual(sha(V / "review.json"), REVIEW_SHA)
        review = read(V / "review.json")
        self.assertEqual(review["result"]["manifest"]["sha256"], MANIFEST_SHA)
        self.assertEqual((review["decision"], review["exit_status"]), ("approved", 0))
        self_review = MANIFEST["self_review"]
        target = F / self_review["repository_relative_path"]
        self.assertEqual(target, R / "self-review.json")
        self.assertEqual(sha(target), self_review["sha256"])
        self.assertTrue(evaluate("Candidate review manifest differs", {
            "review": review, "manifest_path": Q / "TRANSFER-MANIFEST.json", "sha": sha}))
        altered = copy.deepcopy(review)
        altered["result"]["manifest"]["sha256"] = "0" * 64
        self.assertFalse(evaluate("Candidate review manifest differs", {
            "review": altered, "manifest_path": Q / "TRANSFER-MANIFEST.json", "sha": sha}))

    def test_exact_thirty_current_target_bindings_and_all_candidate_hashes(self):
        declarations = [n for n in MAIN.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id in {"allowed_names", "allowed"}
                                for t in n.targets)]
        env = {}
        exec(compile(ast.Module(body=copy.deepcopy(declarations), type_ignores=[]),
                     str(HELPER), "exec"), env)
        allowed = env["allowed"]
        self.assertEqual(len(allowed), 30)
        observed = set()
        for row in MANIFEST["payloads"]:
            target = Path(row["source_path"])
            self.assertTrue(target.is_relative_to(E3))
            relative = target.relative_to(E3).as_posix()
            self.assertIn(relative, allowed)
            self.assertNotIn(relative, observed)
            observed.add(relative)
            expected = ("launchers/" + target.name if relative.startswith("Scripts/")
                        else "metadata/" + target.parent.name + "/RECORD")
            self.assertEqual(row["candidate_relative_path"], expected)
            candidate = Q / expected
            self.assertEqual((candidate.stat().st_size, sha(candidate)),
                             (row["candidate_bytes"], row["candidate_sha256"]))
            self.assertEqual(sha(target), row["source_sha256"])
            info = target.stat()
            identity = {"bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
                        "mode": info.st_mode & 0o7777, "device": info.st_dev,
                        "inode": info.st_ino, "attributes": info.st_file_attributes}
            self.assertEqual(identity, row["source_native_identity"])
            before = F / row["before_image"]["repository_relative_path"]
            self.assertTrue(before.is_relative_to(R / "before-images"))
            self.assertEqual(sha(before), row["source_sha256"])
            OBSERVATIONS.append({"relative_path": relative, "source_sha256": sha(target),
                                 "source_native_identity": identity, "candidate_sha256": sha(candidate)})
        self.assertEqual(observed, allowed)

    def test_original_handle_guard_rejects_each_native_identity_drift(self):
        expected = {"device": 7, "inode": 8, "bytes": 9, "mtime_ns": 10}
        facts = SimpleNamespace(st_dev=7, st_ino=8, st_size=9, st_mtime_ns=10)
        env = {"facts": facts, "expected_identity": expected}
        self.assertTrue(evaluate("Original handle identity changed before preservation", env))
        for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns"):
            changed = copy.copy(facts)
            setattr(changed, field, getattr(changed, field) + 1)
            self.assertFalse(evaluate("Original handle identity changed before preservation",
                                      {**env, "facts": changed}), field)

    def test_pre_replace_guard_rejects_hash_equivalent_native_identity_drift(self):
        expected = {"device": 1, "inode": 2, "mode": 3, "bytes": 4, "mtime_ns": 5, "attributes": 6}
        for key in (None, *expected):
            actual = dict(expected)
            if key is not None:
                actual[key] += 1
            fs = SimpleNamespace(lstat=lambda _: actual, file_identity=lambda value: value)
            env = {"native": SimpleNamespace(fs=fs), "E3": E3, "relative": "Scripts/pip.exe",
                   "row": {"source_native_identity": expected}}
            self.assertEqual(evaluate("Original target identity changed before replacement", env),
                             key is None, key)

    def test_native_backup_guard_rejects_each_original_field_and_hash_drift(self):
        original = {"sha256": "a" * 64, "device": 1, "inode": 2, "mode": 3, "bytes": 4, "mtime_ns": 5}
        facts = SimpleNamespace(st_dev=1, st_ino=2, st_mode=3, st_size=4, st_mtime_ns=5)
        env = {"original": original, "facts": facts, "backup_digest": original["sha256"]}
        self.assertTrue(evaluate("Native original bytes or handle identity differ after replacement", env))
        for field in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns"):
            changed = copy.copy(facts)
            setattr(changed, field, getattr(changed, field) + 1)
            self.assertFalse(evaluate("Native original bytes or handle identity differ after replacement",
                                      {**env, "facts": changed}), field)
        self.assertFalse(evaluate("Native original bytes or handle identity differ after replacement",
                                  {**env, "backup_digest": "b" * 64}))

    def test_identity_verification_precedes_success_events_and_fsync(self):
        outer = next(n for n in MAIN.body if isinstance(n, ast.Try))
        loop = next(n for n in ast.walk(outer) if isinstance(n, ast.For)
                    and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                            and c.func.attr == "publish_prepared" for c in ast.walk(n)))
        calls = [c for c in ast.walk(loop) if isinstance(c, ast.Call)]
        published = next(c.lineno for c in calls if isinstance(c.func, ast.Attribute)
                         and c.func.attr == "publish_prepared")
        appended = next(c.lineno for c in calls if isinstance(c.func, ast.Attribute)
                        and c.func.attr == "append")
        written = next(c.lineno for c in calls if isinstance(c.func, ast.Attribute)
                       and c.func.attr == "write")
        fsync = next(c.lineno for c in calls if isinstance(c.func, ast.Attribute)
                     and c.func.attr == "fsync")
        self.assertLess(condition("Original target identity changed before replacement").lineno, published)
        self.assertLess(published, condition("Native original bytes or handle identity differ after replacement").lineno)
        self.assertLess(condition("Native original bytes or handle identity differ after replacement").lineno, appended)
        self.assertLess(appended, written)
        self.assertLess(written, fsync)

    def test_journal_fault_preserves_primary_exceptions_including_controls(self):
        for incoming in (RuntimeError("primary"), OSError("primary"),
                         KeyboardInterrupt("primary"), SystemExit(4)):
            for journal_fault in (None, OSError("journal"), KeyboardInterrupt("journal")):
                observed, calls = failure_probe(TREE, incoming, journal_fault)
                self.assertIs(observed, incoming)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1]["error_type"], type(incoming).__name__)
                if journal_fault is not None:
                    self.assertIn("Failure journal could not be written: " + type(journal_fault).__name__,
                                  incoming.__notes__)

    def test_first_helper_journal_masking_is_retained_as_rejected_evidence(self):
        old = R / "apply_reviewed_environment_attempt_r1.py"
        self.assertEqual(sha(old), "33b0f64a38f7c02e51d9b495fcce791471b886d936331c47bc25c5a9855184dd")
        primary, secondary = RuntimeError("primary"), OSError("journal")
        observed, calls = failure_probe(ast.parse(old.read_text(encoding="utf-8")), primary, secondary)
        self.assertIs(observed, secondary)
        self.assertIs(observed.__context__, primary)
        self.assertEqual(len(calls), 1)

    def test_save_is_exclusive_and_durable_in_own_disposable_fixture(self):
        function = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "save")
        env = {"json": json, "os": os}
        exec(code_function(function), env)
        path = FIXTURE / "own-journal.json"
        env["save"](path, {"observed": 1})
        before = path.read_bytes()
        self.assertEqual(json.loads(before), {"observed": 1})
        with self.assertRaises(FileExistsError):
            env["save"](path, {"observed": 2})
        self.assertEqual(path.read_bytes(), before)

    def test_full_conservation_frozen_reference_chain_and_comparison(self):
        conservation = MANIFEST["source_conservation"]
        document = F / conservation["repository_relative_path"]
        self.assertEqual(sha(document), conservation["sha256"])
        reference = read(document)["after"]
        snapshot = F / reference["repository_relative_path"]
        self.assertEqual(snapshot, R / "E3-after-tests.json")
        self.assertEqual(sha(snapshot), reference["sha256"])
        historical = read(snapshot)
        rows = [row for row in historical["members"] if row["kind"] == "ordinary_file"]
        self.assertEqual(len(rows), 3601)
        self.assertEqual(sum(row["bytes"] for row in rows), 231026958)
        before = {row["relative_path"]: row for row in rows}
        self.assertTrue(evaluate("Environment files changed since author qualification",
                                 {"baseline_files": before, "historical_files": before}))
        changed = copy.deepcopy(before)
        changed["Scripts/python.exe"]["sha256"] = "0" * 64
        self.assertFalse(evaluate("Environment files changed since author qualification",
                                  {"baseline_files": changed, "historical_files": before}))
        constants = {n.value for n in ast.walk(TREE) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertTrue(reference["sha256"] in constants or
                        ("source_conservation" in constants and "after" in constants),
                        "Publication helper must bind the existing frozen snapshot reference chain")


class RecordingResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.ids.append(test.id())


started = utc()
with (V / ("publication-helper-tests-" + EXPECTED[:12] + ".txt")).open("x", encoding="utf-8") as stream:
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult)
    RecordingResult.ids = []
    result = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(PublicationHelperReview))
report = {"schema_version": 1, "started_at": started, "finished_at": utc(),
          "publication_script_sha256": EXPECTED, "manifest_sha256": MANIFEST_SHA,
          "test_ids": result.ids, "tests_run": result.testsRun, "failures": result.failures,
          "errors": result.errors, "skips": result.skipped, "passed": result.wasSuccessful(),
          "current_source_and_candidate_bindings": OBSERVATIONS,
          "helper_source_unchanged": sha(HELPER) == EXPECTED,
          "execution_scope": "Static AST inspection and isolated exact guard/handler/save fragments only",
          "helper_main_executed": False, "native_replacements_executed": 0,
          "active_E3_writes": False, "fixture_path": str(FIXTURE)}
report["failures"] = [{"id": test.id(), "traceback": trace} for test, trace in result.failures]
report["errors"] = [{"id": test.id(), "traceback": trace} for test, trace in result.errors]
report["skips"] = [{"id": test.id(), "reason": reason} for test, reason in result.skipped]
target = V / ("publication-helper-tests-" + EXPECTED[:12] + ".json")
with target.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"path": str(target), "sha256": sha(target), "tests_run": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
                  "source_unchanged": report["helper_source_unchanged"]}), flush=True)
sys.exit(0 if result.wasSuccessful() and report["helper_source_unchanged"] else 1)
