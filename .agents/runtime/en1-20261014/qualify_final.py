from en1_support import *
import ast, io, tokenize

eligible=['src/ceta/contracts/owner_enrollment.py','tests/contract/test_owner_enrollment.py','contracts/OWNER_ENROLLMENT_V1.md']
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());final=json.loads((R/'final-r5.json').read_text())
assert final['exit_status']==0 and final['tests_run']==82 and final['new_cases']==35 and final['retained_cases']==47
assert final['failures']==final['errors']==final['skips']==[]
assert final['expected_ids']==final['executed_ids']==final['stopped_ids']
assert final['live_thread_names']==['MainThread']
assert all(ordinary(Q/name)==row for name,row in final['candidate_after'].items())
source={name:ordinary(P/name) for name in inputs['current290']};assert source==inputs['current290']
core=source_inventory();expected_core={name:row for name,row in source.items() if name.split('/')[0] in ('src','tests','contracts')}
assert core==expected_core
assert all(not (P/name).exists() for name in eligible)
assert final['contract_module']==str(Q/'src/ceta/contracts/owner_enrollment.py')
for name,path in final['module_origins'].items():assert Path(path)==Q/'tests/contract'/(name+'.py')
for name,record in inputs['dependencies'].items():
    assert ordinary(Path(record['source']['path']))==record['source']
    assert sha(Q/name)==record['source']['sha256']

