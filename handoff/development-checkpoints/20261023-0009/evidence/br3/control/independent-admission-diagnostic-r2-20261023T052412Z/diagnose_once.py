from pathlib import Path
from datetime import datetime,timezone
import collections,hashlib,json,os,sys,time,traceback
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/br3';C=B/'control';D=B/'delivery';OUT=Path(__file__).parent
PIN='2c22f24694d2c6e1706669007cda3f32642df18f92bafcee669c58cda2cb41f3';RUN='ceta-br23-r3'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1')
report=dict(reviewer='/root/independent_broader_review',diagnostic='R2 exclusively captured read-only admission conservation',started_at=datetime.now(timezone.utc).isoformat(),started_monotonic_ns=time.perf_counter_ns(),manifest_sha256=PIN,stage='START',steps=[],fixtures={},canonical_test_bodies_executed=0,claim_gate_release_bootstrap_actions=0,mutated_canonical_inputs_or_fixture_state=False,original_release_exit1_preserved=True,original_release_scalar_differences='NOT_CAPTURED',prior_diagnostic_exit1_capture_failure_preserved=True)

def progress(stage,**data):
    report['stage']=stage
    entry=dict(stage=stage,utc_ns=time.time_ns(),**data);report['steps'].append(entry)
    print(json.dumps(entry,sort_keys=True,allow_nan=False),flush=True)

def raw_error(error):
    tb=BaseException.__dict__['__traceback__'].__get__(error)
    frames=[];local_evidence=[]
    while tb is not None:
        frame=tb.tb_frame;frames.append(dict(file=frame.f_code.co_filename,line=tb.tb_lineno,function=frame.f_code.co_name))
        if frame.f_code.co_name=='visit' and frame.f_code.co_filename.endswith('complete_observer.py'):
            values=frame.f_locals;item=dict(directory=str(values.get('directory')),key=values.get('key'),before_children=values.get('before'),first_native=b.o.native(values['first']) if 'first' in values else None,last_native=b.o.native(values['last']) if 'last' in values else None)
            if 'first' in values and 'last' in values:
                item['differing_native_fields']=[k for k in item['first_native'] if item['first_native'][k]!=item['last_native'][k]]
            item['captured_actual_children_calls']=child_calls.get(item['directory'],[])
            local_evidence.append(item)
        tb=tb.tb_next
    args=BaseException.__dict__['args'].__get__(error)
    return dict(type=type(error).__name__,args=args,traceback=frames,observer_visit_locals=local_evidence)

child_calls={}
def profiler(frame,event,arg):
    if event=='return' and frame.f_code.co_name=='children' and frame.f_code.co_filename.endswith('complete_observer.py'):
        if type(arg) is list:
            path=str(frame.f_locals['directory']);child_calls.setdefault(path,[]).append(dict(returned_at_utc_ns=time.time_ns(),names=arg.copy()))

def checked_snapshot(path):
    child_calls.clear();assert sys.getprofile() is None
    sys.setprofile(profiler)
    try:return b.o.snapshot(path)
    finally:sys.setprofile(None)

