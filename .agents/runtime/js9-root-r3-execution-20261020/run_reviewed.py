"""Retain exact commands, raw output and terminal status for one released phase."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import traceback
import phase_coordinator as c

assert len(sys.argv) == 2
phase = sys.argv[1]
assert phase in ('native-store', 'native-observer', 'candidate-full', 'destination-full', 'publish')
c.bound_packet()
release_record = json.loads((c.R / (phase + '-RELEASE.json')).read_bytes())
release = release_record['release']
release_path = c.F / release['repository_relative_path']
assert hashlib.sha256(release_path.read_bytes()).hexdigest() == release['sha256']
python = c.F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
argv = [str(python), '-B', '-X', 'utf8']
if phase in ('native-store', 'native-observer'):
    argv.extend([str(c.D / 'launch_native.py'), phase, phase.replace('-', '_') + '_r3'])
elif phase == 'publish':
    argv.append(str(c.D / 'publish_source.py'))
else:
    argv.extend([str(c.D / 'launch_full.py'), phase])
argv.extend(['--release-path', str(release_path), '--release-sha256', release['sha256']])
record = dict(argv=argv, cwd=str(c.D), started_at=datetime.now(timezone.utc).isoformat(),
    automatic_retry=False)
c.save(c.R / (phase + '-COMMAND.json'), record)
completed = primary = None
try:
    with (c.R / (phase + '.stdout')).open('xb') as out, (c.R / (phase + '.stderr')).open('xb') as err:
        completed = subprocess.run(argv, cwd=c.D, stdout=out, stderr=err)
except BaseException as error:
    primary = error
diagnostic = None
if primary is not None:
    try:
        message = str(primary)
    except BaseException:
        message = '<exception text unavailable>'
    try:
        trace = ''.join(traceback.format_exception(type(primary), primary, primary.__traceback__))
    except BaseException:
        trace = '<exception traceback unavailable>'
    diagnostic = dict(type=type(primary).__name__, message=message, traceback=trace)
record.update(finished_at=datetime.now(timezone.utc).isoformat(),
    exit_status=None if completed is None else completed.returncode,
    command_returned=completed is not None, execution_error=diagnostic,
    stdout_sha256=hashlib.sha256((c.R / (phase + '.stdout')).read_bytes()).hexdigest(),
    stderr_sha256=hashlib.sha256((c.R / (phase + '.stderr')).read_bytes()).hexdigest())
try:
    c.save(c.R / (phase + '-TERMINAL.json'), record)
except BaseException as secondary:
    if primary is None:
        raise
    data = BaseException.__dict__['__dict__'].__get__(primary)
    dict.update(data, terminal_record=record, terminal_write_error=secondary)
    raise primary
print(json.dumps(record), flush=True)
if primary is not None:
    raise primary
raise SystemExit(completed.returncode)
