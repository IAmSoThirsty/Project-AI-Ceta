"""Complete original test dependencies without changing any Q530 payload."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, sys
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
OLD=F/'.agents/js9-runtime-20261020';Q=F/'.agents/js9-runtime-r5-20261020'
D2=R.parent/'successor-r2'
sys.path.insert(0,str(D2));import js9_support as j
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
claim=json.loads((F/'.agents/runtime/js9-runtime-r5-construction-20261020/control/js9-runtime-r5-construction-20261020/claims.json').read_bytes())['assemble']
assert claim['executor_id']=='/root/recovery_regression20'
assert claim['input_hash']=='baf9070b3439cad477c90cc8fcc966c50ca4c64f658ee18655e9fdb78197ae84'
assert claim['effective_write_scope']==['.agents/js9-runtime-r5-20261020/**']
manifest=R.parent/'MANIFEST-R4.json'
assert sha(manifest)=='212f1913af6ef24c24041628d2dcca23c7b754849ba79de9db8d75a210b3f532'
old=json.loads(manifest.read_bytes())['payload_hashes'];assert len(old)==530
registries=['requirements/requirements.json','architecture/components.json','build/work_packages.json','acceptance/scenarios.json','build/gates.json']
needed=['tools/verify_allocations.py','tools/preserve_ceta_baseline.py','PACKAGE_MANIFEST.json',*registries,
        *['.local-build-cache/restoration-proof/'+name for name in registries]]
extra=[name for name in needed if name not in old]
assert len(extra)==11 and len(set(extra))==11,extra
assert sha(F/'tools/verify_allocations.py')=='8b1ff56c9167eb7c490704c8637e8f5b7699e7d72389dc11826826a7b06a0825'
assert sha(F/'tools/preserve_ceta_baseline.py')=='a3d5509282d1221db55fd102f56cbe7bfcd05979192ac673a8154aa7e5c6735f'
assert sha(OLD/'tools/verify_source_coverage.py')==sha(F/'tools/verify_source_coverage.py')=='e32eb1171d258f5dd65373b9094831ccdd8302f604e06fe86ece488561ae120d'
assert not any(Q.iterdir())
payloads=dict(old);sources={}
for name in [*old,*extra]:
    origin=OLD/name if name in old else F/name
    before=j.s.ordinary(origin);raw=origin.read_bytes()
    assert sha(origin)==hashlib.sha256(raw).hexdigest()==before['sha256']
    if name in old:assert before['sha256']==old[name]
    destination=Q/name;destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:assert stream.write(raw)==len(raw)
    assert j.s.ordinary(origin)==before and sha(destination)==before['sha256']
    if name in extra:
        payloads[name]=before['sha256'];sources[name]=dict(origin=before,destination=j.s.ordinary(destination))
assert all(sha(OLD/name)==pin and sha(Q/name)==pin for name,pin in old.items())
assert len(payloads)==541
proof=dict(at=datetime.now(timezone.utc).isoformat(),candidate=str(Q),payload_hashes=payloads,
    frozen_predecessor=dict(path=str(manifest),sha256=sha(manifest),payloads=530),
    inherited530_byte_identical=True,added_same_project_dependencies=sources,
    dependency_reason='Original AllocationTests and PreservationTests imports plus exact real-input snapshot dependency closure',
    original_test_methods_changed=False,copied_LOC_credit=0,Source_payload_writes=False,
    product_or_native_acceptance=False,skills_used=['protocol-interoperability-auditor'],
    governing_version='thirsty-constitution-v0.1')
save(R/'MANIFEST-Q5.json',proof)
print(json.dumps(dict(candidate=str(Q),payloads=len(payloads),extra=extra,
    manifest_sha256=sha(R/'MANIFEST-Q5.json'),old530_unchanged=True)),flush=True)
