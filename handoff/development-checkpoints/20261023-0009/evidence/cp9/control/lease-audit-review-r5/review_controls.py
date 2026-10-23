"""Independent in-memory R5 controls; no coordinator or Git execution."""
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import copy,hashlib,importlib.util,json,sys,types
F=Path('T:/00-Active/Project-AI-CETA');D=Path(__file__).resolve().parent
SCRIPT=D.parent/'lease_audit_r5.py';EXPECTED='67fc28f556e0657dee127c062aa8228009732c5d7c1ce20751052ca52fc66cae'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(SCRIPT.read_bytes())==EXPECTED
sys.dont_write_bytecode=True;sys.path.insert(0,str(D.parent.parent/'work'))
import exact_git_scope as exact
from taar.orchestration_persistence import sha256_json
spec=importlib.util.spec_from_file_location('independent_lease_audit_r5',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
RUN='ceta-cp9-publication-20261023';P=exact.CONTROL/RUN/'claims.json';SCOPES=exact.scope_paths('a'*40)
assert len(SCOPES)==len(set(SCOPES))==17
def rehash(r):r.pop('receipt_hash',None);r['receipt_hash']=sha256_json(r);return r
def setup():
    packet=dict(run_id=RUN,preparation_run=exact.c.RUN,parent=exact.c.PARENT,ref=exact.c.REF,
        origin=exact.c.ORIGIN,git_scope=copy.deepcopy(SCOPES),pack_id='a'*40,
        graph_fingerprint='b'*64,work_freeze_sha256='c'*64)
    raw=json.dumps(packet,sort_keys=True).encode();pin=sha(raw)
    claim=dict(node_id='integrate',executor_id='/root',claimed_at='2026-10-23T06:30:00+00:00',
        workspace=str(F/'.git'),effective_write_scope=copy.deepcopy(SCOPES),input_hash='d'*64,
        capabilities=[],baseline_snapshot={},git_baseline={'repo_root':str(F)})
    command='PURE_CONTROL_COMMAND_NEVER_EXECUTED'
    common=dict(schema_version=1,run_id=RUN,started_at='2026-10-23T06:00:00+00:00',
        finished_at='2026-10-23T06:00:01+00:00',input_hash='e'*64,changed_files=[],commands=[],
        exit_status=0,git_baseline={},observed_git={})
    # Stock review normalization permits no validation records; a gate needs them.
    review=rehash(dict(common,node_id='review',executor_id='/root/pure-review',decision='approved',
        validations=[],result=dict(publication_packet_sha256=pin,work_freeze_sha256=packet['work_freeze_sha256'])))
    gate=rehash(dict(common,node_id='validate',executor_id='/root',commands=[dict(command=command,exit_status=0)],
        validations=[dict(name='pure',passed=True)],result={}))
    state=dict(schema_version=1,run_id=RUN,scope=str(exact.CONTROL),graph_root='T:/',
        graph_fingerprint=packet['graph_fingerprint'],nodes=dict(
        integrate=dict(state='RUNNING',claim=copy.deepcopy(claim),effective_write_scope=copy.deepcopy(SCOPES),
            executor_id=claim['executor_id'],workspace=claim['workspace']),
        review=dict(state='SUCCEEDED',claim=None,decision='approved',executor_id=review['executor_id'],
            receipt_ref='receipts/review.json',receipt_hash=review['receipt_hash']),
        validate=dict(state='SUCCEEDED',claim=None,validation_passed=True,executor_id=gate['executor_id'],
            receipt_ref='receipts/validate.json',receipt_hash=gate['receipt_hash'])))
    graph=dict(scope=state['scope'],root=state['graph_root'],fingerprint=state['graph_fingerprint'],
        graph=dict(nodes=dict(integrate=dict(access='write_scoped',write_scope=copy.deepcopy(SCOPES)),
            validate=dict(commands=[command]))))
    own=dict(claims_path=str(P),claim=copy.deepcopy(claim),graph_fingerprint=packet['graph_fingerprint'],
        publication_packet_sha256=pin)
    return dict(packet=packet,packet_raw=raw,own=own,claims={'integrate':claim},state=state,
        graph=graph,review=review,gate=gate,extra={})
real_stable=m.stable;real_cs=exact.c.stable;real_is_file=Path.is_file
def invoke(d,own=True,locks=()):
    values={P:d['claims'],P.with_name('state.json'):d['state'],P.with_name('graph.json'):d['graph'],
        P.parent/'receipts/review.json':d['review'],P.parent/'receipts/validate.json':d['gate']}
    values.update(d['extra']);claim_paths=[P,*[p for p in d['extra'] if p.name=='claims.json']]
    def stable(path):
        if path in values:
            value=copy.deepcopy(values[path]);return value,sha(json.dumps(value,sort_keys=True).encode())
        return real_stable(path)
    def cstable(path):
        if path==exact.PACKET:return d['packet_raw'],{'sha256':sha(d['packet_raw'])}
        return real_cs(path)
    def is_file(path):
        if path in values or any(path==p.with_name('events.jsonl') for p in claim_paths):return True
        return real_is_file(path)
    walk=[] if not locks else [(str(F/'.git'),[],list(locks))]
    with patch.object(m,'stable',side_effect=stable),patch.object(exact.c,'stable',side_effect=cstable),\
        patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,
            stdout=('\n'.join(str(p) for p in claim_paths)+'\n').encode(),stderr=b'')),\
        patch.object(m.os,'walk',return_value=walk),patch.object(Path,'is_file',is_file):
        return m.audit(d['own'] if own else None)
