"""Exact final IDs, original22ASTs and actual single author release/readback."""
from ac_support import *
import ast
read=lambda path:json.loads(Path(path).read_text())
local=read(R/'implement.json');stored=read(R/RUN/'receipts/implement.json')
strict={'schema_version','run_id','node_id','executor_id','started_at','finished_at','input_hash',
    'changed_files','result','commands','validations','exit_status'}
typed=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
assert set(local)==strict and set(stored)==strict|{'git_baseline','observed_git','receipt_hash'}
assert all(typed(local[n])==typed(stored[n]) for n in strict)
state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json')
assert state['sequence']==7 and state['nodes']['implement']['state']=='SUCCEEDED'
assert state['nodes']['review']['state']=='READY' and claims=={}
manifest=read(Q/'TRANSFER-MANIFEST.json');assert local['result']['manifest']==reference(Q/'TRANSFER-MANIFEST.json')
for name,row in manifest['payloads'].items():assert ordinary(Q/name)==row
parent=F/'.agents/ac4-20261015';parent_manifest=read(parent/'TRANSFER-MANIFEST.json')
old=read(F/parent_manifest['qualification']['repository_relative_path']);final=read(R/'focused-r1/RESULT.json')
literal=read(R/'literal-closure-r2.json');baseline=read(R/'baseline-r1.json')
assert len(old['expected_ids'])==22 and set(old['expected_ids'])<=set(final['expected_ids'])
assert final['expected_ids']==final['executed_ids']==final['stopped_ids'] and len(set(final['expected_ids']))==26
assert literal['literal_class_AST_sha256']==baseline['literal_class_AST_sha256']
assert len(literal['executed_ids'])==2 and literal['executed_ids']==baseline['executed_ids']
ast_rows={}
for test_id in old['expected_ids']:
    module,cls,name=test_id.split('.')
    def select(root):
        tree=ast.parse((root/'tests/contract'/(module+'.py')).read_text())
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
        return next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name)
    original,current=select(parent),select(Q)
    original_dump=ast.dump(original,include_attributes=False);current_dump=ast.dump(current,include_attributes=False)
    assert original_dump==current_dump
    ast_rows[test_id]=digest(current_dump.encode())
write_new(R/'FINAL-ID-CONSERVATION.json',{'at':utc(),'final26_expected_ids':final['expected_ids'],
    'final26_executed_ids':final['executed_ids'],'original22_ids':old['expected_ids'],
    'original22_method_AST_sha256':ast_rows,'all_original22_method_ASTs_exact':True,
    'final_literal2_ids':literal['executed_ids'],'literal_class_AST_sha256':literal['literal_class_AST_sha256'],
    'qualification':reference(R/'focused-r1/RESULT.json'),'literal_closure':reference(R/'literal-closure-r2.json'),
    'frozen_manifest':reference(Q/'TRANSFER-MANIFEST.json'),'same295payloads':True,
    'profile_permission_reused':False,'profile_operations':[],'worker_launches':[]})
inputs=read(R/'SOURCE-INPUTS.json');assert {name:ordinary(F/name) for name in inputs['Source290']}==inputs['Source290']
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_graph import compile_graph
graph=read(R/RUN/'graph.json');assert compile_graph(Path('T:/'),Q).fingerprint==graph['fingerprint']==state['graph_fingerprint']
write_new(R/'AUTHOR-READBACK.json',{'at':utc(),'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'implement':reference(R/'implement.json'),'persisted_implement':reference(R/RUN/'receipts/implement.json'),
    'all12_authored_fields_typed_exact':True,'sequence':7,'implement_state':'SUCCEEDED','review_state':'READY','claims':{},
    'graph_fingerprint':state['graph_fingerprint'],'final_ID_conservation':reference(R/'FINAL-ID-CONSERVATION.json'),
    'frozen_payloads':295,'Source290_exact':True,'Source_application':False})
names=('implement.json','AUTHOR-READBACK.json','FINAL-ID-CONSERVATION.json','HANDOFF.json','SELF-REVIEW.json',
    'implementation-measures.json','publication-before-images.json','input-conservation.json','environment-after.json',
    'PRIOR-FAILURES.json','baseline-r1.json','baseline-r1.txt','literal-closure-r2.json','literal-closure-r2.txt',
    'focused-r1/RESULT.json','focused-r1/tests.txt')
write_new(R/'AUTHOR-SEAL.json',{'sealed_at':utc(),'author':ACTOR,'manifest':reference(Q/'TRANSFER-MANIFEST.json'),
    'members':{name:reference(R/name) for name in names},'actual_implement_state':'SUCCEEDED','review_state':'READY',
    'claims':{},'further_author_writes':'CLOSED','distinct_review_required':True,'Source_application':False,
    'profile_operations':[],'worker_launches':[]})
print(json.dumps({'implement':'SUCCEEDED','review':'READY','sequence':7,'claims':{},
    'manifest':reference(Q/'TRANSFER-MANIFEST.json'),'implement_receipt':reference(R/'implement.json'),
    'readback':reference(R/'AUTHOR-READBACK.json'),'seal':reference(R/'AUTHOR-SEAL.json'),
    'final_IDs':reference(R/'FINAL-ID-CONSERVATION.json')}))
