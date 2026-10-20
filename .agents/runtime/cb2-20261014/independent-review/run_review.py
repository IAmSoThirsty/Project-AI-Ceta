from pathlib import Path
from dataclasses import replace
import ast, difflib, hashlib, json, os, sys, threading, unittest

P=Path('T:/00-Active/Project-AI-CETA'); Q=P/'.agents/cb2-20261014'
BASE=P/'.agents/runtime/cb2-20261014'; D=BASE/'independent-review'; RUN='cb2-20261014'
OLD=P/'.agents/cb1-20261014'; OD=P/'.agents/runtime/cb1-20261014/independent-review'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014')); import ka1_support as s
s.Q=Q; s.R=D; s.RUN=RUN
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='c4ca0a083524c936ec2b8df4bc1cabef8f68574e3404a007d4542cecc57dd565'
assert s.sha(BASE/'implement.json')=='57d7988710eedb4aabca7e687ff884ab1028a78c4c15a0a5c2d4c6ea89eed3d0'
claim=json.loads((BASE/RUN/'claims.json').read_text())['review']
state=json.loads((BASE/RUN/'state.json').read_text())
assert claim['executor_id']==s.ACTOR and state['nodes']['implement']['state']=='SUCCEEDED'
assert state['nodes']['review']['state']=='RUNNING' and state['sequence']==8
s.write_new(D/'CLAIM-READBACK.json',dict(recorded_at=s.utc(),claim=claim,state=state,
    actual_command='powershell -NoProfile -File T:/02-Config/agents/taar-orchestrate.ps1 node claim cb2-20261014 review --executor /root/history_preservation --workspace T:/00-Active/Project-AI-CETA/.agents/cb2-20261014 --runtime-root T:/00-Active/Project-AI-CETA/.agents/runtime/cb2-20261014',
    command_exit_status=0))
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text()); inputs=json.loads((BASE/'SOURCE-INPUTS.json').read_text())
before={row['relative_path']:s.ordinary(Q/row['relative_path']) for row in manifest['payloads']}
assert len(before)==294 and all(before[row['relative_path']]['sha256']==row['candidate_sha256']
    and before[row['relative_path']]['native_identity']==row['candidate_native_identity'] for row in manifest['payloads'])
source={name:s.ordinary(P/name) for name in inputs['Source290']}; assert source==inputs['Source290']
image=s.ordinary(s.PY)
old_manifest=s.ordinary(OLD/'TRANSFER-MANIFEST.json'); old_probe=s.ordinary(OD/'probe_group_type.py')
assert old_manifest['sha256']=='0ab0a0762dbc840792a229ec2e9c5ee5b5107d36d4f18841845490a8fd3898e3'
assert old_probe['sha256']=='c248020249355aca4650385f4d1b40a08db88f48dfbd1971ae6b2bc63d65dc66'
eligible=['src/ceta/identity/native_code_binding.py','tests/contract/test_native_code_binding.py','contracts/NATIVE_CODE_BINDING_V1.md']
assert sorted(manifest['eligible_application_paths'])==sorted(eligible)
changed=[name for name in before if s.sha(OLD/name)!=before[name]['sha256']]
assert sorted(changed)==sorted(eligible)
old_source=(OLD/eligible[0]).read_bytes(); new_source=(Q/eligible[0]).read_bytes()
assert old_source.count(b"require(self.group in ('source', 'environment'),")==1
assert old_source.replace(b"require(self.group in ('source', 'environment'),",b"require(type(self.group) is str and self.group in ('source', 'environment'),")==new_source
diff=''.join(''.join(difflib.unified_diff((OLD/name).read_text().splitlines(True),
    (Q/name).read_text().splitlines(True),fromfile='CB1/'+name,tofile='CB2/'+name)) for name in eligible)
