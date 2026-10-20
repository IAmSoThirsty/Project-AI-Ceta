"""Bind the failed parent and prove the finite constructor-only successor."""
from foundation_support import *
import ast,difflib,io,tokenize,unittest

v=read(R/'INPUTS.json');P=F/'.agents/fn5-20261015';PR=F/'.agents/runtime/fn5-20261015'
review=PR/'independent-review/review.json'
assert sha(review)=='4e44b88633520763a730b8b9cb5b2f87ef5fd17f9b4cdc3b200f7c32133f1386'
assert sha(PR/'independent-review/REPORT.json')=='b94ac773f43b6725061d1a4dee6d761627c81fdae5d116b65b5d4534ce07e697'
assert sha(PR/'independent-review/REVIEW-READBACK.json')=='35f1a374290410d0cafa0ea29cae82ff1c1851b557e1ec4faace2fcf2f3eed19'
assert sha(PR/'independent-review/REVIEW-SEAL.json')=='de2ce41a3ba9d7560e5cfcbbebca91cb0862e0d8d34c2b25c0361f084f31088b'
local=read(review);stored=read(PR/'fn5-20261015/receipts/review.json')
state=read(PR/'fn5-20261015/state.json');claims=read(PR/'fn5-20261015/claims.json')
envelope=read(PR/'fn5-20261015/results/review.json')
assert set(local)==STRICT and set(stored)==STRICT|{'git_baseline','observed_git','receipt_hash'}
assert all(canonical(local[k])==canonical(stored[k]) for k in STRICT)
assert local['decision']=='rejected' and type(local['exit_status']) is int and local['exit_status']==1
assert state['sequence']==9 and state['nodes']['review']['state']=='FAILED' and claims=={}
assert state['nodes']['review']['artifact_hash'] is None and local['changed_files']==[]
assert set(envelope)=={'node_id','receipt_hash','result'} and envelope['node_id']=='review'
assert canonical(envelope['result'])==canonical(local['result'])
assert envelope['receipt_hash']==stored['receipt_hash']==state['nodes']['review']['receipt_hash']
assert local['result']['manifest_sha256']==sha(P/'TRANSFER-MANIFEST.json')
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt
from taar.orchestration_persistence import sha256_json
normalized=validate_receipt(local,run_id='fn5-20261015',node_id='review',executor_id=local['executor_id'],
    input_hash=local['input_hash'],claimed_at=local['started_at'],node=read(PR/'fn5-20261015/graph.json')['graph']['nodes']['review'])
normalized.pop('receipt_hash');normalized.update(git_baseline=stored['git_baseline'],observed_git=stored['observed_git'])
assert sha256_json(normalized)==stored['receipt_hash']=='948d41f37f10a4802b01196c11cc01c6f14dd1a928eed15e332cebff9746d82c'
write_new(R/'FAILED-PARENT-READBACK.json',dict(at=utc(),review=reference(review),report=reference(PR/'independent-review/REPORT.json'),
    readback=reference(PR/'independent-review/REVIEW-READBACK.json'),seal=reference(PR/'independent-review/REVIEW-SEAL.json'),
    official_computed_fingerprint=stored['receipt_hash'],actual_state='FAILED',sequence=9,claims={},artifact_hash=None,
    selected458_independent='NOT_RUN by parent reviewer; constructor blocker rejected before that replay. FN6 runs its own final cohort.'))

