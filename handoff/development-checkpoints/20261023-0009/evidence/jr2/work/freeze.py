"""Freeze this new preparation with full directory/file evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json
import run_canonical_journal as r
W=Path(__file__).resolve().parent
t=json.loads((W/'CONTROLS-STABLE.json').read_bytes());assert t['tests']==30 and t['successful'] and t['process_exit_status']==0
assert t['source_before']==t['source_after']
for name,pin in t['source_after'].items():assert r.sha(W/name)==pin
b=json.loads((W/'BINDING.json').read_bytes());fresh=r.source_observation(b)
baseline=json.loads((W/'BASELINE-REFRESH.json').read_bytes());assert baseline['source_before']==baseline['source_after']==fresh
prep=json.loads((W/'PREPARATION.json').read_bytes());external=dict(prep['external_pins'])
for path in [W.parent.parent/'jr/work/MANIFEST.json',W.parent.parent/'jr/review/MANIFEST.json',W.parent.parent/'jr/review/REVIEW.json']:
    external[str(path)]=r.sha(path)
assert external[str(W.parent.parent/'jr/review/MANIFEST.json')]=='fdc88fda803e22bbed64ef792c820a094995493555f9c0e511d6ac015542715b'
c=json.loads((W/'COLLECTION.json').read_bytes())
for identity in c['dependencies'].values():
    if identity['file']:
        assert r.stable(Path(identity['origin']))[0]==identity['native']
        external[identity['origin']]=identity['native']['sha256']
r.save(W/'IMPLEMENTATION-RECEIPT.json',dict(created_at=datetime.now(timezone.utc).isoformat(),
    run_id=r.RUN,node_id='implement',executor='/root/fixture_runner_r2',binding_sha256=r.sha(W/'BINDING.json'),
    current_author_controls=dict(total=30,passed=30,failures=0,errors=0,skips=0,raw='CONTROLS-STABLE.stderr',ids='CONTROLS-STABLE.json'),
    predecessor_rejection=dict(work_manifest_sha256='3f1d85ecebf50c72b17d6761284f950083db0c0963faa3927eada7e462ecec7d',review_manifest_sha256='fdc88fda803e22bbed64ef792c820a094995493555f9c0e511d6ac015542715b',decision='rejected',validate='BLOCKED',raw_negative='PRE-REPAIR-NEGATIVE.json'),
    earlier_current_control_runs=[json.loads((W/(label+'.json')).read_bytes()) for label in ('CONTROLS-R2','CONTROLS-FINAL')],
    earlier_current_control_classification='CONTROLS-R2:30 cases pass but exit1 from in-flight source conservation; CONTROLS-FINAL:30 cases pass exit0 on superseded source; both raw outcomes retained; only CONTROLS-STABLE binds current source.',
    canonical_tests_collected=33,canonical_tests_executed=0,
    create_only_report_contract='Actual process exit0 plus exact report seal and no REPORT-ERROR are required; test outcome alone is insufficient.',
    execution_requires_actual_three_Root_claims=True,source560_plus_two_status_native_before_after_equal=True,
    actual_Git_root_branch_HEAD_origin_NULstatus_normal_index_checked=True,
    SQLite_binary_static_only_during_preparation=True,fixture_bootstrap=False,canonical_fixture_writes=False,
    source_overlay=False,ROOT_override=False,Git_mutation=False,native_process_execution=False,
    commands=[dict(command='prepare.py',exit_status=0),dict(command='run_controls.py CONTROLS-STABLE',exit_status=0)],
    existing_issues=[dict(issue='J1 diagnostic masked exact original KeyboardInterrupt for legal nonstring raw storage',classification='fixed now in J2 only; J1 rejection and exact negative witness preserved'),
        dict(issue='Additional diagnostic class/type provider callbacks found before freeze',classification='fixed now using actual-type subclass and identity checks, raw type-name descriptor, unbound string slicing; exact negative witnesses retained'),
        dict(issue='Canonical33 execution and broader/native/installed/full r6 qualification',classification='requires separate authorized follow-up after formal review and actual gate')],
    full_product_acceptance=False))
observation=r.snapshot(W)
hashes={name:item['sha256'] for name,item in observation.items() if item['kind']=='file'}
r.save(W/'MANIFEST.json',dict(schema_version=1,run_id=r.RUN,work_hashes=hashes,work_observation=observation,
    external_pins=external,python_sources=[name for name in hashes if '/' not in name and name.endswith('.py')],
    collected_tests=33,canonical_tests_executed=0,author_controls=30,full_product_acceptance=False,
    post_freeze_outputs=['MANIFEST.json','PREPARED.stdout','PREPARED.stderr','PREPARED.json']))
print(json.dumps(dict(manifest_sha256=r.sha(W/'MANIFEST.json'),binding_sha256=r.sha(W/'BINDING.json'),
    work_files=len(hashes),work_entries=len(observation),support_pins=len(external)),indent=2))
