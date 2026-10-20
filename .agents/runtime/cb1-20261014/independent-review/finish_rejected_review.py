from pathlib import Path
import json,os,subprocess,sys
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cb1-20261014';BASE=P/'.agents/runtime/cb1-20261014';D=BASE/'independent-review';RUN='cb1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN=RUN
cohort=json.loads((D/'COHORT.json').read_text());hostile=json.loads((D/'GROUP-TYPE-PROBE.json').read_text())
assert cohort['tests_run']==16 and cohort['failures']==cohort['errors']==cohort['skips']==[]
assert hostile['tests_run']==2 and len(hostile['failures'])==2 and hostile['errors']==hostile['skips']==[]
assert all(row['CodePin_constructor_accepted'] and row['NativeCodeBinding_constructor_accepted'] and row['private_retained_lease_valid'] and not row['primitive_string'] for row in hostile['facts'])
assert all(owner['closed'] and not owner['pending'] for owner in cohort['owners']+hostile['owned_resources'])
assert not cohort['remaining_threads'] and not hostile['remaining_threads']
assert all(s.ordinary(Q/name)==row for name,row in cohort['candidate_before'].items())
assert all(s.ordinary(P/name)==row for name,row in cohort['source_before'].items())
assert s.sha(Q/'TRANSFER-MANIFEST.json')=='0ab0a0762dbc840792a229ec2e9c5ee5b5107d36d4f18841845490a8fd3898e3'
report=dict(recorded_at=s.utc(),decision='rejected',exit_status=1,reviewer=s.ACTOR,author='/root',
    manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),implement_sha256=s.sha(BASE/'implement.json'),
    original_cases=16,original_passed=16,additional_hostile_cases=2,hostile_passed=0,hostile_failed=2,errors=0,skips=0,
    cohort=s.reference(D/'COHORT.json'),hostile=s.reference(D/'GROUP-TYPE-PROBE.json'),probe=s.reference(D/'probe_group_type.py'),
    candidate_payloads=294,Source_payloads=290,candidate_and_Source_native_bytes_retained=True,
    checked_files=['src/ceta/identity/native_code_binding.py','tests/contract/test_native_code_binding.py','contracts/NATIVE_CODE_BINDING_V1.md'],
    reused_call_sites=['src/ceta/supervisor/windows_jobs.py:_path/_file_identity/_hash_image',
        'src/ceta/supervisor/isolated_worker.py:queue_handle/_release_handle/retry_cleanup/pending_native_resources'],
    finding=dict(id='CB1-R20-F01',classification='blocking current review; narrow successor repair required',
        source_path='src/ceta/identity/native_code_binding.py',source_line=33,
        invariant='CodePin.group must be the exact built-in str primitive and one of source/environment before group comparisons/native allocation.',
        observed='Membership alone invokes equality on arbitrary objects. Both a plain str subclass and a custom equality/hash/order object pass CodePin validation, group-coverage and sorting, native construction, snapshot and the private retained lease.',
        native_effects='Each hostile case retained2 real file handles plus11 ancestor handles, produced source/environment commitments and a live private lease. Every owned binding then closed without pending resources.',
        exact_methods=[row['id'] for row in hostile['facts']],
        repair='Require type(self.group) is str before membership in CodePin.__post_init__; keep revalidation inside NativeCodeBinding, primitive names/paths/digests, native hashing/pinning/lease/cleanup unchanged.',
        acceptance='Retain original16 case bodies and two literal hostile oracle methods, reject both wrong group types before equality/hash/order callbacks or native file allocation. Verify exact genuine primitive source/environment positives and full native retirement.',
        scope_limit='Trusted-manifest input validation defect. No remote/public authority bypass, credential exposure or Source damage established.'),
    verified_other_behavior=['Original16 actual Windows cases pass,23 observed constructors closed/no pending, no remaining threads.',
        'Read-only/noninheritable file and ancestor pins, native IDs/hashes, actual write/delete/replacement/rename denials and recovery verified within frozen cohort.',
        'Same-thread exact lease, foreign-thread/close cancellation, bounded nonblocking acquisition and primary-control custody remain covered.',
        'Library does not enumerate or authorize missing dependencies; canonical authority, clock, native isolation, public admission and effects remain separate.'],
    source_publication=False,configuration_changes=False,independence='Distinct same-host reviewer; only fresh reviewer fixture ROOT redirected, exact Q modules/test bodies retained.')