def alter_receipt(d,name,key,value,rehash_now=True):
    d[name][key]=value
    if rehash_now:
        rehash(d[name]);d['state']['nodes']['review' if name=='review' else 'validate']['receipt_hash']=d[name]['receipt_hash']
def packet_change(d,key,value):
    d['packet'][key]=value;d['packet_raw']=json.dumps(d['packet'],sort_keys=True).encode()
    d['own']['publication_packet_sha256']=sha(d['packet_raw'])
    d['review']['result']['publication_packet_sha256']=d['own']['publication_packet_sha256']
    rehash(d['review']);d['state']['nodes']['review']['receipt_hash']=d['review']['receipt_hash']
def other(d,*,git=True,root='T:/',missing_claim=False,closed=False):
    path=m.R/'pure-r4-review'/'other-run'/'claims.json'
    cl=copy.deepcopy(d['claims']['integrate']);cl['executor_id']='/root/other'
    cl['effective_write_scope']=['00-Active/Project-AI-CETA/.git/**'] if root=='T:/' else ['.git/**']
    if not git:cl['effective_write_scope']=['00-Active/Project-AI-CETA/.agents/separate/**']
    entry=dict(state='SUCCEEDED' if closed else 'RUNNING',claim=None if missing_claim or closed else cl,
        executor_id=cl['executor_id'],workspace=cl['workspace'],effective_write_scope=cl['effective_write_scope'])
    state=dict(schema_version=1,run_id=path.parent.name,scope=str(path.parent.parent),graph_root=root,
        graph_fingerprint='f'*64,nodes={'integrate':entry})
    graph=dict(scope=state['scope'],root=root,fingerprint='f'*64,
        graph=dict(nodes={'integrate':dict(access='write_scoped',write_scope=cl['effective_write_scope'])}))
    d['extra'].update({path:{} if missing_claim or closed else {'integrate':cl},
        path.with_name('state.json'):state,path.with_name('graph.json'):graph})
cases=[]
def run(name,expected,mutate=lambda d:None,own=True,locks=()):
    d=setup();mutate(d)
    try:
        val=invoke(d,own,locks);actual=val['clear_for_exact_Git_publication']
        cases.append(dict(name=name,passed=actual==expected,expected_clear=expected,actual_clear=actual,
            summary=val['summary'],unresolved=val['unresolved']))
    except BaseException as exc:
        cases.append(dict(name=name,passed=expected is False,expected_clear=expected,actual_clear=False,
            exception_type=type(exc).__name__,message=str(exc)))

