"""Publish only two independently reviewed status files, preserving native originals."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, importlib.util, json, os, stat

R = Path(__file__).resolve().parent
F, Q, RUN = R.parents[2], R.parents[2] / '.agents/ct3-20261014', 'ct3-20261014'
OUT = R / 'active-application'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PUBLICATION = F / '.agents/runtime/rs2-20261014/apply_joined_source.py'
assert sha(PUBLICATION) == '4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'
spec = importlib.util.spec_from_file_location('ct3_qualified_native_publication', PUBLICATION)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
ALLOWED = {'build/progress.json', 'handoff/continuity.json'}

def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())

def main():
    assert __debug__
    claim = read(R / RUN / 'claims.json')['integrate']
    assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
    state = read(R / RUN / 'state.json')
    assert state['nodes']['review']['state'] == state['nodes']['validate']['state'] == 'SUCCEEDED'
    review_path = R / 'independent-review/review.json'
    review, stored = read(review_path), read(R / RUN / 'receipts/review.json')
    keys = {'schema_version', 'run_id', 'node_id', 'executor_id', 'started_at', 'finished_at',
            'input_hash', 'changed_files', 'result', 'commands', 'validations', 'exit_status', 'decision'}
    assert set(review) == keys and set(stored) == keys | {'git_baseline', 'observed_git', 'receipt_hash'}
    assert review['decision'] == 'approved' and review['exit_status'] == 0 and review['executor_id'] != '/root'
    assert json.dumps(review, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
        {key: stored[key] for key in keys}, sort_keys=True, separators=(',', ':'), allow_nan=False)
    manifest_path = Q / 'TRANSFER-MANIFEST.json'
    assert sha(manifest_path) == '2773d204475a35934f3f0b80ef110126761b66fb74e9a6065c51f40e4c19de7e'
    manifest = read(manifest_path)
    assert review['result']['manifest_sha256'] == sha(manifest_path)
    helper = read(R / 'independent-review/publication-helper-review.json')
    assert helper['decision'] == 'approved' and helper['exit_status'] == 0
    assert helper['publication_script_sha256'] == sha(Path(__file__))
    assert helper['manifest_sha256'] == sha(manifest_path)
    assert set(manifest['application_paths']) == ALLOWED and len(manifest['payloads']) == 2
    accepted = F / '.agents/runtime/rs-owner2-20261014'
    accepted_state = read(accepted / 'rs-owner2-20261014/state.json')
    assert accepted_state['sequence'] == 13 and all(row['state'] == 'SUCCEEDED' for row in accepted_state['nodes'].values())
    assert read(accepted / 'rs-owner2-20261014/claims.json') == {}
    assert sha(accepted / 'integrate.json') == manifest['accepted_source_ledger']['integrate_receipt']['sha256']
    suite_path = F / manifest['source_suite']['repository_relative_path']
    assert sha(suite_path) == manifest['source_suite']['sha256']
    suite = read(suite_path)
    assert type(suite['tests_run']) is int and suite['tests_run'] == 1416 and len(suite['after_hashes']) == 286
    assert all(type(suite[key]) is int and suite[key] == 0 for key in ('failures', 'errors', 'skips', 'exit_status'))
    assert suite['expected_ids'] == suite['executed_ids'] and len(set(suite['executed_ids'])) == 1416
    assert all(sha(F / relative) == value for relative, value in suite['after_hashes'].items())
    selected, initial_identities = [], {}
    for item in manifest['payloads']:
        relative = item['relative_path']
        assert relative in ALLOWED and item['application_action'] == 'EXTEND_PRESERVE_BEFORE_IMAGE'
        assert native.exact_hash(Q / relative) == item['candidate_sha256']
        assert native.exact_hash(F / relative) == item['active_before_sha256']
        identity = native.fs.file_identity(native.fs.lstat(native.fs.safe_components(F / relative)))
        declared = dict(item['source_native_identity'])
        declared['mode'] = stat.S_IMODE(declared['mode'])
        assert identity == declared
        initial_identities[relative] = identity
        selected.append(item)
    assert len(selected) == 2
    native.fs.safe_components(OUT, allow_missing=True)
    OUT.mkdir(exist_ok=False)
    save(OUT / 'JOINED-SOURCE.json', {'accepted_source_full_sha256': sha(suite_path),
        'accepted_source_integrate_sha256': sha(accepted / 'integrate.json'),
        'metadata_manifest_sha256': sha(manifest_path),
        'retained_source_hashes': suite['after_hashes'],
        'metadata_before_hashes': {item['relative_path']: item['active_before_sha256'] for item in selected},
        'metadata_after_hashes': {item['relative_path']: item['candidate_sha256'] for item in selected},
        'only_metadata_application_paths': sorted(ALLOWED)})
    originals = []
    for item in selected:
        relative = item["relative_path"]
        stage = OUT / "staged" / relative
        before = OUT / "before" / (relative + ".source")
        backup = OUT / "native-backups" / (relative + ".original")
        for parent in (stage.parent, before.parent, backup.parent):
            native.fs.safe_components(parent, allow_missing=True)
            parent.mkdir(parents=True, exist_ok=True)
            native.fs.safe_components(parent)
        with native.fs.open_source(native.fs.safe_components(Q / relative), exclusive=True) as source:
            candidate = source.read()
            assert hashlib.sha256(candidate).hexdigest() == item["candidate_sha256"]
            with stage.open("xb") as output:
                output.write(candidate)
                output.flush()
                os.fsync(output.fileno())
        if item["active_before_sha256"] is not None:
            with native.fs.open_source(native.fs.safe_components(F / relative), exclusive=True) as source:
                data = source.read()
                assert hashlib.sha256(data).hexdigest() == item["active_before_sha256"]
                facts = os.fstat(source.fileno())
                assert native.fs.file_identity(facts) == initial_identities[relative], 'Original identity changed before preservation'
                with before.open("xb") as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                originals.append({"relative_path": relative, "sha256": item["active_before_sha256"],
                    "device": facts.st_dev, "inode": facts.st_ino, "mode": facts.st_mode,
                    "bytes": facts.st_size, "mtime_ns": facts.st_mtime_ns})
    started = {"schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(), "executor": "/root",
        "source_root": str(F), "claim_input_hash": claim["input_hash"], "manifest_sha256": sha(manifest_path),
        "review_sha256": sha(review_path), "helper_review_sha256": sha(R / "independent-review/publication-helper-review.json"),
        "before_images": originals}
    save(OUT / "STARTED.json", started)
    completed = []
    try:
        for item in selected:
            relative = item["relative_path"]
            if item['active_before_sha256'] is not None:
                assert native.fs.file_identity(native.fs.lstat(F / relative)) == initial_identities[relative], 'Original identity changed before replacement'
            native.publish_prepared(OUT / "staged" / relative, F / relative,
                OUT / "native-backups" / (relative + ".original"), item["active_before_sha256"], item["candidate_sha256"])
            if item['active_before_sha256'] is not None:
                backup = OUT / 'native-backups' / (relative + '.original')
                with native.fs.open_source(native.fs.safe_components(backup), exclusive=True) as stream:
                    facts = os.fstat(stream.fileno())
                    digest = hashlib.sha256(stream.read()).hexdigest()
                assert digest == item['active_before_sha256']
                assert native.fs.file_identity(facts) == initial_identities[relative], 'Retained original identity differs'
            assert native.exact_hash(F / relative) == item['candidate_sha256']
            completed.append({"relative_path": relative, "sha256": item["candidate_sha256"]})
        for original in originals:
            relative = original['relative_path']
            with native.fs.open_source(native.fs.safe_components(OUT / 'native-backups' / (relative + '.original')), exclusive=True) as stream:
                facts = os.fstat(stream.fileno())
                assert hashlib.sha256(stream.read()).hexdigest() == original['sha256']
                assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
                    original['device'], original['inode'], original['mode'], original['bytes'], original['mtime_ns'])
        save(OUT / "APPLIED.json", {**started, "completed": completed,
            "finished_at": datetime.now(timezone.utc).isoformat(), "status": "TWO_STATUS_PATHS_APPLIED_WITH_ACCEPTED_SOURCE_RETAINED_AWAITING_DESTINATION_VERIFICATION"})
    except BaseException as error:
        try:
            save(OUT / "FAILED.json", {**started, "completed": completed,
                "failed_at": datetime.now(timezone.utc).isoformat(), "error_type": type(error).__name__, "error": str(error),
                "recovery": "Preserve targets, stages, logical/native originals and reconcile exact two metadata paths under fresh review"})
        except BaseException as journal_error:
            try:
                error.add_note("Publication failure journal could not be written: " + type(journal_error).__name__)
            except BaseException:
                pass
        raise
    print(json.dumps({"actual_status_paths_applied": len(completed), "originals_preserved": len(originals),
                      "application_journal_sha256": sha(OUT / "APPLIED.json")}))


if __name__ == "__main__":
    main()
