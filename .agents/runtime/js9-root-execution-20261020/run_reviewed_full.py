"""Retain the exact full-suite launcher command, raw streams and actual exit."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
F = R.parents[2]
D = F/'.agents/runtime/js9-runtime-20261020/successor-r2'
PY = F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
assert len(sys.argv) == 2 and sys.argv[1] in ('candidate-full', 'destination-full')
phase = sys.argv[1]
release = json.loads((R/(phase+'-RELEASE.json')).read_bytes())['release']
argv = [str(PY), '-B', '-X', 'utf8', str(D/'launch_full.py'), phase,
    '--release-path', str(F/release['repository_relative_path']), '--release-sha256', release['sha256']]
record = dict(argv=argv, cwd=str(D), started_at=datetime.now(timezone.utc).isoformat(), automatic_retry=False)
with (R/(phase+'-COMMAND.json')).open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
with (R/(phase+'.stdout')).open('xb') as out, (R/(phase+'.stderr')).open('xb') as err:
    result = subprocess.run(argv, cwd=D, stdout=out, stderr=err)
record.update(finished_at=datetime.now(timezone.utc).isoformat(), exit_status=result.returncode,
    stdout_sha256=hashlib.sha256((R/(phase+'.stdout')).read_bytes()).hexdigest(),
    stderr_sha256=hashlib.sha256((R/(phase+'.stderr')).read_bytes()).hexdigest())
with (R/(phase+'-TERMINAL.json')).open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
print(json.dumps(record), flush=True)
raise SystemExit(result.returncode)
