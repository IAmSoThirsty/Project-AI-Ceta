"""Mechanical JS7 helper successor and exact accepted Source295 binding."""
from foundation_support import *
import ast
J=F/'.agents/runtime/js7-20261015'
A=J/'amendment-fixture1'
FN=F/'.agents/fn6-20261015'
assert read(R/RUN/'claims.json')['implement']['executor_id']==AUTHOR
baseline=A/'ACCEPTED-SOURCE-BASELINE.json'
assert sha(baseline)=='bd7af13da30e54aa916696cb9c4dbcd32539e2600e0fdc02f8af56f63d47fbbf'
accepted=read(baseline);state=read(J/'js7-20261015/state.json')
assert accepted['Source_accepted'] is True and accepted['Source_payloads']==295
assert state['sequence']==13 and all(n['state']=='SUCCEEDED' and n['claim'] is None for n in state['nodes'].values())
assert read(J/'js7-20261015/claims.json')=={}
assert sha(J/'integrate.json')=='b309260af746777cf4a02bcfca34c728f3b7f77d1117271439b47d9220b4df1f'
assembly=read(R/'ASSEMBLY.json');source={name:ordinary(F/name) for name in accepted['source']}
assert source==accepted['source']==assembly['Source295']
binding=dict(at=utc(),baseline=reference(baseline),integrate=reference(J/'integrate.json'),actual_sequence=13,
    actual_all_six_states={key:value['state'] for key,value in state['nodes'].items()},claims={},Source295=source)
write_new(R/'SOURCE-BASELINE-BINDING.json',binding)
parent=read(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json')
mapping={}
for name in ('js8_support.py','run_full.py','launch_full.py','publish_source.py','complete_source.py',
             'bounded_custody.py','gc_observer.py','tool_environment.py'):
    original='js7_support.py' if name=='js8_support.py' else name
    origin=J/original;assert sha(origin)==parent['scripts'][original]
    raw=origin.read_bytes()
    if name not in ('bounded_custody.py','gc_observer.py','tool_environment.py'):
        raw=raw.replace(b'js7_support',b'js8_support').replace(b'js7-20261015',b'js8-20261015')
        raw=raw.replace(b'Source295',b'Source352').replace(b'Source290',b'Source295')
        raw=raw.replace(b'source295',b'source352').replace(b'payloads295',b'payloads352')
        raw=raw.replace(b'len(expected)==295',b'len(expected)==352').replace(b"len(m['application_paths'])==15",b"len(m['application_paths'])==61")
        raw=raw.replace(b'len(modules)==74',b'len(modules)==88')
        raw=raw.replace(b'len(expected_backups)==10',b'len(expected_backups)==4')
        raw=raw.replace(b"'Source_payloads':295",b"'Source_payloads':352")
        if name=='js8_support.py':
            raw=raw.replace(b"'tool_environment.py')",b"'tool_environment.py','fixture_runtime.py')")
    ast.parse(raw)
    with (R/name).open('xb') as stream:assert stream.write(raw)==len(raw)
    mapping[name]=dict(origin=reference(origin),adapted=reference(R/name),product_authorship_credit=0)
v=read(J/'FINAL-INPUTS.json')
v.pop('Source290',None);v.pop('payloads295',None)
payloads={name:ordinary(Q/name) for name in assembly['payloads']}
v.update(at=utc(),Source295=source,payloads352=payloads,auxiliary_copies11=assembly['auxiliaries'],
    before_images=assembly['before_images'],implement_claim=read(R/RUN/'claims.json')['implement'],
    source_baseline=reference(baseline),source_baseline_binding=reference(R/'SOURCE-BASELINE-BINDING.json'),
    exact_FN6_manifest=reference(FN/'TRANSFER-MANIFEST.json'),accepted_JS7_manifest=reference(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json'),
    Stop_timing_amendment=reference(R/'STOP-TIMING-SCOPE-AMENDMENT.json'),Source_publication=False,
    full_native_executed=False,native_gate_author='WT exclusive native-gate scope; exact reviewed descriptor pending',
    inherited_FN6_native_failure='Retained blocker until exact JS8 repair and newly released qualification succeed',
    product_copy_credit=0)
write_new(R/'INPUTS.json',v)
for name in ('GIT-SEARCH-DEPENDENCY.json',):bytes_copy(J/name,R/name)
write_new(R/'MECHANICAL-HELPER-LINEAGE.json',dict(at=utc(),members=mapping,
    changes='Run/module bindings,Source before295/after352,payload352,module88,application61,native originals4; unchanged OriginalReader/RS2 primitive and custody algorithms.',
    reused_Product_LOC_credit=0,full_native_or_Source_execution=False))
print(canonical(dict(helpers=len(mapping),Source_baseline_accepted=True,payloads=352,selected=61,product_modules=88)))
