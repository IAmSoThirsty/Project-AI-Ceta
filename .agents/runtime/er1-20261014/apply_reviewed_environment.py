"""Publish exactly thirty reviewed E3 files with native and logical originals."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys

R = Path(__file__).resolve().parent
F = R.parents[2]
Q = F / '.agents/er1-20261014'
E3 = F / '.agents/source-assembly-20261014T021300Z/.agents/e3'
RUN = 'er1-20261014'
OUT = R / 'active-application'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
now = lambda: datetime.now(timezone.utc).isoformat()

def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)

def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())

def load_native():
    require(os.name == 'nt' and sys.flags.optimize == 0, 'Normal native Windows Python is required')
    require(Path(sys.executable) == E3 / 'Scripts/python.exe', 'Exact unchanged E3 Python is required')
    primitive = F / '.agents/runtime/rs2-20261014/apply_joined_source.py'
    require(sha(primitive) == '4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77', 'Native primitive changed')
    spec = importlib.util.spec_from_file_location('er1_native_publication', primitive)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    require(sha(R / 'er1_support.py') == '38721b1fa0c112f568a4e957b5ae3a1ecd747645c83ec5882228947805a198d5', 'Native inventory helper changed')
    sys.path.insert(0, str(R))
    import er1_support
    return module, er1_support

def main():
    native, support = load_native()
    claim = read(R / RUN / 'claims.json')['integrate']
    require(claim['executor_id'] == '/root' and claim['workspace'] == str(E3), 'Exclusive E3 integration claim is required')
    state = read(R / RUN / 'state.json')
    require(state['nodes']['review']['state'] == state['nodes']['validate']['state'] == 'SUCCEEDED', 'Actual review and gate are required')
    review_path = R / 'independent-review/review.json'
    require(sha(review_path) == '8322051dbf2b0efac25a46ea2af47ce1fcab2cf62f42d41776a28e677a94e0b3', 'Frozen distinct candidate receipt differs')
    review = read(review_path)
    require(review['decision'] == 'approved' and review['exit_status'] == 0, 'Distinct candidate approval is required')
    helper_path = R / 'independent-review/publication-helper-review.json'
    helper = read(helper_path)
    require(helper['decision'] == 'approved' and helper['exit_status'] == 0 and
            helper['publication_script_sha256'] == sha(Path(__file__)), 'Exact helper approval is required')
    manifest_path = Q / 'TRANSFER-MANIFEST.json'
    require(sha(manifest_path) == '7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83', 'Frozen manifest changed')
    require(helper['manifest_sha256'] == sha(manifest_path), 'Helper review manifest differs')
    manifest = read(manifest_path)
    require(review['result']['manifest']['sha256'] == sha(manifest_path), 'Candidate review manifest differs')
    self_review = manifest['self_review']
    self_review_path = F / self_review['repository_relative_path']
    require(self_review_path == R / 'self-review.json' and sha(self_review_path) == self_review['sha256'], 'Bound author self-review differs')
    require(manifest['active_environment_root'] == str(E3), 'Environment identity differs')
    rows = manifest['payloads']
    require(len(rows) == 30, 'Exactly thirty replacement payloads are required')
    allowed_names = {
        'jsonschema.exe', 'pip.exe', 'pip3.exe', 'pip3.12.exe', 'pyside6-assistant.exe',
        'pyside6-balsam.exe', 'pyside6-balsamui.exe', 'pyside6-deploy.exe', 'pyside6-designer.exe',
        'pyside6-genpyi.exe', 'pyside6-linguist.exe', 'pyside6-lrelease.exe', 'pyside6-lupdate.exe',
        'pyside6-metaobjectdump.exe', 'pyside6-project.exe', 'pyside6-qml.exe',
        'pyside6-qmlcachegen.exe', 'pyside6-qmlformat.exe', 'pyside6-qmlimportscanner.exe',
        'pyside6-qmllint.exe', 'pyside6-qmlls.exe', 'pyside6-qmltyperegistrar.exe',
        'pyside6-qsb.exe', 'pyside6-qtpy2cpp.exe', 'pyside6-rcc.exe',
        'pyside6-svgtoqml.exe', 'pyside6-uic.exe'}
    allowed = {'Scripts/' + name for name in allowed_names} | {
        'Lib/site-packages/pip-25.0.1.dist-info/RECORD',
        'Lib/site-packages/jsonschema-4.26.0.dist-info/RECORD',
        'Lib/site-packages/pyside6_essentials-6.11.2.dist-info/RECORD'}
    require(len(allowed) == 30, 'Fixed allowed target count differs')
    selected = {}
    for row in rows:
        target = Path(row['source_path'])
        require(target.is_relative_to(E3), 'Target escapes own E3')
        relative = target.relative_to(E3).as_posix()
        native.fs.relative_name(relative)
        require(relative in allowed and relative not in selected, 'Unexpected or repeated target')
        candidate_relative = row['candidate_relative_path']
        native.fs.relative_name(candidate_relative)
        expected_candidate = ('launchers/' + target.name if relative.startswith('Scripts/')
            else 'metadata/' + target.parent.name + '/RECORD')
        require(candidate_relative == expected_candidate, 'Candidate-to-target mapping differs')
        require(native.exact_hash(Q / candidate_relative) == row['candidate_sha256'], 'Candidate drift')
        require(native.exact_hash(target) == row['source_sha256'], 'Original target drift')
        require(native.fs.file_identity(native.fs.lstat(target)) == row['source_native_identity'], 'Original target identity drift')
        before = F / row['before_image']['repository_relative_path']
        require(before.is_relative_to(R / 'before-images') and sha(before) == row['source_sha256'], 'Author original differs')
        selected[relative] = row
    require(set(selected) == allowed, 'Exact allowed target set differs')
    conservation_ref = manifest['source_conservation']
    conservation_path = F / conservation_ref['repository_relative_path']
    require(conservation_path == R / 'source-conservation.json' and
            sha(conservation_path) == conservation_ref['sha256'] ==
            'e125aa4d0a3b5a28d1521ee407d138bc4bcb05fa2ade20cab8c69467742ac2e4', 'Frozen conservation proof differs')
    conservation = read(conservation_path)
    historical_path = F / conservation['after']['repository_relative_path']
    require(historical_path == R / 'E3-after-tests.json' and
            sha(historical_path) == conservation['after']['sha256'] ==
            '9c50b10fe1333ef2a4ee5d433c8c94d5a5bd936b2174a51e74bdff2bf0eea013', 'Frozen comparison snapshot differs')
    require(conservation['ordinary_before_after_exact'] is True and
            conservation['ordinary_native_identities_exact'] is True and
            set(conservation['future_active_destination_paths']) == allowed, 'Exact conservation scope differs')
    baseline = support.snapshot_tree()
    baseline_files = {row['relative_path']: row for row in baseline['members'] if row['kind'] == 'ordinary_file'}
    require(len(baseline_files) == 3601, 'Current environment membership differs')
    historical = read(historical_path)
    historical_files = {row['relative_path']: row for row in historical['members'] if row['kind'] == 'ordinary_file'}
    require(baseline_files == historical_files, 'Environment files changed since author qualification')
    native.fs.safe_components(OUT, allow_missing=True); OUT.mkdir(exist_ok=False)
    save(OUT / 'environment-before.json', baseline)
    originals = []
    for relative, row in sorted(selected.items()):
        stage = OUT / 'staged' / relative
        before = OUT / 'before' / (relative + '.source')
        backup = OUT / 'native-backups' / (relative + '.original')
        for parent in (stage.parent, before.parent, backup.parent):
            native.fs.safe_components(parent, allow_missing=True); parent.mkdir(parents=True, exist_ok=True)
            native.fs.safe_components(parent)
        with native.fs.open_source(native.fs.safe_components(Q / row['candidate_relative_path']), exclusive=True) as stream:
            data = stream.read()
        require(len(data) == row['candidate_bytes'] and hashlib.sha256(data).hexdigest() == row['candidate_sha256'], 'Stage binding differs')
        with stage.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        with native.fs.open_source(native.fs.safe_components(E3 / relative), exclusive=True) as stream:
            data = stream.read(); facts = os.fstat(stream.fileno())
        require(hashlib.sha256(data).hexdigest() == row['source_sha256'], 'Original changed before preservation')
        expected_identity = row['source_native_identity']
        require((facts.st_dev, facts.st_ino, facts.st_size, facts.st_mtime_ns) == (
            expected_identity['device'], expected_identity['inode'], expected_identity['bytes'],
            expected_identity['mtime_ns']), 'Original handle identity changed before preservation')
        with before.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        originals.append({'relative_path': relative, 'sha256': row['source_sha256'],
            'device': facts.st_dev, 'inode': facts.st_ino, 'mode': facts.st_mode,
            'bytes': facts.st_size, 'mtime_ns': facts.st_mtime_ns})
    started = {'schema_version': 1, 'started_at': now(), 'executor': '/root',
        'environment_root': str(E3), 'source_root': str(F), 'claim_input_hash': claim['input_hash'],
        'manifest_sha256': sha(manifest_path), 'review_sha256': sha(review_path),
        'self_review_sha256': sha(self_review_path),
        'source_conservation_sha256': sha(conservation_path), 'frozen_comparison_snapshot_sha256': sha(historical_path),
        'helper_review_sha256': sha(helper_path), 'before_images': originals,
        'environment_before_sha256': sha(OUT / 'environment-before.json'),
        'limits': ['Thirty individual native replacements; group atomicity is not provided',
            'On interruption retain every target/stage/original and reconcile all thirty paths before resuming',
            'Same-principal privileged ancestor replacement is outside this controlled owner scope']}
    save(OUT / 'STARTED.json', started)
    completed = []
    try:
        with (OUT / 'publication-events.jsonl').open('x', encoding='utf-8') as events:
            for relative, row in sorted(selected.items()):
                require(native.fs.file_identity(native.fs.lstat(E3 / relative)) == row['source_native_identity'],
                        'Original target identity changed before replacement')
                native.publish_prepared(OUT / 'staged' / relative, E3 / relative,
                    OUT / 'native-backups' / (relative + '.original'), row['source_sha256'], row['candidate_sha256'])
                original = next(item for item in originals if item['relative_path'] == relative)
                backup = OUT / 'native-backups' / (relative + '.original')
                with native.fs.open_source(native.fs.safe_components(backup), exclusive=True) as stream:
                    facts = os.fstat(stream.fileno())
                    backup_digest = hashlib.sha256(stream.read()).hexdigest()
                require(backup_digest == original['sha256'] and
                    (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
                        original['device'], original['inode'], original['mode'], original['bytes'], original['mtime_ns']),
                    'Native original bytes or handle identity differ after replacement')
                completed.append({'relative_path': relative, 'sha256': row['candidate_sha256']})
                events.write(json.dumps({'recorded_at': now(), **completed[-1]}) + '\n')
                events.flush(); os.fsync(events.fileno())
        after = support.snapshot_tree()
        after_files = {row['relative_path']: row for row in after['members'] if row['kind'] == 'ordinary_file'}
        require(set(after_files) == set(baseline_files), 'Environment membership changed')
        for relative, original in baseline_files.items():
            if relative in selected:
                require(after_files[relative]['sha256'] == selected[relative]['candidate_sha256'], 'Published bytes differ')
            else:
                require(after_files[relative] == original, 'Unrelated environment file changed')
        save(OUT / 'environment-after.json', after)
        save(OUT / 'APPLIED.json', {**started, 'completed': completed, 'finished_at': now(),
            'environment_after_sha256': sha(OUT / 'environment-after.json'),
            'status': 'THIRTY_ENVIRONMENT_PATHS_APPLIED_AWAITING_DESTINATION_VERIFICATION'})
    except BaseException as error:
        try:
            save(OUT / 'FAILED.json', {**started, 'completed': completed, 'failed_at': now(),
                'error_type': type(error).__name__, 'error': str(error),
                'recovery': 'Preserve all targets, stages, originals and events; reconcile exact thirty files before resume'})
        except BaseException as journal_error:
            error.add_note('Failure journal could not be written: ' + type(journal_error).__name__)
        raise
    print(json.dumps({'actual_environment_paths_applied': len(completed), 'native_originals': len(originals),
        'unchanged_other_environment_files': len(baseline_files) - len(selected),
        'application_journal_sha256': sha(OUT / 'APPLIED.json')}), flush=True)

if __name__ == '__main__':
    main()
