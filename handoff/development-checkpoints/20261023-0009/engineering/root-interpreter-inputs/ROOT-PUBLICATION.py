"""Root ordinary gates, exact Git claim, one publication, and evidence-backed closure."""
import os,sys
if sys.flags.optimize != 0:
 raise RuntimeError('CP9 requires unoptimized Python before imports or effects')
os.environ.pop('PYTHONOPTIMIZE',None)
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');P=F/'.agents/runtime/oq23/cp9';BASE=P/'control';C=P/'publication-control';W=P/'work';Q=P/'publication-packet';RUN='ceta-cp9-publication-20261023'
os.environ.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import checkpoint_core as c,exact_git_scope as e
from taar.orchestration_runtime import OrchestrationRuntime

def load(packet_pin):
 spec=e.packet(packet_pin)
 assert spec['root_execution_control']['path']==str(Path(__file__)) and spec['root_execution_control']['sha256']==c.sha(Path(__file__).read_bytes())
 assert spec['lease_audit_source']['sha256']==c.sha(Path(spec['lease_audit_source']['path']).read_bytes())
 review=json.loads(Path(spec['lease_audit_review']['path']).read_bytes());assert c.sha(Path(spec['lease_audit_review']['path']).read_bytes())==spec['lease_audit_review']['sha256'] and review['decision']=='approved' and review['source_sha256']==spec['lease_audit_source']['sha256']
 assert c.sha((W/'WORK-FREEZE.json').read_bytes())==spec['work_freeze_sha256']
 module_spec=importlib.util.spec_from_file_location('_exact_current_checkpoint_lease_audit',spec['lease_audit_source']['path']);lease=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(lease)
 return spec,lease

def current(spec,packet_pin):
 import publish_checkpoint as publisher
 return publisher.current_claim(spec,packet_pin)

