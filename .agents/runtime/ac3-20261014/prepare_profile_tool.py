"""Prepare one exact six-key future qualification; never create an approval or profile."""
from ac3_support import *
import ast,difflib
D=R/'profile-tool';D.mkdir()
parent=F/'.agents/runtime/ac2-20261014/profile-tool-repair-r2/profile_qualification_r2.py'
assert sha(parent)=='41e2bc3b5c289228bd6f9e8912474c9a6c16459543775a52aa1a5ec6e10da5bb'
manifest=Q/'TRANSFER-MANIFEST.json'
assert sha(manifest)=='274fbd34857409e54ef04991b4ba424332a58b87f553a2a1409bea64ff52c60b'
assert json.loads((R/RUN/'claims.json').read_text())=={}
proposal={'recorded_at':utc(),'status':'PROPOSAL_REQUIRES_NEW_EXPLICIT_HUMAN_APPROVAL','name':'CETA.ProjectAICETA.IsolatedWorker.AC1.V1',
    'SID':'S-1-15-2-695244707-3853392321-2130098501-3319658173-178928504-1880712989-1319207162',
    'user_sid':'S-1-5-21-1218874621-2294869469-207301144-1003','capabilities':[],
    'candidate_manifest':reference(manifest),'profile_Create_API':'CreateAppContainerProfile','own_cleanup_API':'DeleteAppContainerProfile',
    'profile_attempts_requested':1,'restricted_worker_attempts_requested':1,'ordinary_owned_fixture_control':1,
    'preexisting_profile_rule':'Refuse if the exact reserved profile already exists; never delete any pre-existing profile.',
    'cleanup_rule':'Delete only the exact new profile returned0 by this run after exact SID/name/user proof and actual complete native retirement; report retained/unknown otherwise and observe folder absence separately.',
    'environment_variant':['LOCALAPPDATA','PATH','SystemRoot','TEMP','TMP','WINDIR'],
    'environment_origin':'SystemRoot/WINDIR from Windows; System32 PATH; fresh owned scratch TEMP/TMP; native current-user FOLDERID_LocalAppData via KF_FLAG_DONT_VERIFY with no-create/init flag.',
    'native_image_sha256':'527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f',
    'fixture_scope':str(D/'profile-qualification-<fresh-UUID>'),'Source_application':False,
    'cause203':'UNESTABLISHED; this is a bounded hypothesis qualification, not a verified repair.',
    'prior_attempt':reference(F/'.agents/runtime/ac2-20261014/profile-tool-repair-r2/profile-qualification-7b716b95d15f440a90d6be98a666014c/RESULT.json'),
    'activation_ready':False,'canonical_authority_approval':False}
write_new(D/'PROFILE-CREATION-PROPOSAL-AC3.json',proposal)
old=parent.read_text(encoding='utf8');body=old
body=body.replace("ORIGINAL_R = F / '.agents/runtime/ac2-20261014'","ORIGINAL_R = F / '.agents/runtime/ac3-20261014'")
body=body.replace("assert R == ORIGINAL_R / 'profile-tool-repair-r2'","assert R == ORIGINAL_R / 'profile-tool'")
body=body.replace("Q = F / '.agents/ac2-20261014'","Q = F / '.agents/ac3-20261014'")
body=body.replace("MANIFEST = '41a2c6ab046279a581fe3ff99b126b84d7485d8369108f7abbf53634da254dda'","MANIFEST = '"+sha(manifest)+"'")
body=body.replace("PROPOSAL = F / '.agents/runtime/ac1-20261014/PROFILE-CREATION-PROPOSAL.json'","PROPOSAL = R / 'PROFILE-CREATION-PROPOSAL-AC3.json'")
body=body.replace("capture(PROPOSAL, '75c5a41afd412ab91272ced373b84bfcbe34f5941c1b6dbf95254905a65db55c')","capture(PROPOSAL, '"+sha(D/'PROFILE-CREATION-PROPOSAL-AC3.json')+"')")
deps={}
for name in ('.agents/runtime/ac1-20261014/native_fixture_support.py','.agents/runtime/ac3-20261014/ac3_support.py','.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe'):
    facts=ordinary(F/name);deps[name]={'sha256':facts['sha256'],'native_identity':facts['native_identity']}
