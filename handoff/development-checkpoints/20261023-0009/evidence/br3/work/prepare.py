"""Fresh BR3 collection only; complete source/fixture conservation, no test bodies."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,time
import run_broader as b
from bound_runtime import compile_graph
W=b.W;B=b.B;F=b.F;packet=b.packet();C=B/'control'
state=json.loads((C/b.RUN/'state.json').read_bytes());claim=state['nodes']['implement']['claim']
assert state['nodes']['implement']['state']=='RUNNING' and claim['executor_id']=='/root/broader_successor_author'
assert claim['workspace']==str(W) and claim['effective_write_scope']==[W.relative_to(Path('T:/')).as_posix()+'/**']
assert claim['input_hash']=='60dd422f8f35e5b68e839c7d9806e17c36003a5e0aed18aefedce32df0bf14b0'
graph=compile_graph(Path('T:/'),C)
assert graph.fingerprint=='38a70f9069edec1aeb7daff0dbd491a474891ac5997d9a69a7ceda296aa4740e'
assert b.sha(Path(packet['source_manifest']))==packet['source_manifest_sha256']
payload=json.loads(Path(packet['source_manifest']).read_bytes())['payload_hashes'];assert len(payload)==560
source={}
for relative,pin in payload.items():
    path=F/relative;b.o.ancestors(F,path.parent);native=b.o.stable(path);assert native['sha256']==pin
    source[str(path)]=native
for name,pin in packet['extra_source_pins'].items():
    native=b.o.stable(Path(name));assert native['sha256']==pin;source[name]=native
old=packet['failed_broader_predecessor'];assert b.sha(Path(old['closure']))==old['closure_sha256']
assert b.sha(Path(old['assessment']))==old['assessment_sha256']
assessment=json.loads(Path(old['assessment']).read_bytes())
readonly={}
for name,text in packet['read_only_preserved_fixture_workspaces'].items():
    observation=b.o.snapshot(Path(text));readonly[name]=dict(path=text,observation=observation)
    if name=='failed_br1_js9':
        raw=assessment['current_read_only_diagnosis']['raw_files']
        files={key:record for key,record in observation.items() if record['kind']=='file'}
        assert files.keys()==raw.keys(),'failed JS9 file set drift'
        for key,record in files.items():
            assert record['api_metadata']=={n:value for n,value in raw[key].items() if n!='sha256'},('failed JS9 raw native drift',key)
            assert record['sha256']==raw[key]['sha256'],('failed JS9 bytes drift',key)
binding=dict(run_id=b.RUN,control=str(C),graph_root=str(Path('T:/')),graph_fingerprint=graph.fingerprint,
    workspaces=dict(integrate=str(B/'delivery'),**packet['fixture_workspaces']),source_native=source,Git=packet['Git'],read_only_fixtures=readonly)
before_source=b.source_observation(binding)
def fixtures():
    observed={}
    for name,text in packet['fixture_workspaces'].items():
        path=Path(text)
        if name=='js9':
            try:b.o.plain(path)
            except FileNotFoundError:observed[name]=dict(absent=True)
            else:raise AssertionError('fresh JS9 must remain absent during preparation')
        else:observed[name]=b.o.snapshot(path)
    return observed
started=time.monotonic_ns();before=fixtures();env=b.environment(packet)
suite,ids,modules=b.collect(packet);del suite
cohort=packet['exact_cohort_predecessor'];assert b.sha(Path(cohort['path']))==cohort['sha256']
previous=json.loads(Path(cohort['path']).read_bytes())
assert ids==previous['test_ids'] and len(ids)==len(set(ids))==510,'ordered canonical cohort changed'
after=fixtures();after_source=b.source_observation(binding)
assert before==after,'canonical fixture changed during collection interval'
assert before_source==after_source,'source/native/failed-readonly-fixture/Git changed during collection interval'
# BR1 lacks BR2 raw API fields. Preserve every original field, adding no relaxation
# to any fresh-schema before/freeze/claim/after equality.
old_result=json.loads((Path(old['root'])/'delivery/RESULT.json').read_bytes())
previous_preservation={}
for name,tree in old_result['fixtures_after'].items():
    assert name!='js9' and name in before
    current=before[name]
    for key,record in tree.items():
        assert key in current,('BR1 observed entry disappeared',name,key)
        fields=record if record['kind']=='file' else {k:record[k] for k in ('kind','device','inode','mode')}
        assert all(current[key][k]==value for k,value in fields.items()),('BR1 native/byte preservation failed',name,key)
    previous_preservation[name]=dict(entries=len(tree),all_original_fields_preserved=True)
support=[B/'packet/INPUTS.json',B/'packet/PLAN.md',B/'client.py',C/'INDEPENDENT-PLAN-ASSESSMENT.json',
    Path(packet['source_manifest']),Path(sys.executable),F/'AGENTS.md',Path('T:/PROJECT_ISOLATION_RULEBOOK.md'),
    b.J2/'work/MANIFEST.json',b.J2/'work/run_canonical_journal.py',Path(packet['reference_selector_source']['path']),
    Path(cohort['path']),Path(old['closure']),Path(old['assessment'])]
external={str(p):b.sha(p) for p in support}
assert external[str(B/'client.py')]=='f92052f1d8cc3c1425aec345ec513455ae683df4d311d19b9f1a6a8b751a03a5'
assert external[str(C/'INDEPENDENT-PLAN-ASSESSMENT.json')]=='ed55d77f2f15f3b001c5774e1d7ce64ce92db48369118c58ed0b462840e53bed'
assert external[packet['reference_selector_source']['path']]==packet['reference_selector_source']['sha256']

for item in graph.sources:
    path=Path(item.path)
    if not path.is_absolute():path=Path(graph.root)/path
    external[str(path)]=b.sha(path)
tool=Path('T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce/taar')
for name in ('__init__.py','errors.py','orchestration_runtime.py','orchestration_graph.py','orchestration_persistence.py','orchestration_receipts.py'):
    external[str(tool/name)]=b.sha(tool/name)
b.r.save(W/'BINDING.json',binding)
b.r.save(W/'COLLECTION.json',dict(test_ids=ids,tests_collected=len(ids),selected=packet['selected'],test_modules=modules,
    product_modules=b.product_origins(),dependencies=b.r.dependency_identities(),interpreter=dict(path=sys.executable,native=b.r.stable(Path(sys.executable))[0]),
    sqlite_static_binary=dict(path=str(F/'native/sqlite_runtime/win-x64/sqlite3.dll'),native=b.r.stable(F/'native/sqlite_runtime/win-x64/sqlite3.dll')[0],loaded_by_preparation=False),
    environment=env,source_root=str(F),ordinary_imports=True,module_overlay=False,ROOT_override=False,
    exact_ordered_BR1_ids_preserved=True,test_bodies_executed=False,fixtures_bootstrapped=False,full_product_acceptance=False))
b.r.save(W/'PREPARATION.json',dict(recorded_at=datetime.now(timezone.utc).isoformat(),claim=claim,external_pins=external,
    source_before=before_source,source_after=after_source,fixtures_before=before,fixtures_after=after,
    predecessor_six_fixture_preservation=previous_preservation,read_only_BR1_JS9_raw_and_bytes_preserved=True,
    observation_elapsed_ns=time.monotonic_ns()-started,
    fixture_read_cost=dict(file_entries=sum(v['kind']=='file' for tree in before.values() for v in tree.values() if type(v) is dict),
        file_bytes=sum(v['bytes'] for tree in before.values() for v in tree.values() if type(v) is dict and v['kind']=='file'),
        qualification='Two complete reads of six declared existing bases; failed JS9 read-only observations separately recorded; no parent/history sibling scan'),
    canonical_test_bodies_executed=False,canonical_fixture_writes=False,fixture_bootstrap=False,Git_mutation=False,
    native_worker_execution=False,full_product_acceptance=False))
print(json.dumps(dict(collected=len(ids),selectors=len(packet['selected']),modules=len(modules),binding_sha256=b.sha(W/'BINDING.json'),canonical_bodies_executed=False),indent=2))
