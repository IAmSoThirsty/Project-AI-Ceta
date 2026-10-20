"""Dormant six-case native qualification. Execute only after exact Root release."""
import ctypes
import dataclasses
import datetime
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import threading
import unittest
from unittest.mock import patch

F = Path(r'T:\00-Active\Project-AI-CETA')
import argparse
import js9_support as j
from js9_support import Q,R
parser=argparse.ArgumentParser();parser.add_argument('label')
parser.add_argument('--release-path',type=Path,required=True);parser.add_argument('--release-sha256',required=True)
args=parser.parse_args();assert args.label.isidentifier()
release=j.require_release(args.release_path,args.release_sha256,'native-observer')
j.verify(source='before')
assert os.name=='nt' and struct.calcsize('P')==8
label=args.label
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
expected=j.manifest()['expected_payload_hashes']
before={name:sha(Q/name) for name in expected};assert before==expected
binary = F / '.agents/runtime/ob2-20261014/build-reuse/effect_observer.exe'
worker = F / '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'
pins = {str(binary): '2cb69daab94b1225be228db19ce17393f1972a24ee5aa37d7b035bd30d1917f0',
        str(worker): '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f',
        str(Q / 'native/windows_broker/effect_observer.rs'): '7fe0104015ff13ed1a004c379a0a6c93976c40596e61d4db769b4b23a5a113db'}
assert all(sha(Path(name)) == pin for name, pin in pins.items())
output = R / label
output.mkdir(exist_ok=False)
forbidden, loads = [], []
def audit(event, args):
    if event == 'ctypes.dlopen':
        loads.append(str(args[0]))
    if event in ('subprocess.Popen', 'os.system', 'sqlite3.connect', 'socket.connect', 'socket.bind',
                 'os.startfile', 'os.startfile/2'):
        forbidden.append(event); raise AssertionError('NATIVE_REVIEW_FORBIDS_' + event)
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        flags = args[2]
        if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            assert Path(os.fsdecode(args[0])).resolve().is_relative_to(output), 'WRITE_OUTSIDE_NATIVE_RECEIPT'
    if event == 'os.mkdir':
        assert Path(os.fsdecode(args[0])).resolve().is_relative_to(output), 'MKDIR_OUTSIDE_NATIVE_RECEIPT'
sys.addaudithook(audit)
os.environ['CETA_EFFECT_OBSERVER_EXE'] = str(binary)
os.environ['CETA_OWNED_WORKER_EXE'] = str(worker)
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
import test_native_observer_origin as tests
import test_native_effect_observer as fixtures
import ceta.effects.native_observer as observer_module
import ceta.supervisor.windows_jobs as native
from ceta.identity.native_clock import NativeSessionClock
fixtures.ROOT = output / 'fixtures'
suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.NativeObserverOriginTests)
ids = [case.id() for case in suite]
assert len(ids) == 6 and len(set(ids)) == 6
assert ids == j.packet()['native_observer_ids']
owners, clocks, custodies, leases, source_pins, observers, launches = [], [], [], [], [], [], []
executed, stopped = [], []

def capture_init(cls, collection):
    original = cls.__init__
    def captured(owner, *args, **kwargs):
        collection.append(owner)
        original(owner, *args, **kwargs)
    return patch.object(cls, '__init__', captured)

original_launch = native.WindowsOwnedProcess.launch.__func__
def launch(cls, executable, arguments, **kwargs):
    image = Path(executable).resolve(strict=True)
    cwd = Path(kwargs['cwd']).resolve(strict=True)
    if image == worker:
        assert arguments == ('hold', '30000') and cwd.is_relative_to(output)
        assert sum(row['image'] == str(worker) for row in launches) < 8
    else:
        assert image == binary and arguments == ('observe-v1',) and cwd == binary.parent
        assert sum(row['image'] == str(binary) for row in launches) < 9
    assert kwargs['expected_image_sha256'] == pins[str(image)]
    row = dict(image=str(image), arguments=arguments, cwd=str(cwd),
               environment=kwargs['environment'], inherited_handles=kwargs.get('inherited_handles', ()),
               standard_handles=kwargs.get('standard_handles'), expected_image_sha256=kwargs['expected_image_sha256'])
    launches.append(row)
    try:
        owner = original_launch(cls, executable, arguments, **kwargs)
        row.update(pid=owner.pid, creation_time=owner.creation_time, returned=True)
        return owner
    except BaseException as error:
        row.update(returned=False, error=repr(error))
        raise

class Recorded(unittest.TextTestResult):
    def startTest(self, test): executed.append(test.id()); super().startTest(test)
    def stopTest(self, test): stopped.append(test.id()); super().stopTest(test)

