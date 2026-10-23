from pathlib import Path
from datetime import datetime,timezone
import ast,copy,hashlib,json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');J=F/'.agents/runtime/oq23/jb2';W=J/'work';R=J/'review';C=J/'control'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with p.open('x',encoding='utf8') as h:json.dump(v,h,indent=2,allow_nan=False);h.write('\n')
def functions(tree):
 result={}
 for top in tree.body:
  if isinstance(top,ast.ClassDef):
   for f in top.body:
    if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)):result[top.name+'.'+f.name]=f
  elif isinstance(top,(ast.FunctionDef,ast.AsyncFunctionDef)):result[top.name]=top
 return result
m=read(W/'MANIFEST.json');assert sha(W/'MANIFEST.json')=='e9b0ac804a3bcebad266e400e6ce41a8fbb113749026230baf6e4ed59f93db72'
for n,p in m['files'].items():assert sha(W/n)==p['sha256'] and (W/n).stat().st_size==p['bytes'],n
for p,h in m['external_pins'].items():assert sha(Path(p))==h,p
expected_actual=set(m['files'])|set(m['permitted_postfreeze_outputs'])|{'MANIFEST.json'}
actual={p.relative_to(W).as_posix() for p in W.rglob('*') if p.is_file()};assert actual<=expected_actual
extra_work_pins={str(W/n):sha(W/n) for n in sorted(actual-set(m['files']))}
report=read(R/'INDEPENDENT-RETAINED-COHORT.json');author=read(W/'CONTROLS-FINAL.json');old=read(F/'.agents/runtime/oq23/jb1/work/JOINT-CONTROLS-R3.json');own=read(R/'INDEPENDENT-CONSUMPTION.json')
assert report['tests_run']==136 and report['selected']==report['started']==report['stopped']==author['selected']
assert len(old['selected'])==112 and set(old['selected'])<=set(report['selected']) and len(set(report['selected'])-set(old['selected']))==24
for value in [report,own]:
 assert value['successful'] and value['selected']==value['started']==value['stopped']
 assert not any(value[n] for n in ['failures','errors','skips','expected_failures','unexpected_successes','forbidden_call_attempts'])
assert own['tests_run']==21 and own['pins_unchanged'] and own['candidate_origins']==author['candidate_origins']
assert report['candidate_origins']==author['candidate_origins']
witness=read(W/'TRANSCRIPT-BUDGET-WITNESS-R2.json');assert witness['tests_run']==4 and witness['failures']==witness['errors']==witness['skips']==0
source=read(W/'CANONICAL-BEFORE.json');delta=[]
for n,pin in source['files'].items():
 p=F/n;st=p.stat();now=dict(sha256=sha(p),bytes=st.st_size,mtime_ns=st.st_mtime_ns)
 if now!=pin:delta.append(dict(path=n,before=pin,current=now))
# Root separately disclosed four metadata/pin targets may change. Any actual delta is reported to Root before review completion.
amend=read(W/'OWNER-CONSUMER-INPUT-AMENDMENT.json');pins8=dict(read(J/'packet/INPUTS.json')['source_pins']);pins8[amend['additional_canonical_source']['repository_relative_path']]=amend['additional_canonical_source']['sha256']
assert len(pins8)==8 and all(sha(F/n)==h for n,h in pins8.items())
changes={}
for rel,baseline,expected in [('src/ceta/identity/owner_session.py',F/'src/ceta/identity/owner_session.py',{'NativeOwnerSession.retain_verified_enrollment','NativeCpuOwnerSession.retain_verified_effect'}),('src/ceta/identity/native_approval.py',F/'.agents/runtime/oq23/jb1/work/candidate/src/ceta/identity/native_approval.py',{'NativeApprovalSession.transcript'})]:
 old_tree=ast.parse(baseline.read_text());new_tree=ast.parse((W/'candidate'/rel).read_text());before=functions(old_tree);after=functions(new_tree)
 assert set(before)==set(after)
 changed={k for k in before if ast.dump(before[k],include_attributes=False)!=ast.dump(after[k],include_attributes=False)};assert changed==expected,(rel,changed)
 for k in expected:assert ast.dump(before[k].args,include_attributes=False)==ast.dump(after[k].args,include_attributes=False)
 normalized=copy.deepcopy(new_tree)
 for top in normalized.body:
  if isinstance(top,ast.ClassDef):
   top.body=[copy.deepcopy(before[top.name+'.'+f.name]) if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and top.name+'.'+f.name in expected else f for f in top.body]
 assert ast.dump(normalized,include_attributes=False)==ast.dump(old_tree,include_attributes=False),(rel,'unrelated_AST_delta')
 changes[rel]=sorted(changed)