retained={}
for filename in ('test_temporal.py','test_wire.py','test_all_records.py'):
    name='tests/contract/'+filename
    assert fs.read_bytes(Q/name)==fs.read_bytes(P/name)
    retained[filename]={node.name:digest(ast.dump(node,include_attributes=False).encode())
        for node in ast.walk(ast.parse(fs.read_bytes(Q/name).decode('utf-8-sig')))
        if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')}
assert sum(len(value) for value in retained.values())==47

baseline=json.loads((R/'baseline-r1.json').read_text());reserve=json.loads((R/'reserve-baseline-r2.json').read_text())
assert baseline['exit_status']==reserve['exit_status']==1
assert len(baseline['failures'])==1 and not baseline['errors']
assert len(reserve['failures'])==2 and not reserve['errors']
for label,cutname in (('baseline-r1','baseline-r1'),('reserve-baseline-r2','reserve-baseline-r2'),('final-r3','final-r3'),('clock-boundary-baseline-r4','clock-boundary-baseline-r4')):
    prior=json.loads((R/(label+'.json')).read_text())
    for name in eligible:
        assert sha(R/'cuts'/cutname/name)==prior['candidate_before'][name]['sha256']
clock_baseline=json.loads((R/'clock-boundary-baseline-r4.json').read_text())
assert clock_baseline['exit_status']==1 and len(clock_baseline['failures'])==6 and clock_baseline['errors']==[]
write_new(R/'PRIOR-ATTEMPTS-FINAL.json',{'recorded_at':utc(),'earlier_lineage':reference(R/'PRIOR-ATTEMPTS.json'),
    'earlier_passing_cut':reference(R/'CUT-R3.json'),'clock_baseline':reference(R/'clock-boundary-baseline-r4.json'),
    'clock_cut':str(R/'cuts/clock-boundary-baseline-r4'),'fixed_clock_boundary':'Both exact ClockSample values are revalidated before temporal predicates; no temporal module change',
    'raw_nonzero_relabelled':False})

environment_root=P/'.agents/source-assembly-20261014T021300Z/.agents/e3'
baseline_path=P/'.agents/runtime/er1-20261014/active-application/destination-verification.json'
expected=json.loads(baseline_path.read_text())['expected_environment_files']
environment={name:ordinary(environment_root/name) for name in expected};assert len(environment)==3601
assert all(environment[name]['sha256']==row['sha256'] for name,row in expected.items())
assert ordinary(PY)==inputs['interpreter']
git_after={'HEAD':fs.text_git(P,'rev-parse','HEAD'),'branch':fs.text_git(P,'branch','--show-current'),
    'tracked_status':fs.text_git(P,'status','--porcelain=v1','-uno')}
assert all(git_after[name]==inputs[name] for name in git_after)
write_new(R/'CONSERVATION-FINAL.json',{'recorded_at':utc(),'source_before':inputs['current290'],'source_after':source,
    'source_payload_count':290,'actual_core_path_count':len(core),'actual_core_matches_input':True,
    'git_after':git_after,'dependencies':inputs['dependencies'],'environment_root':str(environment_root),
    'environment_baseline':reference(baseline_path),'environment_files':environment,'environment_ordinary_count':3601,
    'limit':'Recorded290 full Source payload/native endpoint equality plus fresh exact core inventory. E33601 hashes match historical accepted ER1 endpoint, initial/final interpreter identity exact; uninterrupted custody/full earlier environment snapshot not inferred.',
    'native_effects':[],'source_published':False})
def loc(path):
    text=fs.read_bytes(path).decode('utf-8-sig');lines=text.splitlines()
    if path.suffix!='.py':return {'physical_lines':len(lines),'meaningful_lines':None}
    docs=set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and node.body:
            first=node.body[0]
            if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and type(first.value.value) is str:
                docs.update(range(first.lineno,first.end_lineno+1))
    active=set()
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type not in (tokenize.COMMENT,tokenize.ENCODING,tokenize.INDENT,tokenize.DEDENT,tokenize.NL,tokenize.NEWLINE,tokenize.ENDMARKER) and token.string.strip():
            active.update(range(token.start[0],token.end[0]+1))
    return {'physical_lines':len(lines),'meaningful_lines':len(active-docs)}
measures={name:loc(Q/name) for name in eligible}
write_new(R/'LOC-FINAL.json',{'recorded_at':utc(),'files':measures,'retained47_method_AST':retained,
    'new_test_methods':34,'reused290_and2dependency_LOC_credit':0,'runtime_LOC_credit':0,
    'method':'Python token-bearing lines excluding blank/comment/actual AST docstring lines; documentation has zero executable LOC'})
sys.path.insert(0,str(Q/'src'))
from ceta.contracts.owner_enrollment import EnrollmentRequest, NativeObjectIdentity, OwnerTokenFacts
from dataclasses import fields
write_new(R/'EXPORTED-API-FINAL.json',{'recorded_at':utc(),'module':ordinary(Q/eligible[0]),
    'types':{kind.__name__:[field.name for field in fields(kind)] for kind in (NativeObjectIdentity,OwnerTokenFacts,EnrollmentRequest)},
    'functions':['decode_enrollment_request','enrollment_display_bytes','enrollment_display_commitment',
        'require_enrollment_current(request,expected,previous_clock,current_clock)','enrollment_transcript_bytes',
        'decode_enrollment_transcript','enrollment_transcript_commitment',
        'require_enrollment_transcript_binding(request,expected,transcript,previous_clock,current_clock)'],
    'assurance':'DATA_ONLY','private_database_leaf':'history.sqlite3'})
write_new(R/'QUALIFICATION-FINAL.json',{'recorded_at':utc(),'tests':reference(R/'final-r5.json'),'tests_run':82,
    'new_cases':35,'retained_cases':47,'exact_ids':final['executed_ids'],'prior_attempts':reference(R/'PRIOR-ATTEMPTS-FINAL.json'),
    'conservation':reference(R/'CONSERVATION-FINAL.json'),'LOC':reference(R/'LOC-FINAL.json'),'API':reference(R/'EXPORTED-API-FINAL.json'),
    'qualification':'Author pure DATA_ONLY contract tests; no native root/Hello/enrollment/epoch/grant/profile effect or authority validation.',
    'exit_status':0})
print(json.dumps({'tests':82,'new':35,'retained':47,'Source':290,'E3':3601,'LOC':measures,'qualified':True},indent=2))
