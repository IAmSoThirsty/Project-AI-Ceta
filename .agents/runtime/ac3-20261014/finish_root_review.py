"""Approve the bounded environment/cleanup successor without claiming isolation."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parent;D=R/'independent-root-review'
sys.path.insert(0,str(R));import ac3_support as s
Q=s.Q;RUN=s.RUN
read=lambda path:json.loads(path.read_text())
main=read(R/'root-r1/RESULT.json');adverse=read(R/'ADVERSE-QUALIFICATION-ROOT.json');conservation=read(D/'CONSERVATION.json')
assert main['tests_run']==64 and main['exit_status']==0 and not main['failures'] and not main['errors'] and not main['skipped']
assert len(main['native_process_lifetimes'])==13 and main['all_recorded_lifetimes_closed']
assert not main['forbidden_calls'] and not main['remaining_new_threads'] and not main['actual_profile_mutations']
assert main['candidate_before']==main['candidate_after'] and main['source_before']==main['source_after']
assert adverse['exit_status']==0 and adverse['all_original_method_bodies_and_raw_IDs_retained']
assert not adverse['profile_or_restricted_creation_executed']
assert conservation['candidate_before']==conservation['candidate_after']
manifest=read(Q/'TRANSFER-MANIFEST.json')
assert len(manifest['payloads'])==294 and all(s.ordinary(Q/name)==row for name,row in manifest['payloads'].items())
report={'at':s.utc(),'decision':'approved','reviewer':'/root','author':'/root/wt1_reviewer',
 'scope':'Bounded six-key environment and native allocation cleanup library; positive isolation remains unqualified.',
 'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'main':s.reference(R/'root-r1/RESULT.json'),
 'adverse':s.reference(R/'ADVERSE-QUALIFICATION-ROOT.json'),'conservation':s.reference(D/'CONSERVATION.json'),
 'verified':['Personally read all AC2-to-AC3 source changes,new15 native/negative tests, existing cleanup call sites, exact old adverse oracle and updated contract.',
  'SHGetKnownFolderPath uses observed FOLDERID_LocalAppData/current-user/0x4000 DONT_VERIFY without CREATE or INIT. The six-key environment excludes arbitrary ambient variables.',
  'Returned known allocations are freed once; unknown query/free effects retain UNCERTAIN custody and do not block independent known cleanup. Primary errors survive.',
  'Independent64 main and3 byte-exact adverse methods pass.13 recorded ordinary job lifetimes closed; profile/CreateProcess restrictions were guarded and never called.',
  'Candidate294 and Source290 retain their native identities and hashes.'],
 'primary_API_sources':['https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetknownfolderpath',
  'https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/ne-shlobj_core-known_folder_flag'],
 'deferred_original_case':main['deferred_original_case'],
 'limits':['One original actual restricted-launch case was explicitly deferred. This is67 scoped passes, not a full old53 cohort or positive isolation qualification.',
  'Error203 cause remains unestablished. The environment addition is a candidate correction; no restricted launch retried in this review.',
  'A new exact tool/profile attempt requires fresh explicit host approval. Runtime activation, genuine owner authority and effect acceptance remain closed.'],
 'Source_application':False,'isolation_qualified':False}
s.write_new(D/'REPORT.json',report)
claim=read(R/RUN/'claims.json')['review'];assert claim['executor_id']=='/root'
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
from taar.orchestration_receipts import validate_receipt
assert _changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')))==[]
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':'/root',
 'started_at':claim['claimed_at'],'finished_at':s.utc(),'input_hash':claim['input_hash'],'changed_files':[],
 'result':{'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'report':s.reference(D/'REPORT.json'),
   'tests_run':67,'isolation_qualified':False,'deferred_original_case':main['deferred_original_case']},
 'commands':[{'command':str(s.PY)+' -B -X utf8 '+str(R/'root_review_r2.py'),'exit_status':0}],
 'validations':[{'name':'67_scoped_methods_and_complete_known_native_closure','passed':True},
   {'name':'frozen_payloads_conserved_and_live_isolation_explicitly_unqualified','passed':True}], 'exit_status':0,'decision':'approved'}
validate_receipt(receipt,run_id=RUN,node_id='review',executor_id='/root',input_hash=claim['input_hash'],
 claimed_at=claim['claimed_at'],node=read(R/RUN/'graph.json')['graph']['nodes']['review'])
s.write_new(D/'review.json',receipt);s.invoke(['node','complete',RUN,'review',str(D/'review.json')],'root-review-complete')
state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json');stored=read(R/RUN/'receipts/review.json')
assert state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={}
assert all(stored[key]==value for key,value in receipt.items())
s.write_new(D/'ACTUAL-READBACK.json',{'at':s.utc(),'state':state,'claims':claims,'exact13_fields':True})
s.write_new(D/'SEAL.json',{'at':s.utc(),'members':{p.name:s.reference(p) for p in D.iterdir() if p.is_file()}})
print(json.dumps({'decision':'approved','tests':67,'claims':claims,'isolation_qualified':False,'review_sha256':s.sha(D/'review.json')}),flush=True)
