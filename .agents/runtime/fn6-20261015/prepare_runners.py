"""Retain exact FN5 cohorts and add the measured initializer regressions."""
from foundation_support import *
P=F/'.agents/fn5-20261015';PR=F/'.agents/runtime/fn5-20261015'
parent=read(P/'TRANSFER-MANIFEST.json')
names=set(parent['payloads'])|{'tests/contract/test_kernel_initializer_publication.py'}
write_new(R/'ASSEMBLY.json',dict(at=utc(),payloads={n:ordinary(Q/n) for n in sorted(names)},payload_count=352,
    parent_manifest=reference(P/'TRANSFER-MANIFEST.json')))
provenance={}
for leaf in ('run_controlled.py','supervise_controlled.py','bounded_custody.py','run_preparation.py',
    'run_consumers.py','run_joined_controls.py','test_preparation_coordination.py','run_outcomes.py'):
    raw=(PR/leaf).read_bytes();text=raw.decode('utf8').replace('assert len(before)==351','assert len(before)==352')
    fs.write_new(R/leaf,text.encode('utf8'));provenance[leaf]=dict(parent=reference(PR/leaf),current=reference(R/leaf),
        delta='Only joined membership352 when present; test body ASTs and selections unchanged.')
observer=F/'.agents/runtime/js3-20261015/independent-destination/resource_observer.py'
assert sha(observer)=='de5deb609eb8b57b2b52e695ec0b38e1eac05f31ada119e83e74b9157074fd4a'
if not (R/'resource_observer.py').exists():bytes_copy(observer,R/'resource_observer.py')
write_new(R/'RUNNER-PROVENANCE.json',dict(at=utc(),cohort_runners=provenance,
    physical_observer=reference(observer),current_physical_observer=reference(R/'resource_observer.py'),
    original458_selection='82+218+94+8+53+3; all method bodies retained.',new_constructor_methods=3,
    Source_publication=False,original_native7='NOT_RUN',profiles_Hello_CPU_Set=False))
print('FN6 exact352 payloads and original458 recipes plus three new normative initializer cases prepared.')
