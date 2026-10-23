from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,sys,time
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/br3';C=B/'control';D=B/'delivery';W=B/'work';OUT=Path(__file__).parent;RUN='ceta-br23-r3';PIN='2c22f24694d2c6e1706669007cda3f32642df18f92bafcee669c58cda2cb41f3';REVIEW_PIN='07237c9622e6942701517d860d11556334fae58c96c9c26258c5dbd624125665'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
report=dict(reviewer='/root/independent_broader_review',run_id=RUN,manifest_sha256=PIN,review_manifest_sha256=REVIEW_PIN,decision='NOT_YET_DECIDED',started_at=datetime.now(timezone.utc).isoformat(),steps=[],canonical_test_bodies_executed_by_check=0,claims_gates_runtime_verify_or_transitions_executed=0,fixtures_sources_or_frozen_review_mutated=False,full_product_acceptance=False)
mono=time.perf_counter_ns()
def step(name,**data):
    report['stage']=name;entry=dict(stage=name,at=datetime.now(timezone.utc).isoformat(),**data);report['steps'].append(entry);print(json.dumps(entry,sort_keys=True,allow_nan=False),flush=True)
status=1
try:
    step('FROZEN_PREPARATION_AND_REVIEW')
    assert sha(W/'MANIFEST.json')==PIN and sha(B/'review/MANIFEST.json')==REVIEW_PIN
    sys.path.insert(0,str(W));import run_broader as b
    packet,binding=b.load_prepared(PIN);m=read(W/'MANIFEST.json');actual_work=b.o.snapshot(W)
    assert set(actual_work)-set(m['post_freeze_outputs'])==set(m['work_observation']);b.o.preservation(m['work_observation'],actual_work)
    rm=read(B/'review/MANIFEST.json')
    assert rm['reviewer']==report['reviewer'] and rm['decision']=='approved' and rm['candidate_manifest_sha256']==PIN
    for name,pin in rm['files'].items():assert b.o.stable(B/'review'/name)['sha256']==pin,('frozen review file drift',name)
    for name,pin in rm['external_pins'].items():assert sha(Path(name))==pin,('review support drift',name)
    actual_review=b.o.snapshot(B/'review');assert set(actual_review)-set(rm['post_freeze_outputs'])==set(rm['observation']);b.o.preservation(rm['observation'],actual_review)
    prior=read(W/'PRIOR-EVIDENCE.json');assert b.o.snapshot(Path(packet['rejected_broader_preparation']['root'])/'work')==prior['rejected_broader_preparation']['work_observation']
    report['frozen_work_review_and_rejected_BR2_complete_data_conserved']=True
    step('ACTUAL_PROCESS_REPORT_AND_SEAL')
    process=read(C/'EXECUTION-PROCESS.json');intent=read(C/'EXECUTION-INTENT.json');start=read(D/'START.json');result=read(D/'RESULT.json');seal=read(D/'REPORT-SEAL.json')
    expected_argv=[str(Path(packet['python'])),'-B','-X','utf8',str(W/'run_broader.py'),'--manifest-sha256',PIN]
    assert process['exit_status']==0 and process['argv']==intent['argv']==expected_argv and process['cwd']==intent['cwd']==str(F)
    assert process['manifest_sha256']==intent['manifest_sha256']==PIN and intent['one_attempt'] is True and intent['assertions_enabled'] is True
    assert process['stdout_sha256']==sha(C/'EXECUTION.stdout') and process['stderr_sha256']==sha(C/'EXECUTION.stderr')
    for name,key in [('RESULT.json','result_sha256'),('START.json','start_sha256'),('events.jsonl','events_sha256'),('TESTS.log','log_sha256')]:assert sha(D/name)==seal[key],('seal mismatch',name)
    assert not (D/'REPORT-ERROR.json').exists() and seal['test_cohort_passed'] is True and seal['requires_actual_process_exit_zero'] is True
    assert process['full_product_acceptance'] is False and seal['full_product_acceptance'] is False and start['full_product_acceptance'] is False and result['full_product_acceptance'] is False
    assert result['test_cohort_passed'] is True and result['execution_success_requires_process_exit_zero_and_seal'] is True and result['native_process_execution'] is False
    ids=read(W/'COLLECTION.json')['test_ids'];oldids=read(F/'.agents/runtime/oq23/br/work/COLLECTION.json')['test_ids']
    assert ids==oldids==start['test_ids']==result['selected_test_ids']==result['started_test_ids']==result['stopped_test_ids'] and len(ids)==len(set(ids))==result['tests_run']==510
    assert result['failures']==result['errors']==0
    for key in ('skips','expected_failures','unexpected_successes','test_error_details','cleanup'):assert result[key]==[],key
    assert result['primary'] is None and result['early_stop'] is False and type(result['elapsed_ns']) is int and result['elapsed_ns']==223141000000
    assert b.r.execution_complete(D,process['exit_status']) is True
    events=[json.loads(line) for line in (D/'events.jsonl').read_text(encoding='utf8').splitlines() if line.strip()]
    assert len(events)==1020
    for index,test_id in enumerate(ids):
        first,last=events[2*index:2*index+2]
        assert first['kind']=='started' and last['kind']=='stopped' and first['test_id']==last['test_id']==test_id and first['error'] is None and last['error'] is None
    moments=[datetime.fromisoformat(event['at']) for event in events];assert moments==sorted(moments)
    assert datetime.fromisoformat(intent['started_at'])<=moments[0]<=moments[-1]<=datetime.fromisoformat(process['finished_at'])
    log=(D/'TESTS.log').read_text(encoding='utf8');lines=log.splitlines();headers=[];multiline=[]
    for index,line in enumerate(lines):
        match=re.fullmatch(r'\S+ \(([^\r\n]+)\)( \.\.\. ok)?',line)
        if match:
            headers.append(match.group(1))
            if match.group(2) is None:
                assert index+1<len(lines) and lines[index+1].endswith(' ... ok'),('multiline test outcome missing',match.group(1))
                multiline.append(dict(test_id=match.group(1),header=line,description_and_outcome=lines[index+1]))
    assert headers==ids and len(headers)==510,('log test identity mismatch',len(headers))
    assert sum(line.endswith(' ... ok') for line in lines)==510 and len(multiline)==10,('log successful outcome count',len(multiline))
    report['log_presentation']=dict(exact_ordered_test_headers=510,successful_outcomes=510,single_line_presentations=500,multiline_description_presentations=multiline)
    predecessor=OUT.parent/'independent-postrun-check-r1-20261023T053748Z'
    assert sha(predecessor/'REPORT.json')=='a21d77d071db10381a97c444e1d16a620137d65c482bb75d37217a2002a3e9b8' and read(predecessor/'PROCESS.json')['actual_process_exit_status']==1
    report['preserved_postrun_diagnostic_failure']=dict(path=str(predecessor),report_sha256=sha(predecessor/'REPORT.json'),process_sha256=sha(predecessor/'PROCESS.json'),actual_exit_status=1,stage='ACTUAL_PROCESS_REPORT_AND_SEAL',cause='R1 one-line-only unittest log parser recognized500 headers;10 canonical tests use normal header plus description-and-ok second line',canonical_test_failure_inferred=False,no_preservation_check_failure_encountered=True)

    assert re.search(r'^Ran 510 tests in [0-9.]+s$',log,re.MULTILINE) and log.rstrip().endswith('OK')
    report['execution']=dict(actual_exit_status=0,tests_selected_started_stopped=510,exact_ordered_BR1_ids=True,event_count=1020,sequential_event_pairs=True,test_log_exact=True,failures=0,errors=0,skips=0,primary=None,cleanup=[],elapsed_ns=result['elapsed_ns'],elapsed_scope='WHOLE_COHORT_NOT_ADMISSION_LATENCY_QUALIFICATION',process_sha256=sha(C/'EXECUTION-PROCESS.json'),result_sha256=sha(D/'RESULT.json'),seal_sha256=sha(D/'REPORT-SEAL.json'),start_sha256=sha(D/'START.json'),events_sha256=sha(D/'events.jsonl'),log_sha256=sha(D/'TESTS.log'))
    step('CURRENT_EIGHT_CLAIMS_AND_STOCK_EVENT_RECEIPT_CUSTODY')
    runtime=b.BoundRuntime(binding);graph,state=runtime._guard(RUN);claims=read(C/RUN/'claims.json');assert claims==start['claims'] and set(claims)==set(binding['workspaces']) and len(claims)==8
    control_pins={name:sha(C/RUN/name) for name in ('state.json','claims.json','events.jsonl','graph.json','sources.json')}
    for node,claim in claims.items():
        entry=state['nodes'][node];path=Path(binding['workspaces'][node])
        assert entry['state']=='RUNNING' and entry['claim']==claim and claim['executor_id']=='/root' and claim['node_id']==node and claim['workspace']==str(path)
        assert claim['effective_write_scope']==graph.nodes[node]['write_scope']==[path.relative_to(Path('T:/')).as_posix()+'/**'] and claim['input_hash']==runtime._input_hash(graph,state,node)
        if node!='integrate':assert claim['baseline_snapshot']==b.project_observation(path,Path(binding['graph_root']),start['fixtures_before'][node]),('incomplete baseline',node)
    store=runtime._store(RUN);count,head=store.verify_event_chain();assert count==state['sequence'] and head==state['ledger_head']
    succeeded=[]
    for node,entry in state['nodes'].items():
        if entry['state']=='SUCCEEDED':
            value=read(C/RUN/entry['receipt_ref']);claimed=value.pop('receipt_hash');assert claimed==entry['receipt_hash']==b.BoundRuntime.__mro__[1].__init__.__globals__['sha256_json'](value);succeeded.append(node)
    graph_events=[json.loads(line) for line in (C/RUN/'events.jsonl').read_text(encoding='utf8').splitlines() if line.strip()]
    for node in claims:assert sum(event['event_type']=='node_claimed' and event['node_id']==node for event in graph_events)==1,('claim replay',node)
    assert state['nodes']['review']['decision']=='approved' and state['nodes']['validate']['validation_passed'] is True
    report['authority']=dict(graph_fingerprint=graph.fingerprint,all_eight_current_Root_claims=True,claims_equal_START=True,all_fixture_claim_baselines_complete=True,claims=list(claims),stock_event_count=count,stock_ledger_head=head,succeeded_receipt_hashes_valid=succeeded,exactly_one_claim_per_execution_node=True)
    step('CANONICAL_SOURCE_GIT_INDEX_NATIVE_AND_ORIGINS_BEFORE')
    fresh=b.source_observation(binding);freeze=read(W/'FREEZE-OBSERVATION.json');assert len(binding['source_native'])==562 and fresh==freeze['source_before']==freeze['source_after']==start['source_before']==result['source_after']
    metadata=start['metadata'];assert metadata['source_root']==str(F) and metadata['graph_root']==str(Path('T:/')) and metadata['ordinary_imports'] is True and metadata['ROOT_override'] is False and metadata['module_overlay'] is False and metadata['selected']==packet['selected']
    assert len(metadata['test_modules'])==26 and len(metadata['selected'])==28
    for name,item in metadata['test_modules'].items():
        assert item['origin']==str(F/'tests/contract'/(name+'.py')) and item['file'] is True and b.r.stable(Path(item['origin']))[0]==item['native']
    for name,item in metadata['product_modules'].items():
        expected=F/'src'/Path(*name.split('.'))
        if item['file']:
            assert Path(item['origin']) in (expected.with_suffix('.py'),expected/'__init__.py') and b.r.stable(Path(item['origin']))[0]==item['native']
        else:
            assert name=='ceta.effects' and item['namespace_path']==str(expected) and item['loader']=='NamespaceLoader' and item['namespace_init_absent'] is True and not b.o.physical(expected/'__init__.py').exists()
            assert b.o.native(b.o.plain(expected))==item['directory_native']
    for item in metadata['dependencies'].values():
        if item['file']:assert b.r.stable(Path(item['origin']))[0]==item['native']
    assert metadata['environment']['fixture_environment']==packet['fixture_environment'] and metadata['environment']['native_enable_switches_inherited'] is False
    assert metadata['controlled_process_effects']==packet['controlled_process_effects'] and metadata['controlled_process_effects']['native_worker_or_live_profile_qualification'] is False
    report['origins']=dict(canonical_test_modules=26,selected_scopes=28,ordinary_imports=True,ROOT_override=False,module_overlay=False,product_and_dependency_native_origins_current=True,source562_Git_index_native_failedJS9_equal_freeze_START_RESULT=True)
    step('ALL_SEVEN_CURRENT_FIXTURE_TREES_AND_PREEXISTING_PRESERVATION')
    report['fixtures']={}
    for node,text in packet['fixture_workspaces'].items():
        step('FIXTURE_BEGIN',node=node);now=b.o.snapshot(Path(text));before=start['fixtures_before'][node];assert now==result['fixtures_after'][node],('current fixture differs from RESULT',node)
        b.o.preservation(before,now)
        if node!='js9':b.o.preservation(freeze['fixtures'][node],before);b.o.preservation(freeze['fixtures'][node],now)
        else:assert freeze['fixtures'][node]=={'absent':True} and set(before)=={'.'}
        report['fixtures'][node]=dict(current_entries=len(now),current_files=sum(v['kind']=='file' for v in now.values()),preexisting_entries=len(before),preexisting_files=sum(v['kind']=='file' for v in before.values()),new_entries=len(now.keys()-before.keys()),removed_entries=sorted(before.keys()-now.keys()),preexisting_files_and_native_metadata_exact=True,current_equal_RESULT=True,directory_identity_and_mode_preserved=True)
        step('FIXTURE_PASS',node=node,**report['fixtures'][node])
    assert b.source_observation(binding)==fresh
    step('PRESERVED_FAILURES_AND_ONE_ADMISSION_CONTINUATION')
    failed=C/'ROOT-RELEASE-PROCESS.json';approval=C/'INDEPENDENT-ADMISSION-CONTINUATION.json';continuation=C/'ADMISSION-CONTINUATION-PROCESS.json';ci=read(C/'ADMISSION-CONTINUATION-INTENT.json');ap=read(approval);cp=read(continuation)
    assert sha(failed)=='80b9c8979b20996f8e379b2d77348515161bda6bf71b7d803c2a669cfe647280' and read(failed)['actual_process_exit_status']==1
    assert sha(approval)=='0686b8d1da4167c3275e981796ab8fa4a8fc1bd4430c140ae39a50b76cc80f7a' and ap['reviewer']==report['reviewer'] and ap['decision']=='APPROVED_ONE_MISSING_CLAIM_CONTINUATION' and ap['original_failure_scalars']=='NOT_CAPTURED'
    assert sha(C/'CONTINUE-ADMISSION.py')==ap['script_sha256']=='037d9f74b26431d941e86e51e2e48ae42267466c6ed6bad7fc07615b282b1d72'
    assert cp['actual_process_exit_status']==0 and cp['argv'][-2:]==[str(C/'CONTINUE-ADMISSION.py').replace('\\','/'),PIN]
    assert cp['stdout_sha256']==sha(C/'ADMISSION-CONTINUATION.stdout') and cp['stderr_sha256']==sha(C/'ADMISSION-CONTINUATION.stderr')
    assert ci['maximum_continuations']==1 and ci['replay_gate_release_bootstrap_or_tests'] is False and ci['canonical_test_bodies_executed']==0 and ci['independent_decision_sha256']==sha(approval)
    for node,claim in ci['retained_claims'].items():assert claims[node]==claim
    assert ci['missing_claims']==ap['missing_claims']==['fixture_2','fixture_3','fixture_4','fixture_5','js9']
    br1=F/'.agents/runtime/oq23/br';br2=F/'.agents/runtime/oq23/br2';closure1=br1/'control/ROOT-FAILED-EXECUTION-COMPLETION.json';closure2=br2/'control-r2/ROOT-REJECTED-PREPARATION-COMPLETION.json'
    assert sha(closure1)=='59abce80bd41b9c1570abee6fafeb9b4316e2e0f020d495803e1a2847e621304' and read(closure1)['actual_exit_status']==1 and read(closure1)['all_execution_claims_closed_as_FAILED'] is True and not (br1/'delivery/REPORT-SEAL.json').exists()
    assert sha(closure2)=='3422752d9491ba972a564157fefa8e0ae568fdcac1491b45776b088b544e2b6c' and read(closure2)['classification']=='REJECTED_PREPARATION_BEFORE_CANONICAL_EXECUTION' and read(closure2)['canonical_test_bodies_executed']==0 and not (br2/'control-r2/EXECUTION-INTENT.json').exists()
    oldstate=read(br1/'control/ceta-br23-r1/state.json');assert all(oldstate['nodes'][node]['state']=='FAILED' and oldstate['nodes'][node]['claim'] is None for node in claims)
    rejected_state=read(br2/'control-r2/ceta-br23-r2/state.json');assert rejected_state['nodes']['review']['state']=='FAILED' and all(entry['claim'] is None for entry in rejected_state['nodes'].values())
    lost=C/'independent-admission-diagnostic-r2-20261023T052412Z/ATTEMPT-1-LOST-CAPTURE.json';assert sha(lost)=='c1004d0e151e75c3a5efde9e8680d43f042495395a3f3298168b856134467c03' and read(lost)['actual_process_exit_status']==1
    assert {name:sha(C/RUN/name) for name in control_pins}==control_pins,'coordinator state changed during independent check'
    assert sha(C/'EXECUTION-PROCESS.json')==report['execution']['process_sha256'] and sha(D/'RESULT.json')==report['execution']['result_sha256'] and sha(D/'REPORT-SEAL.json')==report['execution']['seal_sha256']
    report['historical_custody']=dict(original_release_actual_exit1_preserved=True,original_release_scalar_differences='NOT_CAPTURED',original_release_cause='UNKNOWN',single_continuation_actual_exit0=True,continuation_process_sha256=sha(continuation),approval_sha256=sha(approval),no_duplicate_execution_node_claims=True,BR1_remains_FAILED_no_success_seal=True,BR2_remains_rejected_without_execution=True,failed_BR1_JS9_full_observation_preserved=True,first_diagnostic_exit1_lost_stream_limitation_preserved=True)
    report['decision']='PASS_LIMITED_CANONICAL_COHORT';report['acceptance_limits']=['Exact 28 selectors / 26 canonical contract modules / same ordered510 tests only','Whole-cohort elapsed is not an admission benchmark or 50ms qualification','Controlled helpers do not qualify a native worker/live profile or genuine native effect path','No installed/offline/migration/endurance/model/human/hardware/full-product acceptance or completion percentage']
    step('PASS_LIMITED_CANONICAL_COHORT');status=0
except BaseException as error:
    tb=BaseException.__dict__['__traceback__'].__get__(error);frames=[]
    while tb is not None:frames.append(dict(file=tb.tb_frame.f_code.co_filename,line=tb.tb_lineno,function=tb.tb_frame.f_code.co_name));tb=tb.tb_next
    report['decision']='REJECTED_POSTRUN_CHECK';report['error']=dict(type=type(error).__name__,args=BaseException.__dict__['args'].__get__(error),traceback=frames)
    print(json.dumps(dict(stage=report['stage'],error=report['error']),sort_keys=True,allow_nan=False),file=sys.stderr,flush=True)
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat();report['diagnostic_elapsed_ns']=time.perf_counter_ns()-mono;report['intended_exit_status']=status
    with (OUT/'REPORT.json').open('x',encoding='utf8',newline='\n') as stream:json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
raise SystemExit(status)
