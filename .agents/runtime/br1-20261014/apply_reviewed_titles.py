"""Four exact active display-name replacements using reviewed native primitives."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os

R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/br1-20261014'
OUT = R / 'active-application'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PUBLICATION = F / '.agents/runtime/rs2-20261014/apply_joined_source.py'
assert sha(PUBLICATION) == '4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'
spec = importlib.util.spec_from_file_location('ceta_title_native_publication', PUBLICATION)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
ALLOWED = frozenset({'src/ceta/desktop/meaning_view.py', 'src/ceta/desktop/operator_view.py',
    'src/ceta/desktop/preparation_view.py', 'src/ceta/desktop/task_view.py'})

def save(path, value):
    with path.open('x', encoding='utf-8') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())

def main():
    claim = read(R / 'br1-20261014/claims.json')['integrate']
    assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
    state = read(R / 'br1-20261014/state.json')
    assert state['nodes']['review']['state'] == state['nodes']['validate']['state'] == 'SUCCEEDED'
    review_path = R / 'independent-review/review.json'
    review = read(review_path)
    assert review['decision'] == 'approved' and review['exit_status'] == 0
    assert sha(Path(__file__)) == review['result']['publication_script_sha256']
    manifest_path = Q / 'TRANSFER-MANIFEST.json'
    manifest = read(manifest_path)
    assert sha(manifest_path) == review['result']['manifest_sha256'] == '12fe2b2a79164fc0efb180c4b8c7d043006af80b61242a707aa92b95dff9d040'
    assert set(manifest['application_paths']) == ALLOWED
    selected = []
    for item in manifest['payloads']:
        relative = item['relative_path']
        assert native.exact_hash(Q / relative) == item['candidate_sha256']
        assert native.exact_hash(F / relative) == item['active_before_sha256']
        if relative in ALLOWED:
            assert item['application_action'] == 'EXTEND_PRESERVE_BEFORE_IMAGE'
            selected.append(item)
        else:
            assert item['candidate_sha256'] == item['active_before_sha256']
    assert len(selected) == 4 and len(manifest['payloads']) == 235
    native.fs.safe_components(OUT, allow_missing=True)
    OUT.mkdir(exist_ok=False)
    originals = []
    for item in selected:
        relative = item['relative_path']
        stage, before, backup = OUT / 'staged' / relative, OUT / 'before' / (relative + '.source'), OUT / 'native-backups' / (relative + '.original')
        for parent in (stage.parent, before.parent, backup.parent):
            native.fs.safe_components(parent, allow_missing=True)
            parent.mkdir(parents=True, exist_ok=True)
            native.fs.safe_components(parent)
        with native.fs.open_source(native.fs.safe_components(Q / relative), exclusive=True) as source:
            candidate = source.read()
            assert hashlib.sha256(candidate).hexdigest() == item['candidate_sha256']
            with stage.open('xb') as output:
                output.write(candidate)
                output.flush()
                os.fsync(output.fileno())
        with native.fs.open_source(native.fs.safe_components(F / relative), exclusive=True) as source:
            data = source.read()
            assert hashlib.sha256(data).hexdigest() == item['active_before_sha256']
            facts = os.fstat(source.fileno())
            with before.open('xb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            originals.append({'relative_path': relative, 'sha256': item['active_before_sha256'], 'device': facts.st_dev,
                'inode': facts.st_ino, 'mode': facts.st_mode, 'bytes': facts.st_size, 'mtime_ns': facts.st_mtime_ns})
    started = {'schema_version': 1, 'started_at': datetime.now(timezone.utc).isoformat(), 'executor': '/root',
        'source_root': str(F), 'claim_input_hash': claim['input_hash'], 'manifest_sha256': sha(manifest_path),
        'review_sha256': sha(review_path), 'before_images': originals}
    save(OUT / 'STARTED.json', started)
    completed = []
    try:
        for item in selected:
            relative = item['relative_path']
            native.publish_prepared(OUT / 'staged' / relative, F / relative, OUT / 'native-backups' / (relative + '.original'),
                item['active_before_sha256'], item['candidate_sha256'])
            completed.append({'relative_path': relative, 'sha256': item['candidate_sha256']})
        save(OUT / 'APPLIED.json', {**started, 'completed': completed,
            'finished_at': datetime.now(timezone.utc).isoformat(), 'status': 'FOUR_REVIEWED_TITLES_APPLIED_AWAITING_ACTIVE_DESTINATION_VERIFICATION'})
    except Exception as error:
        save(OUT / 'FAILED.json', {**started, 'completed': completed,
            'failed_at': datetime.now(timezone.utc).isoformat(), 'error_type': type(error).__name__, 'error': str(error),
            'recovery': 'Preserve every target, stage, logical and native original; reconcile all four paths under new review'})
        raise
    print(json.dumps({'actual_title_paths_applied': len(completed), 'originals_preserved': len(originals),
                     'application_journal_sha256': sha(OUT / 'APPLIED.json')}))

if __name__ == '__main__':
    main()
