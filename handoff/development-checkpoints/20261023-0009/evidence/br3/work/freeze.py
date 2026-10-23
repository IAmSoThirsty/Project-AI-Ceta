"""Freeze fresh BR3 preparation after direct controls and prior failure custody."""
from pathlib import Path
from datetime import datetime,timezone
import ast,json,time
import run_broader as b
W=b.W;B=b.B;C=B/'control';packet=b.packet();count=55
controls=json.loads((W/'CONTROLS-FINAL.json').read_bytes())
assert controls['tests']==count and controls['successful'] and controls['process_exit_status']==0
assert controls['failures']==controls['errors']==controls['skips']==0
assert controls['selected']==controls['started']==controls['stopped'] and len(set(controls['selected']))==count
assert controls['source_before']==controls['source_after']
for name,pin in controls['source_after'].items():assert b.sha(W/name)==pin
for label in ('FOCUSED','CONTROLS-FINAL','PREPARE','PHYSICAL-PIN','PIN-PRIOR-R2'):
    process=json.loads((W/(label+'-PROCESS.json')).read_bytes());assert process['exit_status']==0,(label,process)
prior=json.loads((W/'PRIOR-EVIDENCE.json').read_bytes())
assert prior['journal']['actual_exit_status']==0 and prior['journal']['tests']==33 and prior['journal']['all_actual_nodes_succeeded']
assert prior['timing']['run']=='ceta-tm23-r2' and prior['timing']['actual_case_executions']==1
assert prior['timing']['diagnosis']['reliable_50ms_admission']=='NOT_ESTABLISHED'
assert prior['failed_broader']['closed_as_failed'] and prior['failed_broader']['whole_validation_passed'] is False
rejected=prior['rejected_broader_preparation']
assert rejected['canonical_test_bodies_executed']==0 and rejected['terminal_success'] is False
assert rejected['review']['decision']=='rejected' and rejected['all_actual_claims_closed']
failed_pin=json.loads((W/'PIN-PRIOR-PROCESS.json').read_bytes());assert failed_pin['exit_status']==1
R2=Path(packet['rejected_broader_preparation']['root'])
assert b.o.snapshot(R2/'work')==rejected['work_observation'],'retained BR2 complete work observation changed'
assert rejected['whole_observation_rechecks_required_at_freeze_and_prepared_verification']
assert rejected['nested_disposable_entries_are_data_not_runtime_support']
old_controls=json.loads((R2/'work/CONTROLS-FINAL.json').read_bytes())
assert old_controls['tests']==44 and len(set(old_controls['selected']))==44
assert [name for name in controls['selected'] if name in old_controls['selected']]==old_controls['selected']
assert len([name for name in controls['selected'] if '.test_BR3_' in name])==11
binding=json.loads((W/'BINDING.json').read_bytes());prep=json.loads((W/'PREPARATION.json').read_bytes())
start=time.monotonic_ns();before=b.source_observation(binding);fixtures={}
for name,text in packet['fixture_workspaces'].items():
    path=Path(text)
    if name=='js9':
        try:b.o.plain(path)
        except FileNotFoundError:fixtures[name]={'absent':True}
        else:raise AssertionError('Root bootstrap only after independent review and actual gate')
    else:
        fixtures[name]=b.o.snapshot(path);b.o.preservation(prep['fixtures_before'][name],fixtures[name])
after=b.source_observation(binding);assert before==after
b.r.save(W/'FREEZE-OBSERVATION.json',dict(source_before=before,source_after=after,fixtures=fixtures,
    elapsed_ns=time.monotonic_ns()-start,preserved_initial_collection_entries=True,read_only_failed_JS9_preserved=True,
    preceding_evidence_sha256=b.sha(W/'PRIOR-EVIDENCE.json'),canonical_test_bodies_executed=False,full_product_acceptance=False))
external=dict(prep['external_pins']);external.update(prior['external_pins'])
collection=json.loads((W/'COLLECTION.json').read_bytes())
for identity in collection['dependencies'].values():
    if identity['file']:
        assert b.r.stable(Path(identity['origin']))[0]==identity['native'];external[identity['origin']]=identity['native']['sha256']
external[collection['sqlite_static_binary']['path']]=collection['sqlite_static_binary']['native']['sha256']
for name,pin in {
    'execute_once.py':'e9384efbf8bed7f8acdcec779de3f5a4361c542b951e3b82547907b27f0af85c',
    'ROOT-SELF-REVIEW.py':'1d43389c7361cdfe9bf9b512d5bb71ba31589b8c01cf95156348961d1a76cff6',
    'ROOT-RELEASE.py':'235aec89120dc149e7ff11f51b4b2791beae92041bac82034f452e3a7baab6d7',
    'ROOT-CLOSE.py':'9c2145d7e23cbcd5b2b5410e8c60375e1c7459a6f1e9ad7874805226f8f4716e',
    'INDEPENDENT-PLAN-ASSESSMENT.json':'ed55d77f2f15f3b001c5774e1d7ce64ce92db48369118c58ed0b462840e53bed'}.items():
    path=C/name;assert b.sha(path)==pin;external[str(path)]=pin
