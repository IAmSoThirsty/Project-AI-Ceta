from pathlib import Path
import difflib,json,os,subprocess,sys
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cb2-20261014';BASE=P/'.agents/runtime/cb2-20261014';D=BASE/'independent-review';RUN='cb2-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN=RUN
cohort=json.loads((D/'COHORT.json').read_text());literal=json.loads((D/'LITERAL-GROUP-TYPE-PROBE.json').read_text());reval=json.loads((D/'REVALIDATION-PROBE.json').read_text())
assert cohort['tests_run']==18 and literal['tests_run']==2 and reval['tests_run']==1
for data in (cohort,literal,reval):
    assert data['failures']==data['errors']==data['skips']==data['remaining_threads']==[]
    assert data['expected_ids']==data['executed_ids']==data['stopped_ids']
assert not literal['comparison_callbacks'] and literal['native_binding_constructors']==literal['native_api_constructors']==0
assert reval['native_file_or_ancestor_retains']==0 and not reval['comparison_callbacks']
assert all(row['closed'] and not row['pending'] for row in cohort['owners'])
assert all(s.ordinary(Q/name)==row for name,row in cohort['candidate_before'].items())
assert all(s.ordinary(P/name)==row for name,row in cohort['source_before'].items())
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='c4ca0a083524c936ec2b8df4bc1cabef8f68574e3404a007d4542cecc57dd565'
assert s.sha(BASE/'implement.json')=='57d7988710eedb4aabca7e687ff884ab1028a78c4c15a0a5c2d4c6ea89eed3d0'
eligible=['src/ceta/identity/native_code_binding.py','tests/contract/test_native_code_binding.py','contracts/NATIVE_CODE_BINDING_V1.md']
loc={}
for name in eligible:
    old=(P/'.agents/cb1-20261014'/name).read_text().splitlines(True);new=(Q/name).read_text().splitlines(True)
    delta=list(difflib.unified_diff(old,new));loc[name]=dict(physical_added=sum(row.startswith('+') and not row.startswith('+++') for row in delta),
        physical_removed=sum(row.startswith('-') and not row.startswith('---') for row in delta),net_physical=len(new)-len(old))
prior={name:s.reference(P/'.agents/runtime/cb1-20261014/independent-review'/name)
    for name in ('review.json','REPORT.json','GROUP-TYPE-PROBE.json','probe_group_type.py','ACTUAL-READBACK.json','REVIEW-SEAL.json')}
report=dict(recorded_at=s.utc(),decision='approved',exit_status=0,reviewer=s.ACTOR,author='/root',
    manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),implement_sha256=s.sha(BASE/'implement.json'),
    tests_run=21,candidate_cases=18,retained_candidate_cases=16,new_candidate_regressions=2,
    unchanged_literal_historical_replays=2,additional_revalidation_methods=1,additional_revalidation_subcases=2,
    failures=0,errors=0,skips=0,distinct_functionality_count_claimed=False,
    cohort=s.reference(D/'COHORT.json'),literal=s.reference(D/'LITERAL-GROUP-TYPE-PROBE.json'),revalidation=s.reference(D/'REVALIDATION-PROBE.json'),
    narrow_diff=s.reference(D/'NARROW-DIFF.json'),diff=s.reference(D/'SUCCESSOR.diff'),conservation=s.reference(D/'CONSERVATION.json'),
    checked_files=eligible,physical_changes_vs_CB1=loc,source_LOC_credit='One production predicate replaced; zero net source lines. No reused source credited as new.',
    candidate_payloads=294,Source_payloads=290,candidate_and_Source_native_bytes_retained=True,original_CB1_rejection=prior,
    verified_findings=[
        dict(id='CB2-R20-V01',finding='The entire production source is byte-exact CB1 except the single exact built-in str predicate before membership. Only the three eligible source/test/contract files differ across294 payloads; all16 original test method ASTs remain exact.',evidence=[s.reference(D/'NARROW-DIFF.json'),s.reference(D/'SUCCESSOR.diff')]),
        dict(id='CB2-R20-V02',finding='Both original hostile classes and methods are compiled unchanged from the pinned historical script and pass against CB2. No arbitrary equality/hash/order callback, NativeCodeBinding constructor or native API constructor is invoked in either case.',evidence=[s.reference(D/'LITERAL-GROUP-TYPE-PROBE.json')]),
        dict(id='CB2-R20-V03',finding='Constructor revalidation also denies each bad group after controlled privileged mutation of an otherwise valid frozen CodePin, before file/ancestor retention or comparison. The native API wrapper initializes first; this does not claim zero wrapper allocation in that different path. Both failed-constructor owners close with empty pending resources.',evidence=[s.reference(D/'REVALIDATION-PROBE.json')]),
        dict(id='CB2-R20-V04',finding='All18 frozen candidate methods pass independently on actual disposable Windows files. Native IDs/hashes, write/delete/replace/ancestor rename exclusion, noninheritability, private same-thread leases, cancellation, cleanup recovery and primary control identity remain verified by the retained cases. All25 observed owners close and no new live threads remain.',evidence=[s.reference(D/'COHORT.json'),s.reference(D/'CONSERVATION.json')]),
        dict(id='CB2-R20-V05',finding='Candidate294 and active Source290 bytes/native identities are unchanged before/after execution; direct interpreter image and the original CB1 manifest/probe remain exact.',evidence=[s.reference(D/'CONSERVATION.json')])],
    inspected_reused_call_sites=['src/ceta/supervisor/windows_jobs.py:_path/_file_identity/_hash_image',
        'src/ceta/supervisor/isolated_worker.py:queue_handle/_release_handle/retry_cleanup/pending_native_resources'],
    resolved_finding='CB1-R20-F01 resolved in this exact successor; old rejected review and failed oracles remain immutable.',
    remaining_obligations=[
        'Trusted composition must supply the complete reviewed finite source/environment dependency manifest. The library does not enumerate or approve missing dependencies.',
        'Same-process privileged mutation, administrator/kernel tampering and writable objects outside the declared finite manifest are outside the qualified trust boundary.',
        'The isolated-worker helper is an exact pinned uncredited dependency. No positive AppContainer isolation, genuine owner approval, canonical admission, effect or settlement is established by this review.',
        'Actual Source publication and any joined foundation/full-product acceptance belong to separately reviewed Root integration.'],
    reviewer_lookup_notes=[dict(path='runtime/cb2-20261014/SUCCESSOR.diff',classification='not blocking current task',detail='Author did not provide this optional filename; reviewer generated and inspected an exact independent diff.'),
        dict(path='runtime/cb1-20261014/independent-review/finish_review.py',classification='not blocking current task',detail='Historical finalizer is named finish_rejected_review.py; corrected lookup without modifying historical files.')],
    independence='Distinct same-host reviewer. Original Q modules/test bodies, fresh reviewer-only fixture ROOT; observer wrappers only delegate and record native lifecycle/comparison calls.',
    source_publication=False,configuration_changes=False)
