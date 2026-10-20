from pathlib import Path
from dataclasses import replace
import json,os,sys,threading,unittest
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cb1-20261014';BASE=P/'.agents/runtime/cb1-20261014';D=BASE/'independent-review'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
E=D/'group-type-r1';E.mkdir(exist_ok=False);os.environ['TEMP']=os.environ['TMP']=str(E)
import test_native_code_binding as tests
from ceta.identity import native_code_binding as binding
from ceta.contracts.wire import ContractError
tests.ROOT=E
facts=[];captured=[]


class GroupSubclass(str):
    pass


class EqualityGroup:
    def __init__(self,value):self.value=value
    def __hash__(self):return hash(self.value)
    def __eq__(self,other):
        return self.value==(other.value if type(other) is EqualityGroup else other)
    def __lt__(self,other):
        return self.value<(other.value if type(other) is EqualityGroup else other)
    def __gt__(self,other):
        return self.value>(other.value if type(other) is EqualityGroup else other)


class GroupTypeProbe(tests.NativeCodeBindingTests):
    def attempt(self,group):
        observed={'id':self.id(),'supplied_group_type':type(group).__name__,'primitive_string':type(group) is str}
        facts.append(observed)
        with self.assertRaisesRegex(ContractError,'CODE_BINDING_GROUP_INVALID'):
            bad=replace(self.pins[0],group=group)
            observed['CodePin_constructor_accepted']=True
            owner=self.opened((bad,self.pins[1]));captured.append(owner)
            observed.update(NativeCodeBinding_constructor_accepted=True,
                source_commitment=owner.source_commitment,environment_commitment=owner.environment_commitment,
                source_group_returned_type=type(next(row for row in owner.snapshot() if row[1]=='source.py')[0]).__name__,
                retained_file_count=len(owner._files),retained_ancestor_count=len(owner._ancestors))
            with owner.retained() as lease:
                self.assertIsNone(lease.require_current());observed['private_retained_lease_valid']=True

    def test_plain_string_subclass_group_rejected_before_native_pinning(self):
        self.attempt(GroupSubclass('source'))

    def test_custom_equality_group_rejected_before_native_pinning(self):
        self.attempt(EqualityGroup('source'))


suite=unittest.TestSuite([GroupTypeProbe('test_plain_string_subclass_group_rejected_before_native_pinning'),
    GroupTypeProbe('test_custom_equality_group_rejected_before_native_pinning')])
manifest=json.loads((Q/'TRANSFER-MANIFEST.json').read_text());inputs=json.loads((BASE/'SOURCE-INPUTS.json').read_text())
before={row['relative_path']:s.ordinary(Q/row['relative_path']) for row in manifest['payloads']};source={name:s.ordinary(P/name) for name in inputs['Source290']};assert source==inputs['Source290']
threads=set(threading.enumerate())
with (E/'tests.txt').open('x',encoding='utf-8') as out:result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
remaining=[t.name for t in set(threading.enumerate())-threads if t.is_alive()]
assert all(s.ordinary(Q/name)==row for name,row in before.items());assert all(s.ordinary(P/name)==row for name,row in source.items())
owned=[dict(closed=owner.closed,pending=owner.pending_native_resources) for owner in captured]
s.write_new(D/'GROUP-TYPE-PROBE.json',dict(recorded_at=s.utc(),tests_run=result.testsRun,
    failures=[(t.id(),tb) for t,tb in result.failures],errors=[(t.id(),tb) for t,tb in result.errors],skips=result.skipped,
    facts=facts,raw=s.reference(E/'tests.txt'),native_receipts=tests.NATIVE_RECEIPTS,owned_resources=owned,
    remaining_threads=remaining,source290_and_candidate294_native_conserved=True,
    expected='Only exact built-in str source/environment groups accepted; wrong type rejected before native allocation.',
    scope='Trusted-manifest input validation defect; no remote authority/runtime bypass asserted.'))
assert all(row['closed'] and not row['pending'] for row in owned) and not remaining
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),facts=facts,all_owned_closed=True)),flush=True)
sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)
