"""Refresh established inventory from actual JS8 acceptance; no product edits."""
from pathlib import Path
from datetime import datetime, timezone
import ast, copy, hashlib, importlib.util, json, re
F=Path('T:/00-Active/Project-AI-CETA')
R=F/'.agents/runtime/product-completion-20261015'
D=R/'qualified-r6'
A=F/'.agents/runtime/js8-20261015/amendment-report1'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
io=module('inventory_io_r6',R/'refresh_inventory_r4.py')
read,load,digest=io.read,io.load,io.digest
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def proof(ref): return load(F/ref['repository_relative_path'],ref['sha256'])
def save(name,value):
    with (D/name).open('x',encoding='utf8') as stream: json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def ref(path): return dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=digest(path.read_bytes()))
def main():
    assert not D.exists()
    started=datetime.now(timezone.utc).isoformat()
    x,previous=load(R/'qualified-r5/COMPLETION-INVENTORY.json','57df15153238c435e1b063452a1f63951cdf3b6aff8beb67b985581929199581')
    allowed={'observed_at','accepted_source','historical_source_observations','current_source_publication',
        'current_source_code_index','canonical_components','requirements','remaining_critical_path',
        'latest_native_join_qualification','candidate_catalog','coverage_cardinalities','interpretation_limits',
        'collaborative_review','inventory_revision','authoritative_inventory_path','source_read_conservation',
        'application_demonstration','pending_component_evidence'}
    preserved={key:digest(canonical(value)) for key,value in x.items() if key not in allowed}
    originals=digest(canonical([row['original'] for row in x['requirements']]))
    prior_lanes=copy.deepcopy(x['remaining_critical_path'])
    b,bref=load(A/'ACCEPTED-SOURCE-BASELINE.json')
    assert b['Source_accepted'] is True and b['Source_payloads']==352 and b['product_python_modules']==88
    assert b['full_product_complete'] is b['live_isolation_accepted'] is b['genuine_owner_effect_accepted'] is False
    manifest,mref=proof(b['manifest'])
    assert b['application_paths']==manifest['application_paths'] and len(b['application_paths'])==61
    state,sref=proof(b['state']);claims,cref=proof(b['claims_reference'])
    receipt,rref=proof(b['integrate']);envelope,eref=proof(b['integrate_result'])
    six={'discover','plan','implement','review','validate','integrate'}
    assert claims=={} and set(state['nodes'])==six and all(state['nodes'][n]['state']=='SUCCEEDED' for n in six)
    fingerprint=digest(canonical({k:v for k,v in receipt.items() if k!='receipt_hash'}))
    assert fingerprint==receipt['receipt_hash']==b['integrate_fingerprint']==state['nodes']['integrate']['receipt_hash']
    assert envelope==dict(node_id='integrate',receipt_hash=fingerprint,result=receipt['result'])
    assert receipt['executor_id']=='/root' and receipt['exit_status']==0 and receipt['result']['Source_accepted'] is True
    assert b['actual_sequence']==state['sequence'] and b['ledger_head']==state['ledger_head']
    full,fullref=proof(b['destination_full']);outer,outerref=proof(b['destination_full_launch'])
    delivered,dref=proof(b['delivered_review'])
    assert full['tests_run']==2334 and all(type(full[k]) is int and full[k]==0 for k in ('failures','errors','skips','exit_status'))
    assert full['expected_ids']==full['executed_ids']==full['stopped_ids'] and full['remaining_threads']==[]
    assert outer['exit_status']==0 and all(v is True for v in outer['record']['native_owner_after'].values())
    assert delivered['reviewer']=='/root/publication_recovery_review' and delivered['decision']=='approved'
    assert delivered['tests_run']==180 and delivered['exit_status']==0 and delivered['owned_resources_closed'] is True
    assert delivered['remaining_resources']==delivered['remaining_threads']==[]
    effective=b['effective_payload_hashes'];assert len(effective)==352
    assert full['before_hashes']==full['after_hashes']==full['expected_payload_hashes']==effective
    comparison={};code=[]
    for name,pin in effective.items():
        raw,fact=read(F/name,pin);native=b['source'][name]['native_identity']
        assert fact['python_lstat']==dict(st_dev=native['device'],st_ino=native['inode'],st_size=native['bytes'],st_mtime_ns=native['mtime_ns'])
        comparison[name]=dict(expected_sha256=pin,observed=fact,matches=True)
        if name.startswith('src/ceta/') and name.endswith(('.py','.rs')):
            text=raw.decode('utf-8-sig')
            item=dict(source=fact,present=True,semantics='PRESENCE_IS_NOT_REQUIREMENT_ACCEPTANCE',
                native_unit_mentions=sorted(set(re.findall(r'\bCETA-\d{2}\.\d{2}\.\d{2}\b',text))),source_cut_status='ACCEPTED_JS8_SOURCE352')
            if name.endswith('.py'):
                tree=ast.parse(text);item['top_level_classes']=[n.name for n in tree.body if isinstance(n,ast.ClassDef)]
                item['declared_functions']=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
                item['declared_functions_count']=len(item['declared_functions'])
            code.append(item)
    assert len(code)==88
    actual=dict(sequence=state['sequence'],ledger_head=state['ledger_head'],claims={},states=b['all_six_states'],
        state=sref,claims_source=cref,persisted_integrate=rref,result_envelope=eref,official_augmented_fingerprint=fingerprint)
    x['historical_source_observations'].append(dict(inventory=previous,accepted_source=x['accepted_source'],
        current_source_publication=x['current_source_publication'],remaining_critical_path=prior_lanes,
        latest_native_join_qualification=x['latest_native_join_qualification'],limit='Historical r5 observations preserved at their exact cut.'))
    x['accepted_source']=dict(record=b,source=bref,status='ACCEPTED_JS8_SOURCE352',current_payload_comparison=comparison,
        all_expected_payloads_match=True,actual_all_six_stage_acceptance=actual,
        limit='Exact 61-path library publication; parent product and live public execution acceptance remain open.')
    x['current_source_publication']=dict(status='ACCEPTED_JS8_SOURCE352',source_root=str(F),payloads=352,
        manifest=b['manifest'],amendment=b['amendment'],accepted_baseline=bref,application=b['application'],
        current_payload_comparison=comparison,all_expected_payloads_match=True,destination_full=fullref,
        destination_full_launch=outerref,delivered_review=dref,actual_integration=actual,
        accepted_source_baseline_created=True,Source_accepted=True,full_product_complete=False,
        prior_failed_candidate=b['prior_failed_candidate'],prior_failed_delivery=delivered['prior_failed_attempt'])
    x['current_source_code_index']=sorted(code,key=lambda z:z['source']['path'])
    for c in x['canonical_components']:
        prefix=str(F/c['original']['path'])+'\\'
        c['actual_implementation']=[z for z in code if z['source']['path'].startswith(prefix)]
        c['implementation_evidence']=dict(current_code=c['actual_implementation'],source_cut_status='ACCEPTED_JS8_SOURCE352',
            accepted_source_reference=bref,limits='Source presence; original component semantic acceptance remains open.')
        c['observed_implementation_state']=('EXECUTABLE_SOURCE_PRESENT_FULL_BEHAVIOR_UNVERIFIED' if c['actual_implementation']
            else 'NO_EXECUTABLE_FILES_OBSERVED_IN_REGISTERED_DIRECTORY')
        c['actual_blocker']=('No full current component-source/requirement/oracle acceptance join is established.' if c['actual_implementation']
            else 'No executable Python/Rust file was observed under this registered canonical component path.')
    for row in x['requirements']:
        direct=[c for c in x['canonical_components'] if c['original']['id'] in row['direct_canonical_component_ids']]
        row['implemented_source_paths']=sorted({z['source']['path'] for c in direct for z in c['actual_implementation']})
        row['implementation_evidence'].update(direct_source_paths=row['implemented_source_paths'],source_cut_status='ACCEPTED_JS8_SOURCE352',accepted_source_reference=bref)
        present=sorted(c['original']['path'] for c in direct if c['actual_implementation'])
        absent=sorted(c['original']['path'] for c in direct if not c['actual_implementation'])
        row['implementation_assessment']['registered_component_paths_with_code']=present
        row['implementation_assessment']['registered_component_paths_without_code']=absent
        row['actual_blocker']['known_local_absence']=absent
        row['implementation_assessment']['scope']='Exact accepted JS8 Source352; private successor evidence is separate; requirement acceptance unchanged.'
    first,join,retainer,approval,isolation,application=x['remaining_critical_path'][:6]
    first.update(status='CLOSED_SCOPED_JS8_SOURCE_PUBLICATION_AND_DELIVERED_ACCEPTANCE',
        blocker='Exact 61-path publication accepted; original parent requirements remain open.',
        next='Integrate the reviewed retainer, capacity, observer and outcome successor under a fresh source lease.',
        evidence=dict(accepted_baseline=bref,integrate=rref,actual_sequence=state['sequence'],claims={},destination_full=fullref,delivered_review=dref))
    join.update(status='CLOSED_SCOPED_JS8_NATIVE_AUTHORITY_LIBRARY_JOIN',
        blocker='The reviewed Stop precedence repair and joined library source passed the current mandatory destination gates. Public authority-to-effect acceptance remains open.',
        next='Continue existing retainer/capacity/outcome and public profile composition requirements.',
        evidence=dict(accepted_baseline=bref,delivered_review=dref,destination_full=fullref),
        assessment_kind='SCOPED_LIBRARY_INTEGRATION_ACCEPTED; PUBLIC_RUNTIME_GATES_OPEN')
    join.pop('private_successor',None)
    refs={
        'owner_retainer':('.agents/runtime/owner-retainer-acceptance-review-20261017/REVIEW.json','37104be42d3ba9d01004c5afe80e48a48d0bd277ba01a40e7c8fe15b74d5ddb0'),
        'capacity_connection':('.agents/runtime/cpu-capacity-connection-review-20261017/REVIEW.json','8cb74d1a6fda35802d8e63284f1a1e941094b938c945bc45c762cd617c141147'),
        'native_observer':('.agents/runtime/observer-origin-review-20261017/successor-r1/NATIVE-REVIEW.json','553c9824fa8002b40b44975aaa74d6c853b30bb61dc0b1e4d3f73eefe387dcfb'),
        'outcome_provenance':('.agents/runtime/cpu-outcome-provenance-review-20261017/REVIEW.json','d67ddf69bd2ec97eee7c0c369a583bb8ffe46c410a0e2d7df2fe71b9cc9b6d9f')}
    candidates={}
    for name,(path,pin) in refs.items():
        value,fact=load(F/path,pin);candidates[name]=dict(review=fact,decision=value.get('decision',value.get('status')),Source_integrated=False)
    x['pending_component_evidence']=candidates
    retainer.update(status='REVIEWED_CANDIDATE_COMPONENTS_PENDING_JOIN_AND_NATIVE_INTEGRATION',
        blocker='Retainer, physical capacity connection and producer provenance successors are implemented in private candidates. Their joined source publication, recovery review and native integration remain open.',
        evidence=candidates,next='Review the frozen recovery successor, join exact compatible file deltas, verify native and canonical outcomes, then publish under a fresh source lease.')
    isolation.update(status='REPAIRED_OBSERVER_NATIVE_QUALIFIED_POSITIVE_ISOLATION_PENDING',
        blocker='Observer successor passed six native cases. Positive restricted isolation requires a fresh approved host-profile attempt; genuine public effect remains unverified.',
        evidence=dict(observer=candidates['native_observer'],no_profile_limit='Recorded refusal codes are observations; missing-profile causality remains unproved.'))
    demo=F/'.agents/runtime/canonical-launch-20261017/attempt1/DEMONSTRATION.json'
    demo_value,demo_ref=load(demo,'859d55ad4505456afb68d53760d029e0d0cc06a838f36eeb4a3ab6b9e97f6fb2')
    demo_review_path=demo.parent.parent/'independent-review/REVIEW.json'
    demo_corrections_path=demo.parent.parent/'independent-review/DEMONSTRATION-CORRECTIONS.json'
    demo_review,demo_review_ref=load(demo_review_path,'d338be6e7a863df3fc87cf5a6b34a1d993d50719a5618a6497d21ed9bb62be81')
    demo_corrections,demo_corrections_ref=load(demo_corrections_path,'b02ba3f50759d8d03bbf51a7fe7ce1abe935f3de579519e3a1ed4cbe161a1b80')
    assert demo_review['reviewed_demonstration']==demo_corrections['original_demonstration']==ref(demo)
    assert demo_review['corrections']==ref(demo_corrections_path)
    assert demo_review['decision']=='APPROVED_FOR_SCOPED_DEMONSTRATION_WITH_APPEND_ONLY_REPORTING_CORRECTION'
    assert demo_corrections['product_accepted'] is False
    x['application_demonstration']=dict(evidence=demo_ref,source_cut='Historical JS7 Source295',startup_observed=True,
        independent_review=demo_review_ref,reporting_corrections=demo_corrections_ref,
        screenshot_evidence_status=demo_corrections['corrections'][0]['corrected_text'],
        verification_limits=demo_corrections['clarifications'],
        interface_task_creation_observed=True,task_creation_persisted=True,governed_cpu_effect=False,
        blocker='tools/ceta_operator.py constructs the task session without a production request compiler; preparation is unavailable.',
        current_JS8_startup_observed=False)
    application['demonstration']=x['application_demonstration']
    x['latest_native_join_qualification']=dict(status='JS8_DESTINATION_NATIVE_SUBSET_PASSED',evidence=dref,
        prior_failure='Historical FN6 failure preserved in historical_source_observations',
        limit='Ordinary disposable native workers with controlled authority/capacity; no genuine human approval or restricted public execution.')
    assert not any(row['run_id']=='js8-20261015' for row in x['candidate_catalog'])
    x['candidate_catalog'].append(dict(run_id='js8-20261015',candidate_root=str(F/'.agents/js8-amendment-report1-20261017'),
        manifest=mref,recorded_at=started,author=receipt['executor_id'],declared_scope='Exact accepted JS8 Source352 library publication',
        application_paths=list(b['application_paths']),declared_payload_count=len(effective),
        selected_hashes={name:effective[name] for name in b['application_paths']},source_publication_declaration=True,
        full_gate_complete_declaration=None,activation_ready_declaration=False,
        lifecycle=dict(state_source=sref,sequence=state['sequence'],nodes=copy.deepcopy(state['nodes']),claims={},
            claims_source=cref,persisted_integrate=rref,official_augmented_fingerprint=fingerprint),
        acceptance_status='ACCEPTED_JS8_SOURCE352; FULL_PRODUCT_AND_PUBLIC_RUNTIME_ACCEPTANCE_OPEN',
        limits=['Exact 61-path library publication only; original requirement semantic acceptance remains unchanged.'],
        current_source_publication_observation=x['current_source_publication']))
    x['observed_at']=started
    x['coverage_cardinalities'].update(active_source_code_files=88,source_payloads_in_accepted_baseline=352,published_source_payloads=352,
        candidate_manifests_observed=len(x['candidate_catalog']))
    x['interpretation_limits']=[s.replace('JS7 amended Source295 is now the recorded accepted baseline. CT4 and the original failed destination remain historical. FN6 native qualification failed one denial-precedence assertion and remains private; JS8 preparation is not accepted. Current observations are time-bound and scoped.',
        'JS8 Source352 is the current accepted source baseline. Prior JS7/FN6/candidate/destination failures remain preserved. Private successor components and public runtime acceptance remain separate.') for s in x['interpretation_limits']]
    x['collaborative_review']=dict(state='PENDING_ROOT_AND_DISTINCT_REVIEW_OF_R6',changes_after_review='NEW IMMUTABLE SUCCESSOR ONLY')
    x['inventory_revision']=dict(prepared_at=started,predecessor=previous,changes=['Exact JS8 terminal acceptance and 61-path source publication','Refresh current code evidence without changing original requirement acceptance','Record pending component reviews and historical canonical interface demonstration'],remaining_limit='All original full-product acceptance gaps remain explicit.')
    x['authoritative_inventory_path']=str(D/'COMPLETION-INVENTORY.json')
    for name,row in comparison.items():
        _,after=read(F/name,row['expected_sha256']);assert after['python_lstat']==row['observed']['python_lstat']
    x['source_read_conservation']=dict(observed_start=started,observed_end=datetime.now(timezone.utc).isoformat(),ordinary_accepted_source_payloads=352,changed_inputs=[],stable_accepted_source_read_bytes=True,Source_accepted=True,
        historical_normative_sources='Preserved original observations; not rescanned.',limits='Finite lstat/hash brackets; no held-handle or whole-worktree claim.')
    assert all(digest(canonical(x[key]))==pin for key,pin in preserved.items())
    assert digest(canonical([row['original'] for row in x['requirements']]))==originals
    assert x['remaining_critical_path'][6:]==prior_lanes[6:]
    assert len(x['native_subsystems'])==25 and x['whole_product_complete'] is x['all_mandatory_requirements_accepted'] is False
    D.mkdir(exist_ok=False);save('COMPLETION-INVENTORY.json',x)
    render=module('inventory_render_r6',R/'build_inventory.py').render
    body=render(x).replace('## Complete r6 source-location ledger','## r6 provenance appendix - no additional work items')
    summary='Current accepted source: **JS8 Source352**, 88 product modules, actual integration SUCCEEDED, claims empty. Exact 61-path publication and destination validation accepted. Public authorization-to-effect execution remains open.\n\n'
    body=body.replace('## Accepted source and active work\n\n','## Accepted source and active work\n\n'+summary)
    with (D/'COMPLETION-INVENTORY.md').open('x',encoding='utf8') as stream:stream.write(body)
    save('REFRESH-RESULT.json',dict(at=datetime.now(timezone.utc).isoformat(),exit_status=0,predecessor=previous,baseline=bref,
        inventory=ref(D/'COMPLETION-INVENTORY.json'),render=ref(D/'COMPLETION-INVENTORY.md'),source_payloads=352,
        sequence=state['sequence'],ledger_head=state['ledger_head'],claims={},original_subsystems=25,
        unchanged_normative_sections=preserved,original_requirements_preserved=True,product_tests_executed=0,
        Source_mutations=0,full_product_complete=False,review_state='PENDING_DISTINCT_REVIEW'))
    print(json.dumps(dict(result=ref(D/'REFRESH-RESULT.json'),inventory=ref(D/'COMPLETION-INVENTORY.json'))))
if __name__=='__main__':main()
