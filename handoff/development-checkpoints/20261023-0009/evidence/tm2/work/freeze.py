"""Freeze authored preparation only after actual terminal accepted JR2 success."""
from pathlib import Path
import json
import run_challenge as r
W=r.W; K=r.K; F=r.F
b=json.loads((W/'BINDING.json').read_bytes()); q=r.support(b)
j=F/'.agents/runtime/oq23/jr2'
closure=j/'control/verify-final-api.json'
assert r.sha(closure)=='792959145941101373ac104c4df61dcabcfe29844bd80dacf7944cf69dbf4139'
verification=json.loads(closure.read_bytes())['response']
assert verification['run_id']=='ceta-jr23-r2' and verification['allowed'] is True
assert verification['receipts_valid'] is True and verification['terminal_success'] is True
assert len(verification['states'])==8 and all(v=='SUCCEEDED' for v in verification['states'].values())
completion=j/'control/ROOT-EXECUTION-COMPLETION.json'
closed=json.loads(completion.read_bytes()); assert closed['terminal_success'] is True and closed['all_actual_nodes_succeeded'] is True
assert closed['prepared_manifest_sha256']=='771fa4d915c6b9d6fb2f1f042d3c313448fb4f2cea8607420fcccca65bf4df53'
assert closed['process_receipt_sha256']==r.sha(j/'control/EXECUTION-PROCESS.json')=='5e5173eacd1abc2f0366b3d15e662cb62dcf4090366bae4d07575bbe011ae5a7'
assert closed['result_sha256']==r.sha(j/'delivery/RESULT.json')=='9030fef9127ed3531f0687194e2a73f2be4ceab85c2fa8762f6b31e14a8d0d11'
assert closed['seal_sha256']==r.sha(j/'delivery/REPORT-SEAL.json')=='364a3cbdf2e73bed025326aaef4eeda1ae27bea7b716427bbb35dd7c8700c61a'
assert closed['verification_sha256']==r.sha(closure) and closed['tests']==33
q.save(W/'BINDING-PRE-CLOSURE.json',b)
for path in (closure,completion):b['journal_success_pins'][str(path)]=r.sha(path)
(W/'BINDING.json').write_text(json.dumps(b,indent=2)+'\n',encoding='utf-8',newline='\n')
prep=json.loads((W/'PREPARATION.json').read_bytes()); fresh=q.source_observation(b)
assert prep['source_before']==prep['source_after']==fresh
assert len(b['source_native'])==562 and r.prerequisite(b)==prep['journal_success']
controls=json.loads((W/'controls-final/CONTROL-RESULT.json').read_bytes())
assert controls['successful'] is True and controls['tests_run']==20 and controls['failures']==controls['errors']==0
engine=json.loads((W/'engine-controls-stable/RESULT.json').read_bytes())
assert engine['successful'] is True and engine['tests_run']==8 and engine['failures']==engine['errors']==0
for name,pin in engine['tested_source'].items():assert r.sha(W/name)==pin
external=dict(prep['external_pins']); external.update(b['journal_success_pins'])
predecessor=F/'.agents/runtime/oq23/tm'
for path in (predecessor/'work/MANIFEST.json',predecessor/'review/REVIEW.json',predecessor/'review/MANIFEST.json',predecessor/'review/UNRELATED-FAILURE-OBSERVATION.json',predecessor/'review/TESTS.json',predecessor/'review/TESTS.log'):
    external[str(path)]=r.sha(path)
c=json.loads((W/'COLLECTION.json').read_bytes()); assert c['test_ids']==r.SELECTED and c['tests_collected']==1
for identity in c['dependencies'].values():
    if identity['file']:
        assert q.stable(Path(identity['origin']))[0]==identity['native'];external[identity['origin']]=identity['native']['sha256']
python_sources=[p.name for p in W.glob('*.py')]
for name in python_sources:compile((W/name).read_bytes(),str(W/name),'exec')
q.save(W/'SOURCE-DELTA.json',dict(canonical_source_changes=[],canonical_test_changes=[],
    new_private_python_files={name:dict(added_lines=len((W/name).read_text().splitlines()),removed_lines=0,sha256=r.sha(W/name)) for name in sorted(python_sources)},
    fixture_writes=False,canonical_test_bodies_executed=False))
q.save(W/'IMPLEMENTATION-RECEIPT.json',dict(run_id=r.RUN,node_id='implement',executor='/root/admission_entry_r2',
    classification='PRIVATE_POSTMORTEM_OBSERVER_PREPARATION_COMPLETED',binding_sha256=r.sha(W/'BINDING.json'),
    author_controls=dict(observer=20,standalone_custody=8,failures=0,errors=0,skips=0),
    retained_predecessor=str(F/'.agents/runtime/oq23/tm'),predecessor_manifest_sha256='8c93bba448df811028e284763ed52ba6c90216e480ff8463840eb6412ddd8a42',
    predecessor_independent_witness='RuntimeError marker absent from all artifacts; original25pass added26thFAIL; no canonical case ran',
    current_prior_controls=['engine-controls-final/RESULT.json:8pass including suppressed-context assertion; stable control now checks explicit cause'],
    current_controls=['controls-final/CONTROL-RESULT.json','engine-controls-stable/RESULT.json'],
    canonical_tests_collected=1,canonical_tests_executed=0,canonical_fixture_writes=False,
    source560_plus_two_status_native_before_after_equal=True,source_or_threshold_changes=False,
    actual_JR2_success_pins=b['journal_success_pins'],JR2_terminal_success=True,
    actual_execution_requires_independent_review_and_gate_and_two_live_Root_claims=True,
    successful_guard_timings='NOT_MEASURED',provider_spans='NOT_MEASURED',full_product_acceptance=False,
    existing_issues=[dict(issue='Historical ENTRY and CHALLENGE50ms reliability failures; old elapsed unavailable',classification='requires separate follow-up work; no repair or cause claimed'),
        dict(issue='TM1 superclass formatted error/failure text was discarded, including unrelated RuntimeError reason',classification='fixed now in TM2 private runner only; exact witness plus assertion cause and subtest controls; TM1 rejection retained unchanged'),
        dict(issue='Canonical one-case reproduction and broader regression/native/full r6 acceptance',classification='requires separately authorized Root execution after independent review and actual gate')]))
observation=q.snapshot(W)
hashes={name:item['sha256'] for name,item in observation.items() if item['kind']=='file'}
q.save(W/'MANIFEST.json',dict(schema_version=1,run_id=r.RUN,work_hashes=hashes,work_observation=observation,external_pins=external,
    python_sources=sorted(python_sources),current_controls_source={name:r.sha(W/name) for name in ('owner_timing_observer.py','controls.py')},
    canonical_tests_collected=1,canonical_tests_executed=0,author_controls=28,full_product_acceptance=False,
    post_freeze_outputs=['MANIFEST.json','PREPARED.stdout','PREPARED.stderr','PREPARED.json']))
print(json.dumps(dict(manifest_sha256=r.sha(W/'MANIFEST.json'),receipt_sha256=r.sha(W/'IMPLEMENTATION-RECEIPT.json'),
    work_files=len(hashes),support_pins=len(external),canonical_bodies_executed=0),indent=2))