assembly=read(R/'ASSEMBLY.json');names=set(assembly['payloads'])
before={n:ordinary(Q/n) for n in names};assert before==assembly['payloads'] and len(names)==352
old=(P/'src/ceta/kernel/transactions.py').read_text();new=(Q/'src/ceta/kernel/transactions.py').read_text()
def class_node(text):return next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
a=class_node(old);b=class_node(new)
ma={n.name:n for n in a.body if isinstance(n,ast.FunctionDef)};mb={n.name:n for n in b.body if isinstance(n,ast.FunctionDef)}
assert set(ma)==set(mb)
unchanged={n:ast.dump(ma[n],include_attributes=False)==ast.dump(mb[n],include_attributes=False) for n in ma if n!='__init__'}
assert all(unchanged.values()) and len(unchanged)==33
assert ast.dump(ma['__init__'].args,include_attributes=False)==ast.dump(mb['__init__'].args,include_attributes=False)
assert (ast.dump(ma['__init__'].returns,include_attributes=False) if ma['__init__'].returns else None)==(
    ast.dump(mb['__init__'].returns,include_attributes=False) if mb['__init__'].returns else None)
final=mb['__init__'].body[-1]
assert isinstance(final,ast.If) and ast.unparse(final.test)=='type(owners) is NativeCpuOwnerSession'
assert ast.unparse(final.body[-1])=='NativeCpuOwnerSession._bind_preparation_kernel(owners, self)'
assert ast.unparse(final.body[-2])=='self._preparation_owner = owners'
assert ast.unparse(final.body[-3])=='self._preparation_check = NativeCpuOwnerSession.require_prepared_basis.__get__(owners)'
assert ast.unparse(mb['__init__'].body[-2])=='self._preparation_check = None'
def without_init(tree):
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='KernelTransactions')
    cls.body=[n for n in cls.body if not (isinstance(n,ast.FunctionDef) and n.name=='__init__')];return ast.dump(tree,include_attributes=False)
assert without_init(ast.parse(old))==without_init(ast.parse(new))
parent_manifest=read(P/'TRANSFER-MANIFEST.json')
for name,row in v['parent_payloads'].items():
    # The first INPUTS field names the initial copied FN6 rows. Its native
    # identities must not be mistaken for the distinct frozen parent files.
    expected_parent=parent_manifest['payloads'][name]['candidate']
    assert ordinary(P/name)==expected_parent and expected_parent['sha256']==row['sha256']
    if name!='src/ceta/kernel/transactions.py':assert ordinary(Q/name)==row
write_new(R/'INPUT-ROW-CLARIFICATION.json',dict(at=utc(),original_inputs=reference(R/'INPUTS.json'),
    field='parent_payloads',actual_meaning='Initial351 copied FN6 ordinary-file/native rows, before the constructor repair.',
    exact_frozen_parent_rows_source=reference(P/'TRANSFER-MANIFEST.json'),
    parent_native_comparison='Current parent files compared to parent manifest candidate rows, never the distinct FN6 copied identities.',
    original_inputs_unchanged=True))

def test_methods(path):
    tree=ast.parse(Path(path).read_text());return {cls.name+'.'+fn.name:ast.dump(fn,include_attributes=False)
        for cls in tree.body if isinstance(cls,ast.ClassDef) for fn in cls.body
        if isinstance(fn,ast.FunctionDef) and fn.name.startswith('test_')}
test_conservation={}
for name in v['parent_payloads']:
    if name.startswith('tests/') and name.endswith('.py'):
        assert (Q/name).read_bytes()==(P/name).read_bytes()
        test_conservation[name]=len(test_methods(Q/name))
oracle=test_methods(safe_proof(v['failure_probe']))
current=test_methods(Q/'tests/contract/test_kernel_initializer_publication.py')
literal='InitializerBindingTests.test_failed_final_bound_method_allocation_must_leave_owner_unbound'
assert oracle[literal]==current[literal] and len(current)==3

sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
import test_source_coverage as coverage
leaf_methods=('test_contract_core_has_no_infrastructure_or_other_domain_imports',
    'test_only_the_observed_enum_type_import_is_qualified','test_contract_leaf_rejects_infrastructure_and_relative_domain_escape')
executed=[];stopped=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
with (R/'contract-leaf-tests.txt').open('x',encoding='utf8') as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(
        unittest.TestSuite(coverage.SourceCoverageTests(name) for name in leaf_methods))
