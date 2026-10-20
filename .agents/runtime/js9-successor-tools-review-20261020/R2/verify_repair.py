"""R2 narrow file/AST review and synthetic receipt controls; no tool import."""
import ast
import copy
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

F=Path(r'T:\00-Active\Project-AI-CETA');R=F/'.agents/runtime/js9-runtime-20261020/successor-r2'
OLD=R.parent/'successor-r1';D=F/'.agents/runtime/js9-successor-tools-review-20261020/R2'
inputs={};checks=[];controls=[]
def sha(path):
    h=hashlib.sha256(path.read_bytes()).hexdigest();key=str(path)
    assert key not in inputs or inputs[key]==h
    inputs[key]=h;return h
def load(path):sha(path);return json.loads(path.read_text(encoding='utf-8-sig'))
def check(name,condition):assert condition,name;checks.append(name)
def extract(path,names,namespace):
    nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+'#PURE-EXACT-BODIES','exec'),namespace)
def control(name,operation,expected=True):
    error=None
    try:operation();allowed=True
    except BaseException as e:allowed=False;error=dict(type=type(e).__name__,text=str(e))
    assert allowed is expected,(name,allowed,error)
    controls.append(dict(name=name,allowed=allowed,expected=expected,passed=True,error=error))

packet=load(R/'PACKET.json');prior=load(OLD/'PACKET.json');delta=load(R/'ADAPTER-DELTAS.json')
check('EXACT_R2_PACKET',sha(R/'PACKET.json')=='eb5f4c993a74f7b378db9b2dd10e039fadc64ebff3c31887c78393ce58157055')
check('EXACT_R2_DELTAS',sha(R/'ADAPTER-DELTAS.json')=='6482fc7d02b7b1de23c14cbc408c78076f52a02795396c7726a6402e119d1e63')
check('EXACT12_SCRIPTS',len(packet['scripts'])==12 and set(packet['scripts'])==set(prior['scripts'])|{'launch_native.py'})
for name,pin in packet['scripts'].items():
    check('SCRIPT:'+name,sha(R/name)==pin)
    row=delta['script_deltas'][name];check('DELTA_AFTER:'+name,row['after_sha256']==pin)
    before='' if row['before_sha256'] is None else (OLD/name).read_text()
    if row['before_sha256'] is not None:check('DELTA_BEFORE:'+name,sha(OLD/name)==row['before_sha256'])
    actual=''.join(difflib.unified_diff(before.splitlines(True),(R/name).read_text().splitlines(True),fromfile='frozen-r1/'+name,tofile='successor-r2/'+name))
    check('EXACT_DELTA:'+name,actual==row['delta'])
for key in ('candidate_manifest','case_set','Source_before','environment','git_dependency'):
    ref=packet[key];check('PIN:'+key,sha(F/ref['repository_relative_path'])==ref['sha256'])
    check('UNCHANGED_CONTENT:'+key,ref['sha256']==prior[key]['sha256'])
for key in ('application_paths','product_modules','native_store_ids','native_observer_ids','fixture_dependencies','original_case_id','Git'):
    check('UNCHANGED_PACKET_FIELD:'+key,packet[key]==prior[key])
manifest=load(F/packet['candidate_manifest']['repository_relative_path'])
check('CANDIDATE530_STILL_FROZEN',len(manifest['payload_hashes'])==530 and all(sha(F/'.agents/js9-runtime-20261020'/n)==h for n,h in manifest['payload_hashes'].items()))
before=load(F/packet['Source_before']['repository_relative_path'])
check('SOURCE_CURRENT_HASHES',all(not (F/n).exists() if row is None else sha(F/n)==row['sha256'] for n,row in before['targets'].items()))
for n,row in packet['fixture_dependencies'].items():check('FIXTURE:'+n,sha(Path(row['path']))==row['sha256'])

