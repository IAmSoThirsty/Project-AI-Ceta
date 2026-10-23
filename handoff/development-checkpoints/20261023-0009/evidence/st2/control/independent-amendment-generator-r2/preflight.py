"""Independent pure future-state metadata controls; builder write tail excluded."""
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import ast,copy,hashlib,json,os,sys,traceback
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work';Q=F/'.agents/runtime/oq23/ds2';OUT=Path(__file__).parent
SOURCE=C/'BUILD-HANDLE-EXECUTION-AMENDMENT.py';PIN='12ecd4e5b56d0c10081bbdc23248922e26106ef72a04d1383cae1413bea280ff';RUN='ceta-ds23-r2-gate-r2';GRAPH='997829e1616609bafc88eea12f601eba7d715ad0e03b27e55a3f1af59a0d51ed';QR=Q/'control-r2'/RUN
original_read=Path.read_bytes;cache={};reads=set()
def digest(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def plain(p):
 text=str(p);prefix=chr(92)*2+'?'+chr(92)
 return Path(text[len(prefix):]) if text.startswith(prefix) else Path(p)
def extended(p):
 p=Path(p);text=str(p);prefix=chr(92)*2+'?'+chr(92)
 return Path(prefix+text) if os.name=='nt' and not text.startswith(prefix) else p
def actual(p):
 p=plain(p)
 if p not in cache:cache[p]=original_read(extended(p))
 return cache[p]
def readjson(p):return json.loads(actual(p))
def save(name,v):
 with (OUT/name).open('x',encoding='utf-8',newline='\n') as h:json.dump(v,h,indent=2,ensure_ascii=False,allow_nan=False);h.write('\n')
source=original_read(SOURCE);assert digest(source)==PIN
tr=ast.parse(source,filename=str(SOURCE));prefix=[]
for node in tr.body:
 prefix.append(node)
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='value' for t in node.targets):break
assert isinstance(prefix[-1],ast.Assign) and prefix[-1].targets[0].id=='value'
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('open','write','write_bytes','write_text','fsync') for top in prefix for n in ast.walk(top))
compiled=compile(ast.Module(body=prefix,type_ignores=[]),str(SOURCE)+':WRITE_TAIL_DISABLED','exec')
# Independently exercise the exact final reader function with real filesystem reads.
readerdef=next(n for n in tr.body if isinstance(n,ast.FunctionDef) and n.name=='read_bytes')
reader_ns=dict(Path=Path,os=os);exec(compile(ast.Module(body=[readerdef],type_ignores=[]),str(SOURCE)+':READER_ONLY','exec'),reader_ns)
physical=[]
for base,manifest,key in [(W,W/'MANIFEST.json','work_hashes'),(S/'review',S/'review/MANIFEST.json','files')]:
 for name,pin in readjson(manifest)[key].items():
  path=base/name
  if len(str(path))<=260:continue
  ordinary={}
  try:b=original_read(path);ordinary=dict(status='PASS',sha256=digest(b))
  except BaseException as e:ordinary=dict(status='FAIL',type=type(e).__name__,message=str(e),errno=getattr(e,'errno',None),winerror=getattr(e,'winerror',None))
  b=reader_ns['read_bytes'](path);assert digest(b)==pin
  physical.append(dict(path=str(path),characters=len(str(path)),expected_sha256=pin,ordinary=ordinary,final_reader=dict(status='PASS',sha256=digest(b))))
assert len(physical)==7 and all(x['ordinary']['status']=='FAIL' for x in physical)
for invalid in [Path('relative.json'),Path(r'\\server\share\file.json')]:
 try:reader_ns['read_bytes'](invalid)
 except AssertionError:pass
 else:raise AssertionError(('INVALID_READER_PATH_ACCEPTED',str(invalid)))
