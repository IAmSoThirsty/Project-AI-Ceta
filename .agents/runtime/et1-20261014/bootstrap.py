"""Claim ET1, preserve Source290, and stage only named frozen dependencies."""
from et_support import *
assert not Q.exists(); Q.mkdir()
scope = ('src/ceta/kernel/effect_transactions.py', 'src/ceta/kernel/transactions.py',
         'tests/contract/test_owned_cpu_outcome_transactions.py', 'contracts/OWNED_CPU_OUTCOME_V1.md')
source_names = json.loads((F / '.agents/runtime/na2-20261014/source-inputs.json').read_text())['source_observed_at_start']
source = {name: ordinary(F / name) for name in source_names}; assert len(source) == 290
parent = F / '.agents/na2-20261014'
dependency_manifest = json.loads((parent / 'TRANSFER-MANIFEST.json').read_text())
assert sha(parent / 'TRANSFER-MANIFEST.json') == '2b29c03065265134f4829341e2b995ec1ec12bfbb5e91f4b179f3c15619d96ba'
dependencies = {name: row for name, row in dependency_manifest['payloads'].items() if name not in dependency_manifest['eligible_paths']}
assert len(dependencies) == 310
ka = F / '.agents/ka1-20261014'; ka_manifest = json.loads((ka / 'TRANSFER-MANIFEST.json').read_text())
ka_rows = {row['relative_path']: row for row in ka_manifest['payloads']}
review = F / '.agents/runtime/ka1-20261014/independent-root-review/review.json'
assert sha(review) == '4e7181fd6c0912ad26e30992fc781703c8b3f67b162a1159af8fa2d28f0e7dbf'
assert json.loads(review.read_text())['decision'] == 'approved'
invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN], 'run-init')
claim('discover')
write_new(R / 'SOURCE-INPUTS.json', {'recorded_at': utc(), 'Source290': source,
    'eligible_paths': list(scope), 'dependency_closure': reference(parent / 'TRANSFER-MANIFEST.json'),
    'dependency_rule': 'Exclude all four NA2 implementation paths. Remaining310 bytes are separately reviewed WT4/AC2/NC2/RC2/EN2/NOV2 dependencies, with explicit NOV2 reconciliation; no NA2 approval authority borrowed.',
    'NOV2_reconciliation': reference(F / '.agents/runtime/na2-20261014/NOV2-DEPENDENCY-RECONCILIATION.json'),
    'KA1_manifest': reference(ka / 'TRANSFER-MANIFEST.json'), 'KA1_distinct_review': reference(review),
    'plan': reference(F / '.agents/runtime/real-effect-20261014/plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'),
    'HEAD': fs.text_git(F, 'rev-parse', 'HEAD'), 'branch': fs.text_git(F, 'branch', '--show-current'),
    'dirty_tracked': fs.text_git(F, 'status', '--porcelain=v1', '-uno'), 'Source_application': False})
cmd = {'command': str(PY) + ' -B -X utf8 ' + str(Path(__file__)), 'exit_status': 0}
complete('discover', {'inputs': reference(R / 'SOURCE-INPUTS.json')}, [cmd], [('Source290 and named approved dependencies inspected', True)])
claim('plan')
write_new(R / 'TASK-BINDING.json', {'recorded_at': utc(), 'scope': scope,
    'contract': 'One attempt per consumed permit, then canonical receipt/independent observation/settlement; preserve original consumption and charged liability. Same SqliteJournal/CAS only, captured phase/native-proof owner predicate exactlyNone, no native execution or authority replay.',
    'eligible_product_paths': scope, 'new_shared_contracts': [], 'Source_application': False})
complete('plan', {'binding': reference(R / 'TASK-BINDING.json')}, [cmd], [('Finite same-owner outcome extension; no new store or schema', True)])
claim('implement')
origins = {}
for name, row in source.items(): origins[name] = F / name
for name, row in dependencies.items():
    assert ordinary(parent / name) == row
    if name in source and row['sha256'] == source[name]['sha256']: continue
    if name in source: assert name in ('src/ceta/resource/pressure.py', 'src/ceta/supervisor/windows_jobs.py')
    origins[name] = parent / name
for name in ka_manifest['eligible_application_paths']:
    assert sha(ka / name) == ka_rows[name]['candidate_sha256']
    origins[name] = ka / name
assert len(origins) == 313
staged = {}
for name, origin in origins.items():
    target = Q / name; target.parent.mkdir(parents=True, exist_ok=True)
    fs.write_new(target, fs.read_bytes(origin)); staged[name] = ordinary(target)
    assert staged[name]['sha256'] == sha(origin)
for name in scope:
    if (Q / name).exists():
        target = R / 'before-images' / name; target.parent.mkdir(parents=True, exist_ok=True)
        fs.write_new(target, fs.read_bytes(Q / name))
write_new(R / 'STAGED-INPUTS.json', {'recorded_at': utc(), 'payloads': staged,
    'origins': {name: ordinary(origin) for name, origin in origins.items()},
    'eligible_paths': scope, 'new_dependency_LOC_credit': 0})
print(json.dumps({'implement': 'RUNNING', 'staged_payloads': 313, 'Source_changed': False}))
