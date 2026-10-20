"""Frozen EN3 source/provenance binding and exact private execution copy."""
from review_support import *
import ast
M=D/'replica';assert M.is_dir()
claim=json.loads((R/RUN/'claims.json').read_text())['review'];assert claim['executor_id']==ACTOR
assert sha(Q/'TRANSFER-MANIFEST.json')=='8772cd735ae0ff767108976fef15e004012718ffded50a1d888cc354fae329ec'
assert sha(R/'implement.json')=='521e0136a5cc83b2ed222fb83e927c3b30a0d618fbb3e14d47f8f69ba700a668'
assert sha(R/'AUTHOR-READBACK.json')=='a3fccf52a6c2ca7bc1d304cae22396701268669d690a5e81d09eee71c1523740'
assert sha(R/'AUTHOR-SEAL.json')=='b458a9ad9a4ae71a86530be98311d048d9fd8e32bb372cdc24797628ca9e7e42'
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text())
payloads={name:ordinary(Q/name) for name in manifest['payloads']};assert len(payloads)==296 and payloads==manifest['payloads']
source=json.loads((R/'SOURCE-INPUTS.json').read_text())['Source290']
assert len(source)==290 and source=={name:ordinary(F/name) for name in source}
def inventory(root):
    result={}
    for base,dirs,files in os.walk(root,followlinks=False):
        for name in dirs:assert not fs.reparse(fs.lstat(Path(base)/name))
        for name in files:
            path=Path(base)/name;result[path.relative_to(root).as_posix()]=ordinary(path)
    return result
whole_Q=inventory(Q);environment=inventory(PY.parent.parent)
assert len(environment)==3601 and sum(row['bytes'] for row in environment.values())==231026067
replica={}
for name,row in payloads.items():
    target=M/name;target.parent.mkdir(exist_ok=True,parents=True)
    raw=fs.read_bytes(Q/name);assert digest(raw)==row['sha256']
    assert target.is_file(), 'Retained initial replica member missing'
    replica[name]=ordinary(target);assert replica[name]['sha256']==row['sha256']
parent=F/'.agents/en2-20261014'
parent_manifest=json.loads((parent/'TRANSFER-MANIFEST.json').read_text())
parent_rows={row['relative_path']:row for row in parent_manifest['payloads']}
assert len(parent_rows)==len(parent_manifest['payloads'])==295
parents={name:ordinary(parent/name) for name in parent_rows}
assert all(row['sha256']==parent_rows[name]['candidate_sha256'] and row['native_identity']==parent_rows[name]['candidate_native_identity'] for name,row in parents.items())
changed=[name for name,row in parents.items() if row['sha256']!=payloads[name]['sha256']]
assert set(changed)=={'src/ceta/contracts/owner_enrollment.py','contracts/OWNER_ENROLLMENT_V1.md'}
assert set(payloads)-set(parents)=={'tests/contract/test_owner_enrollment_guid.py'}
assert sum(row['sha256']==payloads[name]['sha256'] for name,row in parents.items())==293
def methods(root):
    return {str(path.relative_to(root))+':'+node.name+'.'+method.name:ast.dump(method,include_attributes=False)
        for path in (root/'tests/contract').glob('*.py')
        for node in ast.walk(ast.parse(path.read_text(encoding='utf8'))) if isinstance(node,ast.ClassDef)
        for method in node.body if isinstance(method,ast.FunctionDef) and method.name.startswith('test_')}
old,new=methods(parent),methods(Q)
assert all(new[name]==body for name,body in old.items()) and len(set(new)-set(old))==6
assert sha(Q/'tests/contract/test_source_coverage.py')==sha(F/'tests/contract/test_source_coverage.py')==sha(parent/'tests/contract/test_source_coverage.py')
for key in ('src/ceta/contracts/owner_enrollment.py','tests/contract/test_owner_enrollment_guid.py','contracts/OWNER_ENROLLMENT_V1.md'):
    assert manifest['application_actions'][key]['action']=='CREATE'
    try:fs.lstat(F/key)
    except FileNotFoundError:pass
    else:raise AssertionError('Source CREATE path unexpectedly occupied: '+key)
write(D/'PREPARATION.json',{'at':utc(),'claim':claim,'manifest':ordinary(Q/'TRANSFER-MANIFEST.json'),
    'payloads':payloads,'whole_Q':whole_Q,'replica':replica,'Source290':source,'E3':environment,
    'parent_payloads':parents,'parent_changed_paths':changed,'all_old_test_methods_AST_exact':True,
    'new_test_methods':sorted(set(new)-set(old)),'leaf_guard_bytes_unchanged':True,
    'git':[fs.text_git(F,'rev-parse','--show-toplevel','--git-common-dir','HEAD'),fs.text_git(F,'status','--porcelain=v1','--untracked-files=no')],
    'execution':'Exact296 payload replica; test __file__/tool/native read paths differ and are explicit. All source/test code bytes unchanged; temporary source-coverage fixtures stay in this runtime.',
    'authorship':'Reviewer authored EN1 original, independently reviewed EN2, Root authored EN3 repair; Root original component acceptance remains dependency evidence.',
    'Source_application':False,'native_process_profile_or_authority_operations':False,
    'prior_setup_failure':ordinary(D/'PREPARATION-FAILURE-r1.json'),'retained_initial_replica_reverified':True})
print(json.dumps({'payloads':296,'whole_Q':len(whole_Q),'parent_reused':293,'Source':290,'E3':3601,'old_tests_exact':True}),flush=True)
