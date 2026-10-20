"""Pure exact-function checks for dormant ordering and Source-claim fences.

No candidate modules, test bodies, native runtimes or release files are loaded.
Synthetic mappings below are Python inputs, never authority records.
"""
from pathlib import Path
import ast,copy,fnmatch,hashlib,importlib,json,random,sys,unittest
from types import SimpleNamespace

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;D=R/'successor-r1'
Q=F/'.agents/js9-runtime-20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cases=json.loads((D/'CASESET.json').read_bytes());rows=[]
def function(path,name,namespace):
    node=next(n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path)+'#pure-function-only','exec'),namespace)
    return namespace[name]

class Case(unittest.TestCase):
    def __init__(self,name):super().__init__('runTest');self.name=name
    def id(self):return self.name
    def runTest(self):raise AssertionError('Synthetic case bodies must never run')

namespace=dict(Path=Path,proof=lambda reference:(D/'CASESET.json',cases),packet=lambda:dict(case_set='PURE_CASE_INPUT'))
ordered=function(D/'js9_support.py','ordered_suite',namespace)
normal=[name for name in cases['expected_ids'] if not name.startswith('reasoning.')]
class Loader:
    def loadTestsFromModule(self,module):
        return unittest.TestSuite(Case(name) for name in cases['expected_ids'] if name.startswith(module.name+'.'))
def check(label,operation,allowed):
    try:value=operation();observed=True;error=None
    except AssertionError as caught:observed=False;error=str(caught)
    assert observed is allowed,(label,observed,error)
    rows.append(dict(case=label,passed=True,allowed=observed,error=error))

original_import=importlib.import_module
def module(name):return SimpleNamespace(name=name,__file__=str(Q/'tests/contract'/Path(name.replace('.','/')+'.py')))
try:
    importlib.import_module=module
    def successful_order():
        supplied=list(reversed(normal))
        result=ordered(unittest.TestSuite(Case(n) for n in supplied),Q,Loader())
        actual=[test.id() for test in result]
        assert actual==cases['expected_ids'] and len(actual)==2622
        assert sum(name.startswith('reasoning.') for name in actual)==50
        assert [n for n in actual if n in set(cases['parent2334_ids'])]==cases['parent2334_ids']
    check('all2622_exact_order_and_explicit50_namespace_cases',successful_order,True)
    check('missing_original_case_denied',lambda:ordered(unittest.TestSuite(Case(n) for n in normal[1:]),Q,Loader()),False)
    check('duplicate_discovered_case_denied',lambda:ordered(unittest.TestSuite(Case(n) for n in normal+[normal[0]]),Q,Loader()),False)
    check('unexpected_discovered_case_denied',lambda:ordered(unittest.TestSuite(Case(n) for n in normal+['unexpected.X.test_y']),Q,Loader()),False)
    importlib.import_module=lambda name:SimpleNamespace(name=name,__file__=str(F/'unrelated.py'))
    check('namespace_module_outside_exact_candidate_denied',lambda:ordered(unittest.TestSuite(Case(n) for n in normal),Q,Loader()),False)
finally:importlib.import_module=original_import

paths=json.loads((D/'PACKET.json').read_bytes())['application_paths']
claim=dict(executor_id='/root',workspace=str(F),input_hash='PURE_SYNTHETIC_NOT_AUTHORITY',
    claimed_at='PURE_TIME',effective_write_scope=paths)
state=dict(run_id='PURE_SYNTHETIC',nodes=dict(integrate=dict(state='RUNNING',executor_id='/root',claim=claim)))
lease=dict(claims='PURE_CLAIMS',state='PURE_STATE',node_id='integrate',input_hash=claim['input_hash'],
    claimed_at=claim['claimed_at'],run_id=state['run_id'])
store={'PURE_CLAIMS':dict(integrate=claim),'PURE_STATE':state}
namespace=dict(F=F,fnmatch=fnmatch,j=SimpleNamespace(proof=lambda name:(None,store[name])))
require=function(D/'publish_source.py','require_source_claim',namespace)
check('exact31_paths_with_matching_running_Source_claim',lambda:require(dict(source_lease=lease),paths),True)
for label,change in [
    ('foreign_executor',lambda c,st:c.update(executor_id='other')),
    ('wrong_workspace',lambda c,st:c.update(workspace=str(Q))),
    ('missing31st_write_scope',lambda c,st:c.update(effective_write_scope=paths[:-1])),
    ('completed_claim',lambda c,st:st['nodes']['integrate'].update(state='SUCCEEDED')),
    ('claim_input_mismatch',lambda c,st:c.update(input_hash='MISMATCH')),
    ('state_executor_mismatch',lambda c,st:st['nodes']['integrate'].update(executor_id='other')),
]:
    c=copy.deepcopy(claim);st=copy.deepcopy(state);change(c,st)
    store['PURE_CLAIMS']=dict(integrate=c);store['PURE_STATE']=st
    check(label+'_denied',lambda:require(dict(source_lease=lease),paths),False)
report=dict(scope='Pure exact AST function bodies with in-memory synthetic records; no authority issued',
    tests=len(rows),cases=rows,all_passed=True,
    sources={name:sha(D/name) for name in ['js9_support.py','publish_source.py','CASESET.json','PACKET.json']},
    candidate_imports=False,product_tests=False,native_calls=False,Source_mutation=False)
with (D/'PURE-CONTROLS-R2.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(cases=len(rows),all_passed=True,result_sha256=sha(D/'PURE-CONTROLS-R2.json'))),flush=True)
