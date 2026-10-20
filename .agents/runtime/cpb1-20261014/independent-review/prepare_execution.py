"""Relocate only author harness output; retain every original test method body."""
from pathlib import Path
import ast, hashlib, json, os, sys
F=Path('T:/00-Active/Project-AI-CETA');Q=F/'.agents/cpb1-20261014';R=F/'.agents/runtime/cpb1-20261014';D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=D
prep=json.loads((D/'PREPARATION.json').read_text())
def methods(raw):
    return {node.name:ast.dump(node,include_attributes=False) for node in ast.walk(ast.parse(raw)) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
prepared={}
for name in ('run_tests.py','probe_return_occupancy.py'):
    raw=(R/name).read_bytes();text=raw.decode('utf-8');old="R=P/'.agents/runtime/cpb1-20261014'";new="R=Path(__file__).resolve().parent"
    assert text.count(old)==1
    relocated=text.replace(old,new)
    assert methods(text)==methods(relocated)
    with (D/name).open('x',encoding='utf-8',newline='\n') as out:out.write(relocated)
    prepared[name]=dict(original=s.ordinary(R/name),relocated=s.ordinary(D/name),all_function_ASTs_unchanged=True,only_change='Top-level output R assignment')
with (D/'SOURCE-INPUTS.json').open('xb') as out:out.write((R/'SOURCE-INPUTS.json').read_bytes())
assert s.sha(D/'SOURCE-INPUTS.json')==s.sha(R/'SOURCE-INPUTS.json')
(D/'fixture-root/.agents/fixtures').mkdir(parents=True,exist_ok=False)
s.write_new(D/'EXECUTION-PREPARATION.json',dict(at=s.utc(),prepared=prepared,source_inputs_byte_transport=dict(original=s.ordinary(R/'SOURCE-INPUTS.json'),copied=s.ordinary(D/'SOURCE-INPUTS.json')),
    fixture_relocation='test_windows_jobs.ROOT only; actual product remains imported from frozen Q/src; all test method ASTs unchanged.',
    initial_candidate326_native_exact=all(s.ordinary(Q/n)==row for n,row in prep['candidate326'].items()),class15_writes_permitted=False))
print(json.dumps(dict(prepared=list(prepared),method_ASTs_exact=True,fixture_scope=str(D/'fixture-root'))))
