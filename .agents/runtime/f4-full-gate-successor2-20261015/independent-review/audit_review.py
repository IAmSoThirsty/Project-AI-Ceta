"""Read-only independent F4 successor2 conservation and exact delta qualification."""
from pathlib import Path
import ast,collections,importlib.util,json,os,stat,sys

F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/f4-full-gate-successor2-20261015'
Q=R/'candidate';D=Path(__file__).resolve().parent
OLD=F/'.agents/runtime/f4-full-gate-successor-20261015';OQ=OLD/'candidate'
PARENT=F/'.agents/runtime/re-foundation4-20261015';PQ=F/'.agents/re-foundation4-20261015'
RUN=R.name;ACTOR='/root/wt1_reviewer';sys.dont_write_bytecode=True
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN=RUN;s.ACTOR=ACTOR
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
from taar.orchestration_runtime import _snapshot_workspace,_changed_files,_artifact_hash

read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
inputs=read(R/'INPUTS.json');manifest=read(Q/'TRANSFER-MANIFEST.json')
seal=read(R/'AUTHOR-SEAL.json');oldseal=read(OLD/'AUTHOR-SEAL.json');oldqual=read(OLD/'QUALIFICATION.json')
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='9a9733b22c199f8c92510d2cedeae148a40b4c3b0a330ee4f11e49b9515124f1'
assert s.sha(R/'READY-FOR-REVIEW.json')=='967692476d65ab5748af383dcefda1eb0153dd35a3e72dd3088cdb1b08eece99'
assert s.sha(R/'AUTHOR-SEAL.json')=='13432f713709517c3391a2b1dff29df3ad04b069f9b91211c53971e590319fbf'
for name,row in seal['candidate_members'].items():assert s.ordinary(Q/name)==row
assert {p.name for p in Q.iterdir()}==set(seal['candidate_members'])
for name,row in seal['evidence_members'].items():assert s.ordinary(R/name)==row
for name,row in inputs['predecessor_candidate'].items():assert s.ordinary(OQ/name)==row
for name,row in oldseal['author_evidence_members'].items():assert s.ordinary(OLD/name)==row
for key in ('rejected_predecessor','exact_failure'):
    value=inputs[key];assert s.sha(F/value['repository_relative_path'])==value['sha256']
assert read(OLD/OLD.name/'state.json')['nodes']['review']['state']=='FAILED'
assert read(OLD/OLD.name/'claims.json')=={}
source={name:s.ordinary(F/name) for name in inputs['Source290']};assert source==inputs['Source290']
assert s.source_inventory()=={name:row for name,row in source.items() if name.split('/')[0] in ('src','tests','contracts')}
environment={name:s.ordinary(s.PY.parents[1]/name) for name in oldqual['E33601']}
assert environment==oldqual['E33601'] and len(environment)==3601
assert sum(v['bytes'] for v in environment.values())==231026067
def inventory(root):
    result={};pending=[root]
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path=directory/entry.name;info=s.fs.lstat(path);assert not s.fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):pending.append(path)
                else:assert stat.S_ISREG(info.st_mode);result[path.relative_to(root).as_posix()]=s.ordinary(path)
    return result
assert inventory(s.PY.parents[1])==environment
f4={name:s.ordinary(PQ/name) for name in oldqual['F4_candidate336']}
assert f4==oldqual['F4_candidate336'] and len(f4)==336
parents={name:s.ordinary(Path(row['path'])) for name,row in inputs['parent_scripts'].items()}
assert parents==inputs['parent_scripts']
for key in ('F4_manifest','parent_review','parent_report','parent_required_ids'):
    assert s.ordinary(Path(inputs[key]['path']))==inputs[key]
assert s.fs.text_git(F,'rev-parse','HEAD')==inputs['HEAD']
assert s.fs.text_git(F,'branch','--show-current')==inputs['branch']
assert s.fs.text_git(F,'status','--porcelain=v1','-uno')==inputs['dirty']

