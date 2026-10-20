"""Actual Root wrapper AST under controlled subprocess results; no child launch."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import ast,hashlib,json,sys
F=Path('T:/00-Active/Project-AI-CETA')
H=F/'.agents/runtime/js9-root-r3-execution-20261020'
R=Path(__file__).resolve().parent
scripts={name:hashlib.sha256((H/name).read_bytes()).hexdigest() for name in ('phase_coordinator.py','issue_release.py','run_reviewed.py')}
source=H/'run_reviewed.py';tree=ast.parse(source.read_text(encoding='utf8'))
tree.body=[node for node in tree.body if not isinstance(node,(ast.Import,ast.ImportFrom))]
denied=[]
def audit(event,args):
    if event.startswith(('subprocess.','socket.','ctypes.','winreg.')) or event=='sqlite3.connect':
        denied.append(event);raise RuntimeError('REVIEW_EFFECT_DENIED:'+event)
sys.addaudithook(audit)
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
rows=[]
for mode in ('nonzero-terminal','spawn-exception'):
    base=R/mode;base.mkdir(exist_ok=False);runtime=base/'runtime';runtime.mkdir()
    project=base/'project';project.mkdir();tools=base/'tools';tools.mkdir()
    release_path=project/'release.json';release_path.write_bytes(b'{"controlled":true}\n')
    ref=dict(repository_relative_path='release.json',sha256=hashlib.sha256(release_path.read_bytes()).hexdigest())
    save(runtime/'native-store-RELEASE.json',dict(release=ref))
    called=[]
    def run(argv,**kwargs):
        called.append(list(argv))
        if mode=='spawn-exception':raise OSError('CONTROLLED_CREATEPROCESS_REFUSED')
        return SimpleNamespace(returncode=7)
    c=SimpleNamespace(F=project,R=runtime,D=tools,bound_packet=lambda:None,save=save)
    namespace=dict(__name__='root_helper_control',Path=Path,datetime=datetime,timezone=timezone,
        hashlib=hashlib,json=json,subprocess=SimpleNamespace(run=run),
        sys=SimpleNamespace(argv=[str(source),'native-store']),c=c)
    observed=None
    try:exec(compile(tree,str(source),'exec'),namespace)
    except BaseException as error:observed=dict(type=type(error).__name__,message=str(error),code=error.code if type(error) is SystemExit else None)
    row=dict(mode=mode,synthetic_subprocess_calls=len(called),actual_process_calls=0,
        observed=observed,command_present=(runtime/'native-store-COMMAND.json').is_file(),
        stdout_present=(runtime/'native-store.stdout').is_file(),stderr_present=(runtime/'native-store.stderr').is_file(),
        terminal_present=(runtime/'native-store-TERMINAL.json').is_file())
    if mode=='nonzero-terminal':assert row['terminal_present'] and observed['code']==7
    else:assert not row['terminal_present'] and observed['type']=='OSError'
    rows.append(row)
assert denied==[]
assert all(hashlib.sha256((H/name).read_bytes()).hexdigest()==pin for name,pin in scripts.items())
result=dict(at=datetime.now(timezone.utc).isoformat(),author='/root',reviewer='/root/recovery_regression20',
    mode='FILE_AST_DATA_ONLY',scripts=scripts,branches=rows,denied_events=denied,
    actual_native_process_profile_socket_SQLite_operations=0,
    finding='ROOT-HELPER-01: process-creation exception leaves no terminal failure record',
    product_or_runtime_acceptance=False)
save(R/'SPAWN-RECORD-CONTROL.json',result)
print(json.dumps(dict(finding=result['finding'],result_sha256=hashlib.sha256((R/'SPAWN-RECORD-CONTROL.json').read_bytes()).hexdigest(),scripts=scripts)),flush=True)