start=body.index('DEPENDENCIES = {');end=body.index('\ndigest =',start)
body=body[:start]+'DEPENDENCIES = '+repr(deps)+'\n'+body[end:]
body=body.replace(".agents/runtime/ac2-20261014/ac2_support.py",".agents/runtime/ac3-20261014/ac3_support.py")
body=body.replace("directory / 'ac2_support.py'","directory / 'ac3_support.py'")
body=body.replace("{'SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP'}, 'BOUNDED_ENVIRONMENT_REQUIRED'", "{'SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'LOCALAPPDATA'}, 'BOUNDED_ENVIRONMENT_REQUIRED'")
def methods(text):
    return {(node.name,member.name):ast.dump(member,include_attributes=False) for node in ast.parse(text).body if isinstance(node,ast.ClassDef)
        for member in node.body if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef))}
assert methods(old)==methods(body),'All existing custody/lifecycle class methods must remain exact'
top=lambda text:{node.name:ast.dump(node,include_attributes=False) for node in ast.parse(text).body if isinstance(node,ast.FunctionDef)}
before,after=top(old),top(body)
assert {name for name in before if before[name]!=after[name]}=={'prepare_probe','assert_isolation'}
assert before['validate_operator_record']==after['validate_operator_record']
compile(body,str(D/'profile_qualification.py'),'exec')
fs.write_new(D/'profile_qualification.py',body.encode())
diff=''.join(difflib.unified_diff(old.splitlines(True),body.splitlines(True),fromfile='frozen-reviewed-profile_r2.py',tofile='AC3-profile_qualification.py'))
fs.write_new(D/'tool-delta.diff',diff.encode())
tests=F/'.agents/runtime/ac2-20261014/profile-tool-repair-r2/test_profile_qualification_r2.py'
old_tests=tests.read_text(encoding='utf8');new_tests=old_tests
new_tests=new_tests.replace("assert R==F/'.agents/runtime/ac2-20261014/profile-tool-repair-r2'","assert R==F/'.agents/runtime/ac3-20261014/profile-tool'")
new_tests=new_tests.replace("profile_qualification_r2.py","profile_qualification.py")
new_tests=new_tests.replace(".agents/runtime/ac2-20261014/ac2_support.py",".agents/runtime/ac3-20261014/ac3_support.py")
fs.write_new(D/'test_profile_qualification.py',new_tests.encode())
write_new(D/'PREPARED-TOOL.json',{'recorded_at':utc(),'author':ACTOR,'parent_tool':ordinary(parent),'new_tool':ordinary(D/'profile_qualification.py'),
    'proposal':reference(D/'PROFILE-CREATION-PROPOSAL-AC3.json'),'candidate_manifest':reference(manifest),'dependency_map':deps,
    'all_existing_custody_lifecycle_method_ASTs_unchanged':True,'operator_approval_guard_AST_unchanged':True,
    'top_level_function_changes':['prepare_probe exact captured support dependency/file path','assert_isolation exact6-key expected environment'],
    'new_human_approval_record_created':False,'actual_Create_Delete_executed':False,
    'positive_qualification':'NOT_EXECUTED_NEW_EXPLICIT_APPROVAL_REQUIRED','tests_parent':reference(tests),'tests_prepared':reference(D/'test_profile_qualification.py'),
    'Source_baseline_guard':'Exact accepted290 full-result SHA and every Source payload still required before and after; a future Source publication requires a fresh reviewed tool cut.'})
print(json.dumps({'tool_sha256':sha(D/'profile_qualification.py'),'proposal_sha256':sha(D/'PROFILE-CREATION-PROPOSAL-AC3.json'),
    'candidate_sha256':sha(manifest),'no_profile_calls':True,'custody_AST_exact':True}),flush=True)
