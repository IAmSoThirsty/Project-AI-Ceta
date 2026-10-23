"""Root-only reviewed qualification closure; no installation or snapshot hook.

This tool remains unexecuted by the author. Its exact bytes must be approved by
the independent reviewer and bound to both supplied manifest pins before Root
runs the ordinary declared gate and delivery integration.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');B=F/'.agents/runtime/oq23/ds2'
W=B/'work';C=B/'control-r2';D=B/'delivery';R=B/'review-r2';RUN='ceta-ds23-r2-gate-r2'
GRAPH='997829e1616609bafc88eea12f601eba7d715ad0e03b27e55a3f1af59a0d51ed'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def approved_review(pin,rpin,state,receipt):
    assert sha(W/'MANIFEST.json')==pin and sha(R/'MANIFEST.json')==rpin
    review=json.loads((R/'REVIEW.json').read_bytes());rm=json.loads((R/'MANIFEST.json').read_bytes())
    assert review['decision']==rm['decision']=='approved' and review['manifest_sha256']==rm['candidate_manifest_sha256']==pin
    assert review['root_candidate_closure_sha256']==rm['root_candidate_closure_sha256']==sha(Path(__file__))
    assert rm['review_sha256']==sha(R/'REVIEW.json')
    for rel,pin_entry in rm['files'].items():
        path=R/rel;assert path.resolve().is_relative_to(R.resolve())
        expected=pin_entry['sha256'] if type(pin_entry) is dict else pin_entry
        assert sha(path)==expected
    node=state['nodes']['review'];assert node['state']=='SUCCEEDED' and node['decision']=='approved'
    assert node['executor_id']==review['reviewer'] and node['executor_id'] not in ('/root',state['nodes']['implement']['executor_id'])
    assert receipt['decision']=='approved' and receipt['executor_id']==node['executor_id']
    assert receipt['result']['manifest_sha256']==pin and receipt['result']['review_sha256']==sha(R/'REVIEW.json')
    assert receipt['result']['root_candidate_closure_sha256']==sha(Path(__file__))
    return review
def main():
    assert sys.flags.optimize==0
    parser=argparse.ArgumentParser();parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--review-manifest-sha256',required=True);args=parser.parse_args()
    sys.dont_write_bytecode=True;os.environ['GIT_OPTIONAL_LOCKS']='0'
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_graph import compile_graph
    from taar.orchestration_runtime import OrchestrationRuntime
    graph=compile_graph(Path('T:/'),C);assert graph.fingerprint==GRAPH
    rt=OrchestrationRuntime(C);v=rt.verify(RUN)
    assert v['allowed'] and v['receipts_valid'] and v['states']['review']=='SUCCEEDED' and v['states']['validate']=='READY'
    state=json.loads((C/RUN/'state.json').read_bytes());review_ref=state['nodes']['review']['receipt_ref']
    assert review_ref=='receipts/review.json'
    reviewed=approved_review(args.manifest_sha256,args.review_manifest_sha256,state,json.loads((C/RUN/review_ref).read_bytes()))
    sys.path.insert(0,str(W))
    import verify_prepared
    assert Path(verify_prepared.__file__).resolve()==(W/'verify_prepared.py').resolve()
    verify_prepared.main()
    assert not any(D.iterdir()) and not (C/'ROOT-QUALIFICATION-COMPLETION.json').exists(),'delivery/closure exists; no replay'
    a=rt.claim(RUN,'validate','/root',workspace=B/'packet-r2');assert a['allowed'];save(C/'ROOT-validate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a))
    a=rt.run_gate(RUN,'validate');save(C/'ROOT-validate-gate-api.json',dict(api='OrchestrationRuntime.run_gate',response=a))
    assert a['allowed'] and a['states']['validate']=='SUCCEEDED'
    state=json.loads((C/RUN/'state.json').read_bytes());gate=json.loads((C/RUN/'receipts/validate.json').read_bytes())
    assert gate['commands']==[dict(command=x,exit_status=0) for x in graph.nodes['validate']['commands']]
    assert gate['exit_status']==0 and state['nodes']['validate']['validation_passed'] is True
    a=rt.claim(RUN,'integrate','/root',workspace=D);assert a['allowed'];save(C/'ROOT-integrate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a))
    claim=json.loads((C/RUN/'claims.json').read_bytes())['integrate']
    assert claim['executor_id']=='/root' and claim['workspace']==str(D) and claim['effective_write_scope']==list(graph.nodes['integrate']['write_scope'])
    q=json.loads((W/'FULL-F-QUALIFICATION.json').read_bytes());controls=json.loads((W/'CONTROLS-R2.json').read_bytes())
    assert q['qualified'] and q['canonical_Git_ST2_and_original_evidence_conserved'] and controls['successful']
    accepted=dict(schema_version=1,recorded_at=datetime.now(timezone.utc).isoformat(),run_id=RUN,
        status='INDEPENDENTLY_REVIEWED_DIRECTORY_SNAPSHOT_QUALIFICATION_ONLY',source_qualification_run_id='ceta-ds23-r2',original_gate_setup_rejected=True,provider_bytes_unchanged_by_gate_metadata_successor=True,
        provider=dict(path=str(W/'directory_snapshot.py'),sha256=sha(W/'directory_snapshot.py')),
        work_manifest_sha256=args.manifest_sha256,review_manifest_sha256=args.review_manifest_sha256,
        review_sha256=sha(R/'REVIEW.json'),root_candidate_closure_sha256=sha(Path(__file__)),
        full_F_qualification_sha256=sha(W/'FULL-F-QUALIFICATION.json'),full_F_snapshot_sha256=q['snapshot_sha256'],
        controls_sha256=sha(W/'CONTROLS-R2.json'),controlled_tests=controls['tests_run'],
        access_time_policy_sha256=sha(W/'ACCESS-TIME-OBSERVATION-POLICY.json'),
        original_failed_probe_and_ST2_claims_preserved=True,
        ST2_or_canonical_or_installed_mutation=False,snapshot_override_installed=False,
        native_worker_or_AC7_activity=False,full_product_acceptance=False)
    save(D/'ACCEPTED-QUALIFICATION.json',accepted)
    changed=[(D/'ACCEPTED-QUALIFICATION.json').relative_to(Path('T:/')).as_posix()]
    receipt=dict(schema_version=1,run_id=RUN,node_id='integrate',executor_id='/root',
        started_at=claim['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),
        input_hash=claim['input_hash'],changed_files=changed,
        result=dict(accepted_qualification_sha256=sha(D/'ACCEPTED-QUALIFICATION.json'),
            manifest_sha256=args.manifest_sha256,review_manifest_sha256=args.review_manifest_sha256,
            provider_sha256=accepted['provider']['sha256'],ST2_or_canonical_or_installed_mutation=False,
            snapshot_override_installed=False,full_product_acceptance=False),commands=[],
        validations=[dict(name='Independent approved exact utility/work/review pins and declared ordinary gate succeeded; accepted qualification only',passed=True)],exit_status=0)
    save(C/'integrate-receipt.json',receipt);a=rt.complete(RUN,'integrate',C/'integrate-receipt.json');assert a['allowed']
    save(C/'ROOT-integrate-complete-api.json',dict(api='OrchestrationRuntime.complete',response=a))
    v=rt.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['terminal_success'] and all(x=='SUCCEEDED' for x in v['states'].values())
    save(C/'verify-final-api.json',dict(api='OrchestrationRuntime.verify',response=v))
    save(C/'ROOT-QUALIFICATION-COMPLETION.json',dict(run_id=RUN,terminal_success=True,
        graph_fingerprint=GRAPH,canonical_or_installed_mutation=False,
        all_actual_nodes_succeeded=True,manifest_sha256=args.manifest_sha256,
        review_manifest_sha256=args.review_manifest_sha256,accepted_qualification_sha256=sha(D/'ACCEPTED-QUALIFICATION.json'),
        verification_sha256=sha(C/'verify-final-api.json'),ST2_or_canonical_or_installed_mutation=False,
        snapshot_override_installed=False,full_product_acceptance=False))
    print(json.dumps(dict(terminal_success=True,states=v['states'],accepted_qualification_only=True,
        ST2_or_canonical_or_installed_mutation=False)))
if __name__=='__main__':main()
