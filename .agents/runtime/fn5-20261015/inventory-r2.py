"""Hash and map every inherited normative test body without importing it."""
from foundation_support import *
import ast,collections,difflib

assembly=read(R/'ASSEMBLY.json');payloads=assembly['payloads']
def methods(path):
    tree=ast.parse(Path(path).read_text(encoding='utf8'))
    rows={}
    for cls in tree.body:
        if not isinstance(cls,ast.ClassDef):continue
        for fn in cls.body:
            if isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)) and fn.name.startswith('test_'):
                identity=Path(path).stem+'.'+cls.name+'.'+fn.name
                rows[identity]=dict(ast_sha256=digest(ast.dump(fn,include_attributes=False).encode('utf8')),
                    line=fn.lineno,end_line=fn.end_lineno)
    return rows

current={n:methods(Q/n) for n in payloads if n.startswith('tests/') and n.endswith('.py')}
comparisons={};differences=[]
for label,run in (('ka5','ka5-20261015'),('os5','os5-20261015'),('js5','js5-20261015')):
    p=F/'.agents'/run;body=read(p/'TRANSFER-MANIFEST.json');rows={}
    for name,row in body['payloads'].items():
        if not (name.startswith('tests/') and name.endswith('.py')):continue
        expected=methods(p/name);actual=current.get(name,{})
        missing=sorted(set(expected)-set(actual))
        changed=sorted(k for k in expected.keys()&actual.keys() if expected[k]['ast_sha256']!=actual[k]['ast_sha256'])
        rows[name]=dict(parent_file=row['candidate'],methods=len(expected),missing=missing,changed=changed)
        if missing or changed:
            differences.append(dict(package=label,path=name,missing=missing,changed=changed))
    comparisons[label]=rows
write_new(R/'TEST-METHOD-INVENTORY-r2.json',dict(at=utc(),product_root=str(Q),
    method_AST_algorithm='SHA256(ast.dump(method, include_attributes=False)); includes assertions, decorators, arguments and bodies.',
    inherited= current,parent_comparisons=comparisons,differences=differences,
    parent_method_totals={k:sum(row['methods'] for row in v.values()) for k,v in comparisons.items()},
    joined_local_test_methods=sum(map(len,current.values())),
    distinct_local_method_ids=len({i for rows in current.values() for i in rows}),
    actual_executed_count='Recorded separately by qualified selected runners; this AST inventory is not execution.',
    deferred='Original restricted no-profile case, original seven native CPU methods and genuine/native owner gates not executed here.'))
expected_method='test_projections.ProjectionTests.test_read_failure_preserves_primary_exception_when_rollback_observation_fails'
expected_differences=[dict(package=label,path='tests/contract/test_projections.py',missing=[],changed=[expected_method]) for label in ('ka5','os5')]
assert differences==expected_differences,differences
write_new(R/'APPROVED-TEST-CONFLICT-RESOLUTION.json',dict(at=utc(),path='tests/contract/test_projections.py',method=expected_method,
    approved_selected_input=reference(F/'.agents/js5-20261015/tests/contract/test_projections.py'),
    preserved_prior=reference(R/'before-images/js5/tests/contract/test_projections.py'),
    old_invariant='After uncertain rollback, manually reset the underlying connection and reuse the same journal.',
    current_approved_invariant='UNCERTAIN rollback permanently denies journal reads; retain exact owner/connection/error, explicitly close then reopen and verify canonical rows.',
    authority='Root exact reviewed JS5 selected fifteen-path adoption includes this strengthened test.',
    no_assertion_weakening=True,new_method_authorship_credit=0,
    prior_failure=dict(tool_chunk='e0b4d5',exit_status=1,kind='Inventory detected this deliberate earlier reviewed contract/test transition; no runtime product failure.')))

ownership={}
for name,row in payloads.items():
    provenance=[d for d in assembly['decisions'] if d['path']==name]
    ownership[name]=dict(candidate=ordinary(Q/name),origin='KA5 exact REUSE' if not provenance else provenance,
        base=read(R/'INPUTS.json')['base_payloads'].get(name),integration_credit=0)
write_new(R/'FILE-OWNERSHIP.json',dict(at=utc(),paths=ownership,
    transactions_diff=reference(R/'transactions-KA5-to-FN5.diff'),
    transactions_OS5_diff=reference(R/'transactions-OS5-to-FN5.diff'),
    default_runtime='KernelTransactions.require_runtime_admission remains exactly the KA5 denial.',
    Source_publication=False,new_product_authorship=0))
print(json.dumps(dict(payloads=len(payloads),methods=sum(map(len,current.values())),
    parents={k:sum(vv['methods'] for vv in v.values()) for k,v in comparisons.items()},changed_test_methods=len(differences))))
