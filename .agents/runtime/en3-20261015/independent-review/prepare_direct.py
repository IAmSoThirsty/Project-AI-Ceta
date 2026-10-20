"""Qualify exact Q imports and Q leaf reads with only temporary outputs redirected."""
from review_support import *
import ast
old=D/'run_tests.py';body=old.read_text()
changes=[("M=D/'replica';E=D/'qualification-r1';E.mkdir()","M=D/'replica';E=D/'direct-r1';E.mkdir()"),
    ("sys.path[:0]=[str(M/'src'),str(M/'tests/contract')]","sys.path[:0]=[str(Q/'src'),str(M/'tests/contract')]"),
    ("parent_file=F/", "class FixtureRoot:\n    def __fspath__(self):return str(Q)\n    def __truediv__(self,part):\n        return E/'leaf-fixtures' if str(part).replace('\\\\','/')=='.local-test-output' else Q/part\n    def resolve(self,*args,**kwargs):return Q.resolve(*args,**kwargs)\nmodules[4].ROOT=FixtureRoot()\nmodules[5].ROOT=Q\nparent_file=F/"),
    ("spec=importlib.util.spec_from_file_location('ceta.contracts._independent_en2_parser_oracle',parent_file)","spec=importlib.util.spec_from_file_location('_independent_en2_parser_oracle',parent_file)"),
    ("previous=importlib.util.module_from_spec(spec);sys.modules[spec.name]=previous;spec.loader.exec_module(previous)","previous=importlib.util.module_from_spec(spec);previous.__package__='ceta.contracts';sys.modules[spec.name]=previous;spec.loader.exec_module(previous)"),
    ("'current_parser':ordinary(M/'src/ceta/contracts/owner_enrollment.py')","'current_parser':ordinary(Q/'src/ceta/contracts/owner_enrollment.py')"),
    ("assert all(Path(path).is_relative_to(M/'src') or name=='ceta.contracts._independent_en2_parser_oracle' and Path(path)==parent_file for name,path in imports.items())","assert all(Path(path).is_relative_to(Q/'src') for path in imports.values())"),
    ("'original_Source_Q_replica_exact':True,'raw_sha256':sha(E/'tests.txt'),","'original_Source_Q_replica_exact':True,'all_ceta_imports_from_exact_Q':True,\n    'leaf_guard_reads_actual_Q_contracts':True,'only_leaf_temporary_root_rebound':str(E/'leaf-fixtures'),'raw_sha256':sha(E/'tests.txt'),")]
for before,after in changes:
    assert body.count(before)==1,before
    body=body.replace(before,after)
target=D/'run_direct.py';compile(body,str(target),'exec')
def methods(text):
    return {n.name+'.'+m.name:ast.dump(m,include_attributes=False) for n in ast.walk(ast.parse(text))
        if isinstance(n,ast.ClassDef) for m in n.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_')}
assert methods(old.read_text())==methods(body)
with target.open('x',encoding='utf8',newline='\n') as out:out.write(body)
write(D/'DIRECT-BINDING.json',{'at':utc(),'parent_runner':ordinary(old),'direct_runner':ordinary(target),
    'own_test_method_ASTs_exact':True,'original109_methods_unchanged':True,
    'reason':'Meet exact frozen-Q import and leaf-read provenance; first byte-exact replica test run remains retained.',
    'changes':['Q/src imports','Actual Q contract leaf reads','Only source-coverage temporary output directory rebound into reviewer runtime',
        'EN2 data-only oracle has separate non-ceta module name with canonical relative imports'],
    'product_code_or_test_edits':False})
print(json.dumps({'direct_runner':str(target),'sha256':sha(target),'method_ASTs_exact':True}),flush=True)