def normalize(value):
    if dataclasses.is_dataclass(value): return normalize(dataclasses.asdict(value))
    if isinstance(value, bytes): return dict(hex=value.hex(), sha256=hashlib.sha256(value).hexdigest())
    if isinstance(value, dict): return {str(k): normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [normalize(item) for item in value]
    return value

def checked(kind, items, read):
    rows = []
    for item in items:
        try: rows.append(read(item))
        except BaseException as error: rows.append(dict(inspection_error=repr(error), closed=False))
    return dict(kind=kind, count=len(rows), rows=rows,
                all_closed=bool(rows) and all(row['closed'] for row in rows))

started = datetime.datetime.now(datetime.timezone.utc).isoformat()
thread_ids = {thread.ident for thread in threading.enumerate()}
controls = [capture_init(native.WindowsOwnedProcess, owners), capture_init(NativeSessionClock, clocks),
    capture_init(observer_module._Custody, custodies), capture_init(native.WindowsCpuQueryHandles, leases),
    capture_init(observer_module._SourcePin, source_pins), capture_init(observer_module.NativeCpuEffectObserver, observers),
    patch.object(native.WindowsOwnedProcess, 'launch', classmethod(launch))]
result, run_error = None, None
with (output / 'native.txt').open('x', encoding='utf-8') as stream:
    try:
        for control in controls: control.start()
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorded, failfast=True).run(suite)
    except BaseException as error:
        run_error = repr(error)
    finally:
        for control in reversed(controls): control.stop()

process_rows = checked('owned_process', owners, lambda o: dict(pid=o.pid, creation_time=o.creation_time,
    image_sha256=o.image_sha256, exit_code=o._exit_code, process_handle=o._process,
    job_handle=o._job, thread_handle=o._thread, cleanup_handles=list(o._cleanup_handles),
    query_exports=len(o._cpu_query_exports), closed=o.lifetime_closed and o._process is None
    and o._job is None and o._thread is None and not o._cleanup_handles and not o._cpu_query_exports))
custody_rows = checked('observer_custody', custodies, lambda o: dict(closed=o.closed and not o.handles
    and not o.uncertain_handles and o.launch_error is None and (o.lease is None or o.lease.closed)
    and (o.process is None or o.process.lifetime_closed), evidence=o.evidence()))
lease_rows = checked('query_lease', leases, lambda o: dict(closed=o.closed and not o.pending_handles(),
    pending_handles=o.pending_handles(), identity=normalize(o.identity), job_digest=o.job_digest))
pin_rows = checked('source_pin', source_pins, lambda o: dict(closed=o.closed and not o.pending_native_resources(),
    pending_resources=o.pending_native_resources()))
def clock_row(clock):
    status = clock.status()
    return dict(closed=status.state == 'CLOSED' and clock._registration is None
        and not status.sampler_alive and clock._callbacks == 0, status=normalize(status))
clock_rows = checked('native_clock', clocks, clock_row)
observer_rows = checked('observer_owner', observers, lambda o: dict(closed=o._custody is None,
    custody_pending=o._custody is not None, origin_retained=o._origin is not None))
custody_summary = [process_rows, custody_rows, lease_rows, pin_rows, clock_rows, observer_rows]
after = {name: sha(Q / name) for name in expected}
new_threads = [thread.name for thread in threading.enumerate() if thread.ident not in thread_ids]
imports = {name: str(Path(mod.__file__).resolve()) for name, mod in tuple(sys.modules.items())
           if (name == 'ceta' or name.startswith('ceta.')) and getattr(mod, '__file__', None)}
all_closed = all(row['all_closed'] for row in custody_summary)
checks = dict(exact_ids=ids == executed == stopped, all_recorded_custody_closed=all_closed,
    exact_nominal_processes=len(owners) == 17 and len(launches) == 17,
    no_new_threads=not new_threads, source_unchanged=before == after,
    pinned_helpers=all(sha(Path(name)) == pin for name, pin in pins.items()),
    imports_only_successor=all(Path(path).is_relative_to(Q / 'src') for path in imports.values()),
    no_forbidden_events=not forbidden, no_runner_error=run_error is None,
    tests_passed=result is not None and result.wasSuccessful() and not result.skipped)
j.verify(source='before')
receipt = dict(actor='/root/recovery_regression20', mode='ACTUAL_DISPOSABLE_WINDOWS_ORIGIN_QUALIFICATION',
    started_at=started, finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    runner_sha256=sha(Path(__file__)), handoff_sha256=j.manifest_reference()['sha256'],
    interpreter=sys.executable, interpreter_sha256=sha(Path(sys.executable)),
    command=[sys.executable, '-B', '-X', 'utf8', *sys.argv], cwd=str(Path.cwd()),
    release=j.exact_ref(args.release_path),failfast=True, helper_pins=pins, before=before, after=after, imports=imports,
    expected_ids=ids, executed_ids=executed, stopped_ids=stopped,
    tests_run=0 if result is None else result.testsRun,
    failures=[] if result is None else [(test.id(), trace) for test, trace in result.failures],
    errors=[] if result is None else [(test.id(), trace) for test, trace in result.errors],
    skips=[] if result is None else [(test.id(), reason) for test, reason in result.skipped],
    run_error=run_error, launches=launches, custody=custody_summary,
    native_receipts=normalize(fixtures.NATIVE_RECEIPTS), new_threads_remaining=new_threads,
    forbidden_events=forbidden, loaded_libraries=loads, checks=checks,
    raw_sha256=sha(output / 'native.txt'), passed=all(checks.values()),
    canonical_permission_capacity_effect_qualified=False, Source_application=False,
    instrumentation='Read-only constructor/launch recording; underlying native calls and fixture cleanup remain real.')
with (output / 'native.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(dict(receipt=str(output / 'native.json'), tests=receipt['tests_run'], checks=checks,
    passed=receipt['passed'])), flush=True)
sys.exit(0 if receipt['passed'] else 1)