for name,pin in external.items():assert b.sha(Path(name))==pin,('external drift',name)
source_names=('complete_observer.py','bound_runtime.py','run_broader.py','prepare.py','pin_prior.py','freeze.py','verify_prepared.py','run_controls.py','test_br_controls.py')
old_source={name:b.sha(R2/'work'/name) for name in source_names};new_source={name:b.sha(W/name) for name in source_names}
for name,pin in old_source.items():external[str(R2/'work'/name)]=pin
payload=json.loads(Path(packet['source_manifest']).read_bytes())['payload_hashes']
immutable=['.local-build-cache/restoration-proof/'+suffix for suffix in ('acceptance/scenarios.json','architecture/components.json','build/gates.json','build/work_packages.json','requirements/requirements.json')]
assert all(name in payload for name in immutable)
for name in ('complete_observer.py','bound_runtime.py','run_broader.py'):
    tree=ast.parse((W/name).read_bytes(),str(W/name))
    assert not any(isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in ('file_stream','observation_port','reporter_observation') and node.decorator_list for node in ast.walk(tree))
    assert not any(isinstance(node,(ast.Yield,ast.YieldFrom)) for node in ast.walk(tree))
b.r.save(W/'SOURCE-DELTA.json',dict(rejected_BR2_source_pins=old_source,current_source_pins=new_source,
    accepted_reporter_sha256='37ca7bbfa361475ea42398c5d3bda42f8c1f95a0f3329154176f286a262d17ed',
    changes=['fresh exact BR3 packet/PLAN/control/run/new JS9 bindings',
        'three generator boundaries replaced with explicit context objects returning False on an existing body error',
        'exact primary identity and saved triple, all close/hook/environment secondary triples, setup unwind and fatal cleanup-only errors',
        'all44 prior controls retained in exact relative order;11 additional direct hostile/setup/combined/cleanup-only cases',
        'frozen rejected BR2 bytes and native metadata retained as failed immutable data, never replayed'],
    unchanged=['directional Windows executable-suffix mode rule and full same-API stability','complete traversal and bounded read identity checks',
        'stock transitions/scopes/receipt/event/overlap/self-review semantics','exact ordered510IDs and560+2source','six original fixture maps and read-only BR1JS9'],
    canonical_payload_delta=[],installed_TAAR_delta=[],canonical_tests_dropped=[],old_executable_replayed=False,
    canonical_source_inputs=562,immutable_registry_fixtures={name:payload[name] for name in immutable},
    old44_control_ids=old_controls['selected'],current_control_ids=controls['selected'],
    preserved_current_pin_failure=dict(process_sha256=b.sha(W/'PIN-PRIOR-PROCESS.json'),actual_exit_status=1,
        issue='ordinary Path.read_bytes cannot read retained disposable long-path payload',
        classification='fixed now in preparation helper only',focused_physical_qualification_sha256=b.sha(W/'PHYSICAL-PIN-QUALIFICATION.json'),
        correction='complete extended physical reader; nested disposable entries remain exact full-observation data; only top-level sources/data are runtime support'),
    admission_deadline_ns=50000000,deadline_changed=False,full_product_acceptance=False))
b.r.save(W/'AUTHOR-SELF-REVIEW.json',dict(author='/root/broader_successor_author',recorded_at=datetime.now(timezone.utc).isoformat(),
    type='Author self-review only; independent exact review remains pending',
    checks=['canonical560+status2/Git/index/native identities and exact ordered510IDs preserved',
        'all44 prior controls retained,11 new hostile/setup/combined/cleanup controls passed',
        'existing body errors leave by explicit exit False without contextlib assignment',
        'BR1 whole failed validation and BR2 rejected zero-execution preparation remain failed',
        'no canonical body execution, fixture bootstrap, native worker or Git mutation'],
    current_controls=dict(tests=count,failures=0,errors=0,skips=0,actual_process_exit_status=0),
    independent_approval=False,canonical_acceptance=False,full_product_acceptance=False))
observation=b.o.snapshot(W)
capture_outputs=['FREEZE-DRIVER.stdout','FREEZE-DRIVER.stderr','FREEZE-PROCESS.json']
for name in capture_outputs:observation.pop(name,None)
hashes={name:value['sha256'] for name,value in observation.items() if value['kind']=='file'}
post=['MANIFEST.json','PREPARED-DRIVER.stdout','PREPARED-DRIVER.stderr','PREPARED-PROCESS.json','AUTHOR-COMPLETION-RECEIPT.json',*capture_outputs]
b.r.save(W/'MANIFEST.json',dict(schema_version=1,run_id=b.RUN,work_hashes=hashes,work_observation=observation,
    external_pins=external,python_sources=[name for name in hashes if '/' not in name and name.endswith('.py')],
    collected_tests=510,canonical_tests_executed=0,author_controls=count,retained_prior_controls=44,new_custody_controls=11,
    full_product_acceptance=False,post_freeze_outputs=post))
print(json.dumps(dict(manifest_sha256=b.sha(W/'MANIFEST.json'),binding_sha256=b.sha(W/'BINDING.json'),files=len(hashes),entries=len(observation),support_pins=len(external),controls=count),indent=2))