# All 23 R3 IDs retained, with actual normalized state executors corrected.
run('valid_exact17_own_packet_and_current_claim_allowed',True)
for field,bad in [('effective_write_scope',['00-Active/Project-AI-CETA/.agents/local/**']),
    ('executor_id','/root/other'),('workspace',str(F/'.agents/local'))]:
    run('contradictory_node_mirror_'+field,False,
        lambda d,field=field,bad=bad:d['state']['nodes']['integrate'].__setitem__(field,bad))
run('other_git_writer_without_own_exception_denied',False,own=False)
run('own_claim_absent_denied',False,lambda d:(d['claims'].clear(),d['state']['nodes']['integrate'].__setitem__('claim',None)))
run('own_claim_path_outside_packet_control_denied',False,lambda d:d['own'].__setitem__('claims_path',str(D/'other/claims.json')))
run('packet_wrong_parent_denied',False,lambda d:packet_change(d,'parent','f'*40))
run('packet_broadened17scope_denied',False,lambda d:packet_change(d,'git_scope',['00-Active/Project-AI-CETA/.git/**']))
run('actual_declaration_differs_from_packet_denied',False,
    lambda d:d['graph']['graph']['nodes']['integrate'].__setitem__('write_scope',['00-Active/Project-AI-CETA/.git/**']))
run('review_not_approved_denied',False,lambda d:d['state']['nodes']['review'].__setitem__('decision','rejected'))
run('gate_not_successful_denied',False,lambda d:d['state']['nodes']['validate'].__setitem__('state','FAILED'))
run('gate_validation_bool_required',False,lambda d:d['state']['nodes']['validate'].__setitem__('validation_passed',1))
run('review_packet_result_drift_denied',False,lambda d:d['review']['result'].__setitem__('publication_packet_sha256','f'*64))
run('review_workfreeze_drift_denied',False,lambda d:d['review']['result'].__setitem__('work_freeze_sha256','f'*64))
run('gate_command_status_drift_denied',False,lambda d:d['gate']['commands'][0].__setitem__('exit_status',1))
run('normalized_gate_exit1_must_not_allow_own_exception',False,lambda d:alter_receipt(d,'gate','exit_status',1))
run('normalized_gate_boolean_exit_must_not_allow_own_exception',False,lambda d:alter_receipt(d,'gate','exit_status',False))
run('normalized_gate_failed_validation_must_not_allow_own_exception',False,
    lambda d:alter_receipt(d,'gate','validations',[dict(name='pure',passed=False)]))
run('normalized_gate_other_run_must_not_allow_own_exception',False,lambda d:alter_receipt(d,'gate','run_id','ceta-other-run'))
run('normalized_review_other_node_must_not_allow_own_exception',False,lambda d:alter_receipt(d,'review','node_id','implement'))
run('normalized_review_receipt_hash_drift_must_not_allow_own_exception',False,
    lambda d:alter_receipt(d,'review','changed_files',['unbound'],False))
run('state_gate_receipt_hash_mismatch_must_not_allow_own_exception',False,
    lambda d:d['state']['nodes']['validate'].__setitem__('receipt_hash','0'*64))

# Additional actual receipt/authority boundaries and scope-conflict controls.
run('review_empty_validations_is_actual_stock_policy',True)
run('review_nonempty_true_validations_also_allowed',True,
    lambda d:alter_receipt(d,'review','validations',[dict(name='review optional',passed=True)]))
