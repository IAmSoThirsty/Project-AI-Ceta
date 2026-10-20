"""One path-by-path integration; no historical whole-tree overlays."""
from foundation_support import *
import ast,difflib

inputs=read(R/'INPUTS.json')
assert read(R/RUN/'claims.json')['implement']['executor_id']==AUTHOR
assert not (R/'ASSEMBLY.json').exists()

def replace_owned(path,raw):
    path=Path(path)
    assert path.is_relative_to(Q) and fs.safe_components(path.parent)
    if path.exists():
        with path.open('wb') as out:out.write(raw)
    else:fs.write_new(path,raw)
    assert path.read_bytes()==raw

decisions=[]
for label in ('os5','js5'):
    for name in inputs['selected'][label]:
        incoming=R/'approved-inputs'/label/name
        assert ordinary(incoming)['sha256']==inputs['overlap'][name][-1 if label=='js5' else 0]['approved_input']['sha256']
        if name=='src/ceta/kernel/transactions.py':continue
        prior=ordinary(Q/name) if (Q/name).exists() else None
        raw=incoming.read_bytes()
        if prior is None or prior['sha256']!=digest(raw):replace_owned(Q/name,raw)
        decisions.append(dict(path=name,package=label,before=prior,after=ordinary(Q/name),
            decision='EXACT_REUSE' if prior and prior['sha256']==digest(raw) else 'EXACT_SELECTED_BYTES',new_product_LOC=0))

name='src/ceta/kernel/transactions.py'
base=R/'before-images/os5'/name;incoming=R/'approved-inputs/os5'/name
a=base.read_text();b=incoming.read_text()
assert (Q/name).read_bytes()==base.read_bytes()
ta,tb=ast.parse(a),ast.parse(b)
ca=next(n for n in ta.body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
cb=next(n for n in tb.body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
ma={n.name:n for n in ca.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
mb={n.name:n for n in cb.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
lines=a.splitlines(True);other=b.splitlines(True)
start=min([ma['prepare'].lineno]+[d.lineno for d in ma['prepare'].decorator_list])-1
end=ma['prepare'].end_lineno
new_prepare=''.join(other[mb['prepare'].lineno-1:mb['_prepare'].end_lineno])
lines[start:end]=['    @_coordinated\n'+new_prepare]
merged=''.join(lines)
helpers=''.join(other[next(n for n in tb.body if isinstance(n,ast.ClassDef) and n.name=='_PreparationInvocation').lineno-1:cb.lineno-1])
assert merged.count('class KernelTransactions:')==1
merged=merged.replace('class KernelTransactions:',helpers+'class KernelTransactions:',1)
assert merged.count('import uuid\n')==1
merged=merged.replace('import uuid\n','import threading\nimport uuid\n',1)
old_init=ast.get_source_segment(b,mb['__init__'])
addition=old_init[old_init.index('        self._preparation_owner ='):]
needle='        self._registry = StoreKey("projection", installation_scope_id, "kernel-registry")'
assert merged.count(needle)==1
merged=merged.replace(needle,needle+'\n'+addition,1)
compile(merged,str(Q/name),'exec')
result_class=next(n for n in ast.parse(merged).body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
methods={n.name:n for n in result_class.body if isinstance(n,ast.FunctionDef)}
retained={n:ast.dump(methods[n],include_attributes=False)==ast.dump(node,include_attributes=False)
    for n,node in ma.items() if n not in ('prepare','__init__')}
assert all(retained.values()) and set(methods)==set(ma)|{'_prepare'}
for method in ('prepare','_prepare'):
    left=methods[method];right=mb[method]
    assert ast.dump(ast.Module(body=left.body,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=right.body,type_ignores=[]),include_attributes=False)
assert len(methods['prepare'].decorator_list)==1 and ast.unparse(methods['prepare'].decorator_list[0])=='_coordinated'
replace_owned(Q/name,merged.encode('utf8'))
fs.write_new(R/'transactions-KA5-to-FN5.diff',''.join(difflib.unified_diff(a.splitlines(True),merged.splitlines(True),fromfile='KA5/transactions.py',tofile='FN5/transactions.py')).encode('utf8'))
fs.write_new(R/'transactions-OS5-to-FN5.diff',''.join(difflib.unified_diff(b.splitlines(True),merged.splitlines(True),fromfile='OS5/transactions.py',tofile='FN5/transactions.py')).encode('utf8'))
decisions.append(dict(path=name,decision='SURGICAL_METHOD_ASSEMBLY',
    KA5_retained_methods=retained,OS5_prepare_and_private_prepare_bodies_exact=True,
    public_prepare_retains_KA5_coordinated_decorator=True,
    constructor='Keep KA5 CPU coordinator; add OS5 exact private preparation owner binding after canonical fields.',
    helpers='Exact OS5 _PreparationInvocation and _preparation_failure; existing coordinator import retained.',
    result=ordinary(Q/name),integration_credit=0))

# Root's later exact three-path scope addition preserves reviewed test bodies.
auxiliary_tests={}
os5=read(F/'.agents/os5-20261015/TRANSFER-MANIFEST.json')
extra_paths=['tests/contract/'+leaf for leaf in ('test_owner_session_cleanup.py',
    'test_owner_session_context_boundary.py','test_native_cpu_owner_approval.py')]
write_new(R/'SCOPE-ADDITION-OS5-TESTS.json',dict(at=utc(),
    original_task_binding=reference(R/'TASK-BINDING.json'),
    original_claim=read(R/RUN/'claims.json')['implement'],
    authority='Root directly authorized these exact three already-reviewed OS5 tests as necessary regression dependencies.',
    CREATE_from_reviewed_test_input=extra_paths,new_implementation_credit=0,
    before={n:None for n in extra_paths},no_other_scope_change=True))
for leaf in ('test_owner_session_cleanup.py','test_owner_session_context_boundary.py','test_native_cpu_owner_approval.py'):
    path='tests/contract/'+leaf;source=F/'.agents/os5-20261015'/path
    auxiliary_tests[leaf]=bytes_copy(source,Q/path,os5['payloads'][path]['candidate'])

# These eleven existing same-project tools/registries are explicit auxiliary inputs.
js5=read(F/'.agents/js5-20261015/TRANSFER-MANIFEST.json')
auxiliaries={}
for path,row in js5['auxiliaries'].items():
    source=F/'.agents/js5-20261015'/path
    expected=row.get('candidate',row)
    facts=ordinary(source)
    assert facts['sha256']==expected['sha256']
    if not (Q/path).exists():auxiliaries[path]=bytes_copy(source,Q/path,facts)
    else:
        assert ordinary(Q/path)['sha256']==facts['sha256'];auxiliaries[path]=ordinary(Q/path)
names=set(inputs['base_payloads'])|set(inputs['selected']['os5'])|set(inputs['selected']['js5'])|set(extra_paths)
rows={n:ordinary(Q/n) for n in sorted(names)}
write_new(R/'ASSEMBLY.json',dict(at=utc(),inputs=reference(R/'INPUTS.json'),payloads=rows,payload_count=len(rows),
    decisions=decisions,auxiliary_test_dependencies=auxiliary_tests,auxiliaries=auxiliaries,
    copied_product_and_test_LOC_credit=0,Source_publication=False,all_active_paths_unmodified=True))
print(json.dumps(dict(normative_payloads=len(rows),selected_overlay_paths=len(decisions),
    KA5_methods_retained=len(retained),runtime_test_dependencies=len(auxiliary_tests),Source_writes=False)))
