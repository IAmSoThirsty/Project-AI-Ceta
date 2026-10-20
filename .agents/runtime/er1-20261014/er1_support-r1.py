"""ER1 native read-only source observation and exact installed TAAR operations."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib,importlib.util,json,os,stat,subprocess,sys
P=Path(r'T:\00-Active\Project-AI-CETA');Q=P/'.agents/er1-20261014';R=P/'.agents/runtime/er1-20261014'
E3=P/'.agents/source-assembly-20261014T021300Z/.agents/e3';PY=E3/'Scripts/python.exe';ACTOR='/root/history_preservation';RUN='er1-20261014'
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def utc():return datetime.now(timezone.utc).isoformat()
def write_new(path,value):
    path=Path(path);assert path.is_relative_to(R) or path.is_relative_to(Q)
    with path.open('x',encoding='utf-8',newline='\n') as output:json.dump(value,output,indent=2,allow_nan=False);output.write('\n')
def reference(path):
    path=Path(path);return {'repository_relative_path':path.relative_to(P).as_posix(),'sha256':sha(path)}
P4=P/'.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(P4)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec=importlib.util.spec_from_file_location('er1_approved_native_reader',P4)
fs=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fs;spec.loader.exec_module(fs)
assert Path(sys.executable)==PY and sys.version_info[:2]==(3,12) and os.name=='nt'
def ordinary(path):
    path=fs.safe_components(Path(path));info=fs.lstat(path);assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    size,value,identity=fs.hash_file(path)
    return {'path':str(path),'bytes':size,'sha256':value,'native_identity':identity}
def snapshot_tree():
    started=utc();root=fs.safe_components(E3);members=[];stack=[root];size=0;count=0
    while stack:
        directory=stack.pop()
        with os.scandir(fs.io_path(directory)) as listing:children=sorted([entry.name for entry in listing],reverse=True)
        for name in children:
            path=directory/name;info=fs.lstat(path);relative=path.relative_to(root).as_posix()
            row={'relative_path':relative,'native_identity':fs.file_identity(info)}
            if fs.reparse(info):
                row['kind']='reparse_not_followed';members.append(row);continue
            if stat.S_ISDIR(info.st_mode):row['kind']='directory';members.append(row);stack.append(path)
            else:
                assert stat.S_ISREG(info.st_mode),f'Unknown native member kind: {relative}'
                observed=ordinary(path);row.update(kind='ordinary_file',bytes=observed['bytes'],sha256=observed['sha256']);members.append(row);count+=1;size+=row['bytes']
                if count%2000==0:print(json.dumps({'observed_E3_files':count,'ordinary_bytes':size}),flush=True)
    members.sort(key=lambda row:row['relative_path'])
    return {'source_root':str(root),'started_at':started,'finished_at':utc(),'root_native_identity':fs.file_identity(fs.lstat(root)),
            'ordinary_files':count,'ordinary_bytes':size,'directories':sum(row['kind']=='directory' for row in members),
            'reparse_not_followed':sum(row['kind']=='reparse_not_followed' for row in members),'members':members}
def invoke(arguments,label):
    command=['powershell','-NoProfile','-File',r'T:\02-Config\agents\taar-orchestrate.ps1',*arguments,'--runtime-root',str(R)]
    start=utc();completed=subprocess.run(command,cwd=r'T:\00-Active',env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True)
    for suffix,data in [('stdout.txt',completed.stdout),('stderr.txt',completed.stderr)]:
        with (R/(label+'.'+suffix)).open('xb') as out:out.write(data)
    response=json.loads(completed.stdout.decode('utf-8-sig'))
    write_new(R/(label+'.json'),{'command_argv':command,'started_at':start,'finished_at':utc(),'exit_status':completed.returncode,'response':response})
    assert completed.returncode==0 and response['allowed'],response
    return response
def claim(node):return invoke(['node','claim',RUN,node,'--executor',ACTOR,'--workspace',str(Q)],node+'-claim')['claim']
def complete(node,result,commands,validations):
    current=json.loads((R/RUN/'claims.json').read_text())[node]
    graph=json.loads((R/RUN/'graph.json').read_text())['graph']
    assert current['executor_id']==ACTOR
    sys.path.insert(0,r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt,load_receipt
    from taar.orchestration_runtime import _snapshot_workspace,_changed_files
    snapshot=_snapshot_workspace(Q,Path('T:/'));changed=_changed_files(current['baseline_snapshot'],snapshot)
    receipt={'schema_version':1,'run_id':RUN,'node_id':node,'executor_id':ACTOR,'started_at':current['claimed_at'],'finished_at':utc(),'input_hash':current['input_hash'],'changed_files':changed,
             'result':result,'commands':commands,'validations':[{'name':name,'passed':passed} for name,passed in validations],'exit_status':0}
    kwargs={'run_id':RUN,'node_id':node,'executor_id':ACTOR,'input_hash':current['input_hash'],'claimed_at':current['claimed_at'],'node':graph['nodes'][node]}
    validate_receipt(receipt,**kwargs);write_new(R/(node+'.json'),receipt);validate_receipt(load_receipt(R/(node+'.json')),**kwargs)
    response=invoke(['node','complete',RUN,node,str(R/(node+'.json'))],node+'-complete')
    return response
