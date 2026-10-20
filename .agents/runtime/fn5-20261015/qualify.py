"""Finite joined ownership, pure contract boundary and before/after proofs."""
from foundation_support import *
import ast,io,tokenize,unittest

v=read(R/'INPUTS.json');assembly=read(R/'ASSEMBLY.json')
names=set(assembly['payloads']);before={n:ordinary(Q/n) for n in names}
assert before==assembly['payloads'] and len(before)==351
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
import test_source_coverage as coverage
selected=('test_contract_core_has_no_infrastructure_or_other_domain_imports',
    'test_only_the_observed_enum_type_import_is_qualified',
    'test_contract_leaf_rejects_infrastructure_and_relative_domain_escape')
suite=unittest.TestSuite(coverage.SourceCoverageTests(name) for name in selected)
executed=[];stopped=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
with (R/'contract-leaf-tests.txt').open('x',encoding='utf8') as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
assert result.wasSuccessful() and not result.skipped
assert len(executed)==3 and executed==stopped

compiled={}
for name in sorted(names):
    if name.endswith('.py'):
        raw=(Q/name).read_bytes();compile(raw,str(Q/name),'exec',dont_inherit=True)
        compiled[name]=digest(raw)
def meaningful(path):
    raw=Path(path).read_text();tree=ast.parse(raw);excluded=set()
    for node in ast.walk(tree):
        if isinstance(node,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str):
                excluded.update(range(node.body[0].lineno,node.body[0].end_lineno+1))
    code=set()
    for token in tokenize.generate_tokens(io.StringIO(raw).readline):
        if token.type not in (tokenize.ENCODING,tokenize.COMMENT,tokenize.NL,tokenize.NEWLINE,tokenize.INDENT,tokenize.DEDENT,tokenize.ENDMARKER):
            code.update(range(token.start[0],token.end[0]+1))
    return len(code-excluded)

parent_after={};mismatches=[]
for label,input in v['packages'].items():
    path=safe_proof(input['manifest']);body=read(path);root=path.parent
    rows={n:ordinary(root/n) for n in body['payloads']}
    expected={n:row['candidate'] for n,row in body['payloads'].items()}
    differences=[n for n in rows if rows[n]!=expected[n]]
    parent_after[label]=dict(manifest=reference(path),payloads=len(rows),ordinary_native_identity_exact=not differences,mismatches=differences)
    mismatches.extend(label+':'+n for n in differences)
assert not mismatches,mismatches
environment={n:ordinary(PY.parent.parent/n) for n in v['E33601']}
e3_exact=environment==v['E33601']
assert e3_exact
observed=set();environment_root=PY.parent.parent
for parent,dirs,files_here in os.walk(environment_root,followlinks=False):
    for child in dirs:assert not fs.reparse(fs.lstat(Path(parent)/child))
    for leaf in files_here:observed.add((Path(parent)/leaf).relative_to(environment_root).as_posix())
assert observed==set(v['E33601'])
after={n:ordinary(Q/n) for n in names};assert before==after
guards=dict(tests_run=3,executed_ids=executed,stopped_ids=stopped,failures=0,errors=0,skips=0,exit_status=0,
    raw=reference(R/'contract-leaf-tests.txt'),actual_contract_root=str(Q/'src/ceta/contracts'))
write_new(R/'QUALIFICATION.json',dict(at=utc(),contract_leaf=guards,
    compiled_Python_payloads=compiled,product_modules=sum(n.startswith('src/ceta/') for n in compiled),
    candidate_before=before,candidate_after=after,parent_after=parent_after,
    E33601_ordinary_file_membership_bytes_native_identity_exact=e3_exact,
    E3_before_member_count=len(v['E33601']),E3_after_member_count=len(environment),
    environment_after=environment,
    no_whole_directory_metadata_equality_claim=True,F4_metadata_issue_unwaived=True,
    no_uninterrupted_Source_conservation_claim=True,Source_publication=False,
    meaningful_LOC=dict(new_product=0,new_normative_tests=0,copied_product_and_tests=0,
        assembly_conflict_resolution=0,new_runtime_integration_test=meaningful(R/'test_preparation_coordination.py'),
        copied_component_code='Previously authored and credited in the original component receipts; zero additional credit in FN5.'),
    prior_failures=v['prior_failures']+assembly['prior_failures']+[
        dict(tool_chunk='e0b4d5',exit_status=1,kind='Exact inherited strengthened projection test mapping; Root confirmed approved transition.'),
        dict(tool_chunk='5b44ac',exit_status=1,kind='New controlled oracle expected ACTIVE instead of canonical ENROLLED; corrected only assertion after preserving original.'),
        dict(tool_chunk='2f3f2c',exit_status=1,kind='Consumer94 methods all passed; receipt reader used wrong native-connection field; original raw/script preserved and corrected run94 passed.')]))
print(json.dumps(dict(contract_leaf=3,compiled_python=len(compiled),product_modules=sum(n.startswith('src/ceta/') for n in compiled),
    candidate_native_exact=True,parents=parent_after,E3_exact=e3_exact,new_product_LOC=0,
    new_runtime_integration_test_LOC=meaningful(R/'test_preparation_coordination.py'))))
