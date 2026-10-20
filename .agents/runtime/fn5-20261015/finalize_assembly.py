"""Finish preserved partial assembly after a hash-row reader type error."""
from foundation_support import *
import ast

assert not (R/'ASSEMBLY.json').exists()
bytes_copy(R/'assemble.py',R/'prior-attempts/assemble-r1.py')
inputs=read(R/'INPUTS.json');scope=read(R/'SCOPE-ADDITION-OS5-TESTS.json')
extra_paths=scope['CREATE_from_reviewed_test_input']
names=set(inputs['base_payloads'])|set(inputs['selected']['os5'])|set(inputs['selected']['js5'])|set(extra_paths)
decisions=[]
for label in ('os5','js5'):
    for name in inputs['selected'][label]:
        row=next(row for row in inputs['overlap'][name] if row['package']==label)
        if name!='src/ceta/kernel/transactions.py':
            assert ordinary(Q/name)['sha256']==row['approved_input']['sha256']
        decisions.append(dict(path=name,package=label,before=row['before'],after=ordinary(Q/name),
            decision=row['decision'],copied_product_LOC_credit=0))
os5=read(F/'.agents/os5-20261015/TRANSFER-MANIFEST.json')
for name in extra_paths:
    assert ordinary(Q/name)['sha256']==os5['payloads'][name]['candidate']['sha256']
    decisions.append(dict(path=name,package='os5',before=None,after=ordinary(Q/name),
        decision='CREATE_FROM_REVIEWED_TEST_INPUT',new_test_LOC_credit=0))
def methods(path):
    tree=ast.parse(Path(path).read_text())
    body=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
    return {n.name:n for n in body.body if isinstance(n,ast.FunctionDef)}
a=methods(R/'before-images/os5/src/ceta/kernel/transactions.py')
b=methods(R/'approved-inputs/os5/src/ceta/kernel/transactions.py')
c=methods(Q/'src/ceta/kernel/transactions.py')
retained={n:ast.dump(node,include_attributes=False)==ast.dump(c[n],include_attributes=False)
    for n,node in a.items() if n not in ('__init__','prepare')}
assert all(retained.values()) and set(c)==set(a)|{'_prepare'}
for name in ('prepare','_prepare'):
    assert ast.dump(ast.Module(body=c[name].body,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=b[name].body,type_ignores=[]),include_attributes=False)
assert ast.unparse(c['prepare'].decorator_list[0])=='_coordinated'
constructor=c['__init__'].body
positions={}
for i,node in enumerate(constructor):
    if '_CpuExecutionCoordinator' in ast.unparse(node):positions['cpu_coordinator']=i
    if '_bind_preparation_kernel' in ast.unparse(node):positions['publish_owner_binding']=i
assert positions['cpu_coordinator']<positions['publish_owner_binding']
js5=read(F/'.agents/js5-20261015/TRANSFER-MANIFEST.json');aux={}
for path,pin in js5['auxiliaries'].items():
    assert type(pin) is str
    source=F/'.agents/js5-20261015'/path;facts=ordinary(source);assert facts['sha256']==pin
    if not (Q/path).exists():bytes_copy(source,Q/path,facts)
    assert ordinary(Q/path)['sha256']==pin;aux[path]=ordinary(Q/path)
write_new(R/'ASSEMBLY.json',dict(at=utc(),inputs=reference(R/'INPUTS.json'),
    payloads={n:ordinary(Q/n) for n in sorted(names)},payload_count=len(names),decisions=decisions,
    transaction_method_conservation=retained,OS5_private_prepare_bodies_exact=True,
    coordinated_prepare=True,constructor_order=positions,scope_addition=reference(R/'SCOPE-ADDITION-OS5-TESTS.json'),
    auxiliaries=aux,copied_product_and_test_LOC_credit=0,Source_publication=False,
    prior_failures=[dict(tool_chunk='197c5d',exit_status=1,type='AttributeError',
        cause='Preparation auxiliary map values are SHA strings, not dictionaries. All selected payloads and merged transaction bytes were already written; finalizer resumed without rerunning publication.',
        preserved_script=reference(R/'prior-attempts/assemble-r1.py'))]))
print(json.dumps(dict(normative_payloads=len(names),reviewed_auxiliaries=len(aux),
    KA5_methods_retained=len(retained),constructor_order=positions,Source_writes=False)))