status=1
try:
    progress('IMPORT_PREPARED_READER')
    sys.path.insert(0,str(B/'work'));import run_broader as b
    progress('VERIFY_FROZEN_PREPARATION')
    packet,binding=b.load_prepared(PIN)
    progress('READ_CURRENT_GRAPH_GATE_AND_CLAIMS')
    runtime=b.BoundRuntime(binding);graph,state=runtime._guard(RUN)
    held=('integrate','fixture_0','fixture_1');missing=('fixture_2','fixture_3','fixture_4','fixture_5','js9')
    def actual_claims(s):
        out={}
        for node in held:
            entry=s['nodes'][node];claim=entry['claim']
            assert entry['state']=='RUNNING' and claim and claim['executor_id']=='/root',('retained claim state/owner',node)
            assert claim['workspace']==binding['workspaces'][node],('retained workspace',node)
            assert claim['effective_write_scope']==[Path(claim['workspace']).relative_to(Path('T:/')).as_posix()+'/**'],('retained exact scope',node)
            assert claim['input_hash']==runtime._input_hash(graph,s,node),('retained current inputs',node)
            out[node]=claim
        for node in missing:assert s['nodes'][node]['state']=='READY' and s['nodes'][node]['claim'] is None,('missing state/claim',node)
        return out
    retained_before=actual_claims(state)
    report['retained_claims']=retained_before;report['missing_still_READY']=list(missing)
    assert not any(D.iterdir()) and not (C/'EXECUTION-INTENT.json').exists(),'canonical execution evidence already exists'
    assert not (C/'ADMISSION-CONTINUATION-INTENT.json').exists(),'continuation already attempted'
    progress('SOURCE_OBSERVATION_BEFORE',source_inputs=len(binding['source_native']))
    before=b.source_observation(binding)
    report['source_before_sha256']=hashlib.sha256(json.dumps(before,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')).hexdigest()
    freeze=json.loads((B/'work/FREEZE-OBSERVATION.json').read_bytes())
    progress('SIX_FIXTURE_OBSERVATIONS_BEGIN')
    for node,text in packet['fixture_workspaces'].items():
        if node=='js9':continue
        progress('FIXTURE_BEGIN',node=node,path=text)
        started=time.perf_counter_ns();now=checked_snapshot(Path(text));old=freeze['fixtures'][node]
        differences={key:dict(frozen=old[key],current=now[key]) for key in old.keys()&now.keys() if old[key]!=now[key]}
        root_calls=child_calls.get(str(Path(text)),[])
        item=dict(path=text,entries=len(now),files=sum(v['kind']=='file' for v in now.values()),bytes=sum(v['bytes'] for v in now.values() if v['kind']=='file'),elapsed_ns=time.perf_counter_ns()-started,exact_all_entries_equal=old==now,added=sorted(now.keys()-old.keys()),missing=sorted(old.keys()-now.keys()),changed=sorted(differences),difference_records=differences,root_native=now['.'],root_actual_children_calls=root_calls)
        report['fixtures'][node]=item
        progress('FIXTURE_DONE',node=node,entries=item['entries'],files=item['files'],bytes=item['bytes'],exact_all_entries_equal=item['exact_all_entries_equal'])
        assert old==now,('fresh diagnostic fixture differs from freeze',node)
    progress('NEW_JS9_EMPTY_OBSERVATION')
    js9=checked_snapshot(Path(packet['fixture_workspaces']['js9']));assert set(js9)=={'.'},'new JS9 not empty'
    report['newJS9_exists_empty']=True
    progress('SOURCE_OBSERVATION_AFTER')
    after=b.source_observation(binding);assert before==after,'source/native/Git/index/read-only failed JS9 changed'
    _,state_after=runtime._guard(RUN);retained_after=actual_claims(state_after);assert retained_before==retained_after,'retained claims changed during diagnostic'
    assert not any(D.iterdir()) and not (C/'EXECUTION-INTENT.json').exists(),'canonical evidence appeared during diagnostic'
    assert not (C/'ADMISSION-CONTINUATION-INTENT.json').exists(),'continuation attempted during diagnostic'
    report.update(all_six_exact=True,source562_Git_index_native_failedJS9_unchanged=True,partial_claims_exact_current_and_unchanged=True,delivery_empty=True,canonical_execution_intent_absent=True,admission_continuation_intent_absent=True,graph_fingerprint=graph.fingerprint,decision_basis='stable sampled conservation only; original release failure cause remains UNKNOWN; no admission latency or product acceptance claim')
    progress('PASS');status=0
except BaseException as error:
    report['error']=raw_error(error);report['all_six_exact']=False
    print(json.dumps(dict(failure=report['error'],stage=report['stage']),sort_keys=True,allow_nan=False),file=sys.stderr,flush=True)
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat();report['elapsed_monotonic_ns']=time.perf_counter_ns()-report['started_monotonic_ns'];report['actual_process_exit_status_intended']=status
    with (OUT/'REPORT.json').open('x',encoding='utf8',newline='\n') as stream:json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
raise SystemExit(status)