def main():
 a=argparse.ArgumentParser();a.add_argument('--packet-sha256',required=True);a.add_argument('--action',choices=('release','claim','execute','close'),required=True);a.add_argument('--review-manifest-sha256');ns=a.parse_args();pin=ns.packet_sha256;spec,lease=load(pin);rt=OrchestrationRuntime(C)
 if ns.action=='release':
  assert ns.review_manifest_sha256 and c.sha((P/'publication-review/MANIFEST.json').read_bytes())==ns.review_manifest_sha256
  check=json.loads((C/'ROOT-PUBLICATION-REVIEW-PREFLIGHT.json').read_bytes());assert check['decision']=='PASS_EXACT_PUBLICATION_REVIEW' and check['publication_packet_sha256']==pin and check['review_manifest_sha256']==ns.review_manifest_sha256
  v=rt.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['states']['review']=='SUCCEEDED' and v['states']['validate']=='READY'
  a=rt.claim(RUN,'validate','/root',workspace=Q);assert a['allowed'];c.save(C/'ROOT-validate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a))
  a=rt.run_gate(RUN,'validate');c.save(C/'ROOT-validate-gate-api.json',dict(api='OrchestrationRuntime.run_gate',response=a));assert a['allowed'] and a['states']['validate']=='SUCCEEDED'
 elif ns.action=='claim':
  assert not (C/'ROOT-integrate-claim-api.json').exists() and not (C/'INTEGRATION-START.json').exists()
  v=rt.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['states']['validate']=='SUCCEEDED' and v['states']['integrate']=='READY'
  audit=lease.audit();c.save(C/'ROOT-PRECLAIM-LEASE-AUDIT.json',audit);assert audit['clear_for_exact_Git_publication']
  exact=e.ExactCheckpointRuntime(C,pin);a=exact.claim(RUN,'integrate','/root',workspace=F/'.git');assert a['allowed'];c.save(C/'ROOT-integrate-claim-api.json',dict(api='ExactCheckpointRuntime.claim after ordinary stock admission',response=a))
  claim=current(spec,pin);c.save(C/'ROOT-OWN-PUBLICATION-CLAIM.json',dict(publication_packet_sha256=pin,graph_fingerprint=spec['graph_fingerprint'],claims_path=str(C/RUN/'claims.json'),claim=claim))
 elif ns.action=='execute':
  assert not (C/'INTEGRATION-START.json').exists() and not (C/'ROOT-EXECUTE-ENTERED.json').exists(),'one publication wrapper invocation only'
  claim=current(spec,pin);own=json.loads((C/'ROOT-OWN-PUBLICATION-CLAIM.json').read_bytes());assert own['claim']==claim and own['publication_packet_sha256']==pin
  audit=lease.audit(own);c.save(C/'ROOT-IMMEDIATE-PUBLICATION-LEASE-AUDIT.json',audit);assert audit['clear_for_exact_Git_publication']
  c.save(C/'ROOT-EXECUTE-ENTERED.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),publication_packet_sha256=pin,claim=claim,lease_audit_sha256=c.sha((C/'ROOT-IMMEDIATE-PUBLICATION-LEASE-AUDIT.json').read_bytes()),canonical_Git_writes_at_marker=False))
  import publish_checkpoint as publisher
  publisher.publish(pin)
 elif ns.action=='close':
  assert not (C/'ROOT-PUBLICATION-COMPLETION.json').exists() and not (C/'integrate-receipt.json').exists(),'no completion replay'
  process=json.loads((C/'PUBLICATION-EXECUTION-PROCESS.json').read_bytes());result=json.loads((C/'INTEGRATION-RESULT.json').read_bytes());post=json.loads((C/'INDEPENDENT-PUBLICATION-POSTCHECK.json').read_bytes());claim=current(spec,pin)
  assert process['actual_process_exit_status']==0 and process['argv'][-4:]==['--packet-sha256',pin,'--action','execute']
  assert result['commit']==spec['commit'] and result['parent']==spec['parent'] and result['ref']==spec['ref'] and result['attempt_count']==1 and result['push_succeeded'] and result['anonymous_readback'] and result['canonical_source_index_HEAD_unchanged'] and result['existing_objects_unchanged'] and result['unrelated_refs_unchanged'] and result['outside_exact_scope']==[]
  assert 'error' not in result and 'postcheck_error' not in result and result['remote_readback']==[spec['commit']+'\t'+spec['ref']] and len(result['anonymous_samples'])==4 and all(x['status']==200 for x in result['anonymous_samples'])
  assert post['decision']=='PASS_EXACT_CHECKPOINT_PUBLICATION' and post['reviewer']=='/root/checkpoint_review_current' and post['publication_packet_sha256']==pin and post['process_sha256']==c.sha((C/'PUBLICATION-EXECUTION-PROCESS.json').read_bytes()) and post['result_sha256']==c.sha((C/'INTEGRATION-RESULT.json').read_bytes())
  exact=e.ExactCheckpointRuntime(C,pin)
  receipt=dict(schema_version=1,run_id=RUN,node_id='integrate',executor_id='/root',started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=claim['input_hash'],changed_files=[e.PREFIX+'/'+x for x in result['observed_changed_Git_paths']],result=dict(publication_packet_sha256=pin,work_freeze_sha256=spec['work_freeze_sha256'],commit=spec['commit'],ref=spec['ref'],push_succeeded=True,anonymous_readback=True,independent_postcheck_sha256=c.sha((C/'INDEPENDENT-PUBLICATION-POSTCHECK.json').read_bytes()),ordinary_pre_push_hook=True,original_C1_integration_remains_FAILED=True,canonical_source_index_HEAD_preserved=True,full_product_acceptance=False),commands=[dict(command=subprocess.list2cmdline(process['argv']),exit_status=0)],validations=[dict(name='Exact prepared descendant, hook-enabled push, remote and four anonymous public readbacks, independent preservation postcheck',passed=True)],exit_status=0)
  c.save(C/'integrate-receipt.json',receipt);a=exact.complete(RUN,'integrate',C/'integrate-receipt.json');assert a['allowed'];c.save(C/'ROOT-integrate-complete-api.json',dict(api='ExactCheckpointRuntime.complete with ordinary receipts/snapshot checks',response=a))
  v=exact.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['terminal_success'] and all(x=='SUCCEEDED' for x in v['states'].values());c.save(C/'verify-final-api.json',dict(api='ExactCheckpointRuntime.verify',response=v));c.save(C/'ROOT-PUBLICATION-COMPLETION.json',dict(run_id=RUN,publication_packet_sha256=pin,commit=spec['commit'],ref=spec['ref'],terminal_success=True,all_actual_nodes_succeeded=True,ordinary_hook_enabled=True,remote_public_readbacks_verified=True,verification_sha256=c.sha((C/'verify-final-api.json').read_bytes()),old_C1_remains_FAILED=True,full_product_acceptance=False,completion_percentage=None))
 print(json.dumps(dict(action=ns.action,status='PASS',publication_packet_sha256=pin,commit=spec['commit'],full_product_acceptance=False)))
if __name__=='__main__':main()
