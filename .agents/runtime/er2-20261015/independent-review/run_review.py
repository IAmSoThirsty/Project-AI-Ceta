"""Exact106 inherited methods plus two finite checks; separate private fixture root."""
from pathlib import Path
import functools
import json
import os
import sys
import threading
import unittest
from review_support import F, Q, R, V, read, conservation, s


def ids(suite):
    if isinstance(suite, unittest.TestSuite):
        for child in suite: yield from ids(child)
    else: yield suite.id()


class FixtureRoot:
    """Route only test fixture joins; product ROOT and all nonfixture reads stay Q."""
    def __init__(self, fixture): self.fixture, self.routes = fixture, []
    def __truediv__(self, value):
        part = Path(value)
        assert not part.is_absolute() and not part.drive and '..' not in part.parts
        if part.parts[:2] == ('.agents', 'fixtures'):
            target = self.fixture.joinpath(*part.parts[2:])
            assert target.is_relative_to(self.fixture)
            list.append(self.routes, str(target))
            return target
        return Q / part
    def resolve(self, **kwargs): return Q.resolve(**kwargs)
    def __fspath__(self): return str(Q)
    def __str__(self): return str(Q)


def main():
    assert len(sys.argv) == 1
    inputs = read(V / 'PREPARATION.json')
    for name, pin in inputs['helpers'].items(): assert s.sha(V / name) == pin
    assert conservation() == read(V / 'BEFORE.json')
    output = V / 'connected-r1'
    output.mkdir(exist_ok=False)
    temporary = output / 'temporary'
    temporary.mkdir()
    os.environ.update(QT_QPA_PLATFORM='offscreen', TEMP=str(temporary), TMP=str(temporary))
    fixture = Path(inputs['fixture_root'])
    assert fixture.parent == Q / '.agents/fixtures' and not fixture.exists()
    fixture.mkdir(exist_ok=False)
    fixture_identity = fixture.stat()
    sys.path[:0] = [str(Q / 'src'), str(Q / 'tools'), str(Q / 'tests/contract')]
    from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
    sqlite = load_sqlite()
    from resource_observer import Observer
    observer = Observer(sqlite)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(['test_editor_retention_queue', 'test_task_meaning_view',
        'test_task_view', 'test_editor_recovery', 'independent_retention_checks'])
    expected = list(ids(suite))
    original = read(R / 'connected-r1/RESULT.json')['expected_ids']
    assert not loader.errors and expected[:106] == original
    assert len(expected) == len(set(expected)) == 108
    mappers = []
    for name, module in list(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if not name.startswith('test_') or path is None or not Path(path).is_relative_to(Q / 'tests/contract'): continue
        if isinstance(getattr(module, 'ROOT', None), Path) and module.ROOT == Q:
            mapper = FixtureRoot(fixture)
            module.ROOT = mapper
            mappers.append((name, mapper))
    # The production guard and native filename helper remain canonical Q.
    import fixture_paths
    import test_editor_recovery as native_helper
    import ceta.composition.owned_service as service_module
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    assert fixture_paths.ROOT == Q and service_module.ROOT == Q
    captures = []
    original_empty_service = native_helper._EditorNativeHelpers.empty_service
    @functools.wraps(original_empty_service)
    def empty_service(test, *args, **kwargs):
        service, root = original_empty_service(test, *args, **kwargs)
        # Original helper has already appended this service to test.services,
        # so observation failure cannot remove its normal tearDown custody.
        assert service in test.services and root.is_relative_to(fixture)
        for slot in ('_client', '_service'):
            channel = getattr(service, slot)
            process = channel.process
            assert type(process) is WindowsOwnedProcess
            captures.append({'test_id': test.id(), 'service': service, 'channel': channel,
                'process': process, 'slot': slot, 'pid': process.pid,
                'creation_time': process.creation_time, 'image_sha256': process.image_sha256,
                'object_id': id(process), 'root': str(root), 'observed_live_at_return': process.poll() is None})
        return service, root
    native_helper._EditorNativeHelpers.empty_service = empty_service
    started, thread_baseline = s.utc(), set(threading.enumerate())
    executed, stopped, native = [], [], []
    @functools.wraps(observer.original_connect)
    def connect(*args, **kwargs): return observer.connect(*args, **kwargs)
    sqlite.connect = connect

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            executed.append(test.id())
            super().startTest(test)
        def stopTest(self, test):
            selected = test.id().startswith(('test_editor_recovery.NativeEditorRecoveryTests.',
                'test_editor_recovery.QtEditorRecoveryTests.'))
            rows = [row for row in captures if row['test_id'] == test.id()]
            if selected:
                assert len(rows) >= 2 and len(rows) == len(getattr(test, 'services', [])) * 2
            for row in rows:
                process, channel = row['process'], row['channel']
                facts = {'process_handle': process._process is None,
                    'thread_handle': process._thread is None, 'job_handle': process._job is None,
                    'startup_handles': not process._cleanup_handles,
                    'input_pipe': channel._input is None, 'output_pipe': channel._output is None,
                    'error_pipe': channel._error is None, 'child_handles': not channel._child_handles,
                    'launch_custody': channel._launch_error is None}
                value = {key: value for key, value in row.items() if key not in ('process', 'channel', 'service')}
                value.update(native_designations=facts, observed_exit_code=process._exit_code,
                    retired=all(facts.values()) and type(process._exit_code) is int)
                native.append(value)
            stopped.append(test.id())
            super().stopTest(test)

    result = primary = None
    try:
        with (output / 'RAW.txt').open('x', encoding='utf-8', newline='\n') as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    except BaseException as error:
        primary = error
        raise
    finally:
        sqlite.connect = observer.original_connect
        native_helper._EditorNativeHelpers.empty_service = original_empty_service
    physical = observer.finish()
    remaining_threads = [thread.name for thread in threading.enumerate()
        if thread not in thread_baseline and thread.is_alive()]
    imports = {name: str(Path(module.__file__).resolve()) for name, module in list(sys.modules.items())
        if (name == 'ceta' or name.startswith('ceta.')) and getattr(module, '__file__', None)}
    assert all(Path(path).is_relative_to(Q / 'src') for path in imports.values())
    assert conservation() == read(V / 'BEFORE.json')
    success = (result.wasSuccessful() and not result.skipped and expected == executed == stopped
        and not remaining_threads and physical['sqlite'] and physical['owned_resources_closed']
        and native and all(row['retired'] for row in native))
    proof = {'started_at': started, 'finished_at': s.utc(), 'manifest_sha256': inputs['manifest_sha256'],
        'expected_ids': expected, 'executed_ids': executed, 'stopped_ids': stopped,
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skips': len(result.skipped), 'failure_details': [(test.id(), detail) for test, detail in result.failures],
        'error_details': [(test.id(), detail) for test, detail in result.errors],
        'remaining_threads': remaining_threads, 'physical_resources': physical,
        'native_fixture_captures': native, 'fixture_root': str(fixture),
        'fixture_native_identity': {'device': fixture_identity.st_dev, 'inode': fixture_identity.st_ino},
        'fixture_routes': {name: mapper.routes for name, mapper in mappers},
        'original106_IDs_unchanged': expected[:106] == original,
        'sqlite_runtime': runtime_identity(), 'ceta_imports': imports,
        'source_parent_candidate_environment_conserved': True,
        'custody_limits': ['Only exact captured returned SQLite objects in this interpreter are physically queried.',
            'Child-process SQLite closure relies on retained native process/job retirement; no internal API wrapping.',
            'Native service helpers retain all captured owners here; generic removed/replaced owners are not completely observed.',
            'Cached native exit plus canonical successful close designations are checked; historical arbitrary handle retirement is not inferred.'],
        'raw': s.reference(output / 'RAW.txt'), 'Source_publication': False, 'full_gate_complete': False,
        'Source_accepted': False, 'exit_status': 0 if success else 1}
    s.write_new(output / 'RESULT.json', proof)
    print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skips': len(result.skipped), 'sqlite_connections': len(physical['sqlite']),
        'native_lifetimes': len(native), 'exit_status': proof['exit_status']}), flush=True)
    return proof['exit_status']


if __name__ == '__main__': sys.exit(main())
