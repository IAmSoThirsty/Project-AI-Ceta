"""Collect exactly one existing canonical case only after accepted JR2 actual success."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
import run_challenge as r
W=r.W; K=r.K; F=r.F
assert sys.flags.optimize==0
assert r.sha(K/'packet/INPUTS.json')==r.PACKET_SHA and r.sha(K/'packet/PLAN.md')==r.PLAN_SHA
packet=json.loads((K/'packet/INPUTS.json').read_bytes())
assert Path(sys.executable).resolve()==Path(packet['python']).resolve() and r.sha(Path(sys.executable))==packet['python_sha256']
claim=json.loads((K/'control'/r.RUN/'claims.json').read_bytes())['implement']
assert claim['executor_id']=='/root/admission_entry_r2' and Path(claim['workspace'])==W
assert claim['effective_write_scope']==[W.relative_to(Path('T:/')).as_posix()+'/**']
assert claim['input_hash']=='667e6780aec6dded9cff875c5da90191357f9c2f034220c23228fac470836196'
j=F/'.agents/runtime/oq23/jr2'
prerequisite_paths=[j/'work/MANIFEST.json',j/'work/run_canonical_journal.py',j/'review/REVIEW.json',j/'review/MANIFEST.json',
    j/'control/EXECUTION-INTENT.json',j/'control/EXECUTION-PROCESS.json',j/'control/EXECUTION.stdout',j/'control/EXECUTION.stderr',
    *(j/'delivery'/name for name in ('START.json','RESULT.json','REPORT-SEAL.json','events.jsonl','TESTS.log'))]
binding=dict(journal_success_pins={str(p):r.sha(p) for p in prerequisite_paths},support_path=str(j/'work/run_canonical_journal.py'),
    support_sha256=r.sha(j/'work/run_canonical_journal.py'),Git=packet['Git'])
prerequisite=r.prerequisite(binding); q=r.support(binding)
manifest=Path(packet['source_manifest']); assert r.sha(manifest)==packet['source_manifest_sha256']
payload=json.loads(manifest.read_bytes())['payload_hashes']; assert len(payload)==560
source_native={}
for rel,pin in payload.items():
    path=F/rel; q.ancestors(F,path.parent); native,_=q.stable(path); assert native['sha256']==pin,rel
    source_native[str(path)]=native
for name,pin in packet['extra_source_pins'].items():
    native,_=q.stable(Path(name)); assert native['sha256']==pin; source_native[name]=native
binding['source_native']=source_native
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_graph import compile_graph
graph=compile_graph(Path('T:/'),K/'control')
binding.update(run_id=r.RUN,control=str(K/'control'),graph_root=str(Path('T:/').resolve()),graph_fingerprint=graph.fingerprint,
    workspaces=dict(integrate=str(K/'delivery'),owner_authority=str(F/'.agents/fixtures/kernel-owner-authority')))
before=q.source_observation(binding)
suite,case,bound,identity,modules=r.canonical_suite(packet,q)
assert suite.countTestCases()==1
external={str(p):r.sha(p) for p in [K/'packet/INPUTS.json',K/'packet/PLAN.md',K/'client.py',manifest,Path(sys.executable),F/'AGENTS.md',Path('T:/PROJECT_ISOLATION_RULEBOOK.md')]}
external.update(binding['journal_success_pins'])
for item in graph.sources:
    path=Path(item.path)
    if not path.is_absolute():path=Path(graph.root)/path
    external[str(path)]=r.sha(path)
tool=Path('T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce/taar')
for name in ('__init__.py','errors.py','orchestration_runtime.py','orchestration_graph.py','orchestration_persistence.py','orchestration_receipts.py'):
    external[str(tool/name)]=r.sha(tool/name)
q.save(W/'BINDING.json',binding)
q.save(W/'COLLECTION.json',dict(test_ids=r.SELECTED,tests_collected=1,test_modules=modules,guard_binding=identity,
    dependencies=r.dependencies(q),interpreter=dict(path=sys.executable,native=q.stable(Path(sys.executable))[0]),
    sqlite_static_binary=dict(path=str(F/'native/sqlite_runtime/win-x64/sqlite3.dll'),native=q.stable(F/'native/sqlite_runtime/win-x64/sqlite3.dll')[0],loaded_by_preparation=False),
    ordinary_imports=True,module_overlay=False,ROOT_override=False,test_bodies_executed=False,canonical_fixture_writes=False,full_product_acceptance=False))
q.save(W/'PREPARATION.json',dict(claim=claim,external_pins=external,source_before=before,source_after=q.source_observation(binding),
    journal_success=prerequisite,canonical_test_bodies_executed=False,canonical_fixture_writes=False,full_product_acceptance=False))
print(json.dumps(dict(collected=1,canonical_test_bodies_executed=False,journal_actual_exit_status=0,full_product_acceptance=False)))
