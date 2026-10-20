"""Capture frozen ET3 inputs and create an exact reviewer-owned execution replica."""
from review_support import *
import ast
M = D/'replica'
assert not M.exists()
claim = json.loads((R/RUN/'claims.json').read_text())['review']
assert claim['executor_id'] == ACTOR and Path(claim['workspace']) == Q
manifest_path = Q/'TRANSFER-MANIFEST.json'
assert sha(manifest_path)=='b061311cf6f52c89b9af93845258ca061043ef6ef60d8530b9048983351e5c9a'
assert sha(R/'implement.json')=='1f6d57166cd250b3bc892d9d89d1dbb5ba0d01eb100847cfe6fc8e42de122c43'
assert sha(R/'AUTHOR-READBACK.json')=='c3d8fdaa83482a8c7222182f47736d3021aa58a651949e7da7baddddf6def946'
assert sha(R/'AUTHOR-SEAL.json')=='8b674f699bef7dd15fe0f03277e6f1a82f71761d09f7d84b65bb8c1884f6947b'
manifest=json.loads(manifest_path.read_text()); assert len(manifest['payloads'])==317
payloads={name:ordinary(Q/name) for name in manifest['payloads']}
assert payloads == manifest['payloads']
source=json.loads((R/'SOURCE-INPUTS.json').read_text())['Source290']
assert len(source)==290 and {name:ordinary(F/name) for name in source}==source
def inventory(root):
    result={}
    for base, dirs, files in os.walk(root,followlinks=False):
        for name in dirs: assert not fs.reparse(fs.lstat(Path(base)/name))
        for name in files:
            path=Path(base)/name; result[path.relative_to(root).as_posix()]=ordinary(path)
    return result
whole_Q=inventory(Q)
e3=PY.parent.parent; environment=inventory(e3)
assert len(environment)==3601 and sum(row['bytes'] for row in environment.values())==231026067
baseline=json.loads((F/'.agents/runtime/er1-20261014/independent-destination/environment-independent-after.json').read_text())
expected={row['relative_path']:row for row in baseline['members'] if row['kind']=='ordinary_file'}
assert set(environment)==set(expected)
assert all(row['sha256']==expected[name]['sha256'] and row['native_identity']==expected[name]['native_identity'] for name,row in environment.items())
M.mkdir()
replica={}
for name,original in payloads.items():
    destination=M/name; destination.parent.mkdir(parents=True,exist_ok=True)
    raw=fs.read_bytes(Q/name); assert digest(raw)==original['sha256']
    with destination.open('xb') as out: out.write(raw); out.flush(); os.fsync(out.fileno())
    replica[name]=ordinary(destination); assert replica[name]['sha256']==original['sha256']
parent=F/'.agents/et2-20261014'
parent_manifest=json.loads((parent/'TRANSFER-MANIFEST.json').read_text())
parent_payloads={name:ordinary(parent/name) for name in parent_manifest['payloads']}
changed=[name for name,row in parent_payloads.items() if row['sha256']!=payloads[name]['sha256']]
assert set(changed)=={'src/ceta/kernel/effect_transactions.py','contracts/OWNED_CPU_OUTCOME_V1.md'}
assert set(payloads)-set(parent_payloads)=={'tests/contract/test_fresh_observer_reconciliation.py'}
def methods(root):
    return {str(path.relative_to(root))+':'+node.name+'.'+method.name:ast.dump(method,include_attributes=False)
        for path in (root/'tests/contract').glob('*.py')
        for node in ast.walk(ast.parse(path.read_text(encoding='utf8')))
        if isinstance(node,ast.ClassDef) for method in node.body
        if isinstance(method,ast.FunctionDef) and method.name.startswith('test_')}
old_methods,new_methods=methods(parent),methods(Q)
assert all(new_methods[name]==body for name,body in old_methods.items())
new_ids=set(new_methods)-set(old_methods); assert len(new_ids)==12
old_code=ast.parse((parent/'src/ceta/kernel/effect_transactions.py').read_text())
new_code=ast.parse((Q/'src/ceta/kernel/effect_transactions.py').read_text())
old_class=next(n for n in old_code.body if isinstance(n,ast.ClassDef) and n.name=='KernelEffectTransactions')
new_class=next(n for n in new_code.body if isinstance(n,ast.ClassDef) and n.name=='KernelEffectTransactions')
code_changes=[a.name for a,b in zip(old_class.body,new_class.body) if ast.dump(a,include_attributes=False)!=ast.dump(b,include_attributes=False)]
assert code_changes==['record']
assert sha(F/'.agents/runtime/ka1-20261014/independent-root-review/review.json')=='4e7181fd6c0912ad26e30992fc781703c8b3f67b162a1159af8fa2d28f0e7dbf'
write(D/'PREPARATION.json',{'at':utc(),'actual_claim':claim,'manifest':ordinary(manifest_path),
    'original_candidate':payloads,'whole_original_Q':whole_Q,'replica':replica,'Source290':source,
    'E3':environment,'E3_root':str(e3),'parent_payloads':parent_payloads,
    'parent_changed_paths':changed,'new_test_ids':sorted(new_ids),'all_prior_test_method_ASTs_exact':True,
    'original_method_count':len(old_methods),'only_changed_code_method':code_changes,
    'git':[fs.text_git(F,'rev-parse','--show-toplevel','--git-common-dir','HEAD'),fs.text_git(F,'status','--porcelain=v1','--untracked-files=no')],
    'authorship':'Reviewer authored KA1, uses Root separate accepted dependency review; ET3 was authored by Root.',
    'execution':'Byte-exact317 payload replica; __file__/native DLL paths and file identities differ explicitly. Existing fixture guards and source/test bodies unchanged; all outputs under reviewer runtime.',
    'native_effects':False,'Source_publication':False})
print(json.dumps({'payloads':317,'whole_Q_files':len(whole_Q),'Source':290,'E3_files':3601,
    'parent_changed_paths':changed,'new_test_methods':12,'original_methods_exact':True}),flush=True)
