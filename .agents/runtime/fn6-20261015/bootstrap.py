"""Claim the smallest initializer-publication successor; no Source action."""
from foundation_support import *
P=F/'.agents/fn5-20261015';PR=F/'.agents/runtime/fn5-20261015'
pin='7c324af5d0a5293e5fab57785e7ffabc3e2b69b6530ef5c1d4320d5cb303fa2d'
assert not Q.exists() and sha(P/'TRANSFER-MANIFEST.json')==pin
probe=PR/'independent-review/probe_initializer_binding.py';failure=PR/'independent-review/initializer-binding-r1/RESULT.json'
assert sha(probe)=='e08cb7431f8723de9d8837d1079054d302d52e707794b7140ae6f30581430578'
assert sha(failure)=='a768240f74608b5ddacb2388f511626f4dc3dde4906c35e485d1350ef94e58fd'
parent=read(P/'TRANSFER-MANIFEST.json')
Q.mkdir();invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN],'run-init')
claim('discover')
write_new(R/'TASK-BINDING.json',dict(at=utc(),author=AUTHOR,candidate=str(Q),runtime=str(R),
    parent_manifest=reference(P/'TRANSFER-MANIFEST.json'),failure_probe=reference(probe),failure=reference(failure),
    Root_directive='FN6 minimal initializer-publication repair; exact bound preparation check before final owner/kernel publication.',
    eligible=['src/ceta/kernel/transactions.py','tests/contract/test_kernel_initializer_publication.py'],
    required='Preserve all351 parent payloads except narrow initializer delta; original458 selected methods and exact rejected oracle, no Source/native/full/profile/Hello/CPU Set.',
    parent_terminal_failed_receipt='Required before final freeze; parent review still finishing at initial inspection.',
    Source_baseline='CT4 accepted Source290 history; JS5 publisher FAILED13; no live Source conservation or publication claim.'))
complete('discover',dict(binding=reference(R/'TASK-BINDING.json')),[],[('exact_frozen_parent_and_measured_controlled_constructor_failure',True)])
claim('plan')
write_new(R/'CODE-SCOPE.json',dict(at=utc(),EXTEND=['src/ceta/kernel/transactions.py'],
    CREATE=['tests/contract/test_kernel_initializer_publication.py'],REUSE=350,
    change='Allocate/store exact bound preparation check and local owner fields before the final _bind_preparation_kernel call. No fallible initializer operation follows that publication.',
    public_signatures='Unchanged',borrowed_store_ownership='Unchanged; initializer failure must never close or mutate borrowed SQLite.',
    new_plan=False,Source_publication=False))
complete('plan',dict(scope=reference(R/'CODE-SCOPE.json')),[],[('finite_two_path_successor_with_exact_regression',True)])
claim('implement')
copied={n:bytes_copy(P/n,Q/n,row['candidate']) for n,row in parent['payloads'].items()}
assert len(copied)==351
bytes_copy(Q/'src/ceta/kernel/transactions.py',R/'before-images/src/ceta/kernel/transactions.py')
for name,row in parent['auxiliaries'].items():bytes_copy(P/name,Q/name,row)
prior=read(PR/'INPUTS.json')
write_new(R/'INPUTS.json',dict(at=utc(),parent_manifest=reference(P/'TRANSFER-MANIFEST.json'),parent_payloads=copied,
    parent_author_seal=reference(PR/'AUTHOR-SEAL.json'),parent_inputs=reference(PR/'INPUTS.json'),
    parent_full_limits=parent['limits'],E33601=prior['E33601'],python=ordinary(PY),
    failure_probe=reference(probe),failure_result=reference(failure),auxiliaries=parent['auxiliaries'],
    Source_baseline='CT4 accepted290, JS5 publisher FAILED13; future handoff requires exact then-current Root accepted cut.',
    Source_publication=False))
# Baseline replay remains bound to the frozen rejected parent. Only own output
# root follows this copied driver; every original oracle method AST is exact.
text=probe.read_text();fs.write_new(R/'probe_initializer_binding.py',text.encode('utf8'))
print(json.dumps(dict(actual_implement='RUNNING',sequence=6,copied351=True,Source_writes=False)))