(D/'SUCCESSOR.diff').write_text(diff,encoding='utf-8',newline='\n')
def test_asts(path):
    tree=ast.parse(path.read_text()); cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='NativeCodeBindingTests')
    return {node.name:ast.dump(node,include_attributes=False) for node in cls.body if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')}
old_tests=test_asts(OLD/eligible[1]); new_tests=test_asts(Q/eligible[1])
assert len(old_tests)==16 and len(new_tests)==18 and all(new_tests[name]==body for name,body in old_tests.items())
new_names=sorted(set(new_tests)-set(old_tests))
assert new_names==['test_custom_equality_group_rejected_before_native_pinning','test_plain_string_subclass_group_rejected_before_native_pinning']
s.write_new(D/'NARROW-DIFF.json',dict(recorded_at=s.utc(),changed_paths=changed,production_exact_one_predicate=True,
    retained_test_methods={name:hashlib.sha256(body.encode()).hexdigest() for name,body in old_tests.items()},
    new_methods=new_names,diff=s.reference(D/'SUCCESSOR.diff'),predecessor=old_manifest,original_hostile_script=old_probe))
E=D/'cohort-r1'; E.mkdir(exist_ok=False); os.environ['TEMP']=os.environ['TMP']=str(E)
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
import test_native_code_binding as tests
from ceta.identity import native_code_binding as binding
from ceta.contracts.wire import ContractError
tests.ROOT=E
owners=[]; ctor=binding.NativeCodeBinding.__init__
def observed(self,*args,**kwargs):
    try:ctor(self,*args,**kwargs)
    finally:
        if hasattr(self,'_api'):owners.append(self)
binding.NativeCodeBinding.__init__=observed
def ids(group):
    for item in group:
        if isinstance(item,unittest.TestSuite):yield from ids(item)
        else:yield item.id()
def run_suite(suite,path):
    expected=list(ids(suite)); executed=[]; stopped=[]; threads=set(threading.enumerate())
    class Result(unittest.TextTestResult):
        def startTest(self,test):executed.append(test.id());super().startTest(test)
        def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
    with path.open('x',encoding='utf-8') as out: result=unittest.TextTestRunner(stream=out,verbosity=2,resultclass=Result).run(suite)
    remaining=[t.name for t in set(threading.enumerate())-threads if t.is_alive()]
    return result,dict(tests_run=result.testsRun,expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
        failures=[(t.id(),tb) for t,tb in result.failures],errors=[(t.id(),tb) for t,tb in result.errors],
        skips=result.skipped,remaining_threads=remaining,raw=s.reference(path))
result,cohort=run_suite(unittest.defaultTestLoader.loadTestsFromModule(tests),E/'tests.txt')
cohort.update(recorded_at=s.utc(),owners=[dict(closed=o.closed,pending=o.pending_native_resources,
    file_count=len(o._files),ancestor_count=len(o._ancestors)) for o in owners],native_receipts=list(tests.NATIVE_RECEIPTS),
    candidate_before=before,source_before=source,python_image=image,fixture_scope=str(E))
imports={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
    if (name=='ceta' or name.startswith('ceta.')) and getattr(module,'__file__',None)}
assert all(Path(path).is_relative_to(Q/'src') for path in imports.values())
cohort['imports']=imports
s.write_new(D/'COHORT.json',cohort)
assert cohort['tests_run']==18 and result.wasSuccessful() and not result.skipped
assert cohort['expected_ids']==cohort['executed_ids']==cohort['stopped_ids'] and not cohort['remaining_threads']
assert all(row['closed'] and not row['pending'] for row in cohort['owners'])

# Compile only the three original class nodes, unchanged. Its old top-level CB1 runner is never executed.
tree=ast.parse((OD/'probe_group_type.py').read_text())
names=['GroupSubclass','EqualityGroup','GroupTypeProbe']
nodes=[node for node in tree.body if isinstance(node,ast.ClassDef) and node.name in names]
assert [node.name for node in nodes]==names
class_hashes={node.name:hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest() for node in nodes}
facts=[]; captured=[]
namespace=dict(__name__='cb2_literal_group_probe',tests=tests,binding=binding,replace=replace,ContractError=ContractError,facts=facts,captured=captured)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(OD/'probe_group_type.py'),'exec'),namespace)
probe_cls=namespace['GroupTypeProbe']; custom=namespace['EqualityGroup']
methods=['test_plain_string_subclass_group_rejected_before_native_pinning','test_custom_equality_group_rejected_before_native_pinning']
H=D/'literal-hostile-r1';H.mkdir(exist_ok=False);tests.ROOT=H
callbacks=[]; native_calls=[]; api_calls=[]
codes={getattr(custom,name).__code__:name for name in ('__eq__','__hash__','__lt__','__gt__')}
def profile(frame,event,arg):
    if event=='call' and frame.f_code in codes:callbacks.append(codes[frame.f_code])
old_profile=sys.getprofile(); api_ctor=binding._BindingAPI.__init__
def native_observed(self,*args,**kwargs):native_calls.append(True);return observed(self,*args,**kwargs)
def api_observed(self,*args,**kwargs):api_calls.append(True);return api_ctor(self,*args,**kwargs)
binding.NativeCodeBinding.__init__=native_observed; binding._BindingAPI.__init__=api_observed
try:
    sys.setprofile(profile)
    hostile_result,hostile=run_suite(unittest.TestSuite(probe_cls(name) for name in methods),H/'tests.txt')
finally:
    sys.setprofile(old_profile);binding.NativeCodeBinding.__init__=observed;binding._BindingAPI.__init__=api_ctor
