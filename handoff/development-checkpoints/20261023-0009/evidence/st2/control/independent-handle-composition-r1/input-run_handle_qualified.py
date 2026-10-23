"""Exact additive F-only observation for the already reviewed four-target ST2 cut."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,os,runpy,sys,time
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work';A=C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
if sys.flags.optimize:raise RuntimeError('OPTIMIZED_INTERPRETER_REFUSED')
import status_core as s,run_status as r
from taar.orchestration_runtime import OrchestrationRuntime

def load(pin):
 a=json.loads(A.read_bytes());assert a['prepared_manifest_sha256']==pin and a['runner_sha256']==s.sha(Path(__file__))
 assert s.sha(W/'MANIFEST.json')==pin and a['original_status_core_sha256']==s.sha(W/'status_core.py')
 decision=json.loads((C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json').read_bytes())
 assert decision['decision']=='APPROVED_EXACT_F_ONLY_HANDLE_QUALIFICATION' and decision['reviewer']=='/root/status_packet_review' and decision['amendment_sha256']==s.sha(A) and decision['runner_sha256']==s.sha(Path(__file__)) and decision['launcher_sha256']==s.sha(C/'execute_handle_qualified_once.py')
 for name,h in a['support_pins'].items():assert s.sha(Path(name))==h,('qualification support drift',name)
 ds_root=F/'.agents/runtime/oq23/ds2'
 for field in ('qualification_closure','qualification_verification','source_provider'):
  path=Path(a[field]);assert path.is_relative_to(ds_root) and str(path) in a['support_pins'],('qualification path outside exact pinned DS2',field)
 assert a['qualification_graph_fingerprint']=='997829e1616609bafc88eea12f601eba7d715ad0e03b27e55a3f1af59a0d51ed'
 ds=json.loads(Path(a['qualification_closure']).read_bytes());assert ds['run_id']=='ceta-ds23-r2-gate-r2' and ds['terminal_success'] and ds['canonical_or_installed_mutation'] is False
 verification=json.loads(Path(a['qualification_verification']).read_bytes())['response'];assert verification['run_id']=='ceta-ds23-r2-gate-r2' and verification['graph_fingerprint']==a['qualification_graph_fingerprint'] and verification['terminal_success'] and verification['receipts_valid'] and all(x=='SUCCEEDED' for x in verification['states'].values())
 assert a['source_provider']==str(F/'.agents/runtime/oq23/ds2/work/directory_snapshot.py')
 spec=importlib.util.spec_from_file_location('_accepted_ds2_directory_provider',a['source_provider']);provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)
 assert provider.EXPECTED_IGNORED==s.EXPECTED_IGNORED and provider.F==F
 return a,provider
class QualifiedObservation:
 def __init__(self,provider,action,amendment):self.provider=provider;self.action=action;self.amendment=amendment;self.count=0
 def __enter__(self):
  self.original=s.snapshot;self.directory=C/('handle-observations-'+self.action);self.directory.mkdir(exist_ok=False)
  def observed(workspace,graph_root,ignored=s.EXPECTED_IGNORED):
   if Path(workspace)!=F:return self.original(workspace,graph_root,ignored=ignored)
   assert Path(graph_root)==F and ignored==s.EXPECTED_IGNORED
   self.count+=1;started=time.perf_counter_ns()
   try:observation=self.provider.snapshot(F,F,ignored=ignored)
   except BaseException:
    primary=sys.exc_info();error=primary[1];storage=BaseException.__dict__['__dict__'].__get__(error)
    try:
     partial=[];trace=primary[2]
     while trace is not None:
      frame=trace.tb_frame
      for local_name in ('opened','self'):
       item=frame.f_locals.get(local_name)
       directory_type=vars(self.provider).get('Directory')
       if isinstance(directory_type,type) and isinstance(item,directory_type):
        state=object.__getattribute__(item,'__dict__')
        partial.append(dict(function=frame.f_code.co_name,source=frame.f_code.co_filename,line=trace.tb_lineno,path=str(state['path']),raw_path_observations=state.get('raw_paths',[]),raw_handle_observations=state.get('raw_handles',[]),entered=state.get('entered'),closed=state.get('closed')))
      trace=trace.tb_next
     args=BaseException.__dict__['args'].__get__(error)
     descriptor=dict(type=type.__getattribute__(type(error),'__name__'),args=[x if type(x) in (str,int,bool,type(None)) else dict(type=type.__getattribute__(type(x),'__name__')) for x in args],custom_formatter_called=False)
     s.save(self.directory/('failure-%03d.json'%self.count),dict(recorded_at=datetime.now(timezone.utc).isoformat(),amendment_sha256=s.sha(A),provider_sha256=s.sha(Path(self.amendment['source_provider'])),elapsed_ns=time.perf_counter_ns()-started,original_exception=descriptor,partial_directory_provenance=partial,partial_observation_complete=False,full_product_acceptance=False))
    except BaseException:
     retained=dict.get(storage,'handle_qualification_diagnostic_secondary_exc_infos',())
     dict.__setitem__(storage,'handle_qualification_diagnostic_secondary_exc_infos',tuple(retained)+(sys.exc_info(),))
    raise
   assert observation['policy']['ignored_directory_names']==sorted(s.EXPECTED_IGNORED) and observation['policy']['ignored_root_relative_subtree']=='.project-ai/automation'
   file_map=s.file_map(observation);raw_provenance=observation['directory_observations'];raw_path=self.directory/('native-%03d.json'%self.count)
   s.save(raw_path,dict(directory_observations=raw_provenance,policy=observation['policy'],atomic_filesystem_snapshot=False))
   s.save(self.directory/('summary-%03d.json'%self.count),dict(recorded_at=datetime.now(timezone.utc).isoformat(),amendment_sha256=s.sha(A),provider_sha256=s.sha(Path(self.amendment['source_provider'])),files=len(file_map),directories=len(observation['directories']),file_map_sha256=hashlib.sha256(json.dumps(file_map,sort_keys=True,separators=(',',':')).encode()).hexdigest(),raw_directory_provenance_path=str(raw_path),raw_directory_provenance_sha256=s.sha(raw_path),all_ordinary_file_native_hash_checks_unchanged=True,ignored_policy_unchanged=True,access_time_values_preserved_reference_only=True,canonical_or_installed_mutation=False))
   return observation
  self.observed=observed;s.snapshot=observed;return self
 def __exit__(self,kind,error,traceback):
  secondary=[];changed=s.snapshot is not self.observed
  try:s.snapshot=self.original
  except BaseException:secondary.append(sys.exc_info())
  if changed:
   try:raise RuntimeError('HANDLE_QUALIFIED_SNAPSHOT_CALLER_REPLACED; original restore attempted')
   except BaseException:secondary.append(sys.exc_info())
  if error is not None:
   storage=BaseException.__dict__['__dict__'].__get__(error);dict.__setitem__(storage,'handle_qualification_primary_exc_info',(kind,error,traceback));dict.__setitem__(storage,'handle_qualification_secondary_exc_infos',tuple(secondary));return False
  if secondary:raise BaseException.with_traceback(secondary[0][1],secondary[0][2])
  return False

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest-sha256',required=True);p.add_argument('--action',choices=('claim-integrate','claim-evidence','apply','close'),required=True);args=p.parse_args();a,provider=load(args.manifest_sha256)
 with QualifiedObservation(provider,args.action,a):
  if args.action=='close':
   sys.argv=[str(C/'ROOT-CLOSE-R2.py'),args.manifest_sha256];runpy.run_path(str(C/'ROOT-CLOSE-R2.py'),run_name='__main__');return 0
  sys.argv=[str(W/'run_status.py'),'--manifest-sha256',args.manifest_sha256]
  if args.action.startswith('claim-'):
   node=args.action.split('-',1)[1];sys.argv+=['--lease','claim','--node',node,'--workspace',str(F if node=='integrate' else S/'delivery')]
  return r.main()
if __name__=='__main__':raise SystemExit(main())
