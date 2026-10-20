"""Truthful bounded rejection; original22pass and two native custody failures."""
from pathlib import Path
import ast,hashlib,json,os,re,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');Q=F/'.agents/ac4-20261015';R=F/'.agents/runtime/ac4-20261015';D=Path(__file__).resolve().parent
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=D
read=lambda p:json.loads(Path(p).read_text())
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='edfdd84ab33dc4ac9ee8f07a3205d4119a5bf496339d40dafc16d5f47576d1f1'
assert s.sha(R/'implement.json')=='a9a8f8e7d848ecb96ee35209a43da7853a5c0d0f86b20931602b2cd89b288d80'
assert s.sha(R/'AUTHOR-READBACK.json')=='4d519473e6f77bcff06db76d4d6c3213be09aac2ad7eac3842302aef6ac254a9'
assert s.sha(R/'AUTHOR-SEAL.json')=='ad4ae65c42231e7106305ba880099b11751feed86764d12ee4580ed3c405ff7c'
manifest=read(Q/'TRANSFER-MANIFEST.json');assert len(manifest['payloads'])==295
for name,row in manifest['payloads'].items():assert s.ordinary(Q/name)==row
original=read(D/'cohort-r1/RESULT.json')
assert original['tests_run']==22 and not original['failures'] and not original['errors'] and not original['skipped']
assert original['expected_ids']==original['executed_ids']==original['stopped_ids']
assert len(set(original['executed_ids']))==22 and original['exit_status']==0
raw_ids=re.findall(r'^test_[^\n]+\(([^)]+)\) \.\.\. ok\s*$',(D/'cohort-r1/tests.txt').read_text(),re.M)
assert raw_ids==original['executed_ids']
assert original['source_before']==original['source_after'] and original['candidate_before']==original['candidate_after']
assert not original['forbidden_calls'] and not any(original['pending_native_resources']) and not original['new_threads']
for name,row in original['source_after'].items():assert s.ordinary(F/name)==row
hostile=read(D/'COMBINED-CUSTODY-PROBE.json')
assert hostile['tests_run']==2 and len(hostile['failures'])==2 and not hostile['errors'] and not hostile['skips']
assert hostile['exit_status']==1 and hostile['all_owned_native_resources_retired'] and not hostile['new_threads']
assert len(hostile['observations'])==2
for item in hostile['observations']:
    assert item['exact_primary_preserved'] and not item['caller_visible_cleanup_present']
    assert item['native_pending_at_error'] and item['all_owned_native_resources_retired']
    assert item['native_handles_before'][0]['GetHandleInformation'] is True
    assert item['native_handles_after_explicit_reviewer_recovery'][0]['GetHandleInformation'] is False
    assert item['native_handles_after_explicit_reviewer_recovery'][0]['error']==6
local_author=read(R/'implement.json');stored_author=read(R/'ac4-20261015/receipts/implement.json')
strict12={'schema_version','run_id','node_id','executor_id','started_at','finished_at','input_hash',
    'changed_files','result','commands','validations','exit_status'}
typed=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
assert set(local_author)==strict12 and set(stored_author)==strict12|{'git_baseline','observed_git','receipt_hash'}
assert all(typed(local_author[n])==typed(stored_author[n]) for n in strict12)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
from taar.orchestration_receipts import validate_receipt,load_receipt
from taar.orchestration_graph import compile_graph
state=read(R/'ac4-20261015/state.json');graph=read(R/'ac4-20261015/graph.json')
assert state['sequence']==8 and state['nodes']['review']['state']=='RUNNING'
compiled=compile_graph(Path('T:/'),Q)
assert compiled.fingerprint==graph['fingerprint']==state['graph_fingerprint']
claim=read(R/'ac4-20261015/claims.json')['review']
assert claim['executor_id']=='/root/pressure_writer' and claim['workspace']==str(Q)
snapshot=_snapshot_workspace(Q,Path('T:/'));changed=_changed_files(claim['baseline_snapshot'],snapshot)
assert changed==[] and len(snapshot)==296
parent=F/'.agents/ac3-20261014'
old=ast.parse((parent/'src/ceta/supervisor/isolated_worker.py').read_text())
new=ast.parse((Q/'src/ceta/supervisor/isolated_worker.py').read_text())
for name in ('IsolationTokenFacts','SECURITY_CAPABILITIES','SID_AND_ATTRIBUTES'):
    select=lambda tree:ast.dump(next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name),include_attributes=False)
    assert select(old)==select(new)
old_path=R/'run_diagnostics.py';runner=D/'run_diagnostics.py'
s.write_new(D/'REVIEW-PREPARATION.json',{'at':s.utc(),'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),
    'source_before_after':original['source_before'],'candidate_snapshot':snapshot,'installed_changed_files':changed,
    'graph_fingerprint':compiled.fingerprint,'author12_persisted15_typed_exact':True,
    'runner_origin':s.reference(old_path),'reviewer_runner':s.reference(runner),
    'runner_rebinding':'FixedF path; outputR=independent-review; original Source inputs readOR; actor=root/pressure_writer. Original test bodies/candidate imports unchanged.'})
