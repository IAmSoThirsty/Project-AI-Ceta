"""Freeze exact composition proofs, then create the explicitly authorized approval once."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work';Q=F/'.agents/runtime/oq23/ds2';R=C/'independent-handle-composition-r1';A=C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json';APPROVAL=C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json'
APIN='3d2edaa37528d2d38d6cb7ecace953eebfbef6c8dde4f221c0c5c1866eda640f';RUNNER='0923c3b1ec7081489d8c9f4dcee17083b3df6d65801215d6c4b27a288640bbf8';LAUNCHER='727a150fc63889a1a1cb9b158f90a99adbf76388edeef4c6b3224d232bfb498d';PREP='5729a01e71127efd8d9970e8b5d1405f9b297eb12e421e94946983f125c6ff32'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path[:0]=[str(W),str(Q/'work')]
import status_core as s,conservation
assert s.sha(A)==APIN and s.sha(C/'run_handle_qualified.py')==RUNNER and s.sha(C/'execute_handle_qualified_once.py')==LAUNCHER
assert not APPROVAL.exists();review=json.loads((R/'REVIEW.json').read_bytes());assert review['decision']=='APPROVED_EXACT_F_ONLY_HANDLE_QUALIFICATION' and review['amendment_sha256']==APIN
assert json.loads((R/'ACTUAL-READBACK-PROCESS.json').read_bytes())['actual_process_exit_status']==1
for name in ('ACTUAL-READBACK-R2-PROCESS.json','COMPOSITION-CONTROLS-PROCESS.json'):assert json.loads((R/name).read_bytes())['actual_process_exit_status']==0
controls=json.loads((R/'COMPOSITION-CONTROLS.json').read_bytes());assert controls['total_cases']==21 and all(item['passed'] for key in ('loader_cases','explicit_guard_cases','partial_provider_cases') for item in controls[key])
a=json.loads(A.read_bytes());assert a['prepared_manifest_sha256']==s.sha(W/'MANIFEST.json')==PREP
for path,pin in a['support_pins'].items():assert s.sha(Path(path))==pin
packet=json.loads((S/'packet/INPUTS.json').read_bytes());assert a['scope']['canonical_targets']==packet['targets']
for rel,pin in packet['target_before_sha256'].items():assert s.sha(F/rel)==pin
for rel in packet['temporary_paths']:assert not (F/rel).exists()
state=json.loads((C/'ceta-st23-r2/state.json').read_bytes());assert state['nodes']['integrate']['state']==state['nodes']['evidence']['state']=='READY' and not json.loads((C/'ceta-st23-r2/claims.json').read_bytes())
assert not any((S/'delivery').iterdir()) and not (C/'EXECUTION-INTENT.json').exists()
for action in ('claim-integrate','claim-evidence','apply','close'):assert not (C/('handle-observations-'+action)).exists()
conservation.observe()
approval=dict(schema_version=1,recorded_at=datetime.now(timezone.utc).isoformat(),decision='APPROVED_EXACT_F_ONLY_HANDLE_QUALIFICATION',reviewer='/root/status_packet_review',amendment_sha256=APIN,runner_sha256=RUNNER,launcher_sha256=LAUNCHER,prepared_manifest_sha256=PREP,review_reference=dict(repository_relative_path=(R/'REVIEW.json').relative_to(F).as_posix(),path=str(R/'REVIEW.json'),sha256=s.sha(R/'REVIEW.json')),proof_manifest_path=str(R/'MANIFEST.json'),execution=review['allowed_execution'],qualification_run_id=a['qualification_run_id'],qualification_graph_fingerprint=a['qualification_graph_fingerprint'],original_failures_preserved=True,no_generic_retry=True,full_product_acceptance=False)
s.save(R/'APPROVAL-OUTPUT.json',approval);approval_bytes=(R/'APPROVAL-OUTPUT.json').read_bytes();approval_pin=s.sha(R/'APPROVAL-OUTPUT.json')
full=s.snapshot(R,F,ignored=frozenset());assert full['excluded_symlinks']=={};base=R.relative_to(F);leaves={Path(name).relative_to(base).as_posix():native for name,native in full['files'].items()};assert 'MANIFEST.json' not in leaves
external=dict(a['support_pins']);external[str(A)]=APIN;external[str(C/'run_handle_qualified.py')]=RUNNER;external[str(C/'execute_handle_qualified_once.py')]=LAUNCHER
for base,mf,key in [(W,W/'MANIFEST.json','work_hashes'),(S/'review',S/'review/MANIFEST.json','files'),(Q/'work',Q/'work/MANIFEST.json','files'),(Q/'review-r2',Q/'review-r2/MANIFEST.json','files')]:
 m=json.loads(mf.read_bytes());external[str(mf)]=s.sha(mf);external.update(m['external_pins'])
 for rel,item in m[key].items():external[str(base/rel)]=item['sha256'] if type(item) is dict else item
prior=C/'independent-handle-callers-r3';pm=json.loads((prior/'MANIFEST.json').read_bytes());external[str(prior/'MANIFEST.json')]=s.sha(prior/'MANIFEST.json')
for rel,pin in pm['files'].items():external[str(prior/rel)]=pin
peer=C/'independent-amendment-generator-r2';pm=json.loads((peer/'MANIFEST.json').read_bytes());external[str(peer/'MANIFEST.json')]=s.sha(peer/'MANIFEST.json')
for rel,pin in pm['files'].items():external[str(peer/rel)]=pin['sha256']
for stem in (C/'ROOT-BUILD-HANDLE-BINDING',Q/'control-r2/ROOT-QUALIFICATION-CLOSE'):
 for suffix in ('-PROCESS.json','.stdout','.stderr'):
  path=Path(str(stem)+suffix);external[str(path)]=s.sha(path)
for name in ('discover','plan','implement','review','validate','integrate'):
 path=Q/'control-r2/ceta-ds23-r2-gate-r2/receipts'/(name+'.json');external[str(path)]=s.sha(path)
for name in ('review','validate'):
 path=C/'ceta-st23-r2/receipts'/(name+'.json');external[str(path)]=s.sha(path)
external[str(C/'BUILD-HANDLE-EXECUTION-AMENDMENT.py')]=s.sha(C/'BUILD-HANDLE-EXECUTION-AMENDMENT.py')
# The four explicitly authorized mutation inputs are before-state evidence, not immutable future-file claims.
authorized={str(F/rel):dict(before_sha256=pin,candidate_sha256=json.loads((W/'BINDING.json').read_bytes())['targets'][rel]['candidate_sha256']) for rel,pin in packet['target_before_sha256'].items()}
for path in list(external):
 if Path(path) in {Path(name) for name in authorized}:assert external.pop(path)==authorized[str(Path(path))]['before_sha256']
for path,pin in external.items():assert s.sha(Path(path))==pin
external[str(APPROVAL)]=approval_pin
manifest=dict(decision=review['decision'],reviewer=review['reviewer'],amendment_sha256=APIN,runner_sha256=RUNNER,launcher_sha256=LAUNCHER,review_sha256=s.sha(R/'REVIEW.json'),approval_output_sha256=approval_pin,files={name:native['sha256'] for name,native in leaves.items()},file_native=leaves,directory_identity={name:{key:native[key] for key in ('device','inode','mode')} for name,native in full['directories'].items()},external_pins=external,authorized_mutation_inputs=authorized,explicit_exclusions=dict(self='MANIFEST.json; exact handoff SHA256',live_coordinator_state_not_external_pinned=True,canonical_four_before_state_and_candidate_pins='Explicit authorized_mutation_inputs; all other immutable pins retained'),preserved_guarded_API_transient_lock_effect=True,no_generic_retries=True,reviewer_canonical_execution=False,full_product_acceptance=False)
s.save(R/'MANIFEST.json',manifest)
for rel,pin in manifest['files'].items():assert s.sha(R/rel)==pin
assert s.sha(A)==APIN and s.sha(C/'run_handle_qualified.py')==RUNNER and s.sha(C/'execute_handle_qualified_once.py')==LAUNCHER
for rel,pin in packet['target_before_sha256'].items():assert s.sha(F/rel)==pin
assert not json.loads((C/'ceta-st23-r2/claims.json').read_bytes()) and not any((S/'delivery').iterdir()) and not (C/'EXECUTION-INTENT.json').exists()
with APPROVAL.open('xb') as stream:assert stream.write(approval_bytes)==len(approval_bytes);stream.flush();os.fsync(stream.fileno())
assert s.sha(APPROVAL)==approval_pin
for path,pin in external.items():assert s.sha(Path(path))==pin
print(json.dumps(dict(decision=approval['decision'],approval_path=str(APPROVAL),approval_sha256=approval_pin,composition_manifest_sha256=s.sha(R/'MANIFEST.json'),composition_review_sha256=s.sha(R/'REVIEW.json'),frozen_files_excluding_manifest=len(leaves),external_pins=len(external),authorized_mutation_inputs=len(authorized),amendment_sha256=APIN,runner_sha256=RUNNER,launcher_sha256=LAUNCHER,exact_single_claims_and_apply_authorized=True,actual_claim_or_application_performed=False,full_product_acceptance=False)))