hostile.update(recorded_at=s.utc(),original_script=old_probe,class_ast_sha256=class_hashes,
    exact_original_classes_and_methods=True,facts=facts,comparison_callbacks=callbacks,
    native_binding_constructors=len(native_calls),native_api_constructors=len(api_calls),captured_native_owners=len(captured),
    fixture_scope=str(H),scope='Two literal historical oracles; neither original top-level runner nor historical output is executed/written.')
s.write_new(D/'LITERAL-GROUP-TYPE-PROBE.json',hostile)
assert hostile_result.wasSuccessful() and hostile['tests_run']==2 and not hostile_result.skipped
assert hostile['expected_ids']==hostile['executed_ids']==hostile['stopped_ids'] and not hostile['remaining_threads']
assert not callbacks and not native_calls and not api_calls and not captured
assert len(facts)==2 and all(not row['primitive_string'] and 'CodePin_constructor_accepted' not in row for row in facts)

# Revalidation remains effective even after a privileged in-process mutation of a frozen CodePin.
# This is a validation test, not a claim of resistance to a hostile privileged Python host.
V=D/'revalidation-r1';V.mkdir(exist_ok=False);tests.ROOT=V
revalidation_facts=[]; callback_counts=[]
class RevalidationProbe(tests.NativeCodeBindingTests):
    def test_mutated_groups_are_revalidated_before_file_open(self):
        for group in (namespace['GroupSubclass']('source'),custom('source')):
            with self.subTest(group_type=type(group).__name__):
                pin=replace(self.pins[0]);object.__setattr__(pin,'group',group)
                self.assertRaisesRegex(ContractError,'CODE_BINDING_GROUP_INVALID',self.opened,(pin,self.pins[1]))
                owner=self.owners[-1]
                self.assertTrue(owner.closed);self.assertFalse(owner.pending_native_resources)
                self.assertEqual(owner._files,[]);self.assertEqual(owner._ancestors,[])
                revalidation_facts.append(dict(group_type=type(group).__name__,owner_closed=owner.closed,pending=owner.pending_native_resources,
                    files=len(owner._files),ancestors=len(owner._ancestors)))
create_file_calls=[]; retained=binding.NativeCodeBinding._retain
def retain_observer(self,*args,**kwargs):create_file_calls.append(True);return retained(self,*args,**kwargs)
binding.NativeCodeBinding._retain=retain_observer
prior=len(callbacks)
try:
    sys.setprofile(profile)
    reval_result,reval=run_suite(unittest.TestSuite([RevalidationProbe('test_mutated_groups_are_revalidated_before_file_open')]),V/'tests.txt')
finally:
    sys.setprofile(old_profile);binding.NativeCodeBinding._retain=retained
reval.update(recorded_at=s.utc(),facts=revalidation_facts,comparison_callbacks=callbacks[prior:],
    native_file_or_ancestor_retains=len(create_file_calls),fixture_scope=str(V),
    limit='Native API wrapper initializes before CodePin revalidation; zero file/ancestor retention and comparison calls verified, not zero Python wrapper allocation.')
s.write_new(D/'REVALIDATION-PROBE.json',reval)
assert reval_result.wasSuccessful() and reval['tests_run']==1 and not reval_result.skipped
assert reval['expected_ids']==reval['executed_ids']==reval['stopped_ids'] and not reval['remaining_threads']
assert len(revalidation_facts)==2 and not create_file_calls and not callbacks[prior:]
assert all(o.closed and not o.pending_native_resources for o in owners)
assert all(s.ordinary(Q/name)==row for name,row in before.items())
assert all(s.ordinary(P/name)==row for name,row in source.items())
assert s.ordinary(s.PY)==image and s.ordinary(OLD/'TRANSFER-MANIFEST.json')==old_manifest and s.ordinary(OD/'probe_group_type.py')==old_probe
s.write_new(D/'CONSERVATION.json',dict(recorded_at=s.utc(),candidate_payloads=294,Source_payloads=290,
    candidate_native_bytes_exact=True,Source_native_bytes_exact=True,python_image_exact=True,predecessor_manifest_and_probe_exact=True,
    manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),all_observed_bindings_closed=True,observed_bindings=len(owners),
    source_publication=False,configuration_changes=False))
print(json.dumps(dict(candidate_tests=18,literal_historical_cases=2,extra_revalidation_methods=1,extra_revalidation_subcases=2,
    failures=0,errors=0,skips=0,observed_bindings=len(owners),comparison_callbacks=0,
    literal_native_binding_or_api_constructors=0,decision='ready for personal evidence inspection')),flush=True)
