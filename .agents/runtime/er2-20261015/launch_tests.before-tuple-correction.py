"""One bounded known-job owner for each separately identified ER2 cohort."""
from pathlib import Path
import argparse
import json
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/er2-20261015'
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'
sys.path.insert(0, str(F / '.agents/runtime/js3-20261015'))
from bounded_custody import run_owned, failure
assert s.sha(F / '.agents/runtime/js3-20261015/bounded_custody.py') == '715b88ab286a524f5815ec3c47b987ba82cc50709272fdc467b7ddc76eeba1b4'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--cohort', action='store_true')
    args = parser.parse_args()
    assert args.label.replace('-', '').isalnum()
    assert not (R / args.label).exists()
    arguments = ['-B', '-X', 'utf8', str(R / 'run_tests.py'), args.label]
    if args.cohort:
        arguments.append('--cohort')
    inputs = json.loads((R / 'SOURCE-INPUTS.json').read_bytes())
    dependency = json.loads((F / '.agents/runtime/js3-20261015/GIT-SEARCH-DEPENDENCY.json').read_bytes())
    environment = {'SystemRoot': dependency['SystemRoot'], 'PATH': dependency['PATH'],
                   'TEMP': str(R), 'TMP': str(R), 'PYTHONDONTWRITEBYTECODE': '1'}
    assert s.ordinary(s.PY) == inputs['python']
    s.write_new(R / (args.label + '-ATTEMPT.json'), {'at': s.utc(), 'argv': [str(s.PY), *arguments],
                'runner': s.reference(R / 'run_tests.py'), 'timeout_seconds': 300, 'automatic_retry': False})
    sys.path.insert(0, str(Q / 'src'))
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess

    def launch():
        return WindowsOwnedProcess.launch(str(s.PY), arguments, cwd=str(R), environment=environment,
            expected_image_sha256=inputs['python']['sha256'])

    def emit(owner):
        s.write_new(R / (args.label + '-OWNER.json'), owner)

    def child():
        path = R / args.label / 'RESULT.json'
        proof = json.loads(path.read_bytes())
        assert proof['executed_ids'] == proof['stopped_ids'] == proof['expected_ids']
        # Before-repair failures remain actual failed results, never approval.
        return s.reference(path)

    primary = record = None
    try:
        record = run_owned(launch, emit, child, timeout=300)
    except BaseException as error:
        primary = error
        record = dict.get(BaseException.__dict__['__dict__'].__get__(error), 'full_runner_report', record)
    report = {'at': s.utc(), 'record': record, 'primary_error': failure(primary) if primary else None,
              'exit_status': record['child_exit'] if primary is None else 1,
              'Source_publication': False, 'Source_accepted': False, 'automatic_retry': False}
    s.write_new(R / (args.label + '-LAUNCH.json'), report)
    if primary is not None:
        raise primary
    return report['exit_status']


if __name__ == '__main__':
    sys.exit(main())
