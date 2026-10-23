"""One independently reviewed continuation of still-READY claims; never replay release or tests."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/br3';C=B/'control';RUN='ceta-br23-r3'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path.insert(0,str(B/'work'))
import run_broader as b
from taar.orchestration_graph import compile_graph
assert len(sys.argv)==2;pin=sys.argv[1];packet,binding=b.load_prepared(pin);decision=json.loads((C/'INDEPENDENT-ADMISSION-CONTINUATION.json').read_bytes())
assert decision['reviewer']=='/root/independent_broader_review' and decision['decision']=='APPROVED_ONE_MISSING_CLAIM_CONTINUATION' and decision['script_sha256']==b.sha(Path(__file__)) and decision['manifest_sha256']==pin
assert decision['failed_release_process_sha256']==b.sha(C/'ROOT-RELEASE-PROCESS.json') and decision['canonical_test_bodies_executed']==0 and decision['original_failure_scalars']=='NOT_CAPTURED'
old_process=json.loads((C/'ROOT-RELEASE-PROCESS.json').read_bytes());assert old_process['actual_process_exit_status']==1
assert not (C/'EXECUTION-INTENT.json').exists() and not any((B/'delivery').iterdir()) and not (C/'ADMISSION-CONTINUATION-INTENT.json').exists()
state=json.loads((C/RUN/'state.json').read_bytes());retained=json.loads((C/RUN/'claims.json').read_bytes());expected={'integrate','fixture_0','fixture_1'}
assert set(retained)==expected and decision['retained_claims']==sorted(expected)
assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved' and state['nodes']['validate']['state']=='SUCCEEDED' and state['nodes']['validate']['validation_passed']
runtime=b.BoundRuntime(binding);graph=compile_graph(Path('T:/'),C)
assert graph.fingerprint==binding['graph_fingerprint'] and runtime.verify(RUN)['receipts_valid']
for node,claim in retained.items():
 assert claim['executor_id']=='/root' and Path(claim['workspace'])==Path(binding['workspaces'][node]) and state['nodes'][node]['state']=='RUNNING' and claim==state['nodes'][node]['claim'] and claim['input_hash']==runtime._input_hash(graph,state,node) and claim['effective_write_scope']==graph.nodes[node]['write_scope']
missing=['fixture_2','fixture_3','fixture_4','fixture_5','js9'];assert decision['missing_claims']==missing
assert all(state['nodes'][node]['state']=='READY' and state['nodes'][node]['claim'] is None for node in missing)
source=b.source_observation(binding)
b.r.save(C/'ADMISSION-CONTINUATION-INTENT.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),manifest_sha256=pin,script_sha256=b.sha(Path(__file__)),independent_decision_sha256=b.sha(C/'INDEPENDENT-ADMISSION-CONTINUATION.json'),failed_release_preserved=b.sha(C/'ROOT-RELEASE-PROCESS.json'),retained_claims=retained,missing_claims=missing,maximum_continuations=1,replay_gate_release_bootstrap_or_tests=False,source_before=source,canonical_test_bodies_executed=0,full_product_acceptance=False))
for node in missing:
 response=runtime.claim(RUN,node,'/root',workspace=Path(binding['workspaces'][node]));assert response['allowed'];b.r.save(C/('ROOT-'+node+'-continuation-claim-api.json'),dict(api='BoundRuntime.claim unchanged installed transitions and reviewed complete observation',response=response))
claims=b.require_live(binding);assert all(claims[node]==claim for node,claim in retained.items());assert b.source_observation(binding)==source
b.r.save(C/'ROOT-RELEASE-READY.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),prepared_manifest_sha256=pin,review_manifest_sha256=b.sha(B/'review/MANIFEST.json'),exact_claims=list(claims),actual_gate_succeeded=True,source562_Git_index_native_unchanged=True,actual_logical_execution_leases=8,sequential_suite_driver=True,bounded_disposable_Python_custody_helpers=True,failed_original_release_process_preserved=b.sha(C/'ROOT-RELEASE-PROCESS.json'),independently_reviewed_single_missing_claim_continuation=True,canonical_test_bodies_executed=0,native_worker_or_live_profile_qualification=False,full_product_acceptance=False))
print(json.dumps(dict(ready=True,claims=list(claims),failed_original_release_process='PRESERVED_EXIT1',continuations=1,canonical_test_bodies_executed=0,manifest_sha256=pin)))
