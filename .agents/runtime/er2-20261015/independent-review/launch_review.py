"""One finite ER2 review cohort in an exact retained ordinary Windows job."""
import json
import sys
from review_support import F, Q, R, V, read, conservation, s


def main():
    assert len(sys.argv) == 1
    inputs = read(V / 'PREPARATION.json')
    for name, pin in inputs['helpers'].items(): assert s.sha(V / name) == pin
    assert conservation() == read(V / 'BEFORE.json')
    assert not (V / 'LAUNCH-ATTEMPT.json').exists() and not (V / 'connected-r1').exists()
    sys.path.insert(0, str(Q / 'src'))
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    from bounded_custody import run_owned, failure
    dependency = read(F / '.agents/runtime/js3-20261015/GIT-SEARCH-DEPENDENCY.json')
    environment = {'SystemRoot': dependency['SystemRoot'], 'PATH': dependency['PATH'],
        'TEMP': str(V), 'TMP': str(V), 'PYTHONDONTWRITEBYTECODE': '1'}
    arguments = ('-B', '-X', 'utf8', str(V / 'run_review.py'))
    s.write_new(V / 'LAUNCH-ATTEMPT.json', {'at': s.utc(), 'argv': [str(s.PY), *arguments],
        'input': s.reference(V / 'PREPARATION.json'), 'timeout_seconds': 300,
        'automatic_retry': False, 'scope': 'Component108; no full/product/Source acceptance'})

    def launch():
        return WindowsOwnedProcess.launch(str(s.PY), arguments, cwd=str(V), environment=environment,
            expected_image_sha256=read(R / 'SOURCE-INPUTS.json')['python']['sha256'])

    def emit(owner): s.write_new(V / 'OUTER-OWNER.json', owner)

    def child():
        path = V / 'connected-r1/RESULT.json'
        proof = read(path)
        assert proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids']
        assert proof['tests_run'] == len(set(proof['expected_ids'])) == 108
        return s.reference(path)

    record = primary = None
    try: record = run_owned(launch, emit, child, timeout=300)
    except BaseException as error:
        primary = error
        record = dict.get(BaseException.__dict__['__dict__'].__get__(error), 'full_runner_report', record)
    proof = {'at': s.utc(), 'record': record, 'primary_error': failure(primary) if primary else None,
        'exit_status': record['child_exit'] if primary is None else 1,
        'Source_publication': False, 'full_gate_complete': False, 'automatic_retry': False}
    s.write_new(V / 'LAUNCH-RESULT.json', proof)
    if primary is not None: raise primary
    return proof['exit_status']


if __name__ == '__main__': sys.exit(main())
