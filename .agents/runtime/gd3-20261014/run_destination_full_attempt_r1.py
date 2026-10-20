"""Stream exact active-source results with dependency and crash evidence kept separate."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
import traceback
import unittest

S = Path(__file__).resolve().parents[3]
R = S / ".agents/runtime/gd3-20261014/active-application"
PY = S / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
assert Path(sys.executable) == PY
tag = 'r1'
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
temporary = R / ("tmp-" + tag)
temporary.mkdir(exist_ok=False)
os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
sys.path[:0] = [str(S / "src"), str(S / "tools"), str(S / "tests/contract")]
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(p, value):
    with p.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

base_path = S / '.agents/runtime/hd2-20261014/active-application/destination-full-r1.json'
assert sha(base_path) == 'e7aa79e76d6277a719070e6fb573121bb230a0c297af0447b829d4d53f495057'
baseline = read(base_path)
assert baseline['exit_status'] == 0 and baseline['tests_run'] == 1281 and baseline['source_unchanged']
expected = dict(baseline['after_hashes'])
assert len(expected) == 279
cut_path = S / '.agents/gd3-20261014/TRANSFER-MANIFEST.json'
assert sha(cut_path) == 'bb070146f6516f928e2ead8e590436f853332e2393ce8fa2687655f3424f5239'
manifest = read(cut_path)
overridden = set()
for item in manifest['payloads']:
    relative = item['relative_path']
    if item['action'] in {'CREATE', 'EXTEND'}:
        overridden.add(relative)
    elif relative in expected:
        assert expected[relative] == item['candidate_sha256']
    assert sha(S / '.agents/gd3-20261014' / relative) == item['candidate_sha256']
    expected[relative] = item['candidate_sha256']
assert overridden == {'src/ceta/resource/diagnostics.py', 'contracts/PROCESS_DIAGNOSTICS_V1.md',
                      'tests/contract/test_process_observation_timing.py', 'tests/contract/test_process_observation_validation.py'}
assert len(expected) == 281
cut_bindings = [{'path': str(p), 'sha256': sha(p)} for p in (base_path, cut_path)]
before = {relative: sha(S / relative) for relative in sorted(expected)}
assert before == expected
started = now()
dependencies = []
for distribution, name in (("PySide6", "PySide6"), ("PySide6_Essentials", "PySide6"), ("shiboken6", "shiboken6"),
                           ("jsonschema", "jsonschema"), ("attrs", "attrs"),
                           ("referencing", "referencing"), ("rpds-py", "rpds")):
    module = importlib.import_module(name)
    path = Path(module.__file__).resolve()
    assert path.is_relative_to(PY.parent.parent / "Lib/site-packages"), (name, path)
    try:
        version = importlib.metadata.version(distribution)
        state = "AVAILABLE"
    except importlib.metadata.PackageNotFoundError:
        version, state = None, "UNAVAILABLE_DISTRIBUTION_METADATA"
    dependencies.append({"distribution": distribution, "module": name, "distribution_version": version,
                         "distribution_metadata_state": state, "declared_module_version": vars(module).get("__version__"),
                         "actual_path": str(path), "module_file_sha256": sha(path)})
modules = []
for path in sorted((S / "src/ceta").rglob("*.py")):
    parts = list(path.relative_to(S / "src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    name = ".".join(parts)
    module = importlib.import_module(name)
    actual = Path(module.__file__).resolve()
    assert actual.is_relative_to(S / "src"), (name, actual)
    modules.append({"module": name, "actual_path": str(actual), "sha256": sha(actual)})
assert len(modules) == 72
suite = unittest.TestLoader().discover(str(S / "tests/contract"), pattern="test_*.py")
def ids(value):
    if isinstance(value, unittest.TestSuite):
        for child in value:
            yield from ids(child)
    else:
        yield value.id()
expected_ids = list(ids(suite))
assert len(expected_ids) == len(set(expected_ids)) == 1326 and not any("_FailedTest" in name for name in expected_ids)
preflight = {"schema_version": 1, "started_at": started, "root": str(S), "cut_bindings": cut_bindings,
             "expected_payload_hashes": expected, "before_hashes": before, "expected_ids": expected_ids,
             "imports": modules, "dependencies": dependencies, "python_executable": str(PY),
             "python_sha256": sha(PY), "overridden_reviewed_paths": sorted(overridden)}
save(R / ("destination-full-" + tag + "-preflight.json"), preflight)
class ObservedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed_ids = []
    def startTest(self, test):
        self.executed_ids.append(test.id())
        super().startTest(test)

log_path = R / ("destination-full-" + tag + ".txt")
try:
    with log_path.open("x", encoding="utf-8", buffering=1) as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=ObservedResult).run(suite)
    after = {relative: sha(S / relative) for relative in sorted(expected)}
    service_paths = [str(S / "src/ceta/composition/client_process.py"), str(S / "src/ceta/composition/service_process.py")]
    ps = ("$a='" + service_paths[0] + "';$b='" + service_paths[1] + "';"
          "$children=@(Get-CimInstance Win32_Process | Where-Object { $p=$_; $p.ProcessId -ne $PID -and "
          "$p.Name -like 'python*.exe' -and $p.CommandLine -and ($p.CommandLine.Contains($a) -or $p.CommandLine.Contains($b)) } "
          "| Select-Object ProcessId,ParentProcessId,Name,ExecutablePath);"
          "[pscustomobject]@{clear=($children.Count -eq 0);children=$children}|ConvertTo-Json -Depth 4 -Compress")
    argv = ["powershell", "-NoProfile", "-Command", ps]
    census = subprocess.run(argv, capture_output=True)
    census_value = json.loads(census.stdout) if census.returncode == 0 else {"clear": False}
    for suffix, data in (("stdout", census.stdout), ("stderr", census.stderr)):
        with (R / ("destination-native-census-" + tag + "." + suffix)).open("xb") as stream:
            stream.write(data)
    passed = (result.wasSuccessful() and not result.skipped and before == after and
              result.executed_ids == expected_ids and census.returncode == 0 and census_value["clear"])
    record = {**preflight, "finished_at": now(), "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
              "executed_ids": result.executed_ids, "failed_ids": [test.id() for test, _ in result.failures + result.errors],
              "skip_details": [{"id": test.id(), "reason": reason} for test, reason in result.skipped],
              "after_hashes": after, "source_unchanged": before == after,
              "output_sha256": sha(log_path), "native_census": {"argv": argv, "exit_status": census.returncode,
              "result": census_value}, "exit_status": 0 if passed else 1}
    save(R / ("destination-full-" + tag + ".json"), record)
    print(json.dumps({key: record[key] for key in ("root", "tests_run", "failures", "errors", "skips",
                                                  "source_unchanged", "failed_ids", "exit_status")}))
except BaseException as failure:
    save(R / ("destination-full-" + tag + "-writer-failure.json"), {
        "recorded_at": now(), "type": type(failure).__name__, "traceback": traceback.format_exc(),
        "test_log": str(log_path), "test_log_sha256": sha(log_path) if log_path.is_file() else None,
        "preflight": str(R / ("destination-full-" + tag + "-preflight.json")), "exit_status": 1})
    raise

# A normal completed exit must not enter the interruption failure handler.
sys.exit(record["exit_status"])