# Only the two audited child post-checks may opt out, never the parent/default.
false_sites=[]
for name in packet['scripts']:
    tree=ast.parse((R/name).read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='verify':
            for kw in node.keywords:
                if kw.arg=='verify_git':
                    check('LITERAL_FALSE_BOUNDARY:'+name,isinstance(kw.value,ast.Constant) and kw.value.value is False)
                    false_sites.append((name,node.lineno))
check('EXACT_TWO_POST_AUDIT_OPTOUTS',sorted(n for n,l in false_sites)==['run_native_observer.py','run_native_store.py'])
support=ast.parse((R/'js9_support.py').read_text())
verify_node=next(n for n in support.body if isinstance(n,ast.FunctionDef) and n.name=='verify')
check('DEFAULT_GIT_TRUE',dict(zip(verify_node.args.kwonlyargs and [n.arg for n in verify_node.args.kwonlyargs],verify_node.args.kw_defaults))['verify_git'].value is True)
calls=[];python=F/'synthetic-python.exe'
v=dict(python={},base_python={},environment_files={})
fake_packet=dict(Git=packet['Git'],Source_before={},fixture_dependencies={},application_paths=[])
def git(root,*args):calls.append(args);return packet['Git']['HEAD' if args[0]=='rev-parse' else 'branch']
ns={'Path':Path,'PY':python,'F':F,'Q':F/'.agents/js9-runtime-20261020',
 'os':SimpleNamespace(name='nt'),'sys':SimpleNamespace(executable=str(python),_base_executable=str(python),flags=SimpleNamespace(optimize=0)),
 'packet':lambda:fake_packet,'manifest':lambda:{'expected_payload_hashes':{}},'inputs':lambda:v,
 'proof':lambda ref:(None,{'targets':{}}),'inventory':lambda path:{},
 's':SimpleNamespace(ordinary=lambda path:{},fs=SimpleNamespace(text_git=git))}
extract(R/'js9_support.py',{'verify'},ns)
control('default_verify_observes_exact_two_Git_queries',lambda:check('DEFAULT_GIT_MEASURED',ns['verify']()['Git_observed']==packet['Git'] and calls==[('rev-parse','HEAD'),('branch','--show-current')]))
calls.clear();control('explicit_false_preserves_unobserved_Git',lambda:check('FALSE_NO_DISPATCH',ns['verify'](verify_git=False)['Git_observed'] is None and calls==[]))
for invalid in (0,1,None,'false'):
    control('invalid_verify_git_type_'+repr(invalid),lambda invalid=invalid:ns['verify'](verify_git=invalid),False)

# Exact terminal + corroboration predicates with synthetic owned records.
refs={};values={};interpreter={'exact':'interpreter'}
env={'python':{'path':'venv','sha256':'python-pin'},'base_python':{'path':'base'}}
source_ref=packet['Source_before'];source_targets={'a':{'sha256':'source-pin'}}
packet_ref={'repository_relative_path':(R/'PACKET.json').relative_to(F).as_posix(),'sha256':sha(R/'PACKET.json')}
for phase in ('native-store','native-observer'):
    script='run_native_store.py' if phase=='native-store' else 'run_native_observer.py'
    label=phase.replace('-','_')+'_synthetic';leaf='RESULT.json' if phase=='native-store' else 'native.json'
    terminal_ref={'repository_relative_path':(R/label/leaf).relative_to(F).as_posix(),'sha256':phase+'-terminal'}
    release_ref={'repository_relative_path':(R/'releases'/label).relative_to(F).as_posix(),'sha256':phase+'-release'}
    parent_ref={'repository_relative_path':(R/(label+'-CORROBORATION.json')).relative_to(F).as_posix(),'sha256':phase+'-parent'}
    argv=['venv','-B','-X','utf8',str(R/script),label,'--release-path',str(F/release_ref['repository_relative_path']),'--release-sha256',release_ref['sha256']]
    ids=packet['native_store_ids'] if phase=='native-store' else packet['native_observer_ids']
    term=dict(phase=phase,packet=packet_ref,candidate_manifest=packet['candidate_manifest'],runner_sha256=packet['scripts'][script],
      passed=True,post_CAS_verified=True,acceptance_complete=False,Git_corroboration=dict(status='PENDING_ROOT_CORROBORATION',before=packet['Git'],after=None),
      interpreter=interpreter,interpreter_observation=interpreter,expected_ids=ids,tests_run=len(ids),
      events=[dict(event=kind,id=i) for i in ids for kind in ('START','STOP')],failures=[],errors=[],skips=[],
      primary_error=None,remaining_threads=[],boundary_violations=[],physical_custody={'owned_resources_closed':True},
      binding_custody=[{'closed':True,'pending':[]}],executed_ids=ids,stopped_ids=ids,run_error=None,
      checks={'all':True},custody=[{'all_closed':True}],observed_argv=['base',*argv[1:]],cwd=str(R),release=release_ref)
    parent=dict(phase=phase,accepted=True,status='ACCEPTED_NATIVE_ENGINEERING_SCOPE',packet=packet_ref,candidate_manifest=packet['candidate_manifest'],
      native_terminal=terminal_ref,native_release=release_ref,exit_status=0,primary_error=None,parent_runner_sha256=packet['scripts']['launch_native.py'],
      native_child_process=dict(child_exit=0,child_result=terminal_ref,primary_error=None,retirement_error=None,native_owner_after={'process':True,'thread':True,'job':True},native_owner={'image_sha256':'python-pin','pid':123,'creation_time':456}),
      native_child_argv=argv,native_child_cwd=str(R),Git_observed=packet['Git'],environment=packet['environment'],Source_before=source_ref,
      Source_observed=source_targets,fixture_dependencies_observed=packet['fixture_dependencies'],interpreter=interpreter,
      started_at_ns=100,finished_at_ns=200,source_publication=False,product_acceptance=False)
    def proof(ref):
        if ref==terminal_ref:return F/ref['repository_relative_path'],term
        if ref==parent_ref:return F/ref['repository_relative_path'],parent
        if ref==source_ref:return None,{'targets':source_targets}
        if ref==release_ref:return F/ref['repository_relative_path'],{'issued_at_ns':90,'expires_at_ns':300}
        raise AssertionError('UNKNOWN_OR_ABSENT_PROOF')
    n={'R':R,'F':F,'proof':proof,'packet':lambda:packet,'exact_ref':lambda path:packet_ref,
       'inputs':lambda:env,'interpreter_observation':lambda value:interpreter,
       'proof_bytes':lambda ref:(F/ref['repository_relative_path'],b'controlled')}
    extract(R/'js9_support.py',{'require_native_terminal','require_native_corroboration'},n)
    control(phase+'_exact_parent_and_terminal_accepted',lambda:n['require_native_corroboration'](parent_ref,phase))
    for field,bad in [('passed',False),('post_CAS_verified',False),('acceptance_complete',True),('tests_run',0),('expected_ids',ids[:-1]),('runner_sha256','wrong')]:
        old=term[field];term[field]=bad
        control(phase+'_terminal_'+field+'_refused',lambda:n['require_native_corroboration'](parent_ref,phase),False);term[field]=old
    for field,bad in [('accepted',False),('exit_status',1),('Git_observed',None),('Source_observed',{}),('fixture_dependencies_observed',{}),('interpreter',{}),('environment',{}),('packet',{}),('candidate_manifest',{}),('parent_runner_sha256','wrong')]:
        old=parent[field];parent[field]=bad
        control(phase+'_parent_'+field+'_refused',lambda:n['require_native_corroboration'](parent_ref,phase),False);parent[field]=old
    child=parent['native_child_process']
    for field,bad in [('child_exit',1),('retirement_error',{'pending':True}),('native_owner_after',{'job':False}),('child_result',{})]:
        old=child[field];child[field]=bad
        control(phase+'_child_'+field+'_refused',lambda:n['require_native_corroboration'](parent_ref,phase),False);child[field]=old
    old=parent['native_child_argv'];parent['native_child_argv']=old.copy();parent['native_child_argv'][4]='foreign.py'
    control(phase+'_wrong_child_command_refused',lambda:n['require_native_corroboration'](parent_ref,phase),False);parent['native_child_argv']=old
    old=term['observed_argv'];term['observed_argv']=[]
    control(phase+'_missing_observed_argv_refused',lambda:n['require_native_corroboration'](parent_ref,phase),False);term['observed_argv']=old

# Downstream requirement occurs in the actual release body, for all three phases.
release_node=next(x for x in support.body if isinstance(x,ast.FunctionDef) and x.name=='require_release')
calls_to_corroboration=[x for x in ast.walk(release_node) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='require_native_corroboration']
check('BOTH_NATIVE_CORROBORATIONS_MANDATORY',len(calls_to_corroboration)==2 and {x.args[1].value for x in calls_to_corroboration}=={'native-store','native-observer'})
check('CONDITION_COVERS_FULL_AND_PUBLICATION',any(isinstance(x,ast.If) and isinstance(x.test,ast.Compare) and isinstance(x.test.left,ast.Name) and x.test.left.id=='phase' and any(isinstance(y,ast.Tuple) and {z.value for z in y.elts}=={'candidate-full','destination-full','publish'} for y in x.test.comparators) for x in ast.walk(release_node)))
launcher=ast.parse((R/'launch_native.py').read_text())
owned_calls=[x for x in ast.walk(launcher) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='run_owned']
check('ONE_NATIVE_CHILD_OWNED300S',len(owned_calls)==1 and any(k.arg=='timeout' and k.value.value==300 for k in owned_calls[0].keywords))
verify_calls=[x for x in ast.walk(launcher) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='verify']
check('PARENT_BOTH_CHECKS_DEFAULT_GIT',len(verify_calls)==2 and all(not any(k.arg=='verify_git' for k in x.keywords) for x in verify_calls))
check('ALL_REVIEW_INPUTS_STABLE',all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in inputs.items()))
result=dict(status='PASS',at=datetime.now(timezone.utc).isoformat(),reviewer='/root/recovery_join_review20',
 mode='FILE_AST_AND_SYNTHETIC_VALUE_ONLY',native_calls=False,subprocess_calls=False,tool_or_product_imports=False,
 checks=checks,control_count=len(controls),controls=controls,inputs_sha256=inputs,stable_inputs=len(inputs),
 false_Git_sites=false_sites,packet_sha256=sha(R/'PACKET.json'))
with (D/'REPAIR-CONTROLS.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('checks','controls','inputs_sha256')}))
