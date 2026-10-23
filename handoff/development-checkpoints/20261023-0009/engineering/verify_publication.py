"""Future publication gate: exact reviewed packet and closed preparation, no writes."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path
import json
import checkpoint_core as c
import exact_git_scope as e
from verify_prepared import audit
from taar.orchestration_graph import compile_graph
from taar.orchestration_runtime import OrchestrationRuntime

def audit_publication():
    raw,pin=c.stable(e.PACKET);packet_pin=pin['sha256'];spec=e.packet(packet_pin)
    prepared_run=OrchestrationRuntime(c.C).verify(c.RUN)
    assert prepared_run['allowed'] and prepared_run['receipts_valid'] and prepared_run['terminal_success'] is True and all(state=='SUCCEEDED' for state in prepared_run['states'].values()),'preparation is not actually closed and accepted'
    assert c.sha((c.W/'WORK-FREEZE.json').read_bytes())==spec['work_freeze_sha256']
    assert c.sha((c.W/'prepared-0002/PREPARED.json').read_bytes())==spec['prepared_sha256']
    prepared=json.loads((c.W/'prepared-0002/PREPARED.json').read_bytes());assert spec['commit']==prepared['commit'],'reviewed publication packet commit differs from prepared commit'
    outcome=audit(spec['final_input_sha256'])
    graph=compile_graph(Path('T:/'),e.CONTROL);assert graph.fingerprint==spec['graph_fingerprint']
    assert graph.nodes['integrate']['write_scope']==spec['git_scope'];e.validate_declarations(spec['git_scope'],spec['pack_id'])
    state=json.loads((e.CONTROL/c.PUBLICATION_RUN/'state.json').read_bytes());review=state['nodes']['review'];assert review['state']=='SUCCEEDED' and review['decision']=='approved'
    receipt=json.loads((e.CONTROL/c.PUBLICATION_RUN/review['receipt_ref']).read_bytes());assert receipt['result']['publication_packet_sha256']==packet_pin and receipt['result']['work_freeze_sha256']==spec['work_freeze_sha256']
    module=c.engine();refs=dict(row.split(' ',1) for row in module.git(c.F,['for-each-ref','--format=%(refname) %(objectname)']).decode().splitlines())
    assert refs[c.REF]==refs['refs/remotes/origin/development/checkpoints']==c.PARENT
    assert module.git(c.F,['ls-remote','--refs','origin',c.REF]).decode().splitlines()==[c.PARENT+'\t'+c.REF]
    module.git(c.F,['merge-base','--is-ancestor',c.HEAD,c.PARENT])
    pack=next(Path(name) for name in prepared['pack_files'] if name.endswith('.pack'))
    assert pack.stem=='checkpoint-'+spec['pack_id'] and c.stable(pack)[1]['sha256']==prepared['pack_files'][str(pack)]
    assert all(not (c.F/'.git/objects/pack'/('pack-'+spec['pack_id']+'.'+suffix)).exists() for suffix in ('pack','idx','rev'))
    assert not (e.CONTROL/'INTEGRATION-START.json').exists(),'one publication attempt was already consumed'
    hook=c.F/'.git/hooks/pre-push';assert c.stable(hook)[1]['sha256']==spec['pre_push_hook_sha256'] and b'git lfs pre-push' in hook.read_bytes()
    return dict(status='PASS',publication_packet_sha256=packet_pin,prepared=outcome,exact_git_declarations=17,actual_publication='NOT_RUN_BY_GATE',ordinary_hook_required=True,full_product_acceptance=False)
if __name__=='__main__':print(json.dumps(audit_publication(),indent=2))
