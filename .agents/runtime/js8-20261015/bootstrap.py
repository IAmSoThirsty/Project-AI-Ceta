"""Existing scoped TAAR assembly lifecycle; Source295 plus exact FN6 delta."""
from foundation_support import *
FN=F/'.agents/fn6-20261015';FR=F/'.agents/runtime/fn6-20261015'
J=F/'.agents/runtime/js7-20261015';A=J/'amendment-fixture1'
assert not Q.exists()
assert sha(FN/'TRANSFER-MANIFEST.json')=='6bd87db98906075971ecde1bd07444d28b3a957ba017cef2836cde097737eb24'
assert sha(A/'AMENDMENT.json')=='ab391fa1ef44c76bbbe5347b4ad114e16b64e87fa856ed8c57073d3f1af7fad2'
fn=read(FN/'TRANSFER-MANIFEST.json');amend=read(A/'AMENDMENT.json')
source_pins=amend['expected_payload_hashes'];source={name:ordinary(F/name) for name in source_pins}
assert len(source)==295 and all(source[name]['sha256']==pin for name,pin in source_pins.items())
fixture='tests/contract/test_launcher_custody_paths.py'
assert source_pins[fixture]=='35af2c33a76b8ac44e368c9df4a36842b0f5a04fff00bc8ccb553a9e68fd5dd1'
selected={name:row['candidate']['sha256'] for name,row in fn['payloads'].items()
          if name!=fixture and source_pins.get(name)!=row['candidate']['sha256']}
assert len(selected)==61 and sum(name in source for name in selected)==4
Q.mkdir();invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN],'run-init')
claim('discover')
write_new(R/'TASK-BINDING.json',dict(at=utc(),author=AUTHOR,candidate=str(Q),runtime=str(R),
    objective='Exact FN6-to-current-Source private integration using existing JS7 assembly/publication mechanisms',
    parent_FN6_manifest=reference(FN/'TRANSFER-MANIFEST.json'),parent_JS7_manifest=reference(F/'.agents/js7-20261015/TRANSFER-MANIFEST.json'),
    current_amendment=reference(A/'AMENDMENT.json'),eligible_application_paths=sorted(selected),
    preserved_forward_fixture=dict(path=fixture,sha256=source_pins[fixture]),
    required='352payloads,4EXTEND57CREATE,88productmodules; no wholesale overlay; exact original method/assertion/deadline bodies.',
    Source_baseline='Current amended295 observed; actual accepted Root baseline required before freeze or active integration.',
    native_tests='Root release held; FN6 native7 failure blocks acceptance. No rerun, bound change or failure relabelling.',
    no_profile_full_case='Retain exact original restricted no-profile case; no implicit authorization or omission.',
    no_Source_or_status_writes=True,no_native_or_test_execution=True,new_framework=False,copy_credit=0))
complete('discover',dict(binding=reference(R/'TASK-BINDING.json')),[],[('exact_frozen_FN6_and_current_amended295_delta_inspected',True)])
claim('plan')
write_new(R/'CODE-SCOPE.json',dict(at=utc(),existing_plan='Existing real-effect foundation and qualified JS7 integration sequence',
    selected=sorted(selected),EXTEND=sorted(name for name in selected if name in source),
    CREATE=sorted(name for name in selected if name not in source),REUSE=291,
    source_code_authorship_credit=0,tests='No test-body changes; test execution held for explicit Root release',
    tooling='Reuse exact JS7 OriginalReader/RS2 native publication, bounded custody, official receipts and full runner; explicit path/count/native-fixture bindings only.',
    full_gate_blocker='FN6 native7 has one measured OWNER_TOO_SLOW vs STOPPED failure; original no-profile test remains separately gated.',
    acceptance_freeze='Held for accepted Source295 and Root disposition of concrete native prerequisite.'))
complete('plan',dict(scope=reference(R/'CODE-SCOPE.json')),[],[('finite_61_path_join_and_reuse_of_existing_mechanisms',True)])
claim('implement')
payloads={};provenance={}
for name,row in fn['payloads'].items():
    use_FN=name in selected
    origin=FN/name if use_FN else F/name
    expected=row['candidate'] if use_FN else source[name]
    payloads[name]=bytes_copy(origin,Q/name,expected)
    provenance[name]=dict(origin=reference(origin),action='CREATE' if name not in source else 'EXTEND' if use_FN else 'REUSE',copy_credit=0)
assert len(payloads)==352 and len(list((Q/'src/ceta').rglob('*.py')))==88
before={name:bytes_copy(F/name,R/'before-images'/name,source[name]) for name in selected if name in source}
jv=read(J/'FINAL-INPUTS.json')
aux={name:bytes_copy(F/name,Q/name,row) for name,row in jv['auxiliary11'].items()} if 'auxiliary11' in jv else {
    name:bytes_copy(F/name,Q/name,jv['auxiliary_source11'][name]) for name in jv['auxiliary_copies11']}
write_new(R/'ASSEMBLY.json',dict(at=utc(),payloads=payloads,provenance=provenance,selected=sorted(selected),
    Source295=source,Source_baseline_acceptance='PENDING_ROOT_PIN',before_images=before,auxiliaries=aux,
    fixture_preserved=fixture,fixture_sha256=source_pins[fixture],payload_count=352,product_python_modules=88,
    Source_publication=False,tests_executed=0,native_execution='NOT_RUN',copy_credit=0))
write_new(R/'STAGED-JOIN.json',dict(at=utc(),selected=sorted(selected),candidate_payloads=payloads,preserved_current_source=source,
    before_images=before,copy_credit=0,Source_publication=False))
print(canonical(dict(actual_implement='RUNNING',selected61=True,payloads352=True,Source_writes=False,tests_executed=0)))
