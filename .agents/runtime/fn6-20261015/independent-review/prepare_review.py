"""Authenticate exact FN6, complete fixture inputs, then claim the real review."""
from review_support import *
import difflib
assert sha(Q/'TRANSFER-MANIFEST.json')=='6bd87db98906075971ecde1bd07444d28b3a957ba017cef2836cde097737eb24'
for name,pin in {'implement.json':'67a66e00ecf37eb5837c1aab4beeb454fb7c20d75eae12c0700170c812f9bc49',
    'AUTHOR-READBACK.json':'aa52ec1202a6dcca60467e43699783299a4e372b941336d02d8ea09f2366be7c',
    'AUTHOR-SEAL.json':'81b89002c46641a4ffa99cfdc01fb1caf95f0fa5e9e87c7c135d3c7ff42cb58e'}.items():assert sha(A/name)==pin
m=read(Q/'TRANSFER-MANIFEST.json');state=read(A/RUN/'state.json')
assert state['sequence']==7 and state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY'
assert read(A/RUN/'claims.json')=={}
local,stored,_,_=current_receipt('implement',A/'implement.json',s.AUTHOR)
from taar.orchestration_runtime import _snapshot_workspace,_artifact_hash
assert _artifact_hash(_snapshot_workspace(Q,Path('T:/')),local['changed_files'])==state['nodes']['implement']['artifact_hash']
for row in read(A/'AUTHOR-SEAL.json')['critical_members']:assert ordinary(Path(row['path']))==row
names=set(m['payloads']);assert len(names)==352
payloads={name:ordinary(Q/name) for name in names}
assert payloads=={name:row['candidate'] for name,row in m['payloads'].items()}
aux={name:ordinary(Q/name) for name in m['auxiliaries']};assert aux==m['auxiliaries']
pm=read(P/'TRANSFER-MANIFEST.json')
parent={name:ordinary(P/name) for name in pm['payloads']}
assert parent=={name:row['candidate'] for name,row in pm['payloads'].items()} and len(parent)==351
unchanged=[name for name in parent if name!='src/ceta/kernel/transactions.py']
assert len(unchanged)==350 and all(payloads[n]['sha256']==parent[n]['sha256'] for n in unchanged)
def methods(path):
    return {c.name+'.'+n.name:ast.dump(n,include_attributes=False) for c in ast.parse(Path(path).read_text()).body
        if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
parent_tests={n:len(methods(Q/n)) for n in parent if n.startswith('tests/') and n.endswith('.py')}
assert sum(parent_tests.values())==2327
assert all((P/n).read_bytes()==(Q/n).read_bytes() for n in parent_tests)
old=ast.parse((P/'src/ceta/kernel/transactions.py').read_bytes());new=ast.parse((Q/'src/ceta/kernel/transactions.py').read_bytes())
def cls(tree):return next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
old_methods={n.name:n for n in cls(old).body if isinstance(n,ast.FunctionDef)}
new_methods={n.name:n for n in cls(new).body if isinstance(n,ast.FunctionDef)}
assert set(old_methods)==set(new_methods)
others={n:ast.dump(old_methods[n],include_attributes=False)==ast.dump(new_methods[n],include_attributes=False)
    for n in old_methods if n!='__init__'}
assert len(others)==33 and all(others.values())
assert ast.dump(old_methods['__init__'].args,include_attributes=False)==ast.dump(new_methods['__init__'].args,include_attributes=False)
assert ast.unparse(new_methods['__init__'].body[-1].body[-1])=='NativeCpuOwnerSession._bind_preparation_kernel(owners, self)'
for tree in (old,new):cls(tree).body=[n for n in cls(tree).body if not(isinstance(n,ast.FunctionDef) and n.name=='__init__')]
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
oracle=F/'.agents/runtime/fn5-20261015/independent-review/probe_initializer_binding.py'
assert sha(oracle)=='e08cb7431f8723de9d8837d1079054d302d52e707794b7140ae6f30581430578'
key='InitializerBindingTests.test_failed_final_bound_method_allocation_must_leave_owner_unbound'
assert methods(oracle)[key]==methods(Q/'tests/contract/test_kernel_initializer_publication.py')[key]
copy_names=('foundation_support.py','run_initializer.py','resource_observer.py','run_controlled.py',
    'supervise_controlled.py','bounded_custody.py','run_preparation.py','run_consumers.py',
    'run_joined_controls.py','test_preparation_coordination.py','run_outcomes.py','INPUTS.json','ASSEMBLY.json')
copies={}
for name in copy_names:
    source=ordinary(A/name)
    if name in m['scripts']:assert source['sha256']==m['scripts'][name]
    s.bytes_copy(A/name,V/name,source)
    copies[name]=dict(original=source,reviewer=ordinary(V/name))
assert set(read(V/'ASSEMBLY.json')['payloads'])==names
environment=read(A/'INPUTS.json')['E33601'];E=s.PY.parent.parent
assert len(environment)==3601 and walk_members(E)==set(environment)
assert {n:ordinary(E/n) for n in environment}==environment
reader_inputs={'.agents/pr4-20261014/preserve_ceta_complete.py':ordinary(s.reader)}
helpers={n:ordinary(V/n) for n in ('review_support.py','prepare_review.py','execute_review.py','supervise_review.py','run_leaf.py')}
write_new(V/'REVIEW-INPUTS.json',dict(at=utc(),manifest=ordinary(Q/'TRANSFER-MANIFEST.json'),payloads=payloads,
    auxiliaries=aux,parent_payloads=parent,E33601=environment,copies=copies,reader_inputs=reader_inputs,own_helpers=helpers,
    all_parent_test_method_counts=parent_tests,all_other_transaction_method_ASTs=others,
    literal_WT_method_AST_exact=True,author_receipt_fingerprint=stored['receipt_hash'],author_artifact_verified=True,
    R_read_dependency_list=['ASSEMBLY.json','INPUTS.json','test_preparation_coordination.py','bounded_custody.py','resource_observer.py'],
    Q_read_dependency_scope='All352 frozen payloads and11 auxiliary files pinned before every cohort; no missing runtime before-image references.',
    native7_OS5native_restricted_profile_Hello_CPU_Set_Source_full='NOT_RUN',Source_publication=False))
write_new(V/'PREPARATION-DISCLOSURE.json',dict(at=utc(),before_review_claim=True,
    exploratory_read_error=dict(command="Get-Content .agents/runtime/fn5-20261015/independent-review/finish_review.py -Raw",exit_status=1,
        reason='Reader guessed a nonexistent evidence helper; no test or product execution. Preserved tool failure is not a qualified zero-exit command.'),
    prior_JS6_failure='Sealed FAILED9; no retry. Complete fixture preflight addresses the prior review scaffold omission without altering that run.'))
claim=invoke(['node','claim',RUN,'review','--executor',ACTOR,'--workspace',str(Q)],'review-claim')['claim']
assert claim['executor_id']==ACTOR
print(json.dumps(dict(claimed=True,payloads=352,parent_tests=2327,unchanged350=True,other_methods=33,fixture_inputs=len(copies))))
