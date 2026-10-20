"""Execute the exact amended Result.startTest boundary with controlled objects."""
from pathlib import Path
import ast,io,json,sys,unittest
F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/f4-full-gate-successor-20261015'
Q=R/'candidate';D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(Q));import full_gate as gate
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R
assert s.sha(Q/'full_gate.py')=='a78d7fd3ebe4803d43b48e3ef9dbfc03b29d4b401808c35aab37e7c2909448f1'
parent=F/'.agents/runtime/re-foundation4-20261015/run_joined.py'
amended=gate.amend_runner(parent.read_bytes())
tree=ast.parse(amended)
node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Result')
entered=[]
class ControlledGate:
    def enter(self,test_id):entered.append(test_id)
class ControlledCase(unittest.TestCase):
    def id(self):return gate.CASE
    def runTest(self):raise AssertionError('No test body should execute in this boundary probe')
env={'__name__':'root_f4_exact_result_boundary','unittest':unittest,'active_case_id':None,
     'executed':[],'stopped':[],'deferred_case':gate.CASE,'__execution_gate':ControlledGate()}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(parent)+'#exact-Result','exec'),env)
result=env['Result'](io.StringIO(),False,0);raised=None
try:result.startTest(ControlledCase())
except BaseException as error:raised=error
assert type(raised) is NameError
assert getattr(raised,'name',None)=='_Result__execution_gate'
assert entered==[] and env['executed']==[] and result.testsRun==0
proof={'at':s.utc(),'reviewer':'/root','classification':'VERIFIED_ENGINEERING_RUNNER_DEFECT',
 'gate':s.reference(Q/'full_gate.py'),'parent_runner':s.reference(parent),
 'amended_runner_sha256':gate.digest(amended.encode()),'exact_class_AST_executed':True,
 'controlled_original_case_id':gate.CASE,'exception_type':type(raised).__name__,'exact_exception_text':str(raised),
 'mangled_global_name':raised.name,'namespace_provided_global':'__execution_gate',
 'gate_enter_calls':entered,'executed_method_ids':env['executed'],'test_bodies_executed':0,
 'native_operations':[],'CETA_imports':[], 'source_changes':[],
 'finding':'A double-underscore global inside Result.startTest is name-mangled to _Result__execution_gate. The injected namespace defines only __execution_gate, so the original required case aborts before gate admission.',
 'next_repair':'Use an unmangled global binding or explicit captured globals lookup; retain this literal original-class oracle and test successful original-case admission before another review.',
 'full2053_executed':False,'Source_publication':False,'probe_exit_status':0}
s.write_new(D/'ORIGINAL-CASE-BOUNDARY-DEFECT-R1.json',proof)
print(json.dumps({'verified_defect':True,'error':str(raised),'native_operations':0,
 'proof':s.reference(D/'ORIGINAL-CASE-BOUNDARY-DEFECT-R1.json')}))
