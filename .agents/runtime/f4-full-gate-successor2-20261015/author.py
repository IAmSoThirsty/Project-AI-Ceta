"""Narrow successor repair of the rejected original-class gate binding."""
from pathlib import Path
import ast,difflib,json,os,sys
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;Q=R/'candidate';RUN=R.name
OLD=F/'.agents/runtime/f4-full-gate-successor-20261015';OQ=OLD/'candidate'
sys.dont_write_bytecode=True;sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q=Q;s.R=R;s.RUN=RUN;s.ACTOR='/root'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(path,text):
 with Path(path).open('x',encoding='utf-8',newline='\n') as out:out.write(text)
def same_functions(old,new):
 collect=lambda raw:{n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef)}
 a,b=collect(old),collect(new)
 return {n for n in a if a[n]!=b[n]}
mode=sys.argv[1]
if mode=='begin':
 assert read(OLD/OLD.name/'state.json')['nodes']['review']['state']=='FAILED'
 assert read(OLD/OLD.name/'claims.json')=={}
 assert s.sha(OLD/'independent-review/ORIGINAL-CASE-BOUNDARY-DEFECT-R1.json')=='95fa453a0ced8b0e858df50ded56a2a065f0be1cf53ec4d1f726e4926392ef71'
 Q.mkdir(exist_ok=False)
 s.invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN],'run-init')
 s.claim('discover')
 old_inputs=read(OLD/'INPUTS.json')
 inputs=dict(old_inputs)
 inputs.update(at=s.utc(),author='/root',reason='Repair only the verified original Result class gate-name mangling; preserve rejected predecessor.',
  rejected_predecessor=s.reference(OLD/'independent-review/REJECTED-ACTUAL-READBACK.json'),
  exact_failure=s.reference(OLD/'independent-review/ORIGINAL-CASE-BOUNDARY-DEFECT-R1.json'),
  predecessor_candidate={p.name:s.ordinary(p) for p in OQ.iterdir() if p.is_file()})
 s.write_new(R/'INPUTS.json',inputs)
 s.complete('discover',{'inputs':s.reference(R/'INPUTS.json')},[],[('Exact rejected cut and NameError identified',True)])
 s.claim('plan')
 s.write_new(R/'TASK-BINDING.json',{'at':s.utc(),'author':'/root','candidate_root':str(Q),
  'write_paths':['full_gate.py','run_authorized.py','complete_authorized.py','test_full_gate.py','README.md','TRANSFER-MANIFEST.json'],
  'repair':'Explicit global lookup at original Result.startTest; exact positive and denied class-boundary tests; successor path and distinct-author identity bindings only.',
  'no_Source_application':True,'no_native_test_authorization':True,'required_distinct_reviewer':'/root/wt1_reviewer'})
 s.complete('plan',{'binding':s.reference(R/'TASK-BINDING.json')},[],[('Single bounded engineering repair with nonoverlapping scope',True)])
 s.claim('implement')
 for name in ('full_gate.py','run_authorized.py','complete_authorized.py','test_full_gate.py','README.md'):
  before=(OQ/name).read_text(encoding='utf-8');text=before
  if name=='full_gate.py':
   old='if active_case_id==deferred_case:__execution_gate.enter(active_case_id)'
   assert text.count(old)==1
   text=text.replace(old,'if active_case_id==deferred_case:globals()["__execution_gate"].enter(active_case_id)')
   # This text is itself embedded in a single-quoted Python source literal.
  elif name=='run_authorized.py':
   assert text.count('f4-full-gate-successor-20261015')==1
   text=text.replace('f4-full-gate-successor-20261015',RUN)
  elif name=='complete_authorized.py':
   assert text.count('f4-full-gate-successor-20261015')==1
   text=text.replace('f4-full-gate-successor-20261015',RUN)
   old="local['executor_id'] != '/root/history_preservation'";assert text.count(old)==1
   text=text.replace(old,"local['executor_id'] != '/root'")
  elif name=='test_full_gate.py':
   extra=(R/'boundary_methods.txt').read_text(encoding='utf-8')
   anchor="if __name__ == '__main__':"
   assert text.count(anchor)==1
   text=text.replace(anchor,extra+'\n\n'+anchor)
  else:
   text+='\nThis second engineering cut repairs the verified class-name-mangling defect.\nThe original Result class AST is executed by four additional controlled boundary\nchecks: admitted original case, unstarted gate, repeated original entry, and an\nordinary case. None executes a CETA test body or native effect. The predecessor\nremains formally rejected; reused code receives zero new implementation credit.\n'
  put(Q/name,text)
 driver=(OLD/'run_tests.py').read_text().replace("s.RUN='f4-full-gate-successor-20261015';s.ACTOR='/root/history_preservation'", "s.RUN='"+RUN+"';s.ACTOR='/root'")
 put(R/'run_tests.py',driver)
 print(json.dumps({'run':RUN,'implement':'RUNNING','candidate_files':5,'Source_publication':False}))
