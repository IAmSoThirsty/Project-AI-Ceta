"""Freeze finite gate engineering proof; no Source or native test cohort execution."""
from pathlib import Path
import ast
import difflib
import io
import json
import os
import sys
import tokenize

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;Q=R/'candidate'
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN='f4-full-gate-successor-20261015';s.ACTOR='/root/history_preservation'
sys.path.insert(0,str(Q));import full_gate as g
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
inputs=read(R/'INPUTS.json');tests=read(R/'tests-r4/RESULT.json')
assert tests['exit_status']==0 and tests['tests_run']==42 and tests['expected_ids']==tests['executed_ids']==tests['stopped_ids']
assert not any(tests[k] for k in ('failures','errors','skips','forbidden_native_and_process_calls','remaining_threads'))
assert tests['original_restricted_no_profile_case']=='NOT_RUN' and not tests['full_Source2053_executed']
current_source={name:s.ordinary(F/name) for name in inputs['Source290']};assert current_source==inputs['Source290']==tests['Source290_after']
parent={name:s.ordinary(row['path']) for name,row in inputs['parent_scripts'].items()};assert parent==inputs['parent_scripts']==tests['F4_parent_scripts_after']
oldQ=F/'.agents/re-foundation4-20261015';oldR=F/'.agents/runtime/re-foundation4-20261015'
assert s.sha(oldQ/'TRANSFER-MANIFEST.json')==g.PARENT_MANIFEST
f4={name:s.ordinary(oldQ/name) for name in tests['F4_candidate336_before']};assert f4==tests['F4_candidate336_before']==tests['F4_candidate336_after']
assert s.ordinary(oldR/'independent-review/review.json')==inputs['parent_review']
assert s.ordinary(oldR/'independent-review/REPORT.json')==inputs['parent_report']
seal_path=oldR/'independent-review/REVIEW-SEAL.json';old_seal=read(seal_path)
sealed_files={name:s.ordinary(row['path']) for name,row in old_seal['members'].items()}
assert sealed_files==old_seal['members']
environment_root=F/'.agents/source-assembly-20261014T021300Z/.agents/e3'
accepted_environment=read(F/'.agents/runtime/er1-20261014/independent-destination/environment-independent-after.json')
environment={}
for row in accepted_environment['members']:
 if row['kind']=='ordinary_file':
  observed=s.ordinary(environment_root/row['relative_path'])
  assert observed['sha256']==row['sha256'] and observed['native_identity']==row['native_identity']
  environment[row['relative_path']]=observed
assert len(environment)==3601 and sum(row['bytes'] for row in environment.values())==231026067
assert s.fs.text_git(F,'rev-parse','HEAD')==inputs['HEAD'] and s.fs.text_git(F,'branch','--show-current')==inputs['branch'] and s.fs.text_git(F,'status','--porcelain=v1','-uno')==inputs['dirty']
payloads={path.name:s.ordinary(path) for path in Q.iterdir() if path.is_file()}
assert set(payloads)=={'full_gate.py','run_authorized.py','complete_authorized.py','test_full_gate.py','README.md'}
assert all(payloads[name]==row for name,row in tests['candidate_after'].items())
for name,row in payloads.items():
 if name.endswith('.py'):compile((Q/name).read_bytes(),str(Q/name),'exec')
runner=g.amend_runner((oldR/'run_joined.py').read_bytes());completion=g.amend_completion((oldR/'complete_source.py').read_bytes())
derived=R/'derived';derived.mkdir(exist_ok=False)
derived_pins={}
for name,old,new in (('run_joined.py',(oldR/'run_joined.py').read_text(),runner),('complete_source.py',(oldR/'complete_source.py').read_text(),completion)):
 view=derived/(name+'.authorized-view.py');diff=derived/(name+'.diff')
 s.fs.write_new(view,new.encode());s.fs.write_new(diff,''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen-F4/'+name,tofile='authorized-successor/'+name)).encode())
 derived_pins[name]={'derived_view':s.reference(view),'diff':s.reference(diff),'reused_parent_new_LOC_credit':0}
def sloc(path):
 text=Path(path).read_text();tree=ast.parse(text);doclines=set()
 for node in ast.walk(tree):
  body=getattr(node,'body',None)
  if isinstance(body,list) and body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):
   doclines.update(range(body[0].lineno,body[0].end_lineno+1))
 lines=set()
 for token in tokenize.generate_tokens(io.StringIO(text).readline):
  if token.type not in (tokenize.COMMENT,tokenize.NL,tokenize.NEWLINE,tokenize.ENCODING,tokenize.ENDMARKER,tokenize.INDENT,tokenize.DEDENT):
   lines.update(range(token.start[0],token.end[0]+1))
 return len(lines-doclines)