report={'schema_version':1,'at':s.utc(),'reviewer':'/root/pressure_writer','author':'/root','decision':'rejected',
    'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'implement':s.reference(R/'implement.json'),
    'scope':'RootAC4diagnostic delta, original predicates/call order and exact native custody/error callers.',
    'independence':'Reviewer did not author AC4diagnostic changes. Reviewer authored earlier AC2cleanup foundation; this inherited issue is explicitly disclosed. Root personally reproduced/confirmed its observed consequence; no claim of independent AC2implementation acceptance.',
    'original_tests':{'count':22,'unique_ids':original['executed_ids'],'result':s.reference(D/'cohort-r1/RESULT.json'),
        'raw':s.reference(D/'cohort-r1/tests.txt'),'failures':0,'errors':0,'skips':0},
    'hostile_tests':{'count':2,'result':s.reference(D/'COMBINED-CUSTODY-PROBE.json'),
        'raw':s.reference(D/'combined-custody-r1.txt'),'probe':s.reference(D/'probe_combined_custody.py'),
        'failures':2,'errors':0,'skips':0,'actual_owned_token_and_SID_read_only_operations':True},
    'findings':[{'id':'AC4-F01','classification':'blocking current task','file':'src/ceta/supervisor/isolated_worker.py',
        'function':'_attach_cleanup','lines':[420,427],
        'trigger':'Real token query completes then exact refusing-setter KeyboardInterrupt/SystemExit is raised; cleanup refuses before native close.',
        'observed':'Identical primary contains new token diagnostics in base storage, but lacks isolation_cleanup/owned_process while actual owned token handle remains live/PENDING.',
        'consequence':'Caller-visible explicit native recovery owner is omitted. The reviewer retained the API separately and retired all exact owned resources; no persistent native leak or late operation is claimed.',
        'proof':s.reference(D/'COMBINED-CUSTODY-PROBE.json'),
        'next_repair':'Fresh successor must retain exact cleanup/owned_process in canonical BaseException storage despite refusing hooks, preserving best-effort notes and the exact primary.'}],
    'verified':['All22originalIDs pass; native current token rejects AppContainerSID mismatch with measured0vsunknown preserved.',
        'IsolationTokenFacts/SECURITY_CAPABILITIES/SID_AND_ATTRIBUTES ASTs and old tests/Rust bytes remain exact.',
        'Both hostile native cases retire exact token handles; GetHandleInformation observed validbefore and invalid/error6after; owned SID memory also retired.',
        'All295candidate payloads, manifest and Source290 native bytes/identities retained; installedchangedfiles empty.',
        'No worker/profile calls or new threads. Positive isolation and activation remain unqualified.'],
    'prior_author_failures':manifest['prior_failures'],
    'additional_existing_issue':{'classification':'requires separate follow-up work','issue':'Historical unanchored:2native regression also matches267; no restrictive launch was executed in this review.'},
    'preparation':s.reference(D/'REVIEW-PREPARATION.json'),'Source_application':False,'positive_isolation_qualified':False}
s.write_new(D/'REPORT.json',report)
receipt={'schema_version':1,'run_id':'ac4-20261015','node_id':'review','executor_id':'/root/pressure_writer',
    'started_at':claim['claimed_at'],'finished_at':s.utc(),'input_hash':claim['input_hash'],'changed_files':changed,
    'decision':'rejected','exit_status':1,'result':{'decision':'rejected','manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),
        'report':s.reference(D/'REPORT.json'),'original22_PASS':True,'blocking_findings':['AC4-F01'],
        'prior_failures':[s.reference(D/'COMBINED-CUSTODY-PROBE.json'),manifest['prior_failures']],
        'actual_owned_native_cleanup_complete':True,'Source_application':False},
    'commands':[{'command':subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(runner),'cohort-r1']),'exit_status':0},
        {'command':subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(Path(__file__))]),'exit_status':0}],
    'validations':[{'name':'Original22 and frozenSource/candidate/native recovery checks pass','passed':True},
        {'name':'Combined refusing-primary and cleanup-failure retains explicit caller recovery custody','passed':False},
        {'name':'No profile/worker/Source operation; same primary retained and all reviewer-owned native resources retired','passed':True}]}
kwargs={'run_id':'ac4-20261015','node_id':'review','executor_id':'/root/pressure_writer',
    'input_hash':claim['input_hash'],'claimed_at':claim['claimed_at'],'node':graph['graph']['nodes']['review']}
validate_receipt(receipt,**kwargs);s.write_new(D/'review.json',receipt);validate_receipt(load_receipt(D/'review.json'),**kwargs)
print(json.dumps({'decision':'rejected','blocking':'AC4-F01','original_tests':22,'hostile_failures':2,
    'changed_files':changed,'review':s.reference(D/'review.json'),'report':s.reference(D/'REPORT.json')}))
