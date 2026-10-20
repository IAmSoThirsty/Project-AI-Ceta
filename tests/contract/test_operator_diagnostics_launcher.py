"""Finite launcher and cleanup boundaries; controlled service, no native launch."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError, RecordCodec, strict_loads
from ceta.resource.diagnostics import PerformanceEnvelope
import test_shutdown_lifecycle as lifecycle

ROOT = Path(__file__).resolve().parents[2]


def launcher():
    spec = importlib.util.spec_from_file_location("diagnostics_launcher_fixture", ROOT / "tools/ceta_operator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Service(lifecycle._ControlledService):
    """Only the process/lifecycle transport boundary is controlled here."""
    def __init__(self):
        super().__init__()
        self.state = "STARTING"
        self.operation_error = None
        self.operation_state = "COMPLETE_PROCESS_USAGE"
        self.calls = []
    def start(self):
        super().start()
        self.state = "READY"
    def snapshot(self): return {"state": self.state, "generation": "a" * 64}
    def resource_diagnostics(self, **kwargs):
        self.calls.append(kwargs)
        if self.operation_error is not None: raise self.operation_error
        return {"state": self.operation_state}


class DiagnosticsLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
    def setUp(self):
        self.module, self.service = launcher(), Service()
        self.envelope = PerformanceEnvelope(20, 2000, 4096)
    def invoke(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = self.module._run_owned_diagnostics(self.service, self.codec, self.envelope)
        return status, json.loads(out.getvalue())

    def test_result_prints_only_after_stop_and_preserves_generation_envelope(self):
        status, result = self.invoke()
        self.assertEqual(status, 0)
        self.assertEqual(result, {"startup": "READY", "operation": "COMPLETE_PROCESS_USAGE",
                                 "diagnostics": {"state": "COMPLETE_PROCESS_USAGE"}, "cleanup": "STOPPED"})
        self.assertEqual(self.service.state, "STOPPED")
        self.assertEqual(self.service.calls[0]["expected_generation"], "a" * 64)
        self.assertIs(self.service.calls[0]["envelope"], self.envelope)

    def test_unavailable_operation_does_not_become_startup_failure(self):
        self.service.operation_error = ContractError("DIAGNOSTICS_PROCESS_UNAVAILABLE")
        status, result = self.invoke()
        self.assertEqual(status, 2)
        self.assertEqual((result["startup"], result["operation"], result["cleanup"]), ("READY", "UNAVAILABLE", "STOPPED"))
        self.assertNotIn("diagnostics", result)

    def test_incomplete_measurements_have_nonzero_exit(self):
        self.service.operation_state = "UNAVAILABLE_PROCESS_USAGE"
        status, result = self.invoke()
        self.assertEqual(status, 2)
        self.assertEqual(result["operation"], "UNAVAILABLE_PROCESS_USAGE")

    def test_startup_denial_keeps_operation_not_executed(self):
        def denied_start(): self.service.started = True; self.service.state = "RECOVERING"
        self.service.start = denied_start
        status, result = self.invoke()
        self.assertEqual(status, 2)
        self.assertEqual((result["startup"], result["operation"]), ("UNAVAILABLE", "NOT_EXECUTED"))
        self.assertEqual(self.service.calls, [])

    def test_start_method_failure_reports_no_operation_after_cleanup(self):
        self.service.start_error = ContractError("CONTROLLED_START_FAILURE")
        status, result = self.invoke()
        self.assertEqual(status, 2)
        self.assertEqual((result["startup"], result["operation"], result["cleanup"]),
                         ("UNAVAILABLE", "NOT_EXECUTED", "STOPPED"))
        self.assertEqual(self.service.calls, [])

    def test_operation_interruption_preserves_exact_primary_and_cleans_up(self):
        primary = KeyboardInterrupt("controlled operation interruption")
        self.service.operation_error = primary
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(KeyboardInterrupt) as caught:
            self.module._run_owned_diagnostics(self.service, self.codec, self.envelope)
        self.assertIs(caught.exception, primary)
        self.assertEqual(self.service.state, "STOPPED")
        self.assertEqual(out.getvalue(), "")

    def test_journal_custody_failure_is_not_flattened_into_json(self):
        primary = ContractError("JOURNAL_CLOSE_UNCERTAIN")
        primary.journal_custody = object()
        self.service.operation_error = primary
        with self.assertRaises(ContractError) as caught: self.invoke()
        self.assertIs(caught.exception, primary)
        self.assertEqual(self.service.state, "STOPPED")

    def test_cleanup_failure_never_publishes_measurement_success(self):
        primary = KeyboardInterrupt("controlled cleanup interruption")
        original_stop = self.service.request_stop
        def failed_stop(*args, **kwargs):
            self.service.poll_error = primary
            return original_stop(*args, **kwargs)
        self.service.request_stop = failed_stop
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(KeyboardInterrupt) as caught:
            self.module._run_owned_diagnostics(self.service, self.codec, self.envelope)
        self.assertIs(caught.exception, primary)
        self.assertEqual(out.getvalue(), "")
        self.assertIsNotNone(self.module._attached_shutdown_incomplete(primary))
        self.assertEqual(len(self.service.calls), 1)

    def test_main_headless_route_does_not_import_gui(self):
        import builtins
        original = builtins.__import__
        def no_gui(name, *args, **kwargs):
            if name.startswith("PySide6") or name.startswith("ceta.desktop"):
                raise AssertionError("headless path imported GUI")
            return original(name, *args, **kwargs)
        class Custody:
            def __init__(self, root): pass
            def reserve_launch(self): pass
            def close(self): pass
        with patch.object(sys, "argv", ["ceta_operator.py", "--diagnostics", "--diagnostics-envelope", "20", "2000", "4096"]),              patch.object(self.module, "LauncherShutdownCustody", Custody),              patch.object(self.module, "OwnedService", return_value=self.service),              patch.object(self.module, "_run_owned_diagnostics", return_value=(0, {"startup": "READY", "operation": "COMPLETE_PROCESS_USAGE", "cleanup": "STOPPED"})) as run,              patch.object(builtins, "__import__", side_effect=no_gui):
            self.assertEqual(self.module.main(), 0)
        self.assertEqual(run.call_count, 1)

    def test_main_custody_close_failure_never_prints_final_success(self):
        primary = RuntimeError("controlled custody close failure")
        class Custody:
            def __init__(self, root): pass
            def reserve_launch(self): pass
            def close(self): raise primary
        out = io.StringIO()
        with patch.object(sys, "argv", ["ceta_operator.py", "--diagnostics", "--diagnostics-envelope", "20", "2000", "4096"]), \
             patch.object(self.module, "LauncherShutdownCustody", Custody), \
             patch.object(self.module, "OwnedService", return_value=self.service), \
             patch.object(self.module, "_run_owned_diagnostics", return_value=(0, {"state": "COMPLETE_PROCESS_USAGE"})), \
             contextlib.redirect_stdout(out), self.assertRaises(RuntimeError) as caught:
            self.module.main()
        self.assertIs(caught.exception, primary)
        self.assertEqual(out.getvalue(), "")

    def test_envelope_required_and_invalid_arguments_rejected_before_profile(self):
        for args in (["--diagnostics"], ["--diagnostics", "--diagnostics-envelope", "-1", "1", "1"],
                     ["--diagnostics-envelope", "1", "1", "1"],
                     ["--diagnostics", "--inspector", "--diagnostics-envelope", "1", "1", "1"]):
            with self.subTest(args=args), patch.object(sys, "argv", ["ceta_operator.py", *args]),                  patch.object(self.module, "OwnedService", side_effect=AssertionError("unexpected service")),                  patch.object(self.module, "LauncherShutdownCustody", side_effect=AssertionError("unexpected custody")),                  patch.object(self.module, "_validate_profile_root", side_effect=AssertionError("unexpected profile")),                  contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                self.module.main()
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__": unittest.main()