save('PHYSICAL-READER-WITNESS.json',dict(source_sha256=PIN,controls='Seven exact frozen long members; relative/UNC refusals',long_members=physical,no_member_dropped=True,no_native_or_product_execution=True))
qm=readjson(Q/'work/MANIFEST.json');qmf=digest(actual(Q/'work/MANIFEST.json'));assert qmf=='736a2a3ef8639bf99acced85d0ce3950b74b01bf9f23d856148ca7a7061df2f6'
helper=Q/'control-r2/ROOT-CLOSE-QUALIFICATION-R2.py';hp=digest(actual(helper));assert hp=='f17cd2b8214f9076cdcfa87683253a5a486bbd31c6d41d2f4887dd0cd9ccd858'
qreview=dict(decision='approved',reviewer='/root/status_packet_review',manifest_sha256=qmf,root_candidate_closure_sha256=hp)
rb=enc(qreview);notes=enc(dict(classification='SYNTHETIC_FUTURE_REVIEW_DATA_ONLY'))
rm=dict(decision='approved',candidate_manifest_sha256=qmf,review_sha256=digest(rb),root_candidate_closure_sha256=hp,files={'REVIEW.json':digest(rb),'NOTES.json':dict(sha256=digest(notes))});rmb=enc(rm);rpin=digest(rmb)
accepted=dict(source_qualification_run_id='ceta-ds23-r2',run_id=RUN,provider_bytes_unchanged_by_gate_metadata_successor=True,original_gate_setup_rejected=True,work_manifest_sha256=qmf,review_manifest_sha256=rpin,review_sha256=digest(rb),root_candidate_closure_sha256=hp,provider=dict(path=str(Q/'work/directory_snapshot.py'),sha256=qm['provider_sha256']),controls_sha256=qm['files']['CONTROLS-R2.json']['sha256'],controlled_tests=50,full_F_qualification_sha256=qm['files']['FULL-F-QUALIFICATION.json']['sha256'],full_F_snapshot_sha256=qm['files']['FULL-F-SNAPSHOT.json']['sha256'],access_time_policy_sha256=qm['files']['ACCESS-TIME-OBSERVATION-POLICY.json']['sha256'])
v=dict(response=dict(run_id=RUN,graph_fingerprint=GRAPH,allowed=True,receipts_valid=True,terminal_success=True,states={n:'SUCCEEDED' for n in ('discover','plan','implement','review','validate','integrate')}))
qc=dict(run_id=RUN,graph_fingerprint=GRAPH,terminal_success=True,canonical_or_installed_mutation=False,manifest_sha256=qmf,review_manifest_sha256=rpin,verification_sha256=digest(enc(v)),accepted_qualification_sha256=digest(enc(accepted)))
future={Q/'review-r2/REVIEW.json':rb,Q/'review-r2/MANIFEST.json':rmb,Q/'review-r2/NOTES.json':notes,Q/'delivery/ACCEPTED-QUALIFICATION.json':enc(accepted),Q/'control-r2/verify-final-api.json':enc(v),Q/'control-r2/ROOT-QUALIFICATION-COMPLETION.json':enc(qc),QR/'claims.json':enc({})}
qs=dict(run_id=RUN,graph_fingerprint=GRAPH,nodes={})
for n in v['response']['states']:
 ex='/root/status_packet_review' if n=='review' else '/root'
 rec=dict(schema_version=1,run_id=RUN,node_id=n,executor_id=ex,exit_status=0,commands=[],validations=[dict(name='Synthetic linked boundary',passed=True)],result={})
 if n=='review':rec.update(decision='approved',result=dict(manifest_sha256=qmf,review_sha256=digest(rb),root_candidate_closure_sha256=hp))
 if n=='validate':rec['commands']=[dict(command=readjson(Q/'packet-r2/INPUTS.json')['exact_gate_command'],exit_status=0)]
 rec['receipt_hash']=digest(canonical(rec))
 qs['nodes'][n]=dict(state='SUCCEEDED',claim=None,executor_id=ex,receipt_ref='receipts/'+n+'.json',receipt_hash=rec['receipt_hash'],validation_passed=n=='validate',decision='approved' if n=='review' else None)
 future[QR/'receipts'/f'{n}.json']=enc(rec)
