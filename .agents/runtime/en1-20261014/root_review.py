"""Independent executable review of EN1's bounded DATA_ONLY contract."""
from en1_support import *
import en1_support,importlib,unittest
D=R/'independent-root-review';D.mkdir(exist_ok=False)
en1_support.ACTOR=ACTOR='/root'
claim=en1_support.claim('review')
manifest_path=Q/'TRANSFER-MANIFEST.json'
assert sha(manifest_path)=='e6a001dc304fd9cd537c6fb3ce92f357736e42d8bdc820d097c0e1186ed017b0'
manifest=json.loads(manifest_path.read_text());rows={row['relative_path']:row for row in manifest['payloads']}
assert len(rows)==295
before={name:ordinary(Q/name) for name in rows}
assert all(value['sha256']==rows[name]['candidate_sha256'] and value['native_identity']==rows[name]['candidate_native_identity'] for name,value in before.items())
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text())
source_before={name:ordinary(P/name) for name in inputs['current290']};assert source_before==inputs['current290']
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
modules=[importlib.import_module(name) for name in ('test_owner_enrollment','test_temporal','test_wire','test_all_records')]
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
def ids(group):
    for case in group:
        if isinstance(case,unittest.TestSuite):yield from ids(case)
        else:yield case.id()
expected=list(ids(suite));assert len(expected)==len(set(expected))==82
executed,stopped=[],[]
class Recorder(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
with (D/'tests.txt').open('x',encoding='utf-8') as out:result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Recorder).run(suite)
after={name:ordinary(Q/name) for name in rows}
source_after={name:ordinary(P/name) for name in inputs['current290']}
assert result.wasSuccessful() and not result.skipped and expected==executed==stopped and before==after and source_before==source_after
proof={'recorded_at':utc(),'executor_id':ACTOR,'decision':'approved','tests_run':82,'new_product_cases':35,
 'retained_cases':47,'failures':0,'errors':0,'skips':0,'expected_ids':expected,'executed_ids':executed,'stopped_ids':stopped,
 'before':before,'after':after,'source_before':source_before,'source_after':source_after,
 'module_origins':{name:str(Path(module.__file__)) for name,module in sys.modules.items() if name.startswith('ceta') and getattr(module,'__file__',None)},
 'manifest_sha256':sha(manifest_path),'raw':reference(D/'tests.txt'),
 'qualification':'Immutable data, bounded codecs, native identity declarations, exact display/transcript bindings and temporal checks only. No native enrollment, authority or Source publication accepted.',
 'personal_review':['Read complete contract, all35 new tests and frozen API.',
 'Exact canonical database leaf/volume/file IDs, bounded dual operation and recovery budgets, reserve remaining after recovery, both clock sample types/currentness, distinct transcript domain and explicit DATA_ONLY checked.',
 'Preserved native measured zero versus unavailable, exact signed wire bounds, strict shape/canonical parsing and no mutable alias.']}
assert all(Path(path).is_relative_to(Q/'src') for path in proof['module_origins'].values())
write_new(D/'REPORT.json',proof)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
from taar.orchestration_receipts import validate_receipt
changed=_changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')));assert changed==[]
receipt={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':ACTOR,'started_at':claim['claimed_at'],
 'finished_at':utc(),'input_hash':claim['input_hash'],'changed_files':[],
 'result':{'manifest_sha256':sha(manifest_path),'report':reference(D/'REPORT.json'),'tests_run':82,'assurance':'DATA_ONLY'},
 'commands':[{'command':str(PY)+' -B -X utf8 '+str(Path(__file__)),'exit_status':0}],
 'validations':[{'name':'82_unique_cases_pass_and_actual_candidate295_Source290_native_bytes_conserved','passed':True}],
 'exit_status':0,'decision':'approved'}
validate_receipt(receipt,run_id=RUN,node_id='review',executor_id=ACTOR,input_hash=claim['input_hash'],
 claimed_at=claim['claimed_at'],node=json.loads((R/RUN/'graph.json').read_text())['graph']['nodes']['review'])
write_new(D/'review.json',receipt)
response=en1_support.invoke(['node','complete',RUN,'review',str(D/'review.json')],'root-review-complete')
state=json.loads((R/RUN/'state.json').read_text());assert state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED'
assert json.loads((R/RUN/'claims.json').read_text())=={}
write_new(D/'ACTUAL-READBACK.json',{'response':response,'state':state,'claims':{},
 'persisted_receipt':json.loads((R/RUN/'receipts/review.json').read_text())})
print(json.dumps({'approved':True,'tests':82,'review_sha256':sha(D/'review.json'),'Source_changes':[]}),flush=True)
