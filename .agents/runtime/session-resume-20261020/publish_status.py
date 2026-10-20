"""Publish the exact independently reviewed status bytes with preserved originals."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
REVIEW = F / '.agents/runtime/session-resume-review-20261020/APPROVAL.json'
REVIEW_PIN = '24fe9558ae1aa1f0ee63e27da52a0c716e625cfd10c55df1dd3707e9e4921561'
PRIMITIVE = F / '.agents/runtime/rs2-20261014/apply_joined_source.py'
PRIMITIVE_PIN = '4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'
ROWS = (
    ('build/progress.json', 'progress.json.candidate',
     'c6b8c1ebc41ef28c682f3da36589b04614b9efbfe12be258a5da20f56f038f5c',
     '8257f739a2f16f9acb4361bebaf0f81b14675f6a12e780d8eac677cf8b4594d0'),
    ('handoff/continuity.json', 'continuity.json.candidate-r2',
     'f45ed2675f7fcec8f16e5058fbbd2718cb195143099d89d62270a80acb14ff2a',
     'b23f4427131d7fa392af9e286c530e6546791ed0724889600da6abe46b2ff206'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        assert stream.write(raw) == len(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    assert sha(REVIEW) == REVIEW_PIN
    assert sha(PRIMITIVE) == PRIMITIVE_PIN
    assert json.loads(REVIEW.read_bytes())['disposition'] == 'APPROVED_EXACT_TWO_DOCUMENT_METADATA_CANDIDATES'
    git = subprocess.run(['git', '-C', str(F), 'status', '--short', '--untracked-files=no'], capture_output=True)
    assert git.returncode == 0
    with (R / 'PREPUBLICATION-GIT-STATUS.txt').open('xb') as stream:
        assert stream.write(git.stdout) == len(git.stdout)
    spec = importlib.util.spec_from_file_location('root_status_existing_publication', PRIMITIVE)
    primitive = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(primitive)
    output = R / 'publication'
    output.mkdir(exist_ok=False)
    for name, candidate, before, after in ROWS:
        assert sha(F / name) == before
        assert sha(R / candidate) == after
    receipt = dict(at=datetime.now(timezone.utc).isoformat(), executor='/root',
        coordinator_reserved_paths=[row[0] for row in ROWS],
        scope='Two metadata files; all three other agents hold disjoint private evidence scopes',
        review_sha256=REVIEW_PIN, publication_primitive_sha256=PRIMITIVE_PIN,
        completed=[], source_acceptance_promoted=False, automatic_retry=False)
    primary = None
    try:
        for name, candidate, before, after in ROWS:
            target = F / name
            stage = output / (Path(name).name + '.staged')
            backup = output / (Path(name).name + '.native-before')
            raw = (R / candidate).read_bytes()
            with stage.open('xb') as stream:
                assert stream.write(raw) == len(raw)
                stream.flush()
                os.fsync(stream.fileno())
            original_identity = os.stat(target, follow_symlinks=False)
            primitive.publish_prepared(stage, target, backup, before, after)
            assert sha(backup) == before and sha(target) == after
            observed = json.loads(target.read_bytes())
            assert observed == json.loads(raw)
            assert observed['safe_halt_20261020'] == json.loads((R / (Path(name).name + '.before')).read_bytes())['safe_halt_20261020']
            receipt['completed'].append(dict(path=name, before_sha256=before, after_sha256=after,
                native_backup=str(backup), original_inode=original_identity.st_ino,
                backup_inode=os.stat(backup, follow_symlinks=False).st_ino))
    except BaseException as error:
        primary = error
        receipt['failure'] = dict(type=type(error).__name__, message=str(error))
    finally:
        receipt['exit_status'] = 0 if primary is None else 1
        receipt['completed_at'] = datetime.now(timezone.utc).isoformat()
        save(output / 'RESULT.json', receipt)
    if primary is not None:
        raise primary
    print(json.dumps(dict(changed=len(receipt['completed']), receipt=str(output / 'RESULT.json'), exit_status=0)))


if __name__ == '__main__':
    main()
