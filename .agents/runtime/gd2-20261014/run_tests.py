from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/gd2-20261014", F / ".agents/runtime/gd2-20261014"
E3 = F / ".agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

if sys.argv[1] != "worker":
    stem, modules = sys.argv[1], sys.argv[2:]
    command = [str(E3), "-B", "-X", "utf8", str(Path(__file__)), "worker", stem, *modules]
    started = datetime.now(timezone.utc).isoformat()
    with (R / (stem + ".txt")).open("x", encoding="utf-8") as raw:
        result = subprocess.run(command, cwd=r"T:\00-Active", stdout=raw, stderr=subprocess.STDOUT,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    (R / (stem + "-command.json")).open("x", encoding="utf-8").write(json.dumps({
        "command": command, "cwd": r"T:\00-Active", "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(), "exit_status": result.returncode,
        "raw_log_sha256": sha(R / (stem + ".txt"))}, indent=2) + "\n")
    print((R / (stem + ".txt")).read_text(encoding="utf-8")[-1200:])
    if (R / (stem + ".json")).exists():
        data = json.loads((R / (stem + ".json")).read_text())
        print(json.dumps({k: data[k] for k in ("tests_run", "failures", "errors", "skipped", "seconds", "successful")}))
    sys.exit(result.returncode)

stem, modules = sys.argv[2], sys.argv[3:]
sys.path[:0] = [str(Q / "src"), str(Q / "tests/contract")]
started = datetime.now(timezone.utc).isoformat()
paths = ("src/ceta/resource/diagnostics.py", "src/ceta/resource/hardware.py", "src/ceta/contracts/resource_management.py",
         "tests/contract/test_process_observation_timing.py", "tests/contract/test_process_observation_validation.py")
before = {p: sha(Q / p) for p in paths}
cases = []

class Result(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.current_start = time.perf_counter()
        self.current_status = "PASS"
    def addFailure(self, test, error):
        self.current_status = "FAIL"
        super().addFailure(test, error)
    def addError(self, test, error):
        self.current_status = "ERROR"
        super().addError(test, error)
    def addSkip(self, test, reason):
        self.current_status = "SKIP"
        super().addSkip(test, reason)
    def addSubTest(self, test, subtest, error):
        if error is not None:
            self.current_status = "FAIL" if issubclass(error[0], test.failureException) else "ERROR"
        super().addSubTest(test, subtest, error)
    def stopTest(self, test):
        cases.append({"id": test.id(), "status": self.current_status, "seconds": time.perf_counter() - self.current_start})
        super().stopTest(test)

suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
count = suite.countTestCases()
print(json.dumps({"started_at": started, "candidate": str(Q), "test_count": count, "source_sha256": before}), flush=True)
begin = time.perf_counter()
result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
elapsed = time.perf_counter() - begin
assert len(cases) == count == result.testsRun
assert len({case['id'] for case in cases}) == count, 'Duplicate imported test IDs'
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if name == "ceta" or name.startswith("ceta.") if getattr(module, "__file__", None)}
assert imports and all(Path(path).is_relative_to(Q / "src") for path in imports.values()), imports
after = {p: sha(Q / p) for p in paths}
assert before == after
data = {"started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(), "modules": modules,
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "seconds": elapsed, "successful": result.wasSuccessful(),
        "cases": cases, "imports": imports, "source_before_sha256": before, "source_after_sha256": after,
        "integration_limit": "Actual retained Windows owner handles feed the existing recorder/analyzer. Injected clocks are explicit deterministic tests; native fault stimuli are explicit delays. Canonical evidence/principal, durable recovery, workload latency and causal integration remain open."}
native_module = sys.modules.get("test_process_observation_timing")
data["native_observations"] = getattr(native_module, "NATIVE_OBSERVATIONS", [])
data["clock_info"] = {name: vars(time.get_clock_info(name)) for name in ("monotonic", "perf_counter")}
(R / (stem + ".json")).open("x", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)

