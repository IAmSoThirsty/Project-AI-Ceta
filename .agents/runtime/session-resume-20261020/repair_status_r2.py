"""Preserve R1; label worker assignments with their actual observation time."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
F = R.parents[2]
now = datetime.now(timezone.utc).isoformat()
candidate = json.loads((R / 'continuity.json.candidate').read_bytes())
candidate['active_workers'] = [
    dict(agent='/root/recovery_regression20', job='JS9 R2 runner repair controls and phase handoff'),
    dict(agent='/root/recovery_join_review20', job='Independent JS9 R2 execution tool review'),
    dict(agent='/root/ac7_native_artifact_review20', job='Independent two-document resume-status review'),
]
candidate['active_workers_observed_at'] = now
candidate['active_workers_observation_basis'] = (
    'Timestamped collaboration.list_agents snapshot: all three named agents were running. '
    'Assignments are recorded at this observation time; consult live agent status for a later time.')
target = R / 'continuity.json.candidate-r2'
raw = (json.dumps(candidate, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
with target.open('xb') as stream:
    assert stream.write(raw) == len(raw)
progress = R / 'progress.json.candidate'
record = dict(at=now, author='/root', repaired_finding='Timestamp current worker assignments',
    progress_candidate_sha256=hashlib.sha256(progress.read_bytes()).hexdigest(),
    continuity_candidate_sha256=hashlib.sha256(raw).hexdigest(),
    prior_continuity_sha256=hashlib.sha256((R / 'continuity.json.candidate').read_bytes()).hexdigest(),
    canonical_writes=False)
with (R / 'PREPARED-R2.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record))
