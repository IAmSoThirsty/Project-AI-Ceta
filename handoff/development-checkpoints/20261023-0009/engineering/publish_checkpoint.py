"""Fresh checkpoint9 publisher. Requires later exact review/gate/claim; never replay."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,sys,urllib.request
from urllib.parse import quote
import checkpoint_core as c
import exact_git_scope as e
from verify_prepared import audit,files
from taar.orchestration_graph import compile_graph,path_matches_scope


def describe(error):
    args=BaseException.__dict__['args'].__get__(error)
    values=[a if type(a) in (str,int,bool,type(None)) else dict(type=type.__getattribute__(type(a),'__name__')) for a in args[:16]]
    return dict(type=type.__getattribute__(type(error),'__name__'),message=args[0] if len(args)==1 and type(args[0]) is str else 'SEE_PRIMITIVE_ARGS; CUSTOM_FORMATTER_NOT_CALLED',args=values,args_truncated=len(args)>16)

def current_claim(spec,packet_pin,expected=None):
    runtime=e.ExactCheckpointRuntime(e.CONTROL,packet_pin);graph=compile_graph(Path('T:/'),e.CONTROL);v=runtime.verify(c.PUBLICATION_RUN)
    assert v['allowed'] and v['receipts_valid'] and v['graph_fingerprint']==graph.fingerprint==spec['graph_fingerprint']
    state=json.loads((e.CONTROL/c.PUBLICATION_RUN/'state.json').read_bytes());claims=json.loads((e.CONTROL/c.PUBLICATION_RUN/'claims.json').read_bytes());claim=claims['integrate'];node=state['nodes']['integrate']
    assert node['state']=='RUNNING' and node['claim']==claim and claim['executor_id']=='/root' and Path(claim['workspace'])==c.F/'.git'
    assert node['effective_write_scope']==claim['effective_write_scope']==spec['git_scope'] and claim['input_hash']==runtime._input_hash(graph,state,'integrate')
    review_node=state['nodes']['review'];gate_node=state['nodes']['validate'];assert review_node['state']=='SUCCEEDED' and review_node['decision']=='approved' and gate_node['state']=='SUCCEEDED' and gate_node['validation_passed'] is True
    review=json.loads((e.CONTROL/c.PUBLICATION_RUN/review_node['receipt_ref']).read_bytes());gate=json.loads((e.CONTROL/c.PUBLICATION_RUN/gate_node['receipt_ref']).read_bytes())
    assert review['result']['publication_packet_sha256']==packet_pin and review['result']['work_freeze_sha256']==spec['work_freeze_sha256']
    assert gate['commands']==[dict(command=command,exit_status=0) for command in graph.nodes['validate']['commands']]
    assert expected is None or expected==claim
    return claim

def refs(module):return dict(row.split(' ',1) for row in module.git(c.F,['for-each-ref','--format=%(refname) %(objectname)']).decode().splitlines())
def valid_readback(raw,expected):assert len(raw)<=8_000_000 and c.sha(raw)==expected

def import_reviewed_pack(module,pack,expected_sha256):
    """Hash and consume one stable byte object at the canonical import boundary."""
    pack_bytes,_=c.stable(pack)
    if c.sha(pack_bytes)!=expected_sha256:raise RuntimeError('reviewed pack bytes changed before canonical import')
    return module.git(c.F,['index-pack','--stdin'],data=pack_bytes).decode('ascii')

def publish(packet_pin):
    spec=e.packet(packet_pin);assert c.sha((c.W/'WORK-FREEZE.json').read_bytes())==spec['work_freeze_sha256']
    audit(spec['final_input_sha256']);prepared_path=c.W/'prepared-0002/PREPARED.json';assert c.sha(prepared_path.read_bytes())==spec['prepared_sha256']
    p=json.loads(prepared_path.read_bytes());assert spec['commit']==p['commit'],'reviewed publication packet commit differs from prepared commit'
    module=c.engine();claim=current_claim(spec,packet_pin)
    pack=next(Path(name) for name in p['pack_files'] if name.endswith('.pack'));pack_id=pack.stem.removeprefix('checkpoint-');assert pack_id==spec['pack_id']
    destinations=[c.F/'.git/objects/pack'/('pack-'+pack_id+'.'+suffix) for suffix in ('pack','idx','rev')];assert all(not path.exists() for path in destinations)
    assert module.checkout_state(c.F)==p['checkout_before']
    before=json.loads((c.W/'CANONICAL-BEFORE-0002.json').read_bytes());before_refs=refs(module);tracking='refs/remotes/origin/development/checkpoints';assert before_refs[c.REF]==before_refs[tracking]==c.PARENT
    assert module.git(c.F,['ls-remote','--refs','origin',c.REF]).decode().splitlines()==[c.PARENT+'\t'+c.REF]
    hook=c.F/'.git/hooks/pre-push';hook_path=module.git(c.F,['config','--get','core.hooksPath'],allowed=(0,1)).decode().strip();assert not hook_path or Path(hook_path).resolve()==hook.parent.resolve()
    assert c.stable(hook)[1]['sha256']==spec['pre_push_hook_sha256'] and b'git lfs pre-push' in hook.read_bytes()
    git_before=files(c.F/'.git');sequence=0
    def audit_command(args,result):
        nonlocal sequence
        if any(word in args for word in ('index-pack','update-ref','push','ls-remote')):
            sequence+=1;c.save(e.CONTROL/('PUBLICATION-COMMAND-%03d.json'%sequence),dict(at=datetime.now(timezone.utc).isoformat(),argv=result.args,exit_status=result.returncode,stdout=result.stdout.decode('utf8',errors='replace'),stderr=result.stderr.decode('utf8',errors='replace')))
    result=dict(run_id=c.PUBLICATION_RUN,parent=c.PARENT,commit=p['commit'],ref=c.REF,attempt_count=1,push_succeeded=False,anonymous_readback=False,full_product_acceptance=False)
    # Create-only durable marker is written before the first possible canonical Git write.
    c.save(e.CONTROL/'INTEGRATION-START.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),publication_packet_sha256=packet_pin,prepared_sha256=spec['prepared_sha256'],work_freeze_sha256=spec['work_freeze_sha256'],claim=claim,Git_before=git_before,refs_before=before_refs,ordinary_pre_push_hook=True,old_C1_integration_remains_FAILED=True))
    primary=None;secondary=[];module.COMMAND_AUDITOR=audit_command
    try:
        current_claim(spec,packet_pin,claim)
        result['index_pack_stdout']=import_reviewed_pack(module,pack,p['pack_files'][str(pack)])
        child=c.tree(module,p['commit']);names=list(p['exports'])
        for name,raw in zip(names,module.batch_blobs(c.F,[child[name][2] for name in names],{}),strict=True):assert c.sha(raw)==p['exports'][name]['sha256']
        module.git(c.F,['merge-base','--is-ancestor',c.PARENT,p['commit']]);current_claim(spec,packet_pin,claim)
        module.git(c.F,['update-ref','--create-reflog','-m','CETA reviewed development checkpoint9',c.REF,p['commit'],c.PARENT]);result['local_ref_updated']=True
        current_claim(spec,packet_pin,claim)
        result['push_stdout']=module.git(c.F,['-c','push.followTags=false','-c','remote.origin.mirror=false','-c','push.recurseSubmodules=no','push','--porcelain','origin',p['commit']+':'+c.REF]).decode();result['push_succeeded']=True
        remote=module.git(c.F,['ls-remote','--refs','origin',c.REF]).decode().splitlines();assert remote==[p['commit']+'\t'+c.REF];result['remote_readback']=remote
        samples=[]
        for name in ('DEVELOPMENT-CHECKPOINT.json','src/ceta/store/journal.py','tests/contract/test_journal_read_budget.py','build/progress.json'):
            request=urllib.request.Request('https://raw.githubusercontent.com/IAmSoThirsty/Project-AI-Ceta/'+p['commit']+'/'+quote(name),headers={'User-Agent':'CETA-development-checkpoint9-readback'})
            with urllib.request.urlopen(request,timeout=30) as response:
                raw=response.read(8_000_001);valid_readback(raw,p['exports'][name]['sha256']);assert response.status==200;samples.append(dict(path=name,url=request.full_url,status=response.status,bytes=len(raw),sha256=c.sha(raw)))
        result['anonymous_samples']=samples;result['anonymous_readback']=True
    except BaseException as error:
        primary=sys.exc_info();result['error']=describe(error)
    try:
        result['finished_at']=datetime.now(timezone.utc).isoformat();result['checkout_after']=module.checkout_state(c.F);assert result['checkout_after']==p['checkout_before']
        assert c.stable(c.F/'.git/index')[1]==before['normal_index_native'] and c.stable(c.F/'.git/HEAD')[1]==before['HEAD_native']
        assert all(c.stable(c.F/name)[1]==pin for name,pin in before['canonical_pins'].items())
        after_refs=refs(module);assert all(before_refs.get(name)==after_refs.get(name) for name in set(before_refs)|set(after_refs) if name not in (c.REF,tracking))
        git_after=files(c.F/'.git');changed=sorted(name for name in set(git_before)|set(git_after) if git_before.get(name)!=git_after.get(name))
        outside=[name for name in changed if not any(path_matches_scope(e.PREFIX+'/'+name,scope) for scope in spec['git_scope'])]
        assert not outside,'Git metadata changed outside exact17 declarations'
        assert all(git_after.get(name)==pin for name,pin in git_before.items() if name.startswith('objects/')),'existing Git object changed'
        assert not [name for name in git_after if name.endswith('.lock') and name not in git_before],'new lock remains'
        result.update(observed_changed_Git_paths=changed,outside_exact_scope=outside,Git_after=git_after,unrelated_refs_unchanged=True,existing_objects_unchanged=True,canonical_source_index_HEAD_unchanged=True)
    except BaseException as error:
        if primary is None:primary=sys.exc_info()
        else:secondary.append(sys.exc_info())
        result['postcheck_error']=describe(error)
    finally:module.COMMAND_AUDITOR=None
    try:c.save(e.CONTROL/'INTEGRATION-RESULT.json',result)
    except BaseException:
        if primary is None:primary=sys.exc_info()
        else:secondary.append(sys.exc_info())
    if primary is not None:
        error=primary[1];storage=BaseException.__dict__['__dict__'].__get__(error);dict.__setitem__(storage,'checkpoint_secondary_exc_infos',tuple(secondary));raise BaseException.with_traceback(error,primary[2])
    assert result['push_succeeded'] and result['anonymous_readback'];print(json.dumps({key:value for key,value in result.items() if key!='Git_after'},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--publication-packet-sha256',required=True);publish(parser.parse_args().publication_packet_sha256)
