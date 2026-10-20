"""Retain the exact narrow post-publication Git whitespace-check terminal."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
argv = ['git', '-C', str(F), 'diff', '--check', '--', 'build/progress.json', 'handoff/continuity.json']
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(argv, cwd=F, capture_output=True)
for suffix, raw in (('stdout', result.stdout), ('stderr', result.stderr)):
    with (R / ('POST-PUBLICATION-DIFF-CHECK.' + suffix)).open('xb') as stream:
        assert stream.write(raw) == len(raw)
record = dict(argv=argv, cwd=str(F), started_at=started,
    finished_at=datetime.now(timezone.utc).isoformat(), exit_status=result.returncode,
    stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
    stderr_sha256=hashlib.sha256(result.stderr).hexdigest(),
    destination_sha256={name:hashlib.sha256((F/name).read_bytes()).hexdigest()
        for name in ('build/progress.json', 'handoff/continuity.json')})
with (R / 'POST-PUBLICATION-DIFF-CHECK.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record))
raise SystemExit(result.returncode)
