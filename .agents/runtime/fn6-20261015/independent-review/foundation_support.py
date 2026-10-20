"""Pinned foundation join, installed receipts and native-file preservation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, stat, subprocess, sys

R=Path(__file__).resolve().parent;F=R.parents[2]
RUN='fn6-20261015';Q=F/'.agents'/RUN
PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
AUTHOR='/root/pressure_writer';INTEGRATOR='/root';ACTOR=AUTHOR
assert Path(sys.executable)==PY and not sys.flags.optimize and os.name=='nt'
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest=lambda raw:hashlib.sha256(raw).hexdigest()
utc=lambda:datetime.now(timezone.utc).isoformat()
canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
SCRIPTS=('foundation_support.py','run_joined.py','publish_source.py','complete_source.py')
STRICT=frozenset(('schema_version','run_id','node_id','executor_id','started_at','finished_at',
 'input_hash','changed_files','result','commands','validations','exit_status','decision'))
reader=F/'.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(reader)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec=importlib.util.spec_from_file_location('foundation4_native_reader',reader)
fs=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fs;spec.loader.exec_module(fs)

def ordinary(path):
    path=fs.safe_components(Path(path));info=fs.lstat(path)
    assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    identity=fs.file_identity(info);size,pin,_=fs.hash_file(path)
    assert size==identity['bytes'] and fs.file_identity(fs.lstat(path))==identity
    return {'path':str(path),'bytes':size,'sha256':pin,'native_identity':identity}

def write_new(path,value):
    path=Path(path);assert path.is_relative_to(R) or path.is_relative_to(Q)
    fs.safe_components(path.parent,allow_missing=True);path.parent.mkdir(parents=True,exist_ok=True)
    fs.safe_components(path.parent)
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode('utf-8')
    fs.write_new(path,raw)

def reference(path):
    path=fs.safe_components(Path(path));assert path.is_relative_to(F)
    return {'repository_relative_path':path.relative_to(F).as_posix(),'sha256':ordinary(path)['sha256']}

def safe_proof(value):
    assert type(value) is dict and set(value)=={'repository_relative_path','sha256'}
    name=fs.relative_name(value['repository_relative_path']);path=F/name
    facts=ordinary(path);assert facts['sha256']==value['sha256']
    return path

def bytes_copy(source,target,expected=None):
    before=ordinary(source)
    if expected is not None:assert before==expected,('source changed before preservation',str(source))
    with fs.open_source(source,exclusive=True) as stream:
        descriptor=fs.file_identity(os.fstat(stream.fileno()))
        # Windows infers .exe executable mode from the pathname; fstat lacks
        # that name. Preserve the full path facts before and after the read.
        assert all(descriptor[key]==before['native_identity'][key]
          for key in ('device','inode','bytes','mtime_ns','attributes'))
        data=stream.read();assert digest(data)==before['sha256']
        assert fs.file_identity(os.fstat(stream.fileno()))==descriptor
    assert ordinary(source)==before
    target=Path(target);fs.safe_components(target.parent,allow_missing=True)
    target.parent.mkdir(parents=True,exist_ok=True);fs.safe_components(target.parent)
    fs.write_new(target,data);after=ordinary(target)
    assert after['sha256']==before['sha256'];return after

def require_native_original(path,expected):
    actual=ordinary(path)
    assert actual['sha256']==expected['sha256'] and actual['bytes']==expected['bytes']
    assert actual['native_identity']==expected['native_identity'],('original native identity drift',str(path))
    return actual

def approved_review():
    """Require the exact local review and actual persisted strict receipt."""
    manifest_path=Q/'TRANSFER-MANIFEST.json';manifest=read(manifest_path)
    local=read(R/'independent-review/review.json')
    stored=read(R/RUN/'receipts/review.json')
    assert type(local) is dict and set(local)==STRICT
    assert type(stored) is dict and set(stored)==STRICT|{'git_baseline','observed_git','receipt_hash'}
    assert all(canonical(local[key])==canonical(stored[key]) for key in STRICT), 'persisted review mismatch'
    assert type(local['schema_version']) is int and local['schema_version']==1
    assert local['run_id']==RUN and local['node_id']=='review'
    assert local['executor_id']!=AUTHOR and type(local['executor_id']) is str and local['executor_id']
    assert local['decision']=='approved' and type(local['exit_status']) is int and local['exit_status']==0
    assert local['changed_files']==[]
    state=read(R/RUN/'state.json');node=state['nodes']['review']
    assert node['state']=='SUCCEEDED' and node['receipt_hash']==stored['receipt_hash']
    result=read(R/RUN/'results/review.json')
    assert result['node_id']=='review' and result['receipt_hash']==stored['receipt_hash']
    assert canonical(result['result'])==canonical(stored['result'])
    assert local['result']['manifest_sha256']==sha(manifest_path)
    scripts={name:sha(R/name) for name in SCRIPTS}
    assert set(local['result']['reviewed_scripts'])==set(SCRIPTS)
    assert local['result']['reviewed_scripts']==manifest['scripts']==scripts
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt
    validate_receipt(local,run_id=RUN,node_id='review',executor_id=local['executor_id'],
      input_hash=local['input_hash'],claimed_at=local['started_at'],
      node=read(R/RUN/'graph.json')['graph']['nodes']['review'])
    return local

def note_secondary(primary,secondary,label):
    """Diagnostic formatting, lookup and annotation never replace primary."""
    try:
        message=label+': '+type(secondary).__name__
        method=getattr(primary,'add_note',None)
        if callable(method):method(message)
    except BaseException:
        pass

def invoke(args,label):
    argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(R)]
    done=subprocess.run(argv,cwd='T:/00-Active',capture_output=True)
    for suffix,raw in [('stdout',done.stdout),('stderr',done.stderr)]:
        with (R/(label+'.'+suffix)).open('xb') as out:out.write(raw)
    response=json.loads(done.stdout.decode('utf-8-sig'))
    write_new(R/(label+'.json'),{'argv':argv,'exit_status':done.returncode,'response':response})
    assert done.returncode==0 and response['allowed'] is True,response
    return response

def claim(node,workspace=Q,executor=AUTHOR):
    return invoke(['node','claim',RUN,node,'--executor',executor,'--workspace',str(workspace)],node+'-claim')['claim']

def complete(node,result,commands,validations):
    current=read(R/RUN/'claims.json')[node]
    actor=INTEGRATOR if node=='integrate' else AUTHOR
    assert current['executor_id']==actor
    workspace=Path(current['workspace']);assert workspace==(F if node=='integrate' else Q)
    sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_runtime import _snapshot_workspace,_changed_files
    from taar.orchestration_receipts import validate_receipt
    changed=_changed_files(current['baseline_snapshot'],_snapshot_workspace(workspace,Path('T:/')))
    if node=='integrate':
        allowed={str((F/name).relative_to(Path('T:/'))).replace('\\','/') for name in read(R/'STAGED-JOIN.json')['selected']}
        assert set(changed)==allowed,changed
    receipt={'schema_version':1,'run_id':RUN,'node_id':node,'executor_id':actor,
      'started_at':current['claimed_at'],'finished_at':utc(),'input_hash':current['input_hash'],
      'changed_files':changed,'result':result,'commands':commands,
      'validations':[{'name':name,'passed':passed} for name,passed in validations],'exit_status':0}
    kwargs=dict(run_id=RUN,node_id=node,executor_id=actor,input_hash=current['input_hash'],claimed_at=current['claimed_at'],
      node=read(R/RUN/'graph.json')['graph']['nodes'][node])
    validate_receipt(receipt,**kwargs);write_new(R/(node+'.json'),receipt)
    validate_receipt(read(R/(node+'.json')),**kwargs)
    return invoke(['node','complete',RUN,node,str(R/(node+'.json'))],node+'-complete')