run('gate_empty_validations_denied',False,lambda d:alter_receipt(d,'gate','validations',[]))
run('gate_integer_truthy_validation_denied',False,lambda d:alter_receipt(d,'gate','validations',[dict(name='pure',passed=1)]))
run('gate_empty_validation_name_denied',False,lambda d:alter_receipt(d,'gate','validations',[dict(name='',passed=True)]))
run('review_failed_validation_denied',False,lambda d:alter_receipt(d,'review','validations',[dict(name='pure',passed=False)]))
run('review_boolean_exit_denied',False,lambda d:alter_receipt(d,'review','exit_status',False))
run('gate_receipt_executor_drift_rehashed_denied',False,lambda d:alter_receipt(d,'gate','executor_id','/root/other'))
run('review_receipt_executor_drift_rehashed_denied',False,lambda d:alter_receipt(d,'review','executor_id','/root/other'))
run('review_stored_root_executor_denied',False,
    lambda d:(d['state']['nodes']['review'].__setitem__('executor_id','/root'),alter_receipt(d,'review','executor_id','/root')))
run('gate_stored_nonroot_executor_denied',False,
    lambda d:(d['state']['nodes']['validate'].__setitem__('executor_id','/root/other'),alter_receipt(d,'gate','executor_id','/root/other')))
run('review_receipt_ref_escape_denied',False,lambda d:d['state']['nodes']['review'].__setitem__('receipt_ref','../review.json'))
run('gate_receipt_ref_escape_denied',False,lambda d:d['state']['nodes']['validate'].__setitem__('receipt_ref','../validate.json'))
run('normalized_review_wrong_run_denied',False,lambda d:alter_receipt(d,'review','run_id','other-run'))
run('normalized_gate_wrong_node_denied',False,lambda d:alter_receipt(d,'gate','node_id','review'))
run('gate_boolean_command_status_denied',False,
    lambda d:alter_receipt(d,'gate','commands',[dict(command=d['gate']['commands'][0]['command'],exit_status=False)]))
run('packet_duplicate_exact_scope_denied',False,lambda d:packet_change(d,'git_scope',SCOPES[:-1]+[SCOPES[0]]))
run('simultaneous_other_git_writer_denied',False,lambda d:other(d))
run('project_root_relative_git_writer_denied',False,lambda d:other(d,root=str(F)))
run('simultaneous_non_git_writer_permitted_by_bounded_policy',True,lambda d:other(d,git=False))
run('closed_other_git_writer_without_claim_permitted',True,lambda d:other(d,closed=True))
run('recorded_running_git_writer_missing_both_claim_mirrors_denied',False,lambda d:other(d,missing_claim=True))
run('existing_git_lock_denied',False,locks=('index.lock',))

old=json.loads((D.parent/'lease-audit-review-r3/RESULT.json').read_bytes())
assert set(row['name'] for row in old['cases'])<=set(row['name'] for row in cases)
prior4=json.loads((D.parent/'lease-audit-review-r4/RESULT.json').read_bytes())
assert [row['name'] for row in prior4['cases']]==[row['name'] for row in cases]
report=dict(recorded_at=datetime.now(timezone.utc).isoformat(),reviewer='/root/broader_successor_author',
    reviewed_script_sha256=sha(SCRIPT.read_bytes()),exact_scope_source_sha256=sha(Path(exact.__file__).read_bytes()),
    actual_packet_validator_used=True,packet_file_read_seam='SYNTHETIC_BYTES_ONLY',
    normalized_receipt_shape='Stored state executor fields match normalized actual receipts; gate executor /root, independent review /root/pure-review; empty review validations permitted',
    original_R3_ids_retained=23,cases=cases,selected=len(cases),passed=sum(x['passed'] for x in cases),
    failed_expectations=sum(not x['passed'] for x in cases),native_or_canonical_or_coordinator_execution=False,
    claims_verify_gates_invoked=False,qualification='In-memory audit controls using the real exact17 packet validator and actual stock canonical JSON hash; no live packet, claim, inventory or mutation.')
with (D/'RESULT.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps(dict(selected=report['selected'],passed=report['passed'],failed_expectations=report['failed_expectations'],
    failures=[row for row in cases if not row['passed']]),indent=2))
raise SystemExit(1 if report['failed_expectations'] else 0)
