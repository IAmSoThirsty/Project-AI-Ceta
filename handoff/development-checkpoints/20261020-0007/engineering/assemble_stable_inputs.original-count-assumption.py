"""Stage stable accepted C7 evidence without observing mutable Git/source state."""
from pathlib import Path
import difflib
import json
import zipfile
from prepare_checkpoint import digest, save, scan_exports, stable_read

W = Path(__file__).resolve().parent
F = Path('T:/00-Active/Project-AI-CETA')
O = F / '.agents/runtime/operational-resume-20261020'
C6 = W.parent.parent / 'checkpoint-0006'


def main():
    source = json.loads((W / 'SOURCE-MANIFEST.json').read_bytes())
    old = json.loads((C6 / 'work/SOURCE-MANIFEST.json').read_bytes())
    current = Path(source['candidate']); previous = Path(old['candidate'])
    rows = []
    for rel in source['payload_hashes']:
        if old['payload_hashes'].get(rel) == source['payload_hashes'][rel]:
            continue
        a = (previous / rel).read_text().splitlines() if rel in old['payload_hashes'] else []
        b = (current / rel).read_text().splitlines()
        delta = list(difflib.ndiff(a, b))
        rows.append(dict(path=rel, added=sum(x.startswith('+ ') for x in delta),
                         removed=sum(x.startswith('- ') for x in delta)))
    category = lambda prefix: dict(added=sum(x['added'] for x in rows if x['path'].startswith(prefix)),
                                  removed=sum(x['removed'] for x in rows if x['path'].startswith(prefix)))
    source_delta = category(('src/', 'tools/')); tests = category('tests/'); docs = category('docs/')
    assert source_delta == dict(added=325, removed=10), source_delta
    assert tests == dict(added=618, removed=0) and docs == dict(added=46, removed=0)
    save(W / 'PRODUCT-LOC.json', dict(paths=rows, source=source_delta, tests=tests, docs=docs,
        copied_loc=0, newly_authored_product_loc=0, engineering_tools_separate=True))
    public = W / 'public'; public.mkdir(exist_ok=False)
    selected = {}
    allowed = {'.json', '.md', '.txt', '.py', '.log', '.stdout', '.stderr', '.patch', '.bin'}
    def add(path, member):
        assert path.suffix in allowed and member not in selected
        raw, pin = stable_read(path)
        selected[member] = dict(input_path=str(path), input_pin=pin, sha256=digest(raw))
    for lane in ('sol-owned-diagnostics-r1', 'sol-operator-diagnostics-r1', 'operator-diagnostics-integration-r1'):
        root = O / lane
        for folder in ('control', 'review', 'delivery', 'work'):
            for path in sorted((root / folder).iterdir()):
                if path.is_file() and path.suffix in allowed:
                    add(path, lane + '/' + folder + '/' + path.name)
        if lane == 'operator-diagnostics-integration-r1':
            for name in ('joined-tests', 'joined-tests-r2', 'live-cli-01'):
                for path in sorted((root / 'work' / name).iterdir()):
                    if path.is_file() and path.suffix in allowed:
                        add(path, lane + '/work/' + name + '/' + path.name)
    for folder in ('control', 'review'):
        for path in sorted((C6 / folder).iterdir()):
            if path.is_file() and path.suffix in allowed:
                add(path, 'checkpoint-0006/' + folder + '/' + path.name)
    for name in ('AUTHOR-RESULT.json', 'SELF-REVIEW.json', 'AUDIT.stdout.json',
                 'PREPARATION-COMMAND.json', 'VERIFICATION-COMMAND.json', 'AUDIT-COMMAND.json',
                 'WORK-FREEZE.json', 'PRODUCT-LOC.json'):
        add(C6 / 'work' / name, 'checkpoint-0006/work/' + name)
    scan = scan_exports(selected)
    save(public / 'RAW-EVIDENCE-SECRET-SCAN.json', scan)
    assert not scan['findings'], 'stable raw evidence requires independent secret review'
    archive = public / 'RAW-EVIDENCE.zip'; members = []
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as z:
        for member, item in selected.items():
            raw, pin = stable_read(item['input_path']); assert pin == item['input_pin']
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED; info.external_attr = 0o100644 << 16
            z.writestr(info, raw)
            members.append(dict(member=member, source=item['input_path'], sha256=digest(raw), bytes=len(raw)))
    save(public / 'EVIDENCE-TRANSPORT.json', dict(method='ZIP_STORED_EXACT_STABLE_RAW_EVIDENCE',
        archive_sha256=digest(archive.read_bytes()), members=members,
        excludes=['environments/caches', 'disposable SQLite/live profiles', 'live coordinator state',
                  'unreviewed budget/observer work', 'secrets/credentials', 'oversized original PDF'],
        limits='Historical source failures,137 ordinary-import tests,6 independent controls and live CLI retain their own scope'))
    save(W / 'STAGED.json', dict(source_payloads=559, evidence_members=len(members),
        source_manifest_sha256=digest((W / 'SOURCE-MANIFEST.json').read_bytes()),
        raw_scan_sha256=digest((public / 'RAW-EVIDENCE-SECRET-SCAN.json').read_bytes()),
        git_state_observed=False, canonical_before_pins_captured=False,
        generic_preparation_executed=False, waiting_for='Root explicit canonical publication complete signal'))
    print(json.dumps(dict(source_payloads=559, evidence_members=len(members), raw_scan='PASS',
                          mutable_git_source_snapshot='DEFERRED_UNTIL_ROOT_SIGNAL')))


if __name__ == '__main__':
    main()
