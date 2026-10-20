"""Actual retained Windows handle: coarse clock can hide an overlong check."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import sys
import time
import unittest
from unittest.mock import patch

F = Path(r"T:\00-Active\Project-AI-CETA")
R = F / ".agents/runtime/gd1-20261014"
S = Path(sys.argv[1]) if len(sys.argv) > 1 else F
TAG = sys.argv[2] if len(sys.argv) > 2 else "baseline-r1"
sys.path[:0] = [str(S / "src"), str(S / "tests/contract")]
from ceta.resource.diagnostics import OwnedProcessTelemetrySampler
from test_process_diagnostics import digest
import test_windows_jobs as jobs
jobs.ROOT = R
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = sha(S / "src/ceta/resource/diagnostics.py")
observations = []


class NativePrecisionProbe(unittest.TestCase):
    setUp, tearDown = jobs.WindowsJobTests.setUp, jobs.WindowsJobTests.tearDown
    until, event, launch, simple = jobs.WindowsJobTests.until, jobs.WindowsJobTests.event, jobs.WindowsJobTests.launch, jobs.WindowsJobTests.simple
    def test_native_currentness_delay_exceeding_bound_is_never_a_measurement(self):
        process, release, _ = self.simple()
        sampler = OwnedProcessTelemetrySampler(process, process.resource_identity,
            scope_digest=digest("gd1-scope"), environment_digest=digest("gd1-env"),
            workload_digest=digest("gd1-idle"), source_generation=1,
            minimum_interval_ns=100_000_000, maximum_age_ns=1_000_000_000,
            maximum_probe_window_ns=5_000_000)
        measured = sampler.sample()
        self.assertTrue(measured.memory_bytes.measured)
        real = process.resource_observation_current
        def delayed(identity):
            value = real(identity)
            begin = time.perf_counter_ns()
            while time.perf_counter_ns() - begin < 6_000_000:
                pass
            return value
        try:
            with patch.object(process, "resource_observation_current", side_effect=delayed):
                for attempt in range(8):
                    tick = time.monotonic_ns()
                    begin = time.perf_counter_ns()
                    sample = sampler.sample()
                    elapsed = time.perf_counter_ns() - begin
                    coarse = time.monotonic_ns() - tick
                    observations.append({"pid": process.pid, "creation_time": process.creation_time,
                        "attempt": attempt, "physical_elapsed_ns": elapsed, "public_clock_delta_ns": coarse,
                        "configured_window_ns": 5_000_000, "memory_measured": sample.memory_bytes.measured,
                        "reason": sample.cpu_milli.reason, "sequence": sample.source.sequence,
                        "same_cached_frame": sample is measured})
                    self.assertGreater(elapsed, 5_000_000)
                    self.assertFalse(sample.memory_bytes.measured, observations[-1])
        finally:
            release.signal()
            self.assertTrue(process.wait(5))
            self.until(lambda: process.active_process_count() == 0)
            observations.append({"pid": process.pid, "creation_time": process.creation_time,
                "child_exit_observed": process.poll(), "active_job_members": process.active_process_count()})


started = datetime.now(timezone.utc).isoformat()
with (R / (TAG + ".txt")).open("x", encoding="utf-8") as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(NativePrecisionProbe))
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if (name == "ceta" or name.startswith("ceta.")) and getattr(module, "__file__", None)}
assert all(Path(path).is_relative_to(S / "src") for path in imports.values())
report = {"started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
          "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
          "skips": len(result.skipped), "source": str(S), "source_before_sha256": before,
          "source_after_sha256": sha(S / "src/ceta/resource/diagnostics.py"), "imports": imports,
          "native_observations": observations,
          "clock_info": {name: vars(time.get_clock_info(name)) for name in ("monotonic", "perf_counter")},
          "fault_stimulus": "Real owner currentness call plus explicit 6 ms scheduling delay; no mocked sensor result",
          "passed": result.wasSuccessful()}
assert report["source_before_sha256"] == report["source_after_sha256"]
with (R / (TAG + ".json")).open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps({"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                  "native_observations": observations, "source_sha256": before}), flush=True)
sys.exit(0 if result.wasSuccessful() else 1)
