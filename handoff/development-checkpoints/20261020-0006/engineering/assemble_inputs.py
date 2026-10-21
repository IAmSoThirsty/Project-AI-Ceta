"""Build only explicit stable C6 source/evidence inputs; never publish."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import json
import zipfile
from prepare_checkpoint import checkout_state, digest, git, save, stable_read, scan_exports

W = Path(__file__).resolve().parent
F = Path('T:/00-Active/Project-AI-CETA')
O = F / '.agents/runtime/operational-resume-20261020'
C5 = W.parent.parent / 'checkpoint-0005'
PREFIX = 'handoff/development-checkpoints/20261020-0006/'


def main():
    claim = json.loads((W.parent / 'control/implement-claim.json').read_bytes())['response']['claim']
    assert claim['executor_id'] == '/root/sol_discovery'
    assert claim['input_hash'] == 'd71e485aca4a9fa42d029dd06d0f88bc7a034034b14b6430c1ecca327f1bf728'
    manifest = json.loads((W / 'SOURCE-MANIFEST.json').read_bytes())
    candidate = Path(manifest['candidate'])
    base = json.loads(Path(manifest['base_manifest']).read_bytes())
    deltas = {}
    for rel, entry in manifest['overlay'].items():
        before = (Path(base['candidate']) / rel).read_text().splitlines() if rel in base['payload_hashes'] else []
        after = (candidate / rel).read_text().splitlines()
        delta = list(difflib.ndiff(before, after))
        deltas[rel] = dict(added=sum(x.startswith('+ ') for x in delta),
                           removed=sum(x.startswith('- ') for x in delta), before=len(before), after=len(after))
    source_delta = [v for k, v in deltas.items() if k.startswith('src/')]
    test_delta = [v for k, v in deltas.items() if k.startswith('tests/')]
    assert sum(v['added'] for v in source_delta) == 53
    assert sum(v['removed'] for v in source_delta) == 3
    assert sum(v['added'] for v in test_delta) == 373
    assert sum(v['removed'] for v in test_delta) == 0
    save(W / 'PRODUCT-LOC.json', dict(paths=deltas, copied_loc=0,
        source_added=53, source_removed=3, tests_added=373, tests_removed=0,
        newly_authored_checkpoint_engineering_tools_separate=True))
    public = W / 'public'; public.mkdir(exist_ok=False)
    selected = {}
    allowed = {'.json', '.jsonl', '.md', '.txt', '.py', '.log', '.patch', '.stdout', '.stderr'}

    def add(path, member):
        assert path.is_file() and path.suffix in allowed, path
        assert member not in selected
        raw, pin = stable_read(path)
        selected[member] = dict(input_path=str(path), input_pin=pin, sha256=digest(raw))

    for lane in ('sol-discovery-r2', 'sol-diagnostics-r1'):
        root = O / lane
        for folder in ('control', 'review', 'delivery'):
            for path in sorted((root / folder).rglob('*')):
                if path.is_file() and path.suffix in allowed:
                    add(path, lane + '/' + path.relative_to(root).as_posix())
        for path in sorted((root / 'work').iterdir()):
            if path.is_file() and path.suffix in allowed:
                add(path, lane + '/work/' + path.name)
    for folder in ('control', 'review'):
        for path in sorted((C5 / folder).rglob('*')):
            if path.is_file() and path.suffix in allowed:
                add(path, 'checkpoint-0005/' + path.relative_to(C5).as_posix())
    for path in sorted((C5 / 'work').iterdir()):
        if path.is_file() and path.suffix in allowed:
            add(path, 'checkpoint-0005/work/' + path.name)
    failed = O / 'sol-discovery-r1/control'
    for name in ('implement-receipt.json', 'implement-complete.json',
                 'implement-receipt-final.json', 'implement-complete-final.json'):
        add(failed / name, 'history/failed-discovery-r1/' + name)
    add(O / 'sol-astra-code-team-r1/control/ROOT-DISCOVERY-CACHE-CONFLICT-REPRODUCTION.json',
        'history/failed-discovery-r1/ROOT-CACHE-CONFLICT-REPRODUCTION.json')
    original_failed = W.parent.parent / 'control-r2'
    for path in sorted(original_failed.rglob('*')):
        if path.is_file() and path.suffix in allowed:
            add(path, 'history/checkpoint-0001-r2/' + path.relative_to(original_failed).as_posix())
    raw_scan = scan_exports(selected)
    save(public / 'RAW-EVIDENCE-SECRET-SCAN.json', raw_scan)
    assert not raw_scan['findings'], 'raw evidence requires independent secret review'
    archive = public / 'RAW-EVIDENCE.zip'
    members = []
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as output:
        for member, item in selected.items():
            raw, pin = stable_read(item['input_path']); assert pin == item['input_pin']
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            output.writestr(info, raw)
            members.append(dict(member=member, source=item['input_path'], sha256=item['sha256'], bytes=len(raw)))
    save(public / 'EVIDENCE-TRANSPORT.json', dict(method='ZIP_STORED_BYTE_EXACT_RAW_EVIDENCE',
        archive_sha256=digest(archive.read_bytes()), members=members,
        exclusions=['environments', 'binary acquisitions', 'disposable SQLite/live state',
                    'credentials', 'oversized original PDF', 'active owner binding/collector wiring']))
    previous_status = json.loads((C5 / 'work/public/STATUS.json').read_bytes())
    status = dict(previous_status)
    status.update(checkpoint_sequence=6, checkpoint_parent='6f100604acb0dd3f4f8cc189feb64cfa7e357e0b',
        prepared_at=datetime.now(timezone.utc).isoformat(), source_payloads=554,
        source_manifest_sha256=digest((W / 'SOURCE-MANIFEST.json').read_bytes()),
        checkpoint_publication='NOT_RUN_PREPARED_FOR_DISTINCT_REVIEW',
        source_component_review='H2 and D exact source deltas independently approved; checkpoint review pending',
        local_canonical_source_changed=False, checkpoint_source_delta=dict(added=53, removed=3),
        checkpoint_test_delta=dict(added=373, removed=0), copied_loc=0,
        current_native_execution=False, current_installed_qualification=False,
        accepted_source_handoffs=manifest['accepted_predecessors'],
        checkpoint_0005_completed=dict(commit='6f100604acb0dd3f4f8cc189feb64cfa7e357e0b',
            push=True, remote_readback=True, anonymous_readback=True, evidence='RAW-EVIDENCE.zip/checkpoint-0005/control'),
        original_source_manifest_status_fields='Historical flags are not current acceptance decisions; fresh minimal manifest used',
        active_owner_binding_and_operator_wiring='EXCLUDED_FROM_THIS_CHECKPOINT_PENDING_JOIN',
        preserved_failures=['H1 terminal FAILED receipt', 'H1 illegal transition denial',
                            'Root cache conflict reproduction', 'initial C1r2 failure'])
    status['verified_development'] = previous_status['verified_development'] + [
        'Accepted H2 CPU process-affinity and cached-scope conflict fencing; controlled tests and independent review retained',
        'Accepted D performance diagnostics typed metric/counter validation; controlled tests and independent review retained']
    status['open_issues'] = previous_status['open_issues'] + [
        'CPU sets, thread affinity, job CPU limits, thermal constraints and complete reservation wiring remain open',
        'D raw observations are controlled data; no new native qualification or causal bottleneck proof',
        'Owned service diagnostics and operator/CLI integration are not included in this checkpoint']
    save(public / 'STATUS.json', status)
    (public / 'STATUS.md').write_text(
        '# Project-AI: CETA development checkpoint 6\n\n'
        'Prepared successor of checkpoint 5, which was pushed with remote and anonymous byte readbacks. '
        'This checkpoint is not published by preparation. It contains 554 product payloads: the prior '
        'EOF-repaired 552 plus independently accepted H2 and D changes. Product source delta +53/-3; '
        'tests +373/-0; copied LOC 0. Existing PDF parts, five immutable fixtures, prior exports and modes '
        'are preserved through the parent tree.\n\n'
        'Raw source/test/review/gate/handoff and publication evidence is preserved byte-for-byte in the '
        'stored evidence archive, with member hashes and complete configured-pattern scans. H1 FAILED '
        'and its denied retry remain failures. Root cache-conflict evidence remains separate from the '
        'accepted repair. Historical native observations are not new qualification.\n\n'
        'The active owner-binding/collector/operator join is excluded. No canonical cutover, native '
        'process action, installed/full-product acceptance, environment acquisition or host repair is '
        'performed. The T-volume warning and all existing application/runtime/loader/offline/endurance '
        'obligations remain open. Checkpoint independent review, gate and one fresh publication attempt '
        'remain Root-owned work.\n', encoding='utf-8')
    extras = []
    for path in sorted(public.iterdir()):
        destination = {'STATUS.json': 'DEVELOPMENT-CHECKPOINT.json',
                       'STATUS.md': 'DEVELOPMENT-CHECKPOINT.md'}.get(path.name, PREFIX + path.name)
        extras.append(dict(source=str(path), destination=destination, sha256=digest(path.read_bytes())))
    for name in ('prepare_checkpoint.py', 'publish_checkpoint.py', 'verify_prepared.py',
                 'assemble_inputs.py', 'SOURCE-MANIFEST.json', 'TOOL-COPY-PINS.json', 'PRODUCT-LOC.json'):
        path = W / name
        extras.append(dict(source=str(path), destination=PREFIX + 'engineering/' + name,
                           sha256=digest(path.read_bytes())))
    checkout = checkout_state(F)
    refs = git(F, ['for-each-ref', '--format=%(refname) %(objectname)']).decode().splitlines()
    assert 'refs/heads/development/checkpoints 6f100604acb0dd3f4f8cc189feb64cfa7e357e0b' in refs
    assert 'refs/remotes/origin/development/checkpoints 6f100604acb0dd3f4f8cc189feb64cfa7e357e0b' in refs
    git(F, ['merge-base', '--is-ancestor', checkout['head'], '6f100604acb0dd3f4f8cc189feb64cfa7e357e0b'])
    canonical = {rel: stable_read(F / rel)[1] if (F / rel).is_file() else None
                 for rel in manifest['payload_hashes']}
    before = dict(checkout=checkout, normal_index_native=stable_read(F / '.git/index')[1],
                  canonical_product_pins=canonical, refs=refs)
    save(W / 'CANONICAL-BEFORE.json', before)
    save(W / 'PREPARE-LEASE-READBACK.json', claim)
    spec = dict(root=str(F), output=str(W / 'prepared-0001'), expected_head=checkout['head'],
        expected_branch=checkout['branch'], origin=checkout['remote_fetch'],
        ref='refs/heads/development/checkpoints', parent='6f100604acb0dd3f4f8cc189feb64cfa7e357e0b',
        manifest=str(W / 'SOURCE-MANIFEST.json'), manifest_sha256=digest((W / 'SOURCE-MANIFEST.json').read_bytes()),
        extra_exports=extras,
        message='Checkpoint independently accepted resource discovery and diagnostics corrections\n\n'
                'Preserve prior EOF repair, complete history and immutable fixtures. Add exact accepted H2 and D '
                'product deltas and truthful source/test/review/publication evidence. Active owner/operator join excluded. '
                'Development preservation only; no canonical or product acceptance.\n')
    save(W / 'CHECKPOINT-INPUTS.json', spec)
    save(W / 'EXPORT-SELECTION.json', dict(source_payloads=554, evidence_members=len(members),
        exports=extras, parent_tree_preservation=True, native_effects=False, publication=False))
    print(json.dumps(dict(source_payloads=554, evidence_members=len(members), extra_exports=len(extras))))


if __name__ == '__main__':
    main()