future[QR/'state.json']=enc(qs)
SSTATE=C/'ceta-st23-r2/state.json';sv=readjson(SSTATE);sgate=readjson(C/'ceta-st23-r2/receipts/validate.json')
def jget(m,p):return json.loads(m[p] if p in m else actual(p))
def jput(m,p,v):m[p]=enc(v)
def mutate_json(p,fn):
 def apply(m):v=jget(m,p);fn(v);jput(m,p,v)
 return apply
def resign(m,base,node,fn):
 sp=base/'state.json';rp=base/'receipts'/f'{node}.json';rr=jget(m,rp);fn(rr);rr.pop('receipt_hash',None);rr['receipt_hash']=digest(canonical(rr));st=jget(m,sp);st['nodes'][node]['receipt_hash']=rr['receipt_hash'];jput(m,rp,rr);jput(m,sp,st)
def changed_bytes(path):return lambda m:m.__setitem__(path,actual(path)+b'\n# independent simulated unreviewed drift\n')
def execute(name,mutate,expected):
 overlay=dict(future);mutate(overlay);ns={'__name__':'independent_metadata_prefix'};prior_path=list(sys.path)
 def read(p):
  p=plain(p);reads.add(p)
  return overlay[p] if p in overlay else actual(p)
 try:
  with patch.object(Path,'read_bytes',read),patch.object(sys,'argv',[str(SOURCE),'--qualification-manifest-sha256',qmf,'--qualification-review-manifest-sha256',rpin]):exec(compiled,ns)
  observed=True;detail=dict(support_pins=len(ns['value']['support_pins']),qualification_run_id=ns['value']['qualification_run_id'],actual_reader_function_present='read_bytes' in ns)
 except (AssertionError,KeyError,ValueError,FileNotFoundError) as e:
  observed=False;detail=dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc())
 finally:sys.path[:]=prior_path
 return dict(id=name,expected_reaches_value=expected,observed_reaches_value=observed,passed=observed is expected,detail=detail)
