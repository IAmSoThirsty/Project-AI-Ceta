"""Rebind existing qualified controlled recipes to the joined candidate."""
from foundation_support import *

assert read(R/RUN/'claims.json')['implement']['executor_id']==AUTHOR
provenance={}
for leaf in ('run_controlled.py','supervise_controlled.py','bounded_custody.py'):
    source=F/'.agents/runtime/ka5-20261015'/leaf
    text=source.read_text()
    text=text.replace("set(read(R/'INPUTS.json')['parent_payloads'])|{'tests/contract/test_cpu_execution_timing_diagnostics.py'}",
        "set(read(R/'ASSEMBLY.json')['payloads'])")
    text=text.replace('assert len(before)==342','assert len(before)==351')
    fs.write_new(R/leaf,text.encode('utf8'));provenance[leaf]=dict(source=reference(source),current=reference(R/leaf),
        adaptation='Only FN5 joined membership/count; original test method selection/assertions unchanged.')
source=F/'.agents/runtime/os5-20261015/run_tests.py'
text=source.read_text()
text=text.replace("P=F/'.agents/os4-20261015';product=P if baseline else Q","assert not baseline;product=Q")
text=text.replace("names=set(inputs['parent_payloads'])\nif not baseline:names.add('tests/contract/test_native_owner_preparation.py')",
    "names=set(read(R/'ASSEMBLY.json')['payloads'])")
fs.write_new(R/'run_preparation.py',text.encode('utf8'))
provenance['run_preparation.py']=dict(source=reference(source),current=reference(R/'run_preparation.py'),
    adaptation='Only FN5 exact membership/current candidate; existing native denial/SQLite/bootstrap/test ASTs retained.')
write_new(R/'RUNNER-PROVENANCE.json',dict(at=utc(),runners=provenance,
    one_arithmetic_method='The same already reviewed KA5 deterministic elapsed fixture; all other old controlled methods clocks untouched.',
    native7='NOT_RUN',restricted_no_profile='NOT_RUN',Source_publication=False))
print('Controlled runners prepared for exact FN5 imports; no tests executed by preparation.')
