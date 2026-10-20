"""Prepare dormant exact-byte JS9 adapters; execute no tests or product effects."""
from pathlib import Path
from datetime import datetime,timezone
import ast,collections,difflib,hashlib,importlib.util,json,os,stat,sys

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
Q=F/'.agents/js9-runtime-20261020';D=R/'successor-r1'
OLD=F/'.agents/runtime/js8-20261015/amendment-report1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
manifest=R/'MANIFEST-R4.json'
assert sha(manifest)=='212f1913af6ef24c24041628d2dcca23c7b754849ba79de9db8d75a210b3f532'
m=json.loads(manifest.read_bytes());assert all(sha(Q/n)==p for n,p in m['payload_hashes'].items())
origins={}
def write(name,text,origin=None):
    path=D/name;ast.parse(text)
    with path.open('x',encoding='utf8',newline='\n') as stream:stream.write(text)
    if origin:
        origins[name]=dict(path=str(origin),sha256=sha(origin),
            delta=''.join(difflib.unified_diff(origin.read_text(encoding='utf8').splitlines(True),text.splitlines(True))))
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def replace(text,old,new):
    assert old in text,old
    return text.replace(old,new)

# Unmodified custody observers and enclosing owned-process retirement wrapper.
for name in ['bounded_custody.py','gc_observer.py','resource_observer.py']:
    raw=(OLD/name).read_bytes()
    with (D/name).open('xb') as stream:stream.write(raw)
    origins[name]=dict(path=str(OLD/name),sha256=sha(OLD/name),exact_byte_copy=True)

text=(OLD/'run_full.py').read_text(encoding='utf8')
text=replace(text,'amendment_support','js9_support')
text=replace(text,"for path in sorted((root/'src/ceta').rglob('*.py')):","for name in m['product_modules']:\n        path=root/name")
text=replace(text,'assert len(modules)==88',"assert len(modules)==len(m['product_modules'])")
text=replace(text,"expected=list(j.ids(suite));j.require_case_ids(expected);assert not loader.errors", "suite=j.ordered_suite(suite,root,loader)\n    expected=list(j.ids(suite));j.require_case_ids(expected);assert not loader.errors")
text=replace(text,"s.sha(Q/'TRANSFER-MANIFEST.json')","j.manifest_reference()['sha256']")
text=replace(text,"j.exact_ref(R/'AMENDMENT.json')","j.exact_ref(R/'CASESET.json')")
write('run_full.py',text,OLD/'run_full.py')
text=replace((OLD/'launch_full.py').read_text(encoding='utf8'),'amendment_support','js9_support')
write('launch_full.py',text,OLD/'launch_full.py')

text=(OLD/'native-gate/native_case_gate.py').read_text(encoding='utf8')
text=replace(text,".agents/runtime/js8-20261015/amendment-report1/native-gate", ".agents/runtime/js9-runtime-20261020/successor-r1")
text=replace(text,"RUN = 'js8-20261015'","RUN = 'js9-runtime-20261020'")
text=replace(text,"JS8_DISPOSABLE_NO_PROFILE_CASE_ROOT_RELEASE_V1","JS9_DISPOSABLE_NO_PROFILE_CASE_ROOT_RELEASE_V1")
text=replace(text,".agents/js8-amendment-report1-20261017", ".agents/js9-runtime-20261020")
text=replace(text,".agents/runtime/js8-20261015/amendment-report1", ".agents/runtime/js9-runtime-20261020/successor-r1")
write('native_case_gate.py',text,OLD/'native-gate/native_case_gate.py')

text=replace((OLD/'fixture_runtime.py').read_text(encoding='utf8'),'amendment_support','js9_support')
text=replace(text,"fs, sha, ordinary, bytes_copy = s.fs, s.sha, s.ordinary, s.bytes_copy", """fs, sha, ordinary, bytes_copy = s.fs, s.sha, s.ordinary, s.bytes_copy
    from js9_support import packet
    capacity=packet()['fixture_dependencies']['capacity']
    assert ordinary(Path(capacity['path']))==capacity
    os.environ.update(CETA_CPU_CAPACITY_NATIVE='1',CETA_OUTCOME_CAPACITY_NATIVE='1',
        CETA_OUTCOME_CAPACITY_HELPER=capacity['path'],CETA_OUTCOME_CAPACITY_SHA256=capacity['sha256'],
        CETA_OUTCOME_CAPACITY_FIXTURES=str(outroot/'native-capacity'),
        CETA_JS9_FIXTURE_ROOT=str(outroot/'controlled-composition'))
    (outroot/'native-capacity').mkdir();(outroot/'controlled-composition').mkdir()""")
text=replace(text,"for name in ('test_windows_jobs','test_kernel_transactions'", "importlib.import_module('test_native_owner_preparation').FIXTURES=outroot/'owner-preparation'\n    for name in ('test_windows_jobs','test_kernel_transactions'")
text=replace(text,"bindings = [dict(test_id=case,kind=kind,closed=o.closed,pending=o.pending_native_resources)", "bindings = [dict(test_id=case,kind=kind,closed=o.closed,pending=o.pending_native_resources,\n            controlled_API=(kind=='store' and o._api is not None and type(o._api).__name__=='SimpleNamespace'))")
text=replace(text,"bindings_closed=all(row['closed'] and not row['pending'] for row in bindings),", """bindings_closed=all(row['closed'] and not row['pending'] or
                row['controlled_API'] and row['kind']=='store' and row['test_id']==
                'test_native_runtime_composition.NativeRuntimeCompositionTests.test_interrupted_native_open_preserves_unknown_output_without_false_closure'
                and not row['closed'] and len(row['pending'])==1 and row['pending'][0]['kind']=='file_open'
                and row['pending'][0]['retry']=='UNCERTAIN' and row['pending'][0]['handle'] is None
                for row in bindings),""")
