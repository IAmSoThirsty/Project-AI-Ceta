"""Distinct review: rerun the unchanged 30 test bodies with fresh owned output only."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,subprocess,sys
R=Path(__file__).resolve().parent;D=R/'independent-root-review';D.mkdir(exist_ok=False)
assert R==Path('T:/00-Active/Project-AI-CETA/.agents/runtime/ac2-20261014/profile-tool-repair-r2')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=R/'test_profile_qualification_r2.py';tool=R/'profile_qualification_r2.py'
assert sha(source)=='a5b5238027ce0cc586394647a341541dfde1b7214d0e2d11a2351206ed8b5f7c'
assert sha(tool)=='41e2bc3b5c289228bd6f9e8912474c9a6c16459543775a52aa1a5ec6e10da5bb'
original=source.read_text(encoding='utf-8')
assert original.count("D=R/'tests-r3'")==1
adapted=original.replace("D=R/'tests-r3'","D=R/'independent-root-review/tests-r1'")
def bodies(raw):
    tree=ast.parse(raw)
    return [ast.dump(node,include_attributes=False) for node in ast.walk(tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
assert bodies(original)==bodies(adapted)
adapted_path=D/'adapted-tests.py';adapted_path.write_text(adapted,encoding='utf-8',newline='\n')
entry=D/'entry.py'
entry.write_text('from pathlib import Path\n'+
    'p=Path('+repr(str(source))+')\n'+
    'raw=Path('+repr(str(adapted_path))+').read_bytes()\n'+
    'exec(compile(raw,str(p),"exec"),{"__file__":str(p),"__name__":"__main__"})\n',encoding='utf-8')
started=datetime.now(timezone.utc).isoformat()
done=subprocess.run([sys.executable,'-B','-X','utf8',str(entry)],cwd=R.parents[3],capture_output=True)
for name,raw in [('stdout',done.stdout),('stderr',done.stderr)]:
    with (D/(name+'.txt')).open('xb') as out:out.write(raw)
result=json.loads((D/'tests-r1/negative-r1.json').read_text(encoding='utf-8'))
assert sha(source)=='a5b5238027ce0cc586394647a341541dfde1b7214d0e2d11a2351206ed8b5f7c'
assert sha(tool)=='41e2bc3b5c289228bd6f9e8912474c9a6c16459543775a52aa1a5ec6e10da5bb'
assert done.returncode==0 and result['exit_status']==0 and result['tests_run']==30
assert not result['failures'] and not result['errors'] and not result['skips']
assert not result['actual_Create_Delete_executed'] and not result['blocked_actual_profile_attempts']
report={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'executor_id':'/root',
 'decision':'approved_for_exact_operator_permission_request_and_qualified_attempt_only',
 'tool_sha256':sha(tool),'original_tests_sha256':sha(source),'adapted_tests_sha256':sha(adapted_path),
 'adaptation':'Only fresh owned output directory literal changed; all function and class ASTs are identical.',
 'tests':30,'controlled_negative_cases':len(result['controlled_cases']),'raw_exit_status':done.returncode,
 'result_sha256':sha(D/'tests-r1/negative-r1.json'),'actual_Create_Delete_executed':False,
 'actual_positive_isolation':'NOT_RUN','operator_permission':'NOT_YET_REQUESTED',
 'source_unchanged':result['Source290_native_and_hash_exact'],'candidate_unchanged':result['candidate294_native_and_hash_exact'],
 'reviewed_repairs':['single captured verified dependency bytes','all native output custody retained before diagnostics',
    'primary failure preserved across independent cleanup/diagnostic failures','no adoption or deletion of preexisting profile',
    'only own successful exact SID creation and proved retirement can reach Delete; all unresolved outcomes retained']}
with (D/'REVIEW.json').open('x',encoding='utf-8') as out:json.dump(report,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
print(json.dumps({'review':report['decision'],'tests':30,'controlled_negative_cases':report['controlled_negative_cases'],
 'tool_sha256':sha(tool),'review_sha256':sha(D/'REVIEW.json'),'actual_profile_mutation':False}),flush=True)