cases=[('valid_linked_future',lambda m:None,True),('provider_member_drift',changed_bytes(Q/'work/directory_snapshot.py'),False),('original_status_core_drift',changed_bytes(W/'status_core.py'),False),('original_review_member_drift',changed_bytes(S/'review/REVIEW.json'),False),('qualification_review_candidate_drift',mutate_json(Q/'review-r2/REVIEW.json',lambda x:x.update(manifest_sha256='0'*64)),False),('qualification_review_manifest_member_drift',lambda m:m.__setitem__(Q/'review-r2/NOTES.json',notes+b' '),False),('accepted_artifact_drift',mutate_json(Q/'delivery/ACCEPTED-QUALIFICATION.json',lambda x:x.update(work_manifest_sha256='0'*64)),False),('closure_verification_link_drift',mutate_json(Q/'control-r2/ROOT-QUALIFICATION-COMPLETION.json',lambda x:x.update(verification_sha256='0'*64)),False),('qualification_gate_flag_false',mutate_json(QR/'state.json',lambda x:x['nodes']['validate'].update(validation_passed=False)),False),('qualification_review_receipt_bad_hash',mutate_json(QR/'receipts/review.json',lambda x:x.update(receipt_hash='0'*64)),False),('qualification_gate_wrong_command',lambda m:resign(m,QR,'validate',lambda r:r.update(commands=[dict(command='SIMULATED_OTHER_COMMAND_NOT_EXECUTED',exit_status=0)])),False),('qualification_bool_exit_status',lambda m:resign(m,QR,'validate',lambda r:r.update(exit_status=False)),False),('qualification_failed_validation',lambda m:resign(m,QR,'validate',lambda r:r.update(validations=[dict(name='Synthetic failed validation',passed=False)])),False),('qualification_other_completed_receipt_bad_hash',mutate_json(QR/'receipts/discover.json',lambda x:x.update(receipt_hash='0'*64)),False),('qualification_other_completed_node_claim_present',mutate_json(QR/'state.json',lambda x:x['nodes']['integrate'].update(claim={'synthetic':'active'})),False),('qualification_current_claims_present',lambda m:m.__setitem__(QR/'claims.json',enc({'integrate':{'synthetic':'active'}})),False),('qualification_state_verification_state_mismatch',mutate_json(QR/'state.json',lambda x:x['nodes']['discover'].update(state='READY')),False),('original_gate_validation_false',mutate_json(SSTATE,lambda x:x['nodes']['validate'].update(validation_passed=False)),False),('original_gate_receipt_link_bad',mutate_json(SSTATE,lambda x:x['nodes']['validate'].update(receipt_hash='0'*64)),False),('original_gate_wrong_command_with_valid_hash',lambda m:resign(m,C/'ceta-st23-r2','validate',lambda r:r.update(commands=[dict(command='SIMULATED_OTHER_COMMAND_NOT_EXECUTED',exit_status=0)])),False),('original_gate_empty_commands_with_valid_hash',lambda m:resign(m,C/'ceta-st23-r2','validate',lambda r:r.update(commands=[])),False),('original_gate_wrong_graph',mutate_json(C/'ceta-st23-r2/graph.json',lambda x:x.update(fingerprint='0'*64)),False),('original_review_receipt_candidate_drift_valid_hash',lambda m:resign(m,C/'ceta-st23-r2','review',lambda r:r['result'].update(manifest_sha256='0'*64)),False),('original_claim_present',lambda m:m.__setitem__(C/'ceta-st23-r2/claims.json',enc({'integrate':{'synthetic':'active'}})),False),('historical_failed_admission_relabel',mutate_json(C/'ROOT-INTEGRATE-CLAIM-R2-PROCESS.json',lambda x:x.update(actual_process_exit_status=0)),False)]
results=[execute(*case) for case in cases]
# Independently consistent altered accepted record must still fail selected member binding.
for key in ['provider','controls_sha256','full_F_snapshot_sha256','access_time_policy_sha256','root_candidate_closure_sha256']:
 def alter(m,key=key):
  a=jget(m,Q/'delivery/ACCEPTED-QUALIFICATION.json')
  if key=='provider':a[key]['sha256']='0'*64
  else:a[key]='0'*64
  jput(m,Q/'delivery/ACCEPTED-QUALIFICATION.json',a);c=jget(m,Q/'control-r2/ROOT-QUALIFICATION-COMPLETION.json');c['accepted_qualification_sha256']=digest(enc(a));jput(m,Q/'control-r2/ROOT-QUALIFICATION-COMPLETION.json',c)
 results.append(execute('accepted_'+key+'_wrong_with_relinked_closure',alter,False))
# Read-only real input conservation, including extended-length frozen members.
conserved={}
for path,b in cache.items():
 now=original_read(extended(path));assert now==b,('REAL_INPUT_DRIFT',str(path));conserved[str(path)]=digest(b)
assert original_read(SOURCE)==source
assert not (C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json').exists() and not any((S/'delivery').iterdir())
report=dict(schema_version=1,recorded_at=datetime.now(timezone.utc).isoformat(),reviewer='/root/independent_broader_review',source_sha256=PIN,controls=len(results),passed=sum(x['passed'] for x in results),failed=[x['id'] for x in results if not x['passed']],results=results,physical_reader_witness_sha256=digest(original_read(OUT/'PHYSICAL-READER-WITNESS.json')),real_inputs_conserved=conserved,write_tail_excluded=True,actual_amendment_created=False,pure_synthetic_Q_future=True,actual_qualification_closure_or_application_approval=False,no_coordinator_native_Fscan_canonical_or_Git_action=True,prior_source_failures_preserved=True)
save('CONTROLS.json',report)
print(json.dumps(dict(controls=len(results),passed=report['passed'],failed=report['failed'],source_sha256=PIN,write_tail_excluded=True,actual_amendment_created=False)))
raise SystemExit(0 if not report['failed'] else 1)
