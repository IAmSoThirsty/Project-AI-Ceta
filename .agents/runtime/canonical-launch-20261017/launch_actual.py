"""Capture one unmodified canonical application launch and its natural exit."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('T:/00-Active/Project-AI-CETA')
OUT = Path(__file__).resolve().parent / 'attempt1'
PY = ROOT / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert Path(sys.executable) == PY and not sys.flags.optimize
sys.path.insert(0, str(ROOT / '.agents/runtime/js8-20261015/amendment-order1'))
import amendment_support as j

def write_new(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())

def now():
    return datetime.now(timezone.utc).isoformat()

assert not OUT.exists()
j.verify(source='before')
OUT.mkdir()
(OUT / 'temporary').mkdir()
before = {name: j.s.ordinary(ROOT / name) for name in j.inputs()['Source295']}
fixture_parent = ROOT / '.agents/fixtures/operator-24'
existing = sorted(p.name for p in fixture_parent.iterdir()) if fixture_parent.exists() else []
command = [str(PY), '-B', '-X', 'utf8', str(ROOT / 'tools/ceta_operator.py')]
environment = j.child_environment(OUT / 'temporary')
environment.update(QT_QPA_PLATFORM='windows', PYTHONNOUSERSITE='1')
write_new('COMMAND.json', dict(started_at=now(), command=command,
    windows_command_line=subprocess.list2cmdline(command), cwd=str(ROOT), environment=environment,
    source_before=before, original_profiles=existing,
    source_baseline='JS7 accepted Source; JS8 candidate full terminal reporting failed and is not published',
    entrypoint_modified=False, startup_status='NOT_YET_OBSERVED',
    governed_execution_status='NOT_ATTEMPTED'))
with (OUT / 'stdout.log').open('xb') as stdout, (OUT / 'stderr.log').open('xb') as stderr:
    process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    write_new('PROCESS.json', dict(at=now(), launcher_pid=process.pid,
        exact_child_command=command, process_created=True,
        startup_status='NOT_YET_OBSERVED', governed_execution_status='NOT_ATTEMPTED'))
    print(json.dumps({'launcher_pid': process.pid, 'command': command, 'evidence': str(OUT)}), flush=True)
    exit_status = process.wait()
after = {name: j.s.ordinary(ROOT / name) for name in before}
profiles = sorted(p.name for p in fixture_parent.iterdir()) if fixture_parent.exists() else []
write_new('EXIT.json', dict(at=now(), exit_status=exit_status,
    source_unchanged=before == after,
    profiles_created=[p for p in profiles if p not in existing],
    stdout_sha256=hashlib.sha256((OUT / 'stdout.log').read_bytes()).hexdigest(),
    stderr_sha256=hashlib.sha256((OUT / 'stderr.log').read_bytes()).hexdigest(),
    startup_and_operation_results='See separately captured interface observations and canonical profile records.'))
print(json.dumps({'exit_status': exit_status, 'source_unchanged': before == after}), flush=True)
raise SystemExit(exit_status)