code_names=('full_gate.py','run_authorized.py','complete_authorized.py')
metrics={'new_engineering_source_SLOC':sum(sloc(Q/name) for name in code_names),'new_engineering_test_SLOC':sloc(Q/'test_full_gate.py'),
 'new_CETA_product_Source_LOC':0,'reused_F4_code_LOC_credit':0,'controlled_test_methods':42,
 'metric':'Python token lines excluding comments/blanks/actual docstrings; runtime engineering code and tests separated from product code.'}
limitations=['No actual original restricted no-profile method, full2053 Source run, Source publication, profile creation/deletion, Hello or CETA native effect.',
 'Synthetic controlled approval records are not actual human permission; genuine origin remains the trusted explicit operator path/hash command boundary.',
 'Original :2 regex is byte/AST preserved and also matches267; separate exact native-error observation required before full completion.',
 'F4 metadata109 remains unresolved/unwaived; whole_fixture_preservation_accepted remains false.',
 'Old F4 test-defined fixture ROOT/guards are retained. A future Root-run full cohort requires fresh owned children under its existing exact fixture scopes; no such children are created by this job.',
 'Same-host trusted operator/admin boundary; endpoint hashes do not prove uninterrupted custody or external UTC authenticity.',
 'Completion remains dormant until exact distinct successor and delivered reviews, actual full native regression and separate Root ordinary-library scope disposition.']
proof={'at':s.utc(),'exit_status':0,'tests':s.reference(R/'tests-r4/RESULT.json'),'raw':s.reference(R/'tests-r4/tests.txt'),
 'controlled_unique_tests':42,'F4_future_full_ids':2053,'F4_future_full_executed':False,'Source290':current_source,
 'F4_candidate336':f4,'F4_scripts':parent,'old_F4_review_seal':s.reference(seal_path),'old_F4_review_sealed_files_rehashed':len(sealed_files),
 'E33601':environment,'E3_bytes':231026067,'Git_HEAD_branch_dirty_preserved':True,'derived':derived_pins,'LOC':metrics,
 'preserved_failures':[s.reference(R/'SYNTAX-FAILURE-R1.json'),s.reference(R/'FIXTURE-FAILURE-R2.json')],
 'Root_scope_clarification':s.reference(R/'ROOT-SCOPE-CLARIFICATION.json'),'prior_passing_cut':s.reference(R/'tests-r3/RESULT.json'),
 'no_genuine_authorization_or_native_completion_generated':True,'limitations':limitations}
s.write_new(R/'QUALIFICATION.json',proof)
manifest={'schema_version':1,'at':s.utc(),'author':s.ACTOR,'candidate_root':str(Q),'runtime_root':str(R),
 'payloads':payloads,'payload_count':5,'eligible_Source_application_paths':[],'scope':'F4 full-regression engineering runner successor only',
 'parent_manifest':s.reference(oldQ/'TRANSFER-MANIFEST.json'),'parent_scripts':parent,
 'successor_scripts':{name:payloads[name]['sha256'] for name in code_names},'qualification':s.reference(R/'QUALIFICATION.json'),
 'tests':s.reference(R/'tests-r4/RESULT.json'),'LOC':metrics,'derived':derived_pins,'prior_failures':proof['preserved_failures'],
 'metadata109_issue_waived':False,'Source_published':False,'limitations':limitations}
s.write_new(Q/'TRANSFER-MANIFEST.json',manifest)
print(json.dumps({'qualified':True,'tests':42,'payloads':5,'Source290_preserved':True,'F4_candidate336_preserved':True,'old_F4_review_files_rehashed':len(sealed_files),'E3_files':len(environment),'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'LOC':metrics}))
