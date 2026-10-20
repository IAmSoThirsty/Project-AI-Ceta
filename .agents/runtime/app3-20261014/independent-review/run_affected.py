"""Independent final-cut source coverage, real Qt recovery and resource cohort."""
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

R = Path(__file__).resolve().parent
S = R.parents[3]
Q = S / ".agents/app3-20261014"
WR = S / ".agents/runtime/app3-20261014"
PY = S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
assert Path(sys.executable).resolve() == PY.resolve()
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
tmp = R / "test-tmp"
tmp.mkdir()
os.environ["TMP"] = os.environ["TEMP"] = str(tmp)
sys.path[:0] = [str(Q / "src"), str(Q / "tests/contract"), str(Q / "tools")]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def now():
    return datetime.now(timezone.utc).isoformat()
def ids(suite):
    if isinstance(suite, unittest.TestSuite):
        for child in suite:
            yield from ids(child)
    else:
        yield suite.id()
def fixture_inventory():
    roots = [Q / ".agents/fixtures", Q / ".local-test-output"]
    return sorted({str(path) for root in roots if root.is_dir() for path in root.rglob("*")})

manifest_path = Q / "TRANSFER-MANIFEST.json"
assert sha(manifest_path) == json.loads((WR / "implement.json").read_text())["result"]["manifest_sha256"]
manifest = json.loads(manifest_path.read_text())
before = {entry["relative_path"]: sha(Q / entry["relative_path"]) for entry in manifest["payloads"]}
assert all(before[e["relative_path"]] == e["candidate_sha256"] for e in manifest["payloads"])
fixtures_before = fixture_inventory()
started, tick = now(), time.monotonic()
imports = []
for path in sorted((Q / "src/ceta").rglob("*.py")):
    parts = list(path.relative_to(Q / "src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    name = ".".join(parts)
    module = importlib.import_module(name)
    actual = Path(module.__file__).resolve()
    assert actual == path.resolve(), (name, actual, path)
    imports.append({"module": name, "path": str(actual), "sha256": sha(actual)})
assert len(imports) == 72
selectors = ["test_source_coverage", "test_task_meaning_view", "test_resource_management", "test_source_references", "test_task_view", "test_editor_recovery", "test_process_diagnostics", "test_windows_jobs"]
suite = unittest.TestLoader().loadTestsFromNames(selectors)
expected_ids = list(ids(suite))
assert len(expected_ids) == len(set(expected_ids)) and len(expected_ids) > 220
assert not any("_FailedTest" in test_id for test_id in expected_ids)
class ObservedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = []
    def startTest(self, test):
        self.executed_ids.append(test.id())
        super().startTest(test)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=ObservedResult).run(suite)
raw_path = R / "affected-r1.txt"
with raw_path.open("x", encoding="utf-8") as out:
    out.write(stream.getvalue())
after = {entry["relative_path"]: sha(Q / entry["relative_path"]) for entry in manifest["payloads"]}
for name, module in tuple(sys.modules.items()):
    if name == "ceta" or name.startswith("ceta."):
        assert Path(module.__file__).resolve().is_relative_to(Q / "src"), (name, module.__file__)
client, service = str(Q / "src/ceta/composition/client_process.py"), str(Q / "src/ceta/composition/service_process.py")
ps = "$a='" + client + "';$b='" + service + "';$children=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.Name -like 'python*.exe' -and $_.CommandLine -and ($_.CommandLine.Contains($a) -or $_.CommandLine.Contains($b)) } | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath);[pscustomobject]@{clear=($children.Count -eq 0);children=$children}|ConvertTo-Json -Depth 4 -Compress"
census_argv = ["powershell", "-NoProfile", "-Command", ps]
census = subprocess.run(census_argv, capture_output=True)
with (R / "native-census-r1.stdout").open("xb") as out:
    out.write(census.stdout)
with (R / "native-census-r1.stderr").open("xb") as out:
    out.write(census.stderr)
census_value = json.loads(census.stdout) if census.returncode == 0 else {"clear": False}
fixtures_after = fixture_inventory()
passed = result.wasSuccessful() and not result.skipped and expected_ids == result.executed_ids and before == after and census.returncode == 0 and census_value["clear"]
record = {"schema_version": 1, "started_at": started, "finished_at": now(), "elapsed_seconds": time.monotonic() - tick,
          "reviewer": "/root/pressure_review", "subject": str(Q), "manifest_sha256": sha(manifest_path),
          "command_argv": [sys.executable, "-B", "-X", "utf8", str(Path(__file__))],
          "selectors": selectors, "expected_test_ids": expected_ids, "executed_test_ids": result.executed_ids,
          "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
          "failure_details": [{"test_id": test.id(), "traceback": trace} for test, trace in result.failures + result.errors],
          "before_hashes": before, "after_hashes": after, "source_unchanged": before == after,
          "imports": imports, "module_count": 72, "all_ceta_imports_inside_app3": True,
          "raw_path": str(raw_path), "raw_sha256": sha(raw_path), "native_census": {"argv": census_argv, "exit_status": census.returncode, "result": census_value},
          "fixture_inventory_before": fixtures_before, "fixture_inventory_after": fixtures_after,
          "new_remaining_fixture_members": sorted(set(fixtures_after) - set(fixtures_before)),
          "preexisting_fixture_members_removed": sorted(set(fixtures_before) - set(fixtures_after)),
          "exit_status": 0 if passed else 1}
with (R / "affected-r1.json").open("x", encoding="utf-8") as out:
    json.dump(record, out, indent=2)
    out.write("\n")
print(json.dumps({key: record[key] for key in ("tests_run", "failures", "errors", "skips", "source_unchanged", "elapsed_seconds", "exit_status")}, indent=2))
sys.exit(record["exit_status"])
