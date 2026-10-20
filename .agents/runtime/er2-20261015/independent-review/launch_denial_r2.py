"""One controlled-only corrected denial case; unchanged exact owned-job custody."""
import json
import sys
from review_support import F, Q, R, V, read, conservation, s


def main():
    assert len(sys.argv) == 1
    assert conservation() == read(V / 'BEFORE.json')
    assert not (V / 'DENIAL-R2-ATTEMPT.json').exists()
    child_pin = s.sha(V / 'check_denial_r2.py')
    assert s.sha(V / 'bounded_custody.py') == '715b88ab286a524f5815ec3c47b987ba82cc50709272fdc467b7ddc76eeba1b4'
    sys.path.insert(0, str(Q / 'src'))
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    from bounded_custody import run_owned, failure
    dependency = read(F / '.agents/runtime/js3-20261015/GIT-SEARCH-DEPENDENCY.json')
    environment = {'SystemRoot': dependency['SystemRoot'], 'PATH': dependency['PATH'],
        'TEMP': str(V), 'TMP': str(V), 'PYTHONDONTWRITEBYTECODE': '1'}
    arguments = ('-B', '-X', 'utf8', str(V / 'check_denial_r2.py'))
    s.write_new(V / 'DENIAL-R2-ATTEMPT.json', {'at': s.utc(), 'argv': [str(s.PY), *arguments],
        'child_sha256': child_pin, 'launcher_sha256': s.sha(V / 'launch_denial_r2.py'),
        'timeout_seconds': 60, 'automatic_retry': False, 'native_service_cases': 0})
    def launch():
        assert s.sha(V / 'check_denial_r2.py') == child_pin
        return WindowsOwnedProcess.launch(str(s.PY), arguments, cwd=str(V), environment=environment,
            expected_image_sha256=read(R / 'SOURCE-INPUTS.json')['python']['sha256'])
    def emit(owner): s.write_new(V / 'DENIAL-R2-OWNER.json', owner)
    def child():
        path = V / 'denial-r2/RESULT.json'
        proof = read(path)
        assert proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids'] and proof['tests_run'] == 1
        return s.reference(path)
    primary = record = None
    try: record = run_owned(launch, emit, child, timeout=60)
    except BaseException as error:
        primary = error
        record = dict.get(BaseException.__dict__['__dict__'].__get__(error), 'full_runner_report', record)
    s.write_new(V / 'DENIAL-R2-LAUNCH.json', {'at': s.utc(), 'record': record,
        'primary_error': failure(primary) if primary else None, 'exit_status': record['child_exit'] if primary is None else 1,
        'automatic_retry': False, 'Source_publication': False})
    if primary is not None: raise primary
    return record['child_exit']


if __name__ == '__main__': sys.exit(main())
