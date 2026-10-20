"""Pin the exact CPB1 cut and take only its distinct installed review claim."""
from pathlib import Path
import ast, hashlib, importlib.util, json, os, stat, subprocess, sys
F=Path('T:/00-Active/Project-AI-CETA');Q=F/'.agents/cpb1-20261014';R=F/'.agents/runtime/cpb1-20261014';D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
support=F/'.agents/runtime/en1-20261014/en1_support.py'
assert hashlib.sha256(support.read_bytes()).hexdigest()=='c1c72b520234d6eb7316b4ad730811696e62cf14cdae481ece576a06fdb7e3d0'
sys.path.insert(0,str(support.parent));import en1_support as s
s.Q=Q;s.R=D
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
canon=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
pins={'TRANSFER-MANIFEST.json':'b90d60320a3aea2f72e6ee0b3cbcc8a4964e01e0107721cf938c5ba038d9568e',
      'implement.json':'3b7b7880fac15ef10a2176c2a56ebe844bdf3959ff249cd8f7de5ac8dc504400',
      'AUTHOR-READBACK-r2.json':'ce4b3fde81aedb316791bf8fb1cbfe6cdd58a70b6293bb7a5a153aa4727c7846',
      'AUTHOR-SEAL.json':'ab2ec92f9ca8e5a648f80fb2854a7c2da723e9a1ad8c88b6ca5c5414866ad26e'}
for name,value in pins.items():assert s.sha((Q if name=='TRANSFER-MANIFEST.json' else R)/name)==value,(name,'pin changed')
def inventory(root):
    files={};directories={};pending=[root]
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                p=directory/entry.name;relative=p.relative_to(root).as_posix();info=s.fs.lstat(p)
                assert not s.fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):directories[relative]=s.fs.file_identity(info);pending.append(p)
                else:assert stat.S_ISREG(info.st_mode);files[relative]=s.ordinary(p)
    return dict(sorted(files.items())),dict(sorted(directories.items()))
manifest=read(Q/'TRANSFER-MANIFEST.json');seal=read(R/'AUTHOR-SEAL.json');inputs=read(R/'SOURCE-INPUTS.json')
candidate,dirs=inventory(Q)
assert len(manifest['payloads'])==303 and len(candidate)==326
assert candidate==seal['candidate_members'] and all(candidate[n]==row for n,row in manifest['payloads'].items())
fixtures=set(candidate)-set(manifest['payloads'])-{'TRANSFER-MANIFEST.json'}
assert len(fixtures)==22 and fixtures==set(seal['fixture_evidence_members'])
assert all(n.startswith('.agents/fixtures/windows-jobs-') for n in fixtures)
author_evidence={n:s.ordinary(R/n) for n in seal['author_evidence_members']}
assert author_evidence==seal['author_evidence_members']
source={n:s.ordinary(F/n) for n in inputs['Source290']};assert len(source)==290 and source==inputs['Source290']
assert s.source_inventory()==source
for name,row in inputs['dependency_files'].items():
    assert s.ordinary(Path(row['path']))==row
    assert candidate[name]['sha256']==row['sha256']
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
parents=[]
for row in inputs['parents']:
    review_path=F/row['approved_review']['repository_relative_path'];assert s.sha(review_path)==row['approved_review']['sha256']
    local=read(review_path);life=review_path.parent.parent/local['run_id'];stored=read(life/'receipts/review.json')
    state=read(life/'state.json');result=read(life/'results/review.json');claims=read(life/'claims.json')
    assert len(local)==13 and len(stored)==16 and all(canon(stored[k])==canon(v) for k,v in local.items())
    assert local['decision']=='approved' and local['exit_status']==0 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={}
    normalized=sha256_json({k:v for k,v in stored.items() if k!='receipt_hash'})
    assert normalized==stored['receipt_hash']==state['nodes']['review']['receipt_hash']==result['receipt_hash']
    assert canon(result['result'])==canon(local['result'])
    assert s.sha(F/row['manifest']['repository_relative_path'])==row['manifest']['sha256']
    parents.append(dict(name=row['name'],review=s.ordinary(review_path),persisted=s.ordinary(life/'receipts/review.json'),normalized=normalized,sequence=state['sequence'],claims=claims))
