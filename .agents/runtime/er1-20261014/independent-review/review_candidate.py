"""Independent exact-artifact and bounded native ER1 qualification after freeze."""
from datetime import datetime, timezone
import ast
import base64
import csv
import hashlib
import io
import json
import msvcrt
import os
from pathlib import Path
import shutil
import struct
import sys
import time
import unittest
import uuid
import zipfile

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/er1-20261014", F / ".agents/runtime/er1-20261014"
V = R / "independent-review"
E3 = F / ".agents/source-assembly-20261014T021300Z/.agents/e3"
SITE = E3 / "Lib/site-packages"
sys.path.insert(0, str(F / "src"))
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
sha = lambda data: hashlib.sha256(data).hexdigest()
def utc(): return datetime.now(timezone.utc).isoformat()
def write(path, data): path.open("x", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
baseline = json.loads((V / "source-inventory-r1.json").read_text())
rows = {row["filename"]: row for row in baseline["launchers"]}
stub = (SITE / "pip/_vendor/distlib/t64.exe").read_bytes()
assert sha(stub) == baseline["standard_stub"]["sha256"]
custody_source = F / "src/ceta/supervisor/windows_jobs.py"
custody_sha = sha(custody_source.read_bytes())
started = utc()
before = {str(path.relative_to(Q)): sha(path.read_bytes()) for path in Q.rglob("*") if path.is_file()}
state = json.loads((R / "er1-20261014/state.json").read_text())
assert state["nodes"]["implement"]["state"] == "SUCCEEDED"
claims = json.loads((R / "er1-20261014/claims.json").read_text())
assert "implement" not in claims and claims["review"]["executor_id"] == "/root/pressure_writer"
FIX = V / ("native-fixtures-" + uuid.uuid4().hex[:12])
FIX.mkdir()
commands = []

def validate_launcher(raw, original):
    if not raw.startswith(stub): raise ValueError("NATIVE_STUB_CHANGED")
    pe = struct.unpack_from("<I", raw, 0x3c)[0]
    if raw[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", raw, pe+4)[0] != 0x8664:
        raise ValueError("NATIVE_PE_CHANGED")
    start = len(stub)
    end = raw.index(b"\n", start) + 1
    if raw[start:end] != ("#!" + str(E3 / "Scripts/python.exe") + "\n").encode():
        raise ValueError("INTERPRETER_BINDING_CHANGED")
    payload = raw[end:]
    eocd = payload.rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 22 != len(payload): raise ValueError("ZIP_TRAILING_OR_COMMENT_DATA")
    _, disk, directory_disk, entries_disk, entries_total, size, offset, comment = struct.unpack_from("<4sHHHHIIH", payload, eocd)
    if (disk, directory_disk, entries_disk, entries_total, comment) != (0, 0, 1, 1, 0) or offset + size != eocd:
        raise ValueError("ZIP_DIRECTORY_CHANGED")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if archive.namelist() != ["__main__.py"] or archive.testzip() is not None:
            raise ValueError("ZIP_MAIN_MEMBERS_CHANGED")
        info = archive.infolist()[0]
        if info.header_offset != 0 or info.compress_type != zipfile.ZIP_STORED or info.extra or info.comment:
            raise ValueError("ZIP_FORMAT_CHANGED")
        main = archive.read("__main__.py")
    if sha(main) != original["main_sha256"]: raise ValueError("ENTRY_POINT_BODY_CHANGED")
    return {"sha256": sha(raw), "bytes": len(raw), "stub_sha256": sha(stub), "main_sha256": sha(main), "zip_bytes": len(payload)}

def run_owned(label, executable, arguments, expected_exit):
    area = FIX / label
    area.mkdir()
    temp = area / "temp"
    temp.mkdir()
    outputs, owned = [], None
    command_started = utc()
    begin = time.perf_counter()
    try:
        for name in ("stdin.bin", "stdout.bin", "stderr.bin"):
            stream = (area / name).open("xb+")
            outputs.append(stream)
            os.set_handle_inheritable(msvcrt.get_osfhandle(stream.fileno()), True)
        env = {key: value for key, value in os.environ.items() if key.upper() in
               {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATH", "PATHEXT"}}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
                   PIP_NO_INPUT="1", PIP_CONFIG_FILE=os.devnull, TEMP=str(temp), TMP=str(temp))
        image_sha = sha(executable.read_bytes())
        owned = WindowsOwnedProcess.launch(str(executable), tuple(arguments), cwd=str(area), environment=env,
            standard_handles=tuple(msvcrt.get_osfhandle(stream.fileno()) for stream in outputs), expected_image_sha256=image_sha)
        pid, creation, retained_hash = owned.pid, owned.creation_time, owned.image_sha256
        if not owned.wait(15): raise TimeoutError("Owned CLI exceeded 15 seconds")
        observed_exit = owned.poll()
        deadline = time.perf_counter() + 3
        while owned.active_process_count() and time.perf_counter() < deadline: time.sleep(.01)
        if owned.active_process_count() != 0: raise RuntimeError("Owned CLI descendants remain live")
        owned.close()
        closed = owned.lifetime_closed
        owned = None
        for stream in outputs: stream.close()
        out, err = (area / "stdout.bin").read_bytes(), (area / "stderr.bin").read_bytes()
        receipt = {"label": label, "command_argv": [str(executable), *arguments], "started_at": command_started,
            "finished_at": utc(), "seconds": time.perf_counter() - begin, "pid": pid, "creation_time_100ns": creation,
            "image_sha256": image_sha, "retained_image_sha256": retained_hash, "observed_exit": observed_exit,
            "expected_exit": expected_exit, "observed_empty_job": True, "lifetime_closed": closed,
            "stdout": out.decode("utf-8", errors="replace"), "stderr": err.decode("utf-8", errors="replace"),
            "stdout_sha256": sha(out), "stderr_sha256": sha(err), "environment_keys": sorted(env), "environment_values_exposed": False}
        write(area / "receipt.json", receipt)
        commands.append(receipt)
        assert observed_exit == expected_exit, receipt
        return receipt
    except BaseException as primary:
        retained = owned or getattr(primary, "owned_process", None)
        if retained is not None:
            retained.terminate(125)
            if retained.wait(5) and retained.active_process_count() == 0:
                retained.close()
                owned = None
            else:
                write(area / "unresolved-owner.json", {"pid": retained.pid, "creation_time_100ns": retained.creation_time,
                    "state": "RETAINED_UNRESOLVED_OWNED_CHILD", "at": utc()})
                raise RuntimeError("Independent review requires coordinator custody") from primary
        if callable(getattr(primary, "close_cleanup", None)): primary.close_cleanup()
        raise
    finally:
        if owned is None:
            for stream in outputs:
                if not stream.closed: stream.close()

class ArtifactReviewTests(unittest.TestCase):
    def test_all_27_exact_main_stub_shebang_and_canonical_zip_bindings(self):
        self.assertEqual(len(rows), 27)
        for name, row in rows.items():
            with self.subTest(name=name):
                validate_launcher((Q / "launchers" / name).read_bytes(), row)
                self.assertEqual(sha((E3 / "Scripts" / name).read_bytes()), row["source"]["sha256"])
                self.assertEqual((R / "before-images" / name).read_bytes(), (E3 / "Scripts" / name).read_bytes())

    def test_only_27_hash_size_fields_change_in_three_records(self):
        total = 0
        for info_name, meta in baseline["metadata"].items():
            old = (SITE / info_name / "RECORD").read_bytes()
            candidate = (Q / "metadata" / info_name / "RECORD").read_bytes()
            self.assertEqual(sha(old), meta["RECORD"]["sha256"])
            self.assertEqual((R / "before-images/metadata" / info_name / "RECORD").read_bytes(), old)
            originals, updated = old.splitlines(keepends=True), candidate.splitlines(keepends=True)
            self.assertEqual(len(originals), len(updated))
            rebuilt = []
            selected = {row["record_fields"][0]: row for row in rows.values() if row["metadata_directory"] == info_name}
            seen = set()
            for line in originals:
                parsed = next(csv.reader(io.StringIO(line.decode("utf-8")), strict=True))
                if parsed[0] not in selected:
                    rebuilt.append(line)
                    continue
                self.assertNotIn(parsed[0], seen)
                seen.add(parsed[0])
                row = selected[parsed[0]]
                raw = (Q / "launchers" / row["filename"]).read_bytes()
                ending = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
                # Exact current source rows have unquoted paths/hash/size.
                # Refuse any unexpected representation rather than generalize it.
                self.assertEqual(line, ",".join(parsed).encode() + ending)
                new_hash = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
                rebuilt.append((parsed[0] + "," + new_hash + "," + str(len(raw))).encode() + ending)
            self.assertEqual(seen, set(selected))
            self.assertEqual(candidate, b"".join(rebuilt))
            total += len(seen)
            old_rows, new_rows = list(csv.reader(io.StringIO(old.decode()))), list(csv.reader(io.StringIO(candidate.decode())))
            self.assertEqual(len(old_rows), len(new_rows))
            for left, right in zip(old_rows, new_rows):
                self.assertEqual(left[0], right[0])
                if left[0] not in selected: self.assertEqual(left, right)
        self.assertEqual(total, 27)

    def test_tampered_stub_interpreter_body_and_extra_zip_data_are_rejected(self):
        name, row = "pip.exe", rows["pip.exe"]
        valid = (Q / "launchers" / name).read_bytes()
        mutated = bytearray(valid)
        mutated[512] ^= 1
        with self.assertRaisesRegex(ValueError, "NATIVE_STUB_CHANGED"): validate_launcher(bytes(mutated), row)
        start, end = len(stub), valid.index(b"\n", len(stub)) + 1
        with self.assertRaisesRegex(ValueError, "INTERPRETER_BINDING_CHANGED"):
            validate_launcher(valid[:start] + b"#!C:\\unbound\\python.exe\n" + valid[end:], row)
        with self.assertRaisesRegex(ValueError, "ZIP_TRAILING_OR_COMMENT_DATA"): validate_launcher(valid + b"unclassified", row)
        for entries, reason in (({"__main__.py": b"raise SystemExit(0)\n"}, "ENTRY_POINT_BODY_CHANGED"),
                                ({"__main__.py": b"raise SystemExit(0)\n", "extra.py": b"payload"}, "ZIP_DIRECTORY_CHANGED")):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as archive:
                for filename, body in entries.items(): archive.writestr(filename, body)
            with self.assertRaisesRegex(ValueError, reason): validate_launcher(valid[:end] + stream.getvalue(), row)

    def test_frozen_candidate_has_exact_expected_artifact_members(self):
        self.assertEqual({path.name for path in (Q / "launchers").iterdir()}, set(rows))
        self.assertEqual({path.parent.name for path in (Q / "metadata").rglob("RECORD")}, set(baseline["metadata"]))
        self.assertEqual(len(list((Q / "metadata").rglob("RECORD"))), 3)

    def test_exact_builder_emission_hook_refuses_wrong_repeated_and_nonbyte_emission(self):
        path = Q / "build_launchers.py"
        parsed = ast.parse(path.read_text())
        node = next(item for item in parsed.body if isinstance(item, ast.ClassDef) and item.name == "CandidateEmission")
        namespace = {"Path": Path}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
        target = FIX / "emission-only.exe"
        emitted = namespace["CandidateEmission"](target)
        for candidate, data in ((FIX / "foreign.exe", b"bytes"), (target, "text")):
            with self.assertRaises(ValueError): emitted.write_binary_file(str(candidate), data)
        self.assertIsNone(emitted.data)
        emitted.write_binary_file(str(target), b"bytes")
        self.assertEqual(emitted.data, b"bytes")
        with self.assertRaises(ValueError): emitted.write_binary_file(str(target), b"replacement")
        self.assertFalse(target.exists())

    def test_exact_builder_csv_helpers_preserve_quotes_and_reject_malformed_fields(self):
        path = Q / "build_launchers.py"
        parsed = ast.parse(path.read_text())
        nodes = [item for item in parsed.body if isinstance(item, ast.FunctionDef) and item.name in {"csv_field_spans", "csv_replacement"}]
        self.assertEqual(len(nodes), 2)
        namespace = {"csv": csv, "io": io}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
        source = b'"../../Scripts/pip.exe","sha256=old","108489"'
        spans = namespace["csv_field_spans"](source)
        self.assertEqual(len(spans), 3)
        self.assertEqual(namespace["csv_replacement"](source[slice(*spans[1])], "sha256=old", "sha256=new"), b'"sha256=new"')
        self.assertEqual(namespace["csv_replacement"](source[slice(*spans[2])], "108489", "108456"), b'"108456"')
        for malformed in (b'"unclosed,hash,size', b"path,hash,size,extra"):
            with self.assertRaises(ValueError): namespace["csv_field_spans"](malformed)
        with self.assertRaises(ValueError): namespace["csv_replacement"](b"sha256=other", "sha256=old", "sha256=new")

class NativeReviewTests(unittest.TestCase):
    def test_all_27_declared_targets_import_as_callable_without_invoking_functions(self):
        script = FIX / "read_only_callable_probe.py"
        targets = [[name, *row["entry_point_value"].split(":", 1)] for name, row in rows.items()]
        body = "import hashlib,importlib,json\nfrom pathlib import Path\n"
        body += "site = Path(" + repr(str(SITE)) + ")\nresults = []\n"
        body += "for name,module_name,symbol in " + repr(targets) + ":\n"
        body += "    module = importlib.import_module(module_name)\n    value = getattr(module,symbol)\n    assert callable(value)\n"
        body += "    origin = Path(module.__file__).resolve()\n    assert origin.is_relative_to(site)\n"
        body += "    results.append({'launcher':name,'module':module_name,'symbol':symbol,'origin':str(origin),'sha256':hashlib.sha256(origin.read_bytes()).hexdigest(),'called':False})\n"
        body += "print(json.dumps(results))\n"
        script.open("x", encoding="utf-8").write(body)
        receipt = run_owned("read-only-callable-imports", E3 / "Scripts/python.exe", ("-B", "-X", "utf8", str(script)), 0)
        observed = json.loads(receipt["stdout"])
        self.assertEqual({item["launcher"] for item in observed}, set(rows))
        self.assertEqual(len(observed), 27)
        self.assertTrue(all(item["called"] is False for item in observed))

    def test_actual_all_three_pip_aliases_resolve_current_environment(self):
        for name in ("pip.exe", "pip3.exe", "pip3.12.exe"):
            image = FIX / ("review-" + name)
            shutil.copyfile(Q / "launchers" / name, image)
            self.assertEqual(sha(image.read_bytes()), sha((Q / "launchers" / name).read_bytes()))
            receipt = run_owned(name.replace(".", "-"), image, ("--disable-pip-version-check", "--version"), 0)
            self.assertIn("pip 25.0.1", receipt["stdout"])
            self.assertIn("(python 3.12)", receipt["stdout"])
            self.assertIn(str(SITE / "pip"), receipt["stdout"])
            self.assertNotIn("CETA_Intelligence_Operating_System_Build_Package", receipt["stdout"])

    def test_actual_schema_valid_and_invalid_instances_use_current_launcher(self):
        schema, positive, negative = FIX / "schema.json", FIX / "positive.json", FIX / "negative.json"
        for path, value in ((schema, {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"], "additionalProperties": False}),
                            (positive, {"count": 4}), (negative, {"count": "invalid"})):
            write(path, value)
        image = FIX / "review-jsonschema.exe"
        shutil.copyfile(Q / "launchers/jsonschema.exe", image)
        good = run_owned("schema-valid", image, ("--instance", str(positive), str(schema)), 0)
        bad = run_owned("schema-invalid", image, ("--instance", str(negative), str(schema)), 1)
        self.assertNotIn("Fatal error in launcher", good["stderr"] + good["stdout"])
        self.assertIn("is not of type", bad["stderr"] + bad["stdout"])

    def test_actual_old_shebang_failure_is_preserved_without_E3_execution(self):
        image = FIX / "review-original-pip.exe"
        shutil.copyfile(E3 / "Scripts/pip.exe", image)
        receipt = run_owned("original-stale-pip", image, ("--version",), 1)
        self.assertEqual(sha(image.read_bytes()), rows["pip.exe"]["source"]["sha256"])
        old_target = rows["pip.exe"]["original_shebang"][2:]
        self.assertIn("CETA_Intelligence_Operating_System_Build_Package", old_target)
        self.assertFalse(Path(old_target).exists())
        self.assertNotIn("pip 25.0.1", receipt["stdout"])
        # The actual no-window invocation may return no diagnostic text.
        # Qualify the observed exit and static absent interpreter binding only.

suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ArtifactReviewTests),
                          unittest.defaultTestLoader.loadTestsFromTestCase(NativeReviewTests)])
cases = []
class Result(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.status = "PASS"
        self.started = time.perf_counter()
    def addFailure(self, test, error): self.status = "FAIL"; super().addFailure(test, error)
    def addError(self, test, error): self.status = "ERROR"; super().addError(test, error)
    def addSubTest(self, test, subtest, error):
        if error is not None: self.status = "FAIL"
        super().addSubTest(test, subtest, error)
    def stopTest(self, test):
        cases.append({"id": test.id(), "status": self.status, "seconds": time.perf_counter() - self.started})
        super().stopTest(test)
with (V / "review-tests-r3.txt").open("x", encoding="utf-8", buffering=1) as raw:
    result = unittest.TextTestRunner(stream=raw, verbosity=2, resultclass=Result).run(suite)
after = {str(path.relative_to(Q)): sha(path.read_bytes()) for path in Q.rglob("*") if path.is_file()}
assert before == after
assert sha(custody_source.read_bytes()) == custody_sha
for row in rows.values():
    assert sha((E3 / "Scripts" / row["filename"]).read_bytes()) == row["source"]["sha256"]
for info_name, meta in baseline["metadata"].items():
    assert sha((SITE / info_name / "RECORD").read_bytes()) == meta["RECORD"]["sha256"]
origins = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if name == "ceta" or name.startswith("ceta.") if getattr(module, "__file__", None)}
assert all(Path(path).is_relative_to(F / "src") for path in origins.values())
report = {"started_at": started, "finished_at": utc(), "tests": result.testsRun, "cases": cases,
    "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
    "successful": result.wasSuccessful() and not result.skipped, "native_cli_invocations": commands,
    "source_inventory_sha256": sha((V / "source-inventory-r1.json").read_bytes()), "candidate_before": before,
    "candidate_after": after, "raw_sha256": sha((V / "review-tests-r3.txt").read_bytes()),
    "native_custody_source": {"path": str(custody_source), "sha256": custody_sha}, "ceta_imports": origins,
    "fixtures_retained": str(FIX), "limits": ["All 23 Qt GUI/server/deployment functions remain unexecuted",
        "Native checks cover safe version/schema CLI paths only; no package install, network reference, active environment or configuration publication",
        "Original stale failure is an expected negative child result; it is not a passing launcher invocation",
        "Stub and existing main-script reuse contribute zero new product LOC"]}
write(V / "review-tests-r3.json", report)
print(json.dumps({"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
    "skips": len(result.skipped), "native_cli_invocations": len(commands), "source_and_candidate_unchanged": before == after,
    "report_sha256": sha((V / "review-tests-r3.json").read_bytes())}))
sys.exit(0 if report["successful"] else 1)
