"""Actual-binding loader overlays and exact DS2/caller failure composition controls."""
from pathlib import Path as RealPath
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime,timezone
import ast,copy,ctypes,hashlib,json,os,sys,time
F=RealPath('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work';Q=F/'.agents/runtime/oq23/ds2';R=C/'independent-handle-composition-r1';A=C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json'
sys.dont_write_bytecode=True;sys.path[:0]=[str(W),str(Q/'work')]
import status_core as actual_core,directory_snapshot as provider_module
source=(C/'run_handle_qualified.py').read_text(encoding='utf8');tree=ast.parse(source);load_node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='load');context_node=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='QualifiedObservation')
load_code=compile(ast.Module(body=[load_node],type_ignores=[]),'exact current loader with actual bindings and controlled overlays','exec');context_code=compile(ast.Module(body=[context_node],type_ignores=[]),'exact current caller context with controlled DS2 provider','exec')
raw_amend=A.read_bytes();actual_amend=json.loads(raw_amend);sha=lambda raw:hashlib.sha256(raw).hexdigest();ids=[]
base_records={str(RealPath(actual_amend[field])):json.loads(actual_core.physical(RealPath(actual_amend[field])).read_bytes()) for field in ('qualification_closure','qualification_verification')}
def loader_case(label,mutate,expected=True,relink=True):
 a=copy.deepcopy(actual_amend);decision=dict(decision='APPROVED_EXACT_F_ONLY_HANDLE_QUALIFICATION',reviewer='/root/status_packet_review',amendment_sha256=sha(raw_amend),runner_sha256=actual_amend['runner_sha256'],launcher_sha256=actual_amend['launcher_sha256']);records=copy.deepcopy(base_records);options={};mutate(a,decision,records,options)
 overrides={};hash_overrides=options.get('hash_overrides',{})
 for path,record in records.items():
  if record!=base_records[path]:overrides[path]=(json.dumps(record,indent=2,allow_nan=False)+'\n').encode();a['support_pins'][path]=sha(overrides[path])
 a_raw=raw_amend if a==actual_amend else (json.dumps(a,indent=2,allow_nan=False)+'\n').encode();overrides[str(A)]=a_raw
 if relink:decision['amendment_sha256']=sha(a_raw)
 overrides[str(C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json')]=json.dumps(decision).encode()
 class P:
  def __init__(self,value):self.real=value.real if isinstance(value,P) else RealPath(str(value))
  def __truediv__(self,name):return P(self.real/name)
  def __str__(self):return str(self.real)
  def is_relative_to(self,other):return self.real.is_relative_to(RealPath(str(other)))
  def read_bytes(self):return overrides[str(self.real)] if str(self.real) in overrides else actual_core.physical(self.real).read_bytes()
 def hash_port(path):
  key=str(RealPath(str(path)))
  if key in hash_overrides:return hash_overrides[key]
  return sha(overrides[key]) if key in overrides else actual_core.sha(RealPath(key))
 loaded=[];port_provider=SimpleNamespace(EXPECTED_IGNORED=options.get('ignored',actual_core.EXPECTED_IGNORED),F=options.get('F',F))
 class Loader:
  def exec_module(self,module):loaded.append('INERT_LOADER_ONLY')
 imports=SimpleNamespace(util=SimpleNamespace(spec_from_file_location=lambda name,path:SimpleNamespace(loader=Loader()),module_from_spec=lambda spec:port_provider))
 namespace=dict(A=P(A),C=P(C),W=P(W),F=F,Path=P,__file__=str(C/'run_handle_qualified.py'),json=json,s=SimpleNamespace(sha=hash_port,EXPECTED_IGNORED=actual_core.EXPECTED_IGNORED),importlib=imports)
 exec(load_code,namespace);failure=None;answer=None
 try:answer=namespace['load'](actual_amend['prepared_manifest_sha256'])
 except AssertionError as error:failure=type(error).__name__
 assert (failure is None)==expected,(label,failure,expected)
 if expected:assert answer[0]==actual_amend and answer[1] is port_provider and sha(a_raw)==actual_core.sha(A)
 ids.append(dict(id=label,passed=True,accepted=expected,error=failure,inert_loader_count=len(loaded),actual_record_bytes=expected,synthetic_overlay=not expected,real_provider_import_or_execution=False))
loader_case('exact_actual_A_support_and_proposed_approval_accepts',lambda *x:None)
loader_case('wrong_named_reviewer_refused',lambda a,d,r,o:d.update(reviewer='/root/OTHER'),False)
loader_case('stale_approval_amendment_refused',lambda a,d,r,o:d.update(amendment_sha256='OLD'),False,relink=False)
loader_case('stale_approval_runner_refused',lambda a,d,r,o:d.update(runner_sha256='OLD'),False)
loader_case('stale_approval_launcher_refused',lambda a,d,r,o:d.update(launcher_sha256='OLD'),False)
loader_case('required_provider_support_omission_refused',lambda a,d,r,o:a['support_pins'].pop(a['source_provider']),False)
loader_case('critical_support_drift_refused',lambda a,d,r,o:o.update(hash_overrides={str(C/'AGENTS.md'):'DRIFT'}),False)
loader_case('original_preparation_drift_refused',lambda a,d,r,o:o.update(hash_overrides={str(W/'MANIFEST.json'):'DRIFT'}),False)
loader_case('failed_qualification_closure_refused',lambda a,d,r,o:r[a['qualification_closure']].update(terminal_success=False),False)
loader_case('old_qualification_run_refused',lambda a,d,r,o:r[a['qualification_closure']].update(run_id='ceta-ds23-r2'),False)
loader_case('failed_qualification_node_refused',lambda a,d,r,o:r[a['qualification_verification']]['response']['states'].update(review='FAILED'),False)
loader_case('different_verified_graph_refused',lambda a,d,r,o:r[a['qualification_verification']]['response'].update(graph_fingerprint='OTHER'),False)
loader_case('old_amendment_graph_refused',lambda a,d,r,o:a.update(qualification_graph_fingerprint='b848fefb7c69a06d4ffc32f71bac48ac316edc03755773ec0c6103365d2b4c0b'),False)
def prior_provider(a,d,r,o):
 old=str(F/'.agents/runtime/oq23/ds1/work/directory_snapshot.py');a.update(source_provider=old);a['support_pins'][old]=actual_core.sha(RealPath(old))
loader_case('pinned_rejected_DS1_provider_refused',prior_provider,False)
def other_DS2(a,d,r,o):
 other=str(Q/'work/complete_candidate.py');a.update(source_provider=other);a['support_pins'][other]=actual_core.sha(RealPath(other))
loader_case('different_DS2_source_file_refused',other_DS2,False)
loader_case('different_ignored_profile_refused',lambda a,d,r,o:o.update(ignored=actual_core.EXPECTED_IGNORED|{'EXTRA'}),False)
loader_case('different_provider_F_refused',lambda a,d,r,o:o.update(F=F/'OTHER'),False)
# Explicit optimization guards survive compilation with optimize=2.
guard_results=[]
for name in ('run_handle_qualified.py','execute_handle_qualified_once.py'):
 t=ast.parse((C/name).read_bytes());guard=next(x for x in t.body if isinstance(x,ast.If) and isinstance(x.test,ast.Attribute) and x.test.attr=='optimize')
 caught=None
 try:exec(compile(ast.Module(body=[guard],type_ignores=[]),'exact explicit optimization guard','exec',optimize=2),dict(sys=SimpleNamespace(flags=SimpleNamespace(optimize=1))))
 except RuntimeError as error:caught=error
 assert caught is not None and caught.args==('OPTIMIZED_INTERPRETER_REFUSED',)
 guard_results.append(dict(id=name+'_optimized_mode_refused',passed=True))
# Exact DS2 native-query failure rows through the unchanged caller capture path.
class Hostile(KeyboardInterrupt):
 def __setattr__(self,name,value):raise RuntimeError('hostile setter called')
 def __str__(self):raise RuntimeError('hostile formatter called')
 def __repr__(self):raise RuntimeError('hostile formatter called')
class VirtualOutput:
 def __init__(self,path):self.path=path
 def __truediv__(self,name):return VirtualOutput(self.path+'/'+name)
 def __str__(self):return self.path
 def mkdir(self,exist_ok):assert exist_ok is False
probe=json.loads((Q/'work/DIRECTORY-HANDLE-PROBE.json').read_bytes())['directories'][0]
partials=[]
def deny(*args,**kwargs):raise AssertionError('actual native/process/socket action forbidden')
with patch('ctypes.WinDLL',side_effect=deny),patch('ctypes.CDLL',side_effect=deny),patch('subprocess.run',side_effect=deny),patch('subprocess.Popen',side_effect=deny),patch('socket.socket',side_effect=deny):
 for failed_class in (1,18):
  primary=Hostile('CONTROLLED_DS2_NATIVE_PARTIAL');secondary=OSError('CONTROLLED_INNER_CLOSE');captured=[]
  class P(provider_module.WinProvider):
   def __init__(self):self.closes=0;self.api=SimpleNamespace(GetFileInformationByHandleEx=self.info)
   def path_stat(self,path):return copy.deepcopy(probe['raw_path_before_open'])
   def open(self,path):return 404
   def close(self,handle):self.closes+=1;raise secondary
   def info(self,handle,number,pointer,size):
    if number==failed_class:raise primary
    kind,key={0:(provider_module.Basic,'basic'),1:(provider_module.Standard,'standard'),18:(provider_module.Identity,'identity')}[number];data=kind()
    for name,_ in kind._fields_:
     value=probe['native_handle_before'][key][name]
     if name=='FileId':getattr(data,name)[:]=bytes.fromhex(value)
     else:setattr(data,name,value)
    ctypes.memmove(pointer,ctypes.byref(data),size);return 1
  class Outer:
   def open(self,path):return 101
   def path_stat(self,path):return copy.deepcopy(probe['raw_path_before_open'])
   def query(self,handle):return copy.deepcopy(probe['native_handle_before'])
   def close(self,handle):pass
  inner=P()
  def child():
   with provider_module.Directory(Q/'work/CONTROLLED_INNER_PATH_ONLY',inner):raise AssertionError('query must fail before body')
  def provide(*args,**kwargs):
   with provider_module.Directory(Q/'work/CONTROLLED_OUTER_PATH_ONLY',Outer()) as opened:return child()
  def original(*args,**kwargs):return 'ORIGINAL_ONLY'
  state=SimpleNamespace(snapshot=original,EXPECTED_IGNORED=actual_core.EXPECTED_IGNORED,sha=actual_core.sha,file_map=actual_core.file_map,save=lambda path,value:captured.append((str(path),json.loads(json.dumps(value,allow_nan=False)))))
  namespace=dict(s=state,F=F,C=VirtualOutput('virtual/control'),A=A,Path=RealPath,datetime=datetime,timezone=timezone,hashlib=hashlib,json=json,sys=sys,time=time)
  exec(context_code,namespace);port=SimpleNamespace(Directory=provider_module.Directory,snapshot=provide);context=namespace['QualifiedObservation'](port,'CONTROLLED_PARTIAL',actual_amend);caught=None
  try:
   with context:state.snapshot(F,F)
  except BaseException as error:caught=error
  assert caught is primary and state.snapshot is original and inner.closes==1 and len(captured)==1
  record=captured[0][1];assert record['original_exception']['custom_formatter_called'] is False and record['partial_observation_complete'] is False
  partial_rows=[row for item in record['partial_directory_provenance'] for row in item['raw_handle_observations'] if row.get('complete') is False]
  assert partial_rows and all(row['failed_class']==failed_class and row['completed_classes']==([0] if failed_class==1 else [0,1]) for row in partial_rows)
  data=BaseException.__dict__['__dict__'].__get__(primary);assert [row['handle'] for row in data['directory_snapshot_custody']]==[404,101] and data['directory_snapshot_secondary_exc_info'][0][1] is secondary
  assert data['handle_qualification_primary_exc_info'][1] is primary and data['handle_qualification_secondary_exc_infos']==()
  partials.append(dict(id='DS2_partial_class_'+str(failed_class)+'_through_exact_current_caller',passed=True,exact_primary_identity=True,all_inner_outer_custodians_preserved=True,inner_close_attempts=1,raw_partial_query_rows_retained=True,capture=record,synthetic_not_native=True))
report=dict(classification='EXACT_ACTUAL_BINDING_LOADER_AND_PARTIAL_PROVIDER_COMPOSITION_CONTROLS',amendment_sha256=actual_core.sha(A),runner_sha256=actual_core.sha(C/'run_handle_qualified.py'),launcher_sha256=actual_core.sha(C/'execute_handle_qualified_once.py'),loader_cases=ids,loader_case_count=len(ids),explicit_guard_cases=guard_results,partial_provider_cases=partials,total_cases=len(ids)+len(guard_results)+len(partials),actual_approval_file_created=False,no_actual_provider_snapshot_or_native_or_coordinator_or_canonical_execution=True,full_product_acceptance=False)
actual_core.save(R/'COMPOSITION-CONTROLS.json',report);print(json.dumps(dict(loader_cases=len(ids),explicit_guard_cases=len(guard_results),partial_provider_cases=len(partials),total_cases=report['total_cases'],all_passed=True,amendment_sha256=report['amendment_sha256'])))