old=(OQ/'full_gate.py').read_text();new=(Q/'full_gate.py').read_text()
a='if active_case_id==deferred_case:__execution_gate.enter(active_case_id)'
b='if active_case_id==deferred_case:globals()["__execution_gate"].enter(active_case_id)'
assert old.count(a)==1 and old.replace(a,b)==new
assert (OQ/'run_authorized.py').read_text().replace('f4-full-gate-successor-20261015',RUN)==(Q/'run_authorized.py').read_text()
old=(OQ/'complete_authorized.py').read_text()
expected=old.replace('f4-full-gate-successor-20261015',RUN).replace("local['executor_id'] != '/root/history_preservation'","local['executor_id'] != '/root'")
assert expected==(Q/'complete_authorized.py').read_text()
test_methods=lambda text:{node.name:ast.dump(node,include_attributes=False) for node in ast.walk(ast.parse(text)) if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')}
oldtests=test_methods((OQ/'test_full_gate.py').read_text());newtests=test_methods((Q/'test_full_gate.py').read_text())
assert len(oldtests)==42 and len(newtests)==46 and all(newtests[name]==body for name,body in oldtests.items())
newnames=set(newtests)-set(oldtests);assert len(newnames)==4 and all(name.startswith('test_exact_original_Result_class_') for name in newnames)

sys.path.insert(0,str(Q));import full_gate as gate
amended_runner=gate.amend_runner((PARENT/'run_joined.py').read_bytes())
amended_completion=gate.amend_completion((PARENT/'complete_source.py').read_bytes())
assertions=lambda text:collections.Counter(ast.dump(node,include_attributes=False) for node in ast.walk(ast.parse(text)) if isinstance(node,ast.Assert))
removed=assertions((PARENT/'complete_source.py').read_text())-assertions(amended_completion)
assert sum(removed.values())==1 and 'reviewed_scripts' in next(iter(removed)) and 'Path' in next(iter(removed))
assert 'NO_PROFILE_MUTATION_IN_JOINED_RUNNER' in amended_runner
required=read(PARENT/'REQUIRED-SOURCE-TESTS.json')['required_ids']
assert len(required)==len(set(required))==2053 and required.count(gate.CASE)==1
assert gate.select_ids(required,authorized=True,partial=False)==(required,[])
partial,deferred=gate.select_ids(required,authorized=False,partial=True)
assert len(partial)==2052 and deferred==[gate.CASE]
proof=read(D/'controlled-r1/RESULT.json');assert proof['exit_status']==0 and proof['tests_run']==46
assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids'] and len(set(proof['expected_ids']))==46
assert not any(proof[k] for k in ('failures','errors','skips','forbidden_native_and_process_calls','remaining_threads','CETA_product_imports'))
assert proof['candidate_before']==proof['candidate_after']==seal['candidate_members']
assert proof['Source290_before']==proof['Source290_after']==source
assert proof['F4_candidate336_before']==proof['F4_candidate336_after']==f4
assert proof['F4_parent_scripts_before']==proof['F4_parent_scripts_after']==parents
assert proof['original_restricted_no_profile_case']=='NOT_RUN' and proof['full_Source2053_executed'] is False
assert proof['real_operator_authorization_created'] is False
assert s.sha(F/proof['raw']['repository_relative_path'])==proof['raw']['sha256']
assert s.sha(F/proof['driver']['repository_relative_path'])==proof['driver']['sha256']
author=read(R/'implement.json');stored=read(R/RUN/'receipts/implement.json');state=read(R/RUN/'state.json');claim=read(R/RUN/'claims.json')['review']
assert state['sequence']==8 and state['nodes']['review']['state']=='RUNNING' and claim['executor_id']==ACTOR
assert len(author)==12 and len(stored)==15 and canonical(author)==canonical({key:stored[key] for key in author})
assert state['nodes']['implement']['receipt_hash']==stored['receipt_hash']==sha256_json({key:value for key,value in stored.items() if key!='receipt_hash'})
assert read(R/RUN/'results/implement.json')==dict(node_id='implement',receipt_hash=stored['receipt_hash'],result=author['result'])
snapshot=_snapshot_workspace(Q,Path('T:/'));assert len(snapshot)==6 and _changed_files(claim['baseline_snapshot'],snapshot)==[]
assert state['nodes']['implement']['artifact_hash']==_artifact_hash(snapshot,stored['changed_files'])
record=dict(at=s.utc(),reviewer=ACTOR,decision='approved',scope='Dormant engineering successor only',
    manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),candidate6=seal['candidate_members'],
    source290=source,E33601=environment,F4candidate336=f4,parent_scripts=parents,
    predecessor6_and_author154_conserved=True,author74_conserved=True,
    original42_test_ASTs_exact=True,new_actual_Result_boundary_methods=sorted(newnames),
    controlled46=s.reference(D/'controlled-r1/RESULT.json'),
    exact_script_deltas=True,old_completion_assertions_retained_except_self_path=True,
    amended_runner_sha256=gate.digest(amended_runner.encode()),amended_completion_sha256=gate.digest(amended_completion.encode()),
    full_required_ids2053=required,actual2053executed=False,original_restricted_native_case='NOT_RUN',
    actual_operator_approval=False,metadata109_waived=False,whole_fixture_preservation_accepted=False,
    author_strict12_15_fingerprint_and_envelope=True,Source_publication=False,exit_status=0)
s.write_new(D/'CONSERVATION-AND-QUALIFICATION.json',record)
print(json.dumps(dict(proof=s.reference(D/'CONSERVATION-AND-QUALIFICATION.json'),controlled46=True,Source290=True,E33601=True,F4candidate336=True,exact_script_deltas=True,full2053='NOT_RUN')))