assert result.wasSuccessful() and not result.skipped and executed==stopped and len(executed)==3
compiled={}
for name in names:
    if name.endswith('.py'):
        raw=(Q/name).read_bytes();compile(raw,str(Q/name),'exec',dont_inherit=True);compiled[name]=digest(raw)
def code_lines(text):
    excluded=set();tree=ast.parse(text)
    for n in ast.walk(tree):
        if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body:
            first=n.body[0]
            if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str):
                excluded.update(range(first.lineno,first.end_lineno+1))
    lines=set()
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type not in (tokenize.COMMENT,tokenize.NL,tokenize.NEWLINE,tokenize.INDENT,tokenize.DEDENT,tokenize.ENDMARKER,tokenize.ENCODING):
            lines.update(range(token.start[0],token.end[0]+1))
    return lines-excluded
delta=list(difflib.ndiff(old.splitlines(),new.splitlines()))
old_lines=code_lines(old);new_lines=code_lines(new);source_add=source_remove=0;oi=ni=0
for line in delta:
    if line.startswith('  '):oi+=1;ni+=1
    elif line.startswith('- '):oi+=1;source_remove+=oi in old_lines
    elif line.startswith('+ '):ni+=1;source_add+=ni in new_lines
text=(Q/'tests/contract/test_kernel_initializer_publication.py').read_text();tree=ast.parse(text)
reused=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='InitializerBindingTests')
reused_lines=set(range(reused.lineno,reused.end_lineno+1));new_test_lines=code_lines(text)-reused_lines
diff=R/'transactions-initializer.diff';fs.write_new(diff,''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozenFN5',tofile='FN6')).encode('utf8'))
environment={name:ordinary(PY.parent.parent/name) for name in v['E33601']};assert environment==v['E33601']
membership=set()
for parent,dirs,files_here in os.walk(PY.parent.parent,followlinks=False):
    for child in dirs:assert not fs.reparse(fs.lstat(Path(parent)/child))
    for leaf in files_here:membership.add((Path(parent)/leaf).relative_to(PY.parent.parent).as_posix())
assert membership==set(v['E33601'])
after={n:ordinary(Q/n) for n in names};assert before==after
write_new(R/'QUALIFICATION.json',dict(at=utc(),payloads=before,candidate_after=after,parent351_ordinary_native_exact=True,
    unchanged350_payloads=True,all_original_test_files_and_methods_byte_exact=test_conservation,
    exact_original_WT_oracle_method=True,new_normative_methods=3,
    all_other33_transaction_method_ASTs_exact=unchanged,all_noninitializer_production_AST_exact=True,
    public_signature_exact=True,final_constructor_statement_is_owner_publication=True,constructor_diff=reference(diff),
    compiled_python=compiled,product_modules=sum(n.startswith('src/ceta/') for n in compiled),
    contract_leaf=dict(tests_run=3,executed_ids=executed,stopped_ids=stopped,failures=0,errors=0,skips=0,exit_status=0,raw=reference(R/'contract-leaf-tests.txt')),
    E33601_ordinary_membership_bytes_native_exact=True,environment_after=environment,
    whole_directory_metadata_equality_claim=False,Source_conservation_claim=False,Source_publication=False,
    meaningful_LOC=dict(source_added=source_add,source_removed=source_remove,
        moved_publication_line_new_credit=0,new_functional_assignment_lines=2,
        new_test_lines=len(new_test_lines),reused_WT_oracle_lines=len(code_lines(text)&reused_lines),
        new_normative_methods=2,reused_WT_oracle_methods=1,copied351_payload_credit=0,copied_FN5_runtime8_test_credit=0)))
print(json.dumps(dict(payloads=352,unchanged350=True,other_transaction_methods=33,
    original_parent_test_methods=sum(test_conservation.values()),new_normative_test_methods=3,
    source_added=source_add,source_removed=source_remove,new_test_lines=len(new_test_lines),reused_test_lines=len(code_lines(text)&reused_lines),E3_exact=True)))