elif mode=='finish':
 proof=read(R/'tests-r1/RESULT.json');assert proof['tests_run']==46 and proof['exit_status']==0
 assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids']
 assert not any(proof[k] for k in ('failures','errors','skips','forbidden_native_and_process_calls','remaining_threads'))
 inputs=read(R/'INPUTS.json');prior=read(OLD/'QUALIFICATION.json')
 for name,row in inputs['Source290'].items():assert s.ordinary(F/name)==row
 for name,row in prior['F4_candidate336'].items():assert s.ordinary(Path(row['path']))==row
 for name,row in prior['E33601'].items():assert s.ordinary(s.PY.parent.parent/name)==row
 for name,row in inputs['predecessor_candidate'].items():assert s.ordinary(OQ/name)==row
 for name,row in read(OLD/'AUTHOR-SEAL.json')['author_evidence_members'].items():assert s.ordinary(OLD/name)==row
 assert read(OLD/OLD.name/'state.json')['nodes']['review']['state']=='FAILED'
 assert s.fs.text_git(F,'rev-parse','HEAD')==inputs['HEAD']
 assert s.fs.text_git(F,'branch','--show-current')==inputs['branch']
 assert s.fs.text_git(F,'status','--porcelain=v1','-uno')==inputs['dirty']
 for name in ('full_gate.py','run_authorized.py','complete_authorized.py','test_full_gate.py'):
  expected={'full_gate.py':{'amend_runner'},'run_authorized.py':{'main'},'complete_authorized.py':{'require_successor_review'},'test_full_gate.py':set()}
  assert same_functions((OQ/name).read_text(),(Q/name).read_text())==expected[name]
 oldtests={n.name for n in ast.walk(ast.parse((OQ/'test_full_gate.py').read_text())) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
 newtests={n.name for n in ast.walk(ast.parse((Q/'test_full_gate.py').read_text())) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
 assert len(oldtests)==42 and len(newtests-oldtests)==4
 payloads={p.name:s.ordinary(p) for p in Q.iterdir() if p.is_file()}
 (R/'diffs').mkdir()
 for name in payloads:
  put(R/'diffs'/(name+'.diff'),''.join(difflib.unified_diff((OQ/name).read_text().splitlines(True),(Q/name).read_text().splitlines(True),fromfile='rejected-v1/'+name,tofile='repaired-v2/'+name)))
 scripts={name:s.sha(Q/name) for name in ('full_gate.py','run_authorized.py','complete_authorized.py')}
 qualification={'at':s.utc(),'author':'/root','exact_tests':s.reference(R/'tests-r1/RESULT.json'),
  'original42_test_method_ASTs_unchanged':True,'new_class_boundary_methods':4,'Source290_E33601_F4candidate336_conserved':True,
  'predecessor6_and_author154_conserved':True,'old_review':'FAILED preserved','exact_failure':inputs['exact_failure'],
  'Source_publication':False,'original_restricted_native_test':'NOT_RUN','actual_human_approval_created':False,'exit_status':0}
 s.write_new(R/'QUALIFICATION.json',qualification)
 manifest={'schema_version':1,'at':s.utc(),'author':'/root','candidate_root':str(Q),'runtime_root':str(R),
  'payloads':payloads,'payload_count':5,'eligible_Source_application_paths':[],
  'scope':'Exact class-boundary repair and successor identity bindings; dormant engineering tool only.',
  'predecessor_manifest':s.reference(OQ/'TRANSFER-MANIFEST.json'),'predecessor_failure':inputs['exact_failure'],
  'parent_manifest':s.reference(F/'.agents/re-foundation4-20261015/TRANSFER-MANIFEST.json'),
  'successor_scripts':scripts,'qualification':s.reference(R/'QUALIFICATION.json'),'tests':s.reference(R/'tests-r1/RESULT.json'),
  'LOC':{'new_CETA_product_Source_LOC':0,'reused_code_LOC_credit':0,'new_boundary_test_methods':4,
   'implementation_changes':'One gate-lookup expression; two successor identity bindings and distinct-author exclusion.'},
  'limitations':read(OQ/'TRANSFER-MANIFEST.json')['limitations'],'Source_publication':False}
 s.write_new(Q/'TRANSFER-MANIFEST.json',manifest)
 s.complete('implement',{'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),
  'successor_scripts':scripts,'tests':s.reference(R/'tests-r1/RESULT.json'),'qualification':s.reference(R/'QUALIFICATION.json'),
  'controlled_tests_passed':46,'original_case_native_executed':False,'Source_publication':False},
  [{'command':str(s.PY)+' -B -X utf8 '+str(R/'run_tests.py')+' tests-r1','exit_status':0}],
  [('46 distinct controlled methods and exact Result class boundary pass',True),('Original42 methods and all strict full2053 gates retained',True),
   ('Current Source F4 E3 and rejected predecessor conserved',True)])
 state=read(R/RUN/'state.json');stored=read(R/RUN/'receipts/implement.json');local=read(R/'implement.json')
 sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
 from taar.orchestration_persistence import sha256_json
 assert state['sequence']==7 and state['nodes']['review']['state']=='READY' and read(R/RUN/'claims.json')=={}
 assert len(local)==12 and len(stored)==15 and local=={k:stored[k] for k in local}
 assert stored['receipt_hash']==sha256_json({k:v for k,v in stored.items() if k!='receipt_hash'})
 assert read(R/RUN/'results/implement.json')=={'node_id':'implement','receipt_hash':stored['receipt_hash'],'result':stored['result']}
 s.write_new(R/'READY-FOR-REVIEW.json',{'at':s.utc(),'author':'/root','manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),
  'successor_scripts':scripts,'tests':s.reference(R/'tests-r1/RESULT.json'),'qualification':s.reference(R/'QUALIFICATION.json'),
  'driver':s.reference(R/'run_tests.py'),'reviewer':'/root/wt1_reviewer','sequence':7,'claims':{},'Source_publication':False})
 s.write_new(R/'AUTHOR-SEAL.json',{'at':s.utc(),'author':'/root','candidate_members':{p.name:s.ordinary(p) for p in Q.iterdir() if p.is_file()},
  'evidence_members':{p.relative_to(R).as_posix():s.ordinary(p) for p in R.rglob('*') if p.is_file() and not p.is_relative_to(Q) and not p.is_relative_to(R/RUN)}})
 print(json.dumps({'state':'review READY','manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'ready':s.reference(R/'READY-FOR-REVIEW.json'),'seal':s.reference(R/'AUTHOR-SEAL.json')}))
else:raise AssertionError('Unknown author mode')