s.write_new(D/'REPORT.json',report)
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_receipts import validate_receipt,load_receipt
from taar.orchestration_runtime import _snapshot_workspace,_changed_files
claim=json.loads((BASE/RUN/'claims.json').read_text())['review'];graph=json.loads((BASE/RUN/'graph.json').read_text())['graph']
assert claim['executor_id']==s.ACTOR and _changed_files(claim['baseline_snapshot'],_snapshot_workspace(Q,Path('T:/')))==[]
receipt=dict(schema_version=1,run_id=RUN,node_id='review',executor_id=s.ACTOR,started_at=claim['claimed_at'],finished_at=s.utc(),input_hash=claim['input_hash'],changed_files=[],
    result=dict(manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),report=s.reference(D/'REPORT.json'),finding_id='CB1-R20-F01',
        original16_passed=True,hostile2_failed=True,all_owned_native_handles_retired=True,Source290_retained=True,candidate294_retained=True,source_publication=False),
    commands=[dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(D/'run_review.py')]),exit_status=0),
              dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(D/'probe_group_type.py')]),exit_status=1)],
    validations=[dict(name='Frozen16 actual native cases pass and all owned resources retired',passed=True),
        dict(name='Only exact primitive group accepted before arbitrary comparison or pinning',passed=False),
        dict(name='Candidate294 and Source290 bytes/native identities unchanged',passed=True)],exit_status=1,decision='rejected')
kwargs=dict(run_id=RUN,node_id='review',executor_id=s.ACTOR,input_hash=claim['input_hash'],claimed_at=claim['claimed_at'],node=graph['nodes']['review'])
validate_receipt(receipt,**kwargs);s.write_new(D/'review.json',receipt);validate_receipt(load_receipt(D/'review.json'),**kwargs)
cmd=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1','node','complete',RUN,'review',str(D/'review.json'),'--runtime-root',str(BASE)]
r=subprocess.run(cmd,cwd='T:/00-Active',capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
(D/'review-complete.stdout.txt').write_bytes(r.stdout);(D/'review-complete.stderr.txt').write_bytes(r.stderr)
response=json.loads(r.stdout.decode('utf-8-sig'));s.write_new(D/'review-complete.json',dict(command_argv=cmd,exit_status=r.returncode,response=response))
state=json.loads((BASE/RUN/'state.json').read_text());claims=json.loads((BASE/RUN/'claims.json').read_text());persisted=json.loads((BASE/RUN/'receipts/review.json').read_text())
assert state['nodes']['review']['state']=='FAILED' and state['sequence']==9 and claims=={}
assert len(receipt)==13 and len(persisted)==16 and all(persisted[key]==value for key,value in receipt.items())
assert persisted['decision']=='rejected'
s.write_new(D/'ACTUAL-READBACK.json',dict(recorded_at=s.utc(),state=state,claims=claims,authored_fields=13,persisted_fields=16,authored_fields_exact=True,
    engine_response=response,actual_complete_command_exit_status=r.returncode,submitted_decision='rejected',persisted_decision=persisted['decision'],
    failed_node_decision_preserved=state['nodes']['review'].get('decision'),review_sha256=s.sha(D/'review.json')))
files={path.relative_to(D).as_posix():s.ordinary(path) for path in D.rglob('*') if path.is_file()}
s.write_new(D/'REVIEW-SEAL.json',dict(recorded_at=s.utc(),files=files,review_sha256=s.sha(D/'review.json'),manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),
    scope_released=True,source_publication=False,decision='rejected'))
print(json.dumps(dict(review_sha256=s.sha(D/'review.json'),report_sha256=s.sha(D/'REPORT.json'),readback_sha256=s.sha(D/'ACTUAL-READBACK.json'),
    seal_sha256=s.sha(D/'REVIEW-SEAL.json'),state=state['nodes']['review']['state'],sequence=state['sequence'],claims=claims,
    complete_command_exit_status=r.returncode,engine_response=response)),flush=True)