life=R/'cpb1-20261014';state=read(life/'state.json');claims=read(life/'claims.json');submitted=read(R/'implement.json');stored=read(life/'receipts/implement.json')
assert state['sequence']==7 and state['nodes']['review']['state']=='READY' and state['nodes']['implement']['state']=='SUCCEEDED' and claims=={}
assert len(submitted)==12 and len(stored)==15 and all(canon(stored[k])==canon(v) for k,v in submitted.items())
assert sha256_json({k:v for k,v in stored.items() if k!='receipt_hash'})==stored['receipt_hash']==state['nodes']['implement']['receipt_hash']==read(life/'results/implement.json')['receipt_hash']
baseline=read(R/'environment-before.json');environment,environment_dirs=inventory(s.PY.parents[1])
assert len(environment)==3601 and environment==baseline['members'] and sum(v['bytes'] for v in environment.values())==231026067
expected=read(R/'connected-r2.json')['expected_ids'];assert len(expected)==len(set(expected))==163
assert sum(n.startswith('test_native_cpu_binding.') for n in expected)==42
prod=ast.parse((Q/'src/ceta/effects/native_cpu_binding.py').read_text(encoding='utf-8'))
api=[n.name for node in prod.body if isinstance(node,ast.ClassDef) and node.name=='NativeCpuBinding' for n in node.body if isinstance(n,ast.FunctionDef) and not n.name.startswith('_')]
assert api==['capture','require_current','driver_arguments','cancel','close']
calls=[ast.unparse(node.func) for node in ast.walk(prod) if isinstance(node,ast.Call)]
assert not any('SetInformationJobObject' in n or 'apply_cpu_rate_limit' in n or 'restore_cpu_rate_limit' in n for n in calls)
prep=dict(at=s.utc(),executor_id='/root/wt1_reviewer',manifest=s.ordinary(Q/'TRANSFER-MANIFEST.json'),pins=pins,candidate326=candidate,candidate_directories=dirs,
    payloads303=manifest['payloads'],preexisting_fixture22=sorted(fixtures),author_evidence=author_evidence,Source290=source,E3_members=environment,E3_directories=environment_dirs,
    parent_acceptances=parents,expected_ids=expected,eligible_paths=manifest['eligible_application_paths'],public_API=api,production_call_sites=calls,
    authored_scope='Only independent CPB1 delta; reviewer previously authored WT4. WT4 dependency is reused under distinct Root actual accepted review, not reapproved as own independent code.',
    observed_HEAD=s.fs.text_git(F,'rev-parse','HEAD'),branch=s.fs.text_git(F,'branch','--show-current'),dirty_tracked=s.fs.text_git(F,'status','--porcelain=v1','-uno'),
    fixture_relocation='Only test_windows_jobs.ROOT is relocated to reviewer-owned fixture-root; no product root guard or method AST changes; no Q fixture writes authorized.',
    no_Source_publication=True,forbidden=['class15 policy Set','profile creation/deletion','restricted launch','Hello','genuine enrollment','Source mutation'])
s.write_new(D/'PREPARATION.json',prep)
argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1','node','claim','cpb1-20261014','review','--executor','/root/wt1_reviewer','--workspace',str(Q),'--runtime-root',str(R)]
done=subprocess.run(argv,cwd=str(F),capture_output=True)
for suffix,raw in (('stdout',done.stdout),('stderr',done.stderr)):
    with (D/('claim-r1.'+suffix)).open('xb') as out:out.write(raw)
response=json.loads(done.stdout.decode('utf-8-sig'));assert done.returncode==0 and response['allowed'],response
claimed=read(life/'claims.json')['review'];assert claimed['executor_id']=='/root/wt1_reviewer' and Path(claimed['workspace'])==Q
s.write_new(D/'ACTUAL-REVIEW-CLAIM.json',dict(at=s.utc(),argv=argv,exit_status=done.returncode,claim=claimed,state_sequence=read(life/'state.json')['sequence']))
print(canon(dict(claimed=True,payloads=303,ordinary=326,Source=290,E3=3601,exact_expected_methods=163,parent_reviews=len(parents))))
