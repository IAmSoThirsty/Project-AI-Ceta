"""Actual disposable SQLite and public operator seam; controlled process boundary."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch
import uuid

from ceta.application.operator import OperatorSession
from ceta.composition.owned_service import OwnedService
from ceta.composition import resource_diagnostics as collector
from ceta.contracts.resource_management import (ProcessResourceIdentity, ProcessResourceCounters,
    ProcessUsageMeasurements, QuantityObservation, ObservationState)
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.wire import ContractError, RecordCodec, strict_loads
from ceta.resource.diagnostics import PerformanceEnvelope
from ceta.store.journal import SqliteJournal
from test_store_transactions import entry

ROOT = Path(__file__).resolve().parents[2]
GENERATION = "a" * 64
INSTALLATION = "installation:diagnostics-fixture"
SCOPES = (INSTALLATION, "project:diagnostics-fixture")


class ProcessPort:
    """Controlled counters implement the exact borrowed native observation port."""
    def __init__(self, now, pid):
        self.now, self.calls, self.alive, self.unavailable = now, 0, True, False
        self.resource_identity = ProcessResourceIdentity(pid, 1001, "sha256:" + "1" * 64)
    def resource_observation_current(self, identity):
        return self.alive and identity == self.resource_identity
    def resource_counters(self):
        self.calls += 1
        at = self.now[0]
        def q(value):
            return QuantityObservation(ObservationState.MEASURED, value, at, "fixture")
        read = (QuantityObservation(ObservationState.UNAVAILABLE, None, at, "fixture", "PROCESS_IO_QUERY_FAILED")
                if self.unavailable else q(at // 100))
        return ProcessResourceCounters(self.resource_identity, at, q(1000),
            ProcessUsageMeasurements(at, q(at // 10), q(900), read, q(at // 200)))
    def close(self): raise AssertionError("borrowed process closed")
    def terminate(self): raise AssertionError("borrowed process terminated")


class OperatorResourceDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / ".agents/fixtures/opdiag" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
        self.writer = SqliteJournal(self.root, self.codec, SCOPES, create=True, profile=STORE_PROFILE)
        self.service = OwnedService(self.root, self.codec, INSTALLATION, SCOPES)
        self.now = [1_000_000_000]
        self.ports = [ProcessPort(self.now, 42), ProcessPort(self.now, 43)]
        self.service._service = SimpleNamespace(process=self.ports[0], _closed=False, _process_closed=False)
        self.service._client = SimpleNamespace(process=self.ports[1], _closed=False, _process_closed=False)
        self.service._generation, self.service._state = GENERATION, "READY"
        self.envelope = PerformanceEnvelope(20, 5000, 4096)
    def tearDown(self): self.writer.close()
    def wait(self, seconds): self.now[0] += round(seconds * 1_000_000_000)
    def collect(self, **kwargs):
        return collector.collect_owned_diagnostics(self.service, expected_generation=GENERATION,
            envelope=self.envelope, _clock=lambda: self.now[0], _wait=kwargs.pop("_wait", self.wait), **kwargs)
    def reject(self, code, **kwargs):
        with self.assertRaisesRegex(ContractError, code): self.collect(**kwargs)
    def commit(self, scope):
        point = self.writer.position(scope)
        self.writer.commit((point,), (entry(self.codec, point, uuid.uuid4().hex),))

    def test_public_application_real_journal_producer_consumer(self):
        """AT-CETA-20.05.01/02-09; controlled OS port, no native qualification."""
        session = OperatorSession(self.service, self.codec)
        session.set_draft("private draft must never enter diagnostics")
        original = collector.collect_owned_diagnostics
        def controlled(service, **kwargs):
            return original(service, **kwargs, _clock=lambda: self.now[0], _wait=self.wait)
        before = dict(session.__dict__)
        with patch.object(collector, "collect_owned_diagnostics", side_effect=controlled):
            result = session.resource_diagnostics(self.envelope)
        self.assertEqual(result["state"], "COMPLETE_PROCESS_USAGE")
        self.assertEqual(result["store_position"], {"next_commit": 0, "head": None})
        self.assertEqual(result["task_attribution"], "UNAVAILABLE_SHARED_RUNTIME_PROCESSES")
        self.assertEqual(result["latency"], "UNOBSERVED")
        self.assertEqual(result["envelope_status"], "CALLER_DECLARED_UNQUALIFIED")
        self.assertNotIn("private draft", repr(result))
        self.assertEqual(session.__dict__, before)
        self.assertTrue(all(p.calls == 2 for p in self.ports))
        self.assertEqual(self.writer.store_position().next_commit, 0)

    def test_public_collector_cancels_inside_constructor_sqlite_vm(self):
        from ceta.store.journal import SqliteJournal
        query = "WITH RECURSIVE n(x) AS (SELECT 0 UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT sum(x) FROM n"
        original, calls = SqliteJournal._verify, [0]
        def cancel():
            calls[0] += 1
            return calls[0] > 30
        def costly(instance, *args, **kwargs):
            instance._connection.execute(query).fetchone()
            return original(instance, *args, **kwargs)
        with patch.object(SqliteJournal, "_verify", new=costly):
            with self.assertRaisesRegex(ContractError, "JOURNAL_READ_CANCELLED") as caught:
                self.collect(cancelled=cancel)
        custody = caught.exception.journal_custody
        self.assertGreater(custody._read_budget.vm_steps, 0)
        self.assertTrue(custody._closed)
        self.assertEqual(self.writer.store_position().next_commit, 0)
        self.assertEqual([x.calls for x in self.ports], [0, 0])
        self.assertEqual(self.collect()["state"], "COMPLETE_PROCESS_USAGE")

    def test_collector_vm_control_exception_retains_exact_primary_and_closed_journal(self):
        from ceta.store.journal import SqliteJournal
        query = "WITH RECURSIVE n(x) AS (SELECT 0 UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT sum(x) FROM n"
        original = SqliteJournal._verify
        def costly(instance, *args, **kwargs):
            instance._connection.execute(query).fetchone()
            return original(instance, *args, **kwargs)
        for primary in (KeyboardInterrupt("collector VM"), SystemExit(43)):
            calls = [0]
            def cancel():
                calls[0] += 1
                if calls[0] > 30: raise primary
                return False
            with patch.object(SqliteJournal, "_verify", new=costly):
                with self.assertRaises(type(primary)) as caught: self.collect(cancelled=cancel)
            self.assertIs(caught.exception, primary)
            self.assertTrue(primary.journal_custody._closed)
            self.assertGreater(primary.journal_custody._read_budget.vm_steps, 0)
            self.assertEqual([x.calls for x in self.ports], [0, 0])
        self.assertEqual(self.collect()["state"], "COMPLETE_PROCESS_USAGE")

    def test_changed_global_other_scope_and_installation_journal_refused(self):
        for scope in SCOPES:
            with self.subTest(scope=scope):
                done = []
                def wait(seconds):
                    self.wait(seconds)
                    if not done: self.commit(scope); done.append(True)
                self.reject("DIAGNOSTICS_JOURNAL_CHANGED", _wait=wait)

    def test_changed_generation_stopping_or_recovering_during_wait_refused(self):
        for state in ("STOPPING", "RECOVERING"):
            def wait(seconds): self.wait(seconds); self.service._state = state
            self.reject("DIAGNOSTICS_OWNER_CHANGED", _wait=wait)
            self.service._state = "READY"
        def changed(seconds): self.wait(seconds); self.service._generation = "b" * 64
        self.reject("DIAGNOSTICS_OWNER_CHANGED", _wait=changed)

    def test_no_counter_query_when_authority_binding_unavailable(self):
        self.service._state = "STOPPING"
        self.reject("SERVICE_DIAGNOSTICS_OWNER_UNAVAILABLE")
        self.assertEqual([x.calls for x in self.ports], [0, 0])
        self.service._state = "READY"
        with self.assertRaisesRegex(ContractError, "SERVICE_DIAGNOSTICS_GENERATION_CHANGED"):
            collector.collect_owned_diagnostics(self.service, expected_generation="b" * 64, envelope=self.envelope)
        self.assertEqual([x.calls for x in self.ports], [0, 0])

    def test_missing_measurements_never_report_complete(self):
        self.ports[0].unavailable = True
        result = self.collect()
        self.assertEqual(result["state"], "UNAVAILABLE_PROCESS_USAGE")
        self.assertIsNone(result["processes"]["service"]["read_io_bytes"])

    def test_cancelled_wrong_callback_and_frozen_clock_are_bounded(self):
        self.reject("DIAGNOSTICS_CANCELLED", cancelled=lambda: True)
        self.reject("DIAGNOSTICS_CANCELLATION_INVALID", cancelled=lambda: 1)
        waits = []
        self.reject("DIAGNOSTICS_CLOCK_NOT_ADVANCING", _wait=lambda seconds: waits.append(seconds))
        self.assertLessEqual(len(waits), 4)
        self.assertTrue(all(x <= .05 for x in waits))

    def test_rollback_and_expired_window_refused(self):
        def rollback(seconds): self.now[0] -= 1
        self.reject("DIAGNOSTICS_CLOCK_INVALID", _wait=rollback)
        def delayed(seconds): self.now[0] += 2_000_000_000
        self.reject("DIAGNOSTICS_DEADLINE_EXCEEDED", _wait=delayed)

    def test_process_exit_and_replacement_refused(self):
        def exit_process(seconds): self.wait(seconds); self.ports[0].alive = False
        self.reject("DIAGNOSTICS_PROCESS_UNAVAILABLE", _wait=exit_process)
        self.ports[0].alive = True
        def replace_process(seconds):
            self.wait(seconds); self.service._service.process = ProcessPort(self.now, 44)
        self.reject("DIAGNOSTICS_OWNER_CHANGED", _wait=replace_process)

    def test_journal_change_during_analysis_is_rechecked(self):
        original = collector.PerformanceDiagnostics.analyze_process_current
        changed = []
        def analyze(engine, *args, **kwargs):
            result = original(engine, *args, **kwargs)
            if not changed: self.commit(SCOPES[1]); changed.append(True)
            return result
        with patch.object(collector.PerformanceDiagnostics, "analyze_process_current", new=analyze):
            self.reject("DIAGNOSTICS_JOURNAL_CHANGED")

    def test_final_native_currentness_cannot_hide_journal_movement(self):
        port = self.ports[0]
        original, calls = port.resource_observation_current, []
        def current(identity):
            calls.append(True)
            if len(calls) == 5: self.commit(SCOPES[1])
            return original(identity)
        with patch.object(port, "resource_observation_current", side_effect=current):
            self.reject("DIAGNOSTICS_JOURNAL_CHANGED")

    def test_slow_final_journal_fence_invalidates_measurement_deadline(self):
        reader = SqliteJournal(self.root, self.codec, SCOPES, read_only=True, profile=STORE_PROFILE)
        original, calls = reader.store_position, []
        def position():
            result = original()
            calls.append(True)
            if len(calls) >= 2: self.now[0] += 2_000_000_000
            return result
        with patch.object(collector, "SqliteJournal", return_value=reader), \
             patch.object(reader, "store_position", side_effect=position):
            self.reject("DIAGNOSTICS_DEADLINE_EXCEEDED")

    def test_exit_during_journal_validation_cannot_publish_current_process(self):
        reader = SqliteJournal(self.root, self.codec, SCOPES, read_only=True, profile=STORE_PROFILE)
        original, calls = reader.store_position, []
        def position():
            result = original()
            calls.append(True)
            if len(calls) == 2: self.ports[0].alive = False
            return result
        with patch.object(collector, "SqliteJournal", return_value=reader), \
             patch.object(reader, "store_position", side_effect=position):
            self.reject("DIAGNOSTICS_PROCESS_UNAVAILABLE")

    def test_primary_and_close_failure_preserve_exact_custody_and_retry(self):
        reader = SqliteJournal(self.root, self.codec, SCOPES, read_only=True, profile=STORE_PROFILE)
        real_close = reader.close
        primary, secondary = KeyboardInterrupt("controlled interruption"), ContractError("CONTROLLED_CLOSE_FAILURE")
        def close(): real_close(); raise secondary
        with patch.object(collector, "SqliteJournal", return_value=reader), patch.object(reader, "close", side_effect=close):
            with self.assertRaises(KeyboardInterrupt) as caught:
                self.collect(cancelled=lambda: (_ for _ in ()).throw(primary) if self.ports[0].calls else False)
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.diagnostics_journal_cleanup_error, secondary)
        self.assertIs(primary.diagnostics_journal_custody, reader)
        self.assertEqual(self.collect()["state"], "COMPLETE_PROCESS_USAGE")

    def test_close_only_failure_never_returns_result(self):
        reader = SqliteJournal(self.root, self.codec, SCOPES, read_only=True, profile=STORE_PROFILE)
        real_close = reader.close
        secondary = ContractError("CONTROLLED_CLOSE_FAILURE")
        def close(): real_close(); raise secondary
        with patch.object(collector, "SqliteJournal", return_value=reader), patch.object(reader, "close", side_effect=close):
            with self.assertRaises(ContractError) as caught: self.collect()
        self.assertIs(caught.exception, secondary)
        self.assertIs(secondary.diagnostics_journal_custody, reader)

    def test_concurrent_explicit_calls_preserve_canonical_state(self):
        outputs, errors = [], []
        def run():
            try: outputs.append(self.collect())
            except ContractError as error: errors.append(error.code)
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5); self.assertFalse(thread.is_alive())
        self.assertEqual(self.writer.store_position().next_commit, 0)
        self.assertEqual(len(outputs) + len(errors), 2)
        self.assertTrue(all(x["state"] == "COMPLETE_PROCESS_USAGE" for x in outputs))


if __name__ == "__main__": unittest.main()
