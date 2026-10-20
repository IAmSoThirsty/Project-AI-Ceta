"""Actual frozen FN5 constructor/SQLite fixture, controlled binding refusal."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import threading
import unittest
from contextlib import ExitStack
from unittest.mock import patch

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/fn5-20261015'
R = F / '.agents/runtime/fn5-20261015'
V = Path(__file__).resolve().parent
PIN = '7c324af5d0a5293e5fab57785e7ffabc3e2b69b6530ef5c1d4320d5cb303fa2d'
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.R = V
assert s.sha(Q / 'TRANSFER-MANIFEST.json') == PIN
manifest = json.loads((Q / 'TRANSFER-MANIFEST.json').read_bytes())
before = {name: s.ordinary(Q / name) for name in manifest['payloads']}
assert len(before) == 351
observer_source = F / '.agents/runtime/js3-20261015/independent-destination/resource_observer.py'
assert s.sha(observer_source) == 'de5deb609eb8b57b2b52e695ec0b38e1eac05f31ada119e83e74b9157074fd4a'
if not (V / 'resource_observer.py').exists():
    with (V / 'resource_observer.py').open('xb') as out: out.write(observer_source.read_bytes())
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
sqlite = load_sqlite()
from ceta.identity import native_approval, native_clock, native_owner_view, owner_session
from ceta.effects.native_cpu_binding import NativeCpuBinding
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
from ceta.kernel import transactions, cpu_execution
from resource_observer import Observer

D = V / 'initializer-binding-r1'
D.mkdir(exist_ok=False)
FACTS, forbidden = [], []


def deny(*args, **kwargs):
    forbidden.append('native-worker-profile-clock-or-approval-allocation')
    raise AssertionError('FN5_INITIALIZER_PROBE_NO_NATIVE_EFFECT')


class InitializerBindingTests(unittest.TestCase):
    def test_failed_final_bound_method_allocation_must_leave_owner_unbound(self):
        schema = json.loads((Q / 'contracts/schemas/records.schema.json').read_bytes())
        for kind in (KeyboardInterrupt, SystemExit, MemoryError):
            with self.subTest(kind=kind.__name__):
                f = preparation.Fixture(schema)
                original = f.owner._preparation_kernel
                f.owner._preparation_kernel = None
                primary = kind('CONTROLLED final bound-method allocation refusal')
                captures = []
                class BindingRefusal:
                    def __get__(self, owner, cls=None):
                        if owner is None: return self
                        captures.append(owner)
                        raise primary
                try:
                    with patch.object(owner_session.NativeCpuOwnerSession, 'require_prepared_basis', BindingRefusal()):
                        try:
                            transactions.KernelTransactions(f.store, f.codec, preparation.data.INSTALLATION, f.owner)
                        except BaseException as caught:
                            self.assertIs(caught, primary)
                        else: self.fail('original constructor must reject')
                    poisoned = f.owner._preparation_kernel
                    retry_error = None
                    try: transactions.KernelTransactions(f.store, f.codec, preparation.data.INSTALLATION, f.owner)
                    except BaseException as caught: retry_error = caught
                    row = dict(control=kind.__name__, exact_primary=True, manual_binding_calls=len(captures),
                        exact_owner=captures == [f.owner], owner_unbound=poisoned is None,
                        incomplete_kernel_id=id(poisoned), original_kernel_id=id(original),
                        published_kernel_is_original=poisoned is original,
                        bound_kernel_missing_preparation_check=poisoned is not None and not hasattr(poisoned, '_preparation_check'),
                        next_constructor_error=str(retry_error) if retry_error is not None else None,
                        borrowed_store_stays_open=not f.store._closed,
                        borrowed_connection_object_id=id(f.store._connection),
                        borrowed_connection_executes_select=f.store._connection.execute('SELECT 1').fetchone() == (1,),
                        transaction_open=f.store._connection.in_transaction,
                        fixture_controlled_native_and_approval=True, actual_native_calls=0)
                    FACTS.append(row)
                    self.assertIsNone(poisoned, 'Failed final binding must not publish an incomplete kernel onto the owner')
                finally:
                    # Only this controlled fixture's original owner link is
                    # restored to retire its borrowed test store normally.
                    f.owner._preparation_kernel = original
                    f.close()


if __name__ == '__main__':
    threads = set(threading.enumerate())
    observer = Observer(sqlite)
    primary = result = None
    with ExitStack() as guards:
        for target, name in ((subprocess, 'Popen'), (WindowsOwnedProcess, 'launch'),
            (native_approval.NativeApprovalOwner, '__init__'), (native_approval._NativeApi, '__init__'),
            (native_clock.NativeSessionClock, '__init__'), (native_owner_view._ViewAPI, '__init__'),
            (NativeCpuBinding, '__init__')):
            guards.enter_context(patch.object(target, name, deny))
        import test_native_owner_preparation as preparation
        preparation.ROOT = Q
        preparation.FIXTURES = D / 'fixtures'
        observer.install()
        try:
            with (D / 'RAW.txt').open('x', encoding='utf8') as raw:
                result = unittest.TextTestRunner(stream=raw, verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(InitializerBindingTests))
        except BaseException as error: primary = error
        finally: observer.uninstall()
    resources = observer.finish()
    after = {name: s.ordinary(Q / name) for name in manifest['payloads']}
    remaining = [dict(name=t.name, native_id=t.native_id) for t in set(threading.enumerate()) - threads if t.is_alive()]
    assert before == after and not forbidden and not remaining
    assert resources['owned_resources_closed'] is True and resources['remaining_resources'] == []
    assert all(row['physical_closed_probe'] for row in resources['sqlite'])
    assert all(row['closed'] and row['fileno_denied'] for row in resources['streams'])
    report = dict(at=s.utc(), manifest_sha256=PIN, tests_run=result.testsRun if result is not None else 0,
        failures=len(result.failures) if result is not None else None, errors=len(result.errors) if result is not None else None,
        skips=len(result.skipped) if result is not None else None,
        failure_details=[dict(id=t.id(), traceback=body) for t, body in result.failures + result.errors] if result is not None else [],
        facts=FACTS, physical_resources=resources, remaining_threads=remaining, forbidden_calls=forbidden,
        candidate_before=before, candidate_after=after, sqlite_runtime=runtime_identity(),
        original458_selected_methods='NOT_RUN pending initializer blocker disposition', original7native='NOT_RUN',
        primary_type=type(primary).__name__ if primary is not None else None,
        qualification='Real exact FN5 constructor and existing canonical SQLite fixture; bound-method allocation refusal and all native/approval facts CONTROLLED',
        native_process_profile_Hello_CPU_execution=False, Source_publication=False,
        exit_status=0 if result is not None and result.wasSuccessful() and primary is None else 1)
    s.write_new(D / 'RESULT.json', report)
    print(json.dumps(dict(tests_run=report['tests_run'], failures=report['failures'], errors=report['errors'],
        subcases=len(FACTS), all_SQLite_closed=resources['owned_resources_closed'], exit_status=report['exit_status'])))
    if primary is not None: raise primary
    sys.exit(report['exit_status'])
