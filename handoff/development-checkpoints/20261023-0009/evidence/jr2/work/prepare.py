"""Import/collect canonical cases without running their test bodies."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
import run_canonical_journal as r

W=Path(__file__).resolve().parent;J=W.parent;F=r.F
assert r.sha(J/'packet/INPUTS.json')==r.PACKET_SHA and r.sha(J/'packet/PLAN.md')==r.PLAN_SHA
packet=json.loads((J/'packet/INPUTS.json').read_bytes())
assert Path(sys.executable).resolve()==Path(packet['python']).resolve() and r.sha(Path(sys.executable))==packet['python_sha256']
claim=json.loads((J/'control'/r.RUN/'claims.json').read_bytes())['implement']
assert claim['executor_id']=='/root/fixture_runner_r2' and Path(claim['workspace'])==W
assert claim['effective_write_scope']==[W.relative_to(Path('T:/')).as_posix()+'/**']
assert claim['input_hash']=='5fb1b2c3a3e3d3dd58c0ca069a6c264b6d96fbfd11d1836b682f1ee04804b227'
manifest=Path(packet['source_manifest']);assert r.sha(manifest)==packet['source_manifest_sha256']
payload=json.loads(manifest.read_bytes())['payload_hashes'];assert len(payload)==560
source_native={}
for rel,pin in payload.items():
    path=F/rel;r.ancestors(F,path.parent);native,_=r.stable(path);assert native['sha256']==pin,rel
    source_native[str(path)]=native
for name,pin in packet['extra_source_pins'].items():
    native,_=r.stable(Path(name));assert native['sha256']==pin;source_native[name]=native
suite,ids,modules=r.canonical_suite(packet)
# Importing and loading a unittest suite is not executing its test bodies.
del suite
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_graph import compile_graph
graph=compile_graph(Path('T:/'),J/'control')
binding=dict(run_id=r.RUN,control=str(J/'control'),graph_root=str(Path('T:/').resolve()),graph_fingerprint=graph.fingerprint,
    workspaces=dict(integrate=str(J/'delivery'),**packet['fixture_workspaces']),source_native=source_native,Git=packet['Git'])
external={str(p):r.sha(p) for p in [J/'packet/INPUTS.json',J/'packet/PLAN.md',J/'client.py',manifest,Path(sys.executable),
    F/'AGENTS.md',Path('T:/PROJECT_ISOLATION_RULEBOOK.md'),Path(packet['approved_observation_primitives']['path'])]}
assert external[packet['approved_observation_primitives']['path']]==packet['approved_observation_primitives']['sha256']
for item in graph.sources:
    path=Path(item.path)
    if not path.is_absolute():path=Path(graph.root)/path
    external[str(path)]=r.sha(path)
tool=Path('T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce/taar')
for name in ('__init__.py','errors.py','orchestration_runtime.py','orchestration_graph.py','orchestration_persistence.py','orchestration_receipts.py'):
    external[str(tool/name)]=r.sha(tool/name)
r.save(W/'BINDING.json',binding)
r.save(W/'COLLECTION.json',dict(test_ids=ids,tests_collected=len(ids),test_modules=modules,
    dependencies=r.dependency_identities(),interpreter=dict(path=sys.executable,native=r.stable(Path(sys.executable))[0]),
    sqlite_static_binary=dict(path=str(F/'native/sqlite_runtime/win-x64/sqlite3.dll'),native=r.stable(F/'native/sqlite_runtime/win-x64/sqlite3.dll')[0],loaded_by_preparation=False),
    source_root=str(F),ordinary_imports=True,module_overlay=False,ROOT_override=False,
    test_bodies_executed=False,fixtures_bootstrapped=False,full_product_acceptance=False))
r.save(W/'PREPARATION.json',dict(created_at=datetime.now(timezone.utc).isoformat(),claim=claim,external_pins=external,
    source_native_before=source_native,source_native_after=r.source_observation(binding),canonical_test_bodies_executed=False,
    fixture_writes=False,fixture_bootstrap=False,Git_mutation=False,native_process_execution=False,full_product_acceptance=False))
print(json.dumps(dict(collected=len(ids),binding_sha256=r.sha(W/'BINDING.json'),canonical_bodies_executed=False),indent=2))
