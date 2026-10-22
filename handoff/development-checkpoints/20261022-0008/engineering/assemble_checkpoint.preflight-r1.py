"""Freeze reviewed candidate B and retained execution evidence; no canonical writes."""
from datetime import datetime, timezone
from pathlib import Path
import difflib
import json
import os
import subprocess
import sys
import zipfile
from prepare_checkpoint import checkout_state, digest, git, save, scan_exports, stable_read

W = Path(__file__).resolve().parent
F = Path('T:/00-Active/Project-AI-CETA')
O = F / '.agents/runtime/operational-resume-20261020'
B = O / 'sol-journal-read-budget-r1'
C = O / 'canonical-application-diagnostics-r1'
OLD = W.parent.parent / 'checkpoint-0007'
PARENT = 'c7bcf2bfc0b6e6085d39967d4559a97c705411ec'
PUBLIC_PREFIX = 'handoff/development-checkpoints/20261022-0008/'


def main():
    assert not (W / 'CHECKPOINT-INPUTS.json').exists()
    frozen_inputs = json.loads((W.parent / 'packet/INPUTS.json').read_bytes())
    for path, pin in [(frozen_inputs['source_manifest'], frozen_inputs['source_manifest_sha256']),
                      (frozen_inputs['candidate_manifest'], frozen_inputs['candidate_manifest_sha256']),
                      (B / 'review/REVIEW.json', frozen_inputs['candidate_review_sha256'])]:
        assert digest(stable_read(path)[0]) == pin
    source = json.loads(Path(frozen_inputs['source_manifest']).read_bytes())
    previous = json.loads((OLD / 'work/SOURCE-MANIFEST.json').read_bytes())
    assert source['payload_hashes'] == previous['payload_hashes']
    assert len(source['payload_hashes']) == 559
    canonical_pins = {p: stable_read(F / p)[1] for p in source['payload_hashes']}
    assert {p: pin['sha256'] for p, pin in canonical_pins.items()} == source['payload_hashes']
    save(W / 'SOURCE-MANIFEST.json', dict(candidate=str(F), payload_count=559,
        payload_hashes=source['payload_hashes'], derived_from=frozen_inputs['source_manifest'],
        derived_manifest_sha256=frozen_inputs['source_manifest_sha256'], canonical_delta=0))
    before = checkout_state(F)
    assert before['root'].replace('\\', '/') == str(F).replace('\\', '/')
    assert before['branch'] == 'refs/heads/candidate/societal-reasoning-v1'
    assert before['head'] == 'd0ee29ce75f99fe974e10ec9baf38c5a516dd2df'
    assert before['remote_fetch'] == before['remote_push'] == 'git@github.com:IAmSoThirsty/Project-AI-Ceta.git'
    refs = dict(row.split(' ', 1) for row in git(F, ['for-each-ref', '--format=%(refname) %(objectname)']).decode().splitlines())
    assert refs['refs/heads/development/checkpoints'] == refs['refs/remotes/origin/development/checkpoints'] == PARENT
    assert git(F, ['ls-remote', '--refs', 'origin', 'refs/heads/development/checkpoints']).decode().splitlines() == [PARENT + '\trefs/heads/development/checkpoints']
    git(F, ['merge-base', '--is-ancestor', before['head'], PARENT])
    save(W / 'CANONICAL-BEFORE.json', dict(checkout=before, canonical_pins=canonical_pins,
        normal_index_native=stable_read(F / '.git/index')[1], refs=refs))
    completed = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(W / 'test_exact_git_scope.py')],
        cwd=F, capture_output=True)
    for suffix, data in [('stdout', completed.stdout), ('stderr', completed.stderr)]:
        with (W / ('SCOPE-CONTROLS.' + suffix)).open('xb') as stream: stream.write(data)
    save(W / 'SCOPE-CONTROLS.json', dict(argv=completed.args, exit_status=completed.returncode,
        tests=9, product_tests=False, actual_git_mutation=False))
    assert completed.returncode == 0
    public = W / 'public'; public.mkdir()
    selected = {}
    def add(path, member):
        raw, pin = stable_read(path)
        assert member not in selected and len(raw) < 95_000_000
        selected[member] = dict(input_path=str(path), input_pin=pin, sha256=digest(raw))
    bm = json.loads((B / 'work/MANIFEST.json').read_bytes())
    candidate = Path(bm['candidate'])
    assert len(bm['payload_hashes']) == 560
    for rel, pin in sorted(bm['payload_hashes'].items()):
        assert digest(stable_read(candidate / rel)[0]) == pin
        if '.local-build-cache/' in rel:
            assert rel.startswith('.local-build-cache/restoration-proof/') and rel.endswith('.json')
        add(candidate / rel, 'journal-read-budget-candidate/source/' + rel)
    assert sum('.local-build-cache/' in rel for rel in bm['payload_hashes']) == 5
    allowed = {'.json', '.md', '.txt', '.py', '.log', '.stdout', '.stderr', '.patch', '.bin'}
    for job in [B, C]:
        for folder in ('packet', 'work', 'review', 'control'):
            for path in sorted((job / folder).iterdir()):
                if path.is_file() and path.suffix in allowed:
                    add(path, job.name + '/' + folder + '/' + path.name)
    for name in ('START.json', 'SOURCE-PINS.json', 'OWNED-LAUNCH.json', 'stdout.bin', 'stderr.bin', 'RESULT.json', 'stdin.bin'):
        add(C / 'work/live-cli-01' / name, C.name + '/work/live-cli-01/' + name)
    for name in ('SOURCE-BEFORE.json', 'TESTS.json', 'TESTS.log', 'run_independent.py', 'TERMINAL.json'):
        path = B / 'review' / name
        assert path.is_file()
    # Frozen failure records are evidence, not accepted source packages.
    J = O / 'sol-product-integration-r1'
    for sub in ('work', 'work/attempt2'):
        for name in ('TEST-RESULT.json', 'TESTS.log'):
            add(J / sub / name, J.name + '/' + sub + '/' + name)
    FR = O / 'sol-fixture-runner-repair-r1'
    for name in ('REVIEW.json', 'TESTS.json', 'TESTS.log', 'independent_controls.py'):
        add(FR / 'review' / name, FR.name + '/review/' + name)
    for folder in ('control', 'review'):
        for path in sorted((OLD / folder).iterdir()):
            if path.is_file() and path.suffix in allowed:
                add(path, 'checkpoint-0007/' + folder + '/' + path.name)
    scan = scan_exports(selected)
    save(public / 'RAW-SECRET-SCAN.json', scan)
    assert not scan['findings'], 'Review raw secret-scan findings before any export'
    archive = public / 'REVIEWED-CANDIDATE-AND-EVIDENCE.zip'
    members = []
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as z:
        for name, item in selected.items():
            raw, pin = stable_read(item['input_path']); assert pin == item['input_pin']
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED; info.external_attr = 0o100644 << 16
            z.writestr(info, raw)
            members.append(dict(member=name, source=item['input_path'], sha256=digest(raw), bytes=len(raw)))
    save(public / 'TRANSPORT.json', dict(method='ZIP_STORED_EXACT_REVIEWED_CANDIDATE_AND_RAW_EVIDENCE',
        archive_sha256=digest(archive.read_bytes()), members=members,
        excludes=['secrets/credentials', 'environments', 'generated caches except five immutable registry source inputs',
            'disposable fixtures/live profiles', 'live coordinator state', 'oversized original PDF',
            'unreviewed combined candidate source', 'rejected fixture-runner implementation', 'incomplete performance work']))
    rows = []
    for rel in list(bm['changed_paths']) + list(bm['added_paths']):
        before_path = Path(bm['baseline_candidate']) / rel
        old_lines = before_path.read_text(encoding='utf-8').splitlines() if before_path.exists() else []
        new_lines = (candidate / rel).read_text(encoding='utf-8').splitlines()
        ops = difflib.SequenceMatcher(a=old_lines, b=new_lines).get_opcodes()
        rows.append(dict(path=rel, added=sum(l-k for op,i,j,k,l in ops if op in ('replace','insert')),
            removed=sum(j-i for op,i,j,k,l in ops if op in ('replace','delete'))))
    assert len({r['path'] for r in rows}) == 5
    category = lambda prefix: dict(added=sum(r['added'] for r in rows if r['path'].startswith(prefix)),
        removed=sum(r['removed'] for r in rows if r['path'].startswith(prefix)))
    loc = dict(candidate_paths=rows, candidate_source=category('src/'), candidate_tests=category('tests/'),
        candidate_docs=category('docs/'), canonical_source_delta=0, copied_product_loc=0,
        authoring_time='Prior reviewed candidate; no new product code authored during checkpoint preparation')
    save(public / 'SOURCE-TEST-DELTA.json', loc)
    status = json.loads((OLD / 'work/public/STATUS.json').read_bytes())
    status.update(checkpoint_sequence=8, checkpoint_parent=PARENT, prepared_at=datetime.now(timezone.utc).isoformat(),
        checkpoint_publication='PREPARED_REQUIRES_DISTINCT_REVIEW_AND_FRESH_EXACT_GIT_CLAIM',
        canonical_source_changed_since_checkpoint7=False, source_payloads=559,
        preserved_candidate=dict(name='Journal cooperative read-budget', namespace=PUBLIC_PREFIX+'REVIEWED-CANDIDATE-AND-EVIDENCE.zip',
            payloads=560, review_tests=113, failures=0, errors=0, skips=0, canonical_promoted=False,
            candidate_manifest_sha256=frozen_inputs['candidate_manifest_sha256']),
        canonical_cli_evidence=dict(actual_exit_status=0, startup='READY', diagnostics='COMPLETE_PROCESS_USAGE', cleanup='STOPPED',
            retained_execution_date='2026-10-20', current_reexecution=False, formal_workflow_gate='NOT_RUN_MISSING_VERIFIER_PATH'),
        current_source_test_delta=loc, full_product_acceptance=False,
        exact_git_scope_correction='Repository-local narrow adapter; requires independent review before use',
        latest_test_state=dict(canonical_selected508=dict(failures=2, errors=0, passed=False),
            joined_initial636=dict(failures=3, errors=85, passed=False), joined_successor638=dict(failures=5, errors=2, passed=False),
            fixture_runner_review=dict(decision='rejected', tests=27, failures=1)),
        acceptance_limits=['Candidate B only; combined native admission timing remains failed with the 50ms bound unchanged',
            'Actual CLI diagnostics run is caller-unqualified and does not establish a positive governed consequential effect',
            'Formal CLI graph gate still points at an absent verifier; retained exact-run review does not close it',
            'Installed, offline, native isolation, recovery, endurance, hardware and human acceptance remain open',
            'Original first-checkpoint integration receipt remains FAILED although its push/readbacks succeeded',
            'No work or checkpoints asserted during queued heartbeat interval'])
    save(public / 'STATUS.json', status)
    (public / 'STATUS.md').write_text('# Project-AI: CETA development checkpoint 8\n\n'
        'Canonical559 payloads are unchanged from checkpoint7. A separately reviewed560-payload Journal read-budget candidate is preserved '
        'under this checkpoint\'s handoff archive, with113 passing scoped tests and exact source/review pins. '
        'It has not been promoted to canonical product source. Candidate source+220/-9,tests+377/-0,docs+9/-3;copied product LOC0.\n\n'
        'The retained actual canonical Windows CLI evidence reports exit0,READY,COMPLETE_PROCESS_USAGE,STOPPED and five closed outer handles. '
        'Its envelope remains caller-unqualified;CPU/latency unavailable;no positive governed consequential effect is established. '
        'The formal workflow validation path is missing and that gate has not passed.\n\n'
        'Preserved failures include the636-test initial integration,638-test successor and rejected27-test fixture-runner review. '
        'Canonical508 still has two timing-priority failures. The50ms admission bound is unchanged. '
        'Full product,installed,offline,isolation,recovery,endurance,hardware and human acceptance remain open. '
        'The original first-checkpoint FAILED receipt remains FAILED.\n\n'
        'Preparation uses a temporary index/object database;normal HEAD,index,canonical files and every parent path/mode, '
        'PDF part/reassembly tool and exactly five immutable registry source fixtures remain preserved. '
        'Environments,generated caches,disposable fixtures,live coordinator state,secrets and original oversized PDF are excluded. '
        'A separately reviewed local correction narrows the installed coordinator\'s Git lease;no installed tool is edited.\n',encoding='utf-8')
    extras = []
    for path in sorted(public.iterdir()):
        destination = {'STATUS.json':'DEVELOPMENT-CHECKPOINT.json','STATUS.md':'DEVELOPMENT-CHECKPOINT.md'}.get(path.name,PUBLIC_PREFIX+path.name)
        extras.append(dict(source=str(path), destination=destination, sha256=digest(path.read_bytes())))
    for rel in sorted(list(bm['changed_paths']) + list(bm['added_paths'])):
        extras.append(dict(source=str(candidate / rel), destination=PUBLIC_PREFIX+'candidate/'+rel,
            sha256=bm['payload_hashes'][rel]))
    for name in ('prepare_checkpoint.py','assemble_checkpoint.py','exact_git_scope.py','test_exact_git_scope.py',
                 'publish_checkpoint.py','verify_prepared.py','SOURCE-MANIFEST.json','SCOPE-CONTROLS.json',
                 'SCOPE-CONTROLS.stdout','SCOPE-CONTROLS.stderr', 'assemble_checkpoint.syntax-r1.py',
                 'ASSEMBLY-COMMAND.json','ASSEMBLY.stdout','ASSEMBLY.stderr'):
        path = W / name
        extras.append(dict(source=str(path),destination=PUBLIC_PREFIX+'engineering/'+name,sha256=digest(path.read_bytes())))
    save(W / 'CHECKPOINT-INPUTS.json', dict(root=str(F), output=str(W/'prepared-0001'), expected_head=before['head'],
        expected_branch=before['branch'], expected_status_sha256=before['status_sha256'], origin=before['remote_fetch'],
        ref='refs/heads/development/checkpoints', parent=PARENT, manifest=str(W/'SOURCE-MANIFEST.json'),
        manifest_sha256=digest((W/'SOURCE-MANIFEST.json').read_bytes()), extra_exports=extras,
        message='Preserve reviewed Journal read-budget candidate and canonical diagnostics evidence\n\nCanonical559 unchanged. Candidate113 scoped tests pass; failed508/636/638 and rejected fixture-runner review retained honestly. Development preservation only;full product acceptance remains open.'))
    print(json.dumps(dict(canonical_payloads=559,candidate_payloads=560,evidence_members=len(members),loc=loc)))


if __name__ == '__main__': main()
