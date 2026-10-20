"""Exact-function DATA_ONLY reproduction; no native or subprocess execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

F=Path(r'T:\00-Active\Project-AI-CETA')
R=F/'.agents/runtime/js9-runtime-20261020/successor-r1'
D=F/'.agents/runtime/js9-successor-tools-review-20261020'
reader=F/'.agents/pr4-20261014/preserve_ceta_complete.py'
def functions(path,names,namespace):
    nodes=[n for n in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+'#PURE-EXACT-FUNCTIONS','exec'),namespace)
rows=[]
for script in ('run_native_store.py','run_native_observer.py'):
    blocked=[]
    hook_ns={'os':os,'Path':Path,'output':D/'in-memory-only', 'blocked':blocked,
             'forbidden':blocked,'loads':[]}
    functions(R/script,{'audit'},hook_ns)
    dispatch=[]
    def synthetic_run(argv,**kwargs):
        # CPython subprocess.Popen emits this event before creating a process.
        # Call the actual reviewed hook body directly; never call subprocess.
        dispatch.append({'executable':'git','argv':argv})
        hook_ns['audit']('subprocess.Popen',('git',argv,None,kwargs['env']))
        return SimpleNamespace(returncode=0,stdout=b'83fc9432b4a37ee7f91d6c5b0d358a015548aed4\n',stderr=b'')
    fs_ns={'Path':Path,'subprocess':SimpleNamespace(run=synthetic_run),
           'git_environment':lambda:{},'require':lambda value,text:None if value else (_ for _ in ()).throw(AssertionError(text))}
    functions(reader,{'git','text_git'},fs_ns)
    python=F/'synthetic-interpreter.exe'
    p={'Git':{'HEAD':'83fc9432b4a37ee7f91d6c5b0d358a015548aed4','branch':'candidate/societal-reasoning-v1'},
       'Source_before':{},'fixture_dependencies':{},'application_paths':[]}
    v={'python':{},'base_python':{},'environment_files':{}}
    verify_ns={'Path':Path,'PY':python,'Q':F/'.agents/js9-runtime-20261020','F':F,
       'sys':SimpleNamespace(executable=str(python),_base_executable=str(python),flags=SimpleNamespace(optimize=0)),
       'os':SimpleNamespace(name='nt'),'packet':lambda:p,
       'manifest':lambda:{'expected_payload_hashes':{}},'inputs':lambda:v,
       'proof':lambda reference:(None,{'targets':{}}),'inventory':lambda root:{},
       's':SimpleNamespace(ordinary=lambda path:{},fs=SimpleNamespace(text_git=fs_ns['text_git']))}
    functions(R/'js9_support.py',{'verify'},verify_ns)
    try:verify_ns['verify'](source='before')
    except BaseException as error:
        row={'script':script,'type':type(error).__name__,'message':str(error),'synthetic_dispatches':dispatch,'recorded_boundary_violations':blocked}
        assert len(dispatch)==1 and blocked and ('BOUNDARY' in row['message'] or 'FORBIDS_subprocess.Popen' in row['message'])
        rows.append(row)
    else:raise AssertionError('UNEXPECTED_ACCEPTANCE:'+script)
result={'status':'REPRODUCED','finding':'JS9-TOOLS-01','scope':'DATA_ONLY actual verify/git/text_git/audit AST functions; synthetic subprocess event; no child, DLL, worker, profile, listener, DB or tool import',
        'cases':rows,'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (reader,R/'js9_support.py',R/'run_native_store.py',R/'run_native_observer.py')}}
with (D/'POSTVERIFY-BOUNDARY-REPRODUCTION.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2);out.write('\n')
print(json.dumps(result))
