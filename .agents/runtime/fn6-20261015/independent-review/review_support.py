"""Reviewer-owned FN6 evidence; frozen product and author runtime stay read-only."""
from pathlib import Path
import importlib.util, json, sys, os, ast, subprocess

V=Path(__file__).resolve().parent
A=V.parent
F=A.parents[2]
Q=F/'.agents/fn6-20261015'
P=F/'.agents/fn5-20261015'
RUN='fn6-20261015'
ACTOR='/root/wt1_reviewer'
import hashlib
assert hashlib.sha256((A/'foundation_support.py').read_bytes()).hexdigest()=='682b679fee50635273ae49f54592f9c61f55105b475023b1211668f1a98ec525'
spec=importlib.util.spec_from_file_location('foundation_support',A/'foundation_support.py')
s=importlib.util.module_from_spec(spec);sys.modules[spec.name]=s;spec.loader.exec_module(s)
s.R=V
sys.path.insert(0,str(V))
read=s.read;sha=s.sha;utc=s.utc;ordinary=s.ordinary;reference=s.reference;write_new=s.write_new;canonical=s.canonical

def current_receipt(node,local_path,expected_actor):
    local=read(local_path);stored=read(A/RUN/'receipts'/f'{node}.json')
    state=read(A/RUN/'state.json');envelope=read(A/RUN/'results'/f'{node}.json')
    fields=s.STRICT if node=='review' else s.STRICT-{'decision'}
    assert set(local)==fields and set(stored)==fields|{'git_baseline','observed_git','receipt_hash'}
    assert all(canonical(local[k])==canonical(stored[k]) for k in fields)
    assert local['executor_id']==expected_actor
    assert set(envelope)=={'node_id','receipt_hash','result'}
    assert envelope['node_id']==node and canonical(envelope['result'])==canonical(local['result'])
    assert envelope['receipt_hash']==stored['receipt_hash']==state['nodes'][node]['receipt_hash']
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt
    from taar.orchestration_persistence import sha256_json
    normalized=validate_receipt(local,run_id=RUN,node_id=node,executor_id=expected_actor,
        input_hash=local['input_hash'],claimed_at=local['started_at'],node=read(A/RUN/'graph.json')['graph']['nodes'][node])
    normalized.pop('receipt_hash')
    normalized.update(git_baseline=stored['git_baseline'],observed_git=stored['observed_git'])
    assert sha256_json(normalized)==stored['receipt_hash']
    return local,stored,state,envelope

def walk_members(root):
    names=set()
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in dirs:assert not s.fs.reparse(s.fs.lstat(Path(parent)/name))
        names.update((Path(parent)/name).relative_to(root).as_posix() for name in files)
    return names

def preflight():
    frozen=read(V/'REVIEW-INPUTS.json')
    assert ordinary(Q/'TRANSFER-MANIFEST.json')==frozen['manifest']
    for name,row in frozen['copies'].items():
        assert ordinary(A/name)==row['original'],('author input drift',name)
        assert ordinary(V/name)==row['reviewer'],('reviewer input drift',name)
    for name,row in frozen['payloads'].items():assert ordinary(Q/name)==row,('Q drift',name)
    for name,row in frozen['auxiliaries'].items():assert ordinary(Q/name)==row,('Q auxiliary drift',name)
    for name,row in frozen['parent_payloads'].items():assert ordinary(P/name)==row,('parent drift',name)
    E=s.PY.parent.parent
    assert walk_members(E)==set(frozen['E33601'])
    for name,row in frozen['E33601'].items():assert ordinary(E/name)==row,('E3 drift',name)
    for name,row in frozen['reader_inputs'].items():assert ordinary(F/name)==row,('reader input drift',name)
    for name,row in frozen['own_helpers'].items():assert ordinary(V/name)==row,('review helper drift',name)
    assert read(A/RUN/'claims.json')['review']['executor_id']==ACTOR
    assert read(A/RUN/'state.json')['nodes']['review']['state']=='RUNNING'
    return frozen

def invoke(args,label):
    argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(A)]
    done=subprocess.run(argv,cwd=F,capture_output=True)
    for ext,raw in (('stdout',done.stdout),('stderr',done.stderr)):
        with (V/(label+'.'+ext)).open('xb') as out:out.write(raw)
    response=json.loads(done.stdout.decode('utf-8-sig'))
    write_new(V/(label+'.json'),dict(argv=argv,exit_status=done.returncode,response=response))
    assert done.returncode==0 and response['allowed'] is True,response
    return response