s.write_new(D/'REPORT.json',report)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt,load_receipt
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
claim=json.loads((BASE/RUN/'claims.json').read_text())['review'];graph=json.loads((BASE/RUN/'graph.json').read_text())['graph']
assert claim['executor_id']==s.ACTOR and _changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')))==[]
receipt=dict(schema_version=1,run_id=RUN,node_id='review',executor_id=s.ACTOR,started_at=claim['claimed_at'],finished_at=s.utc(),input_hash=claim['input_hash'],changed_files=[],
    result=dict(manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),report=s.reference(D/'REPORT.json'),tests_run=21,candidate_cases=18,
        literal_historical_replays=2,additional_revalidation_methods=1,all_native_custody_retired=True,
        Source290_retained=True,candidate294_retained=True,resolved_finding='CB1-R20-F01',source_publication=False),
    commands=[dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(D/'run_review.py')]),exit_status=0)],
    validations=[dict(name='Exact one-predicate production repair and original16 test ASTs retained',passed=True),
        dict(name='All18 frozen cases and2 unchanged historical oracles plus1 extra method pass',passed=True),
        dict(name='No bad-group comparison or native binding allocation in literal constructor path',passed=True),
        dict(name='Revalidation rejects before file retention and25 observed native owners retire',passed=True),
        dict(name='Source290 candidate294 native bytes retained and historical rejection preserved',passed=True)],exit_status=0,decision='approved')
kwargs=dict(run_id=RUN,node_id='review',executor_id=s.ACTOR,input_hash=claim['input_hash'],claimed_at=claim['claimed_at'],node=graph['nodes']['review'])
validate_receipt(receipt,**kwargs);s.write_new(D/'review.json',receipt);validate_receipt(load_receipt(D/'review.json'),**kwargs)
cmd=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1','node','complete',RUN,'review',str(D/'review.json'),'--runtime-root',str(BASE)]
r=subprocess.run(cmd,cwd='T:/00-Active',capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
(D/'review-complete.stdout.txt').write_bytes(r.stdout);(D/'review-complete.stderr.txt').write_bytes(r.stderr)
response=json.loads(r.stdout.decode('utf-8-sig'));s.write_new(D/'review-complete.json',dict(command_argv=cmd,exit_status=r.returncode,response=response));assert r.returncode==0 and response['allowed']
state=json.loads((BASE/RUN/'state.json').read_text());claims=json.loads((BASE/RUN/'claims.json').read_text());persisted=json.loads((BASE/RUN/'receipts/review.json').read_text())
assert state['nodes']['review']['state']=='SUCCEEDED' and state['sequence']==9 and claims=={}
assert len(receipt)==13 and len(persisted)==16 and all(persisted[key]==value for key,value in receipt.items())
s.write_new(D/'ACTUAL-READBACK.json',dict(recorded_at=s.utc(),state=state,claims=claims,authored_fields=13,persisted_fields=16,
    authored_fields_exact=True,review_sha256=s.sha(D/'review.json'),manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json')))
files={path.relative_to(D).as_posix():s.ordinary(path) for path in D.rglob('*') if path.is_file()}
s.write_new(D/'REVIEW-SEAL.json',dict(recorded_at=s.utc(),files=files,manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),review_sha256=s.sha(D/'review.json'),
    source_publication=False,review_scope_released=True))
print(json.dumps(dict(review_sha256=s.sha(D/'review.json'),report_sha256=s.sha(D/'REPORT.json'),readback_sha256=s.sha(D/'ACTUAL-READBACK.json'),
    seal_sha256=s.sha(D/'REVIEW-SEAL.json'),state=state['nodes']['review']['state'],sequence=state['sequence'],claims=claims,tests=21,physical_changes_vs_CB1=loc)),flush=True)
