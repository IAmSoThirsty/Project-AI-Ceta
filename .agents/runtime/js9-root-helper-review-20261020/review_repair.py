"""Independent bounded review of Root's helpers; no engineering effect runs."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import ast,hashlib,json,sys,traceback
F=Path('T:/00-Active/Project-AI-CETA');H=F/'.agents/runtime/js9-root-r3-execution-20261020'
R=Path(__file__).resolve().parent;D=F/'.agents/runtime/js9-runtime-20261020/successor-r3';Q=F/'.agents/js9-runtime-r5-20261020'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
scripts={name:sha(H/name) for name in ('phase_coordinator.py','issue_release.py','run_reviewed.py')}
assert scripts['phase_coordinator.py']=='4ecaecb74acea18f73246e5f87ec058e1300bda1b08f657a7965b3e043829429'
assert scripts['issue_release.py']=='60a5f888d7f2c87bfd8fec85dc828f194cbbe4ea1e68dc720b513ad5a4562a2b'
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def extract(path,names,namespace):
    tree=ast.parse(path.read_text(encoding='utf8'));tree.body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert {node.name for node in tree.body}==set(names)
    exec(compile(tree,str(path),'exec'),namespace)
controls=[]
phase=dict(R=H,D=D,Q=Q,F=F,hashlib=hashlib,json=json)
extract(H/'phase_coordinator.py',['bound_packet'],phase)
packet=phase['bound_packet']();controls.append('actual_packet_bound541_and31')
authorization=dict(F=F,R=H,D=D,Q=Q,OLD=D.parent/'successor-r2',OLD_AUTH=F/'.agents/runtime/js9-root-execution-20261020/NO-PROFILE-AUTHORIZATION.json',
    sha=sha,ref=lambda path:dict(repository_relative_path=path.relative_to(F).as_posix(),sha256=sha(path)),
    c=SimpleNamespace(bound_packet=phase['bound_packet']),json=json)
extract(H/'issue_release.py',['unchanged_authorized_operation'],authorization)
continuity=authorization['unchanged_authorized_operation']()
assert continuity['original_operation_unchanged'] and continuity['prior_no_profile_attempts']==0
assert continuity['exact_phase_limits']==dict(candidate_full=1,destination_full=1)
assert not continuity['new_human_authorization_fabricated'] and not continuity['automatic_retry']
controls.append('actual_exact_operation_equivalence_and_unconsumed_old_proof')
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_graph import compile_graph,scopes_may_overlap
from taar.orchestration_runtime import OrchestrationRuntime
graph=compile_graph(F,H);state=json.loads((H/'js9-root-r3-execution-20261020/state.json').read_bytes())
claims=json.loads((H/'js9-root-r3-execution-20261020/claims.json').read_bytes())
assert graph.fingerprint==state['graph_fingerprint']
assert graph.policy['prohibit_scope_overlap'] and graph.policy['prohibit_self_review'] and graph.policy['require_receipts']
scopes={}
for node,workspace in [('implement',D),('candidate_fixtures',Q/'.agents/fixtures'),('candidate_cache',Q/'.local-test-output'),
        ('integrate',F),('destination_evidence',D),('destination_fixtures',F/'.agents/fixtures')]:
    actual,scope=OrchestrationRuntime._effective_workspace_scope(None,graph,graph.nodes[node],workspace)
    assert actual==str(workspace.resolve())
    scopes[node]=scope
for cohort in [('implement','candidate_fixtures','candidate_cache'),('integrate','destination_evidence','destination_fixtures')]:
    for position,left in enumerate(cohort):
        for right in cohort[position+1:]:assert not scopes_may_overlap(scopes[left],scopes[right])
controls.append('actual_installed_TAAR_candidate_and_destination_scopes_disjoint')
assert scopes['integrate']==packet['application_paths']+['.local-test-output/**']
for node in ('implement','candidate_fixtures','candidate_cache'):
    assert state['nodes'][node]['state']=='RUNNING' and claims[node]['executor_id']=='/root'
    assert claims[node]['effective_write_scope']==scopes[node]
controls.append('actual_three_candidate_claims_current_and_exact')
edges={(edge['from'],edge['to'],edge['type']) for edge in graph.edges}
assert all((node,'review','requires_review') in edges for node in ('implement','candidate_fixtures','candidate_cache'))
assert ('review','validate','authorizes') in edges and ('validate','integrate','gates') in edges
assert ('validate','destination_evidence','depends_on') in edges and ('validate','destination_fixtures','depends_on') in edges
controls.append('actual_compiled_dependency_review_and_gate_edges')

tree=ast.parse((H/'run_reviewed.py').read_text(encoding='utf8'))
tree.body=[node for node in tree.body if not isinstance(node,(ast.Import,ast.ImportFrom))]
denied=[]
def audit(event,args):
    if event.startswith(('subprocess.','socket.','ctypes.','winreg.')) or event=='sqlite3.connect':
        denied.append(event);raise RuntimeError('REVIEW_EFFECT_DENIED:'+event)
sys.addaudithook(audit)
branches=[]
for mode in ('nonzero-terminal','spawn-exception','spawn-and-terminal-writer-exception'):
    base=R/('r2-'+mode);base.mkdir(exist_ok=False)
    runtime=base/'runtime';runtime.mkdir();project=base/'project';project.mkdir();tools=base/'tools';tools.mkdir()
    release_path=project/'release.json';release_path.write_bytes(b'{"controlled":true}\n')
    ref=dict(repository_relative_path='release.json',sha256=sha(release_path))
    save(runtime/'native-store-RELEASE.json',dict(release=ref))
    primary=OSError('CONTROLLED_CREATEPROCESS_REFUSED');writer_error=OSError('CONTROLLED_TERMINAL_WRITE_REFUSED');called=[]
    def run(argv,**kwargs):
        called.append(list(argv))
        if mode!='nonzero-terminal':raise primary
        return SimpleNamespace(returncode=7)
    def controlled_save(path,value):
        if mode=='spawn-and-terminal-writer-exception' and path.name.endswith('-TERMINAL.json'):raise writer_error
        save(path,value)
    c=SimpleNamespace(F=project,R=runtime,D=tools,bound_packet=lambda:None,save=controlled_save)
    namespace=dict(Path=Path,datetime=datetime,timezone=timezone,hashlib=hashlib,json=json,traceback=traceback,
        subprocess=SimpleNamespace(run=run),sys=SimpleNamespace(argv=[str(H/'run_reviewed.py'),'native-store']),c=c)
    observed=None
    try:exec(compile(tree,str(H/'run_reviewed.py'),'exec'),namespace)
    except BaseException as error:observed=error
    assert len(called)==1
    terminal=runtime/'native-store-TERMINAL.json'
    if mode=='nonzero-terminal':
        assert type(observed) is SystemExit and observed.code==7
        value=json.loads(terminal.read_bytes());assert value['exit_status']==7 and value['command_returned'] is True and value['execution_error'] is None
    else:
        assert observed is primary
        if mode=='spawn-exception':value=json.loads(terminal.read_bytes())
        else:
            assert primary.terminal_write_error is writer_error
            value=primary.terminal_record
        assert value['exit_status'] is None and value['command_returned'] is False
        assert value['execution_error']['message']=='CONTROLLED_CREATEPROCESS_REFUSED'
        assert 'raise primary' in value['execution_error']['traceback']
        assert value['finished_at'] and value['stdout_sha256']==value['stderr_sha256']==hashlib.sha256(b'').hexdigest()
    branches.append(dict(mode=mode,passed=True,synthetic_subprocess_calls=1,actual_process_calls=0))
    controls.append('actual_wrapper_AST_'+mode)
assert not denied
assert all(sha(H/name)==pin for name,pin in scripts.items())
result=dict(at=datetime.now(timezone.utc).isoformat(),author='/root',reviewer='/root/recovery_regression20',
    mode='FILE_AST_DATA_ONLY',scripts=scripts,installed_graph_fingerprint=graph.fingerprint,
    scopes=scopes,controls=controls,branches=branches,operation_equivalence=continuity,
    repaired_finding='ROOT-HELPER-01',no_automatic_retry=True,actual_native_process_profile_socket_SQLite_operations=0,
    denied_effect_events=denied,product_tools_or_Q5_review=False,
    limitation='Completion helper records supplied command/validation evidence; actual phase results and receipts still require independent acceptance. No execution performed by this reviewer.')
save(R/'REPAIR-CONTROLS.json',result)
disposition=dict(at=datetime.now(timezone.utc).isoformat(),decision='approved',exit_status=0,
    author='/root',reviewer='/root/recovery_regression20',reviewed_scripts=scripts,
    scope='Only Root phase_coordinator.py, issue_release.py, run_reviewed.py at exact listed pins',
    controls=dict(path=str(R/'REPAIR-CONTROLS.json'),sha256=sha(R/'REPAIR-CONTROLS.json')),
    previous_finding= dict(path=str(R/'SPAWN-RECORD-CONTROL.json'),sha256=sha(R/'SPAWN-RECORD-CONTROL.json'),status='fixed_on_reviewed_successor'),
    Native_or_Source_execution_released_by_this_review=False,actual_TAAR_review_node_claimed=False,
    skills_used=['protocol-interoperability-auditor'],governing_version='thirsty-constitution-v0.1')
save(R/'DISPOSITION.json',disposition)
print(json.dumps(dict(decision='approved',scripts=scripts,controls=len(controls),
    controls_sha256=sha(R/'REPAIR-CONTROLS.json'),disposition_sha256=sha(R/'DISPOSITION.json'))),flush=True)