env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false')
def git(*args):
 p=subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=F,env=env,capture_output=True,check=False);assert p.returncode==0,p.stderr;return p.stdout
Git=dict(root=git('rev-parse','--show-toplevel').decode().strip(),head=git('rev-parse','HEAD').decode().strip(),branch=git('symbolic-ref','HEAD').decode().strip(),origin=git('remote','get-url','origin').decode().strip(),all_untracked_status_sha256=hashlib.sha256(git('status','--porcelain=v1','-z','--untracked-files=all')).hexdigest(),index_sha256=sha(F/'.git/index'))
packet=read(J/'packet/INPUTS.json');assert Git['root'].replace('\\','/').casefold()==F.as_posix().casefold()
assert all(Git[k]==packet['Git'][k] for k in ['head','branch','origin','index_sha256']) and Git['all_untracked_status_sha256']==packet['Git']['all_untracked_status_sha256']
closure=C/'ROOT-CLOSE-CANDIDATE.py';assert sha(closure)=='c9065cdc7dde212da9b9840dfb4615805c41d32837ab7bc354eb3f30aad5d973'
state=read(C/'ceta-jb23-r2/state.json');assert state['graph_fingerprint']==m['graph_fingerprint'] and state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['implement']['claim'] is None and state['nodes']['review']['state']=='RUNNING' and state['nodes']['review']['claim']['executor_id']=='/root/independent_broader_review'
previous=read(F/'.agents/runtime/oq23/jb1/control/ceta-jb23-r1/state.json');assert previous['nodes']['review']['state']=='FAILED' and previous['nodes']['review']['claim'] is None
old_review=read(F/'.agents/runtime/oq23/jb1/review/REVIEW.json');assert old_review['decision']=='rejected'
failures=[]
for n in sorted(actual):
 if n.endswith('-PROCESS.json'):
  v=read(W/n);status=v.get('exit_status',v.get('actual_process_exit_status'))
  if status!=0:failures.append(dict(path=str(W/n),sha256=sha(W/n),actual_exit_status=status))
assert any(x['path'].endswith('TRANSCRIPT-CONTROLS-PROCESS.json') and x['actual_exit_status']==1 for x in failures)
result=dict(recorded_at=datetime.now(timezone.utc).isoformat(),manifest_sha256=sha(W/'MANIFEST.json'),frozen_work_files=len(m['files']),work_file_hashes_and_sizes_exact=True,external_pins_exact=len(m['external_pins']),supplemental_closed_author_output_pins=extra_work_pins,canonical_source_baseline_count=len(source['files']),canonical_source_delta=delta,exact8_candidate_canonical_inputs_match=True,Git=Git,retained_cohort=136,prior_exact_ids_retained=112,new_author_controls=24,independently_authored_controls=21,independent_no_skips_or_forbidden_calls=True,four_case_prior_defect_successor=4,AST_changed_methods=changes,public_interfaces_unchanged=True,hot_fence_AST_unchanged=True,root_candidate_closure_sha256=sha(closure),root_closure_review='Read-only inspected. Actual declared preparation gate then Root D-only claim; eight exact-byte create-only copies and accepted-candidate evidence; ordinary receipt completion/verification. No canonical integration or native qualification. Root must invoke once with exact frozen review manifest after actual approved review.',rejected_JB1_preserved=True,failed_author_attempts=failures,canonical_or_fixture_or_native_effects=False,qualification='Independent candidate review only. Source delta, if any, requires explicit Root provenance assessment before final disposition. No reliable admission timing/native epoch/provider/AC7 or full-product acceptance.')
save(R/'FINAL-AUDIT.json',result);print(json.dumps(dict(canonical_source_baseline=len(source['files']),canonical_source_delta=delta,retained=136,independent=21,work_exact=True,external_exact=len(m['external_pins']),review_claim='RUNNING',full_product_acceptance=False)));raise SystemExit(0)
