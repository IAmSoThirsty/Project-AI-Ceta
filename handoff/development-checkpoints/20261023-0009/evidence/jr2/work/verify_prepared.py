"""Read-only preparation integrity and complete work observation; no test runs."""
from pathlib import Path
import json
import run_canonical_journal as r
W=Path(__file__).resolve().parent
m=json.loads((W/'MANIFEST.json').read_bytes())
for name,pin in m['work_hashes'].items():assert r.sha(W/name)==pin,('work drift',name)
for name,pin in m['external_pins'].items():assert r.sha(Path(name))==pin,('support drift',name)
actual=r.snapshot(W)
allowed={'MANIFEST.json','PREPARED.stdout','PREPARED.stderr','PREPARED.json'}
assert set(actual)-allowed==set(m['work_observation']),'work entry set changed'
r.preservation(m['work_observation'],actual)
assert r.sha(W.parent/'packet/INPUTS.json')==r.PACKET_SHA
assert r.sha(W.parent/'packet/PLAN.md')==r.PLAN_SHA
b=json.loads((W/'BINDING.json').read_bytes());fresh=r.source_observation(b)
baseline=json.loads((W/'BASELINE-REFRESH.json').read_bytes())
assert baseline['source_before']==baseline['source_after']==fresh
assert len(b['source_native'])==562 and b['Git']['status_sha256']=='b2a3e5f277d839cd93bc797f7ababbe5baf7e575fc12bbe5a0555f4bba436faf'
c=json.loads((W/'COLLECTION.json').read_bytes())
assert len(c['test_ids'])==len(set(c['test_ids']))==c['tests_collected']==33
assert c['ordinary_imports'] and not c['module_overlay'] and not c['ROOT_override'] and not c['test_bodies_executed']
for name,identity in c['test_modules'].items():
    assert identity['origin']==str(r.F/'tests/contract'/(name+'.py'))
for identity in c['dependencies'].values():
    if identity['file']:assert r.stable(Path(identity['origin']))[0]==identity['native']
assert r.stable(Path(c['sqlite_static_binary']['path']))[0]==c['sqlite_static_binary']['native']
assert not c['sqlite_static_binary']['loaded_by_preparation']
t=json.loads((W/'CONTROLS-STABLE.json').read_bytes())
assert t['tests']==30 and t['successful'] and t['process_exit_status']==0
assert t['failures']==t['errors']==t['skips']==0 and t['selected']==t['started']==t['stopped']
assert len(set(t['selected']))==30 and t['source_before']==t['source_after']
for name,pin in t['source_after'].items():assert r.sha(W/name)==pin
assert not t['canonical_test_bodies_executed'] and not t['canonical_fixture_writes']
negative=json.loads((W/'PRE-REPAIR-NEGATIVE.json').read_bytes())
assert negative['observed_type']=='AttributeError' and negative['raw_nonstring_key']==7 and negative['exact_predecessor_function_AST']
assert negative['product_test_executed'] is False
for name in m['python_sources']:compile((W/name).read_bytes(),str(W/name),'exec')
assert m['full_product_acceptance'] is False
print('PREPARED PASS:30 disposable author controls;J1 rejection and exact negative witness retained;bounded raw diagnostics and protected report assembly;33 canonical cases collected only;complete directory/file observations;actual source560+2status/Git/native pins unchanged;no canonical bodies or fixture writes;full acceptance false')