text=replace(text,"qualification='Exact captured Python owners", "controlled_binding_uncertainty=[row for row in bindings if row['controlled_API'] and row['pending']],\n            qualification='Actual native bindings must close; the one exact pure no-return control remains explicitly pending. Exact captured Python owners")
write('fixture_runtime.py',text,OLD/'fixture_runtime.py')

# Exact original2334 IDs, all successor methods and inherited native cases.
parent_path=F/'.agents/runtime/js8-20261015/APPROVED-CASESET.json'
assert sha(parent_path)=='df36448a047fb101973936d0e97324368926fce27b801c01150f2e9dec88fcfb'
parent=json.loads(parent_path.read_bytes())['expected_ids'];all_ids=set(parent);locators={}
for path in sorted((Q/'tests/contract').rglob('test_*.py')):
    module=path.relative_to(Q/'tests/contract').with_suffix('').as_posix().replace('/','.')
    tree=ast.parse(path.read_bytes());classes={c.name:c for c in tree.body if isinstance(c,ast.ClassDef)};memo={}
    def methods(name):
        if name in memo:return memo[name]
        node=classes[name];own={n.name:n for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')};valid=False
        for base in node.bases:
            if isinstance(base,ast.Attribute) and base.attr=='TestCase' or isinstance(base,ast.Name) and base.id=='TestCase':valid=True
            elif isinstance(base,ast.Name) and base.id in classes:
                inherited=methods(base.id)
                if inherited is not None:valid=True;own={**inherited,**own}
        memo[name]=own if valid else None;return memo[name]
    for name in classes:
        members=methods(name)
        if members is None:continue
        for method,node in members.items():
            case=module+'.'+name+'.'+method;all_ids.add(case)
            locators[case]=dict(path=path.relative_to(Q).as_posix(),source_sha256=sha(path),
                method_ast_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
                first_line=node.lineno,last_line=node.end_lineno)
assert len(all_ids)==2622
assert set(parent).issubset(locators),'Original case AST locator unavailable'
extra=all_ids-set(parent);last={case.rsplit('.',1)[0]:i for i,case in enumerate(parent)};ordered=[]
for i,case in enumerate(parent):
    ordered.append(case);prefix=case.rsplit('.',1)[0]
    if last[prefix]==i:ordered.extend(sorted(n for n in extra if n.rsplit('.',1)[0]==prefix))
ordered.extend(sorted(extra-set(ordered)))
assert len(ordered)==len(set(ordered))==2622
assert [name for name in ordered if name in set(parent)]==parent
reasoning=[name for name in ordered if name.startswith('reasoning.')];assert len(reasoning)==50
save(D/'CASESET.json',dict(at=now(),expected_count=2622,expected_ids=ordered,parent2334_ids=parent,
    parent_reference=dict(repository_relative_path=parent_path.relative_to(F).as_posix(),sha256=sha(parent_path)),
    added_ids=sorted(extra),method_locators=locators,
    explicit_namespace_modules=['reasoning.test_reasoning_integration','reasoning.test_reasoning_repairs'],
    method_bodies_changed_for_inventory=False,reasoning_original21_plus_repair29=True))

# Native observer adaptation retains original launch bounds and cleanup gates.
native=F/'.agents/runtime/observer-origin-review-20261017/successor-r1/run_native_successor.py'
text=native.read_text(encoding='utf8')
start=text.index("Q = F / '.agents/observer-origin-repair-20261017'")
end=text.index("binary = F / '.agents/runtime/ob2-20261014/build-reuse/effect_observer.exe'")
text=text[:start]+"""import argparse
import js9_support as j
from js9_support import Q,R
parser=argparse.ArgumentParser();parser.add_argument('label')
parser.add_argument('--release-path',type=Path,required=True);parser.add_argument('--release-sha256',required=True)
args=parser.parse_args();assert args.label.isidentifier()
release=j.require_release(args.release_path,args.release_sha256,'native-observer')
j.verify(source='before')
assert os.name=='nt' and struct.calcsize('P')==8
label=args.label
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
expected=j.manifest()['expected_payload_hashes']
before={name:sha(Q/name) for name in expected};assert before==expected
"""+text[end:]
text=replace(text,"sha(A / 'HANDOFF.json')","j.manifest_reference()['sha256']")
text=replace(text,"reviewer='/root/native_denial_diagnosis'","actor='/root/recovery_regression20'")
text=replace(text,"receipt = dict(actor=", "j.verify(source='before')\nreceipt = dict(actor=")
text=replace(text,"failfast=True, helper_pins=pins", "release=j.exact_ref(args.release_path),failfast=True, helper_pins=pins")
write('run_native_observer.py',text,native)

save(D/'ADAPTER-DELTAS.json',dict(at=now(),origins=origins,
    executed=False,Source_publication=False,profile_creation=False,
    controlled_uncertain_binding_observation='Exact pure no-native-return case remains PENDING; actual native bindings still require closure',
    final_Q_manifest_sha256=sha(manifest)))
print(json.dumps(dict(prepared=str(D),static_case_ids=len(ordered),reasoning_cases=len(reasoning),native_execution=False)),flush=True)
