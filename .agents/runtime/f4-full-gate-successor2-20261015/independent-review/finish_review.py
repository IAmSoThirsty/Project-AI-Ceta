"""Complete the narrow F4 engineering review and verify its actual consumer."""
from pathlib import Path
import json,os,stat,subprocess,sys

F=Path('T:/00-Active/Project-AI-CETA');R=F/'.agents/runtime/f4-full-gate-successor2-20261015'
Q=R/'candidate';D=Path(__file__).resolve().parent;RUN=R.name;ACTOR='/root/wt1_reviewer'
sys.dont_write_bytecode=True
sys.path.insert(0,str(F/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=D;s.RUN=RUN;s.ACTOR=ACTOR
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.orchestration_persistence import sha256_json
from taar.orchestration_receipts import validate_receipt,load_receipt
from taar.orchestration_runtime import _snapshot_workspace,_changed_files

read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
audit=read(D/'CONSERVATION-AND-QUALIFICATION.json');assert audit['decision']=='approved' and audit['exit_status']==0
tests=read(D/'controlled-r1/RESULT.json');assert tests['tests_run']==46 and tests['exit_status']==0
assert not any(tests[key] for key in ('failures','errors','skips','forbidden_native_and_process_calls','remaining_threads'))
assert all(s.ordinary(Q/name)==row for name,row in audit['candidate6'].items())
assert all(s.ordinary(F/name)==row for name,row in audit['source290'].items())
scripts={name:s.sha(Q/name) for name in ('full_gate.py','run_authorized.py','complete_authorized.py')}
assert scripts==read(Q/'TRANSFER-MANIFEST.json')['successor_scripts']
claim=read(R/RUN/'claims.json')['review'];assert claim['executor_id']==ACTOR
snapshot=_snapshot_workspace(Q,Path('T:/'));assert len(snapshot)==6
assert _changed_files(claim['baseline_snapshot'],snapshot)==[]
report=dict(at=s.utc(),reviewer=ACTOR,author='/root',decision='approved',
    action='Independent Collaborative Review of frozen F4 full-gate successor2 engineering tools',
    authority='Root single-job delegation and actual read-only installed review claim',
    scope='Dormant authorization/runner/completion adapters and controlled test enforcement; eligible Source application paths are empty',
    manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),reviewed_successor_scripts=scripts,
    controlled46=s.reference(D/'controlled-r1/RESULT.json'),conservation=s.reference(D/'CONSERVATION-AND-QUALIFICATION.json'),
    verified_findings=[
        'Actual amended Result class uses the injected unmangled global; started exact case admission passes, unstarted/repeated entry denies before recording, ordinary case requires no gate.',
        'All42 predecessor test method ASTs are exact and4 new actual-class boundary methods pass. Exact V1-to-V2 source differences and author bindings were independently compared.',
        'Full2053 ordered IDs remain required. Partial2052 excludes only the original restricted method and is explicitly nonaccepted; skips, deferrals, wrong order, Boolean counts and changed provenance are rejected.',
        'Approval digest/nonce consumption, strict document domains, source/environment/tool currentness, wall/elapsed expiry, single native attempt and exact denial observation pass controlled cases.',
        'Native ordinary-file capture held actual read-only Windows sharing on fresh clearly synthetic files. No CETA/process/profile/CPU/Hello operation or genuine permission record was performed.',
        'Original completion assertions remain except its exact self-path adjustment. Distinct actual successor and delivered reviews, full native closure, current Source/native-originals, exact metadata scope disposition and installed integration remain mandatory.',
        'Source290 E33601 F4candidate336, predecessor6/author154 and current author74 evidence/native identities are conserved; predecessor rejected state is preserved.'
    ],
    conditions_before_any_Source_acceptance=[
        'Fresh exact human authorization for the original restricted no-profile case through its trusted operator command boundary',
        'Actual destination full2053 original IDs without skips/deferrals, exact native denial and all original cleanup/conservation checks',
        'Distinct delivered Source review binding exact result/APPLIED/native payload map',
        'Separate Root scope disposition for exact ordinary library payloads with metadata109 unresolved, unwaived and no attribute-mutation authorization',
        'Existing F4 installed integration claim/ledger completion by Root only'],
    limitations=read(Q/'TRANSFER-MANIFEST.json')['limitations'],
    disagreement='No new blocker established in this exact bounded engineering review. Runtime/full-native/Source acceptance remains unexecuted.',
    new_CETA_product_Source_LOC=0,new_native_effects=0,genuine_authorization_created=False,
    full2053_executed=False,Source_publication=False,whole_fixture_preservation_accepted=False,
    metadata_issue_waived=False)
s.write_new(D/'REPORT.json',report)
receipt=dict(schema_version=1,run_id=RUN,node_id='review',executor_id=ACTOR,
    started_at=claim['claimed_at'],finished_at=s.utc(),input_hash=claim['input_hash'],changed_files=[],
    result=dict(manifest_sha256=s.sha(Q/'TRANSFER-MANIFEST.json'),reviewed_successor_scripts=scripts,
        report=s.reference(D/'REPORT.json'),controlled46=s.reference(D/'controlled-r1/RESULT.json'),
        conservation=s.reference(D/'CONSERVATION-AND-QUALIFICATION.json'),full2053_executed=False,
        Source_publication=False,genuine_authorization_created=False),
    commands=[dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(D/'run_controls.py'),'controlled-r1']),exit_status=0),
        dict(command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(D/'audit_review.py')]),exit_status=0)],
    validations=[dict(name=name,passed=True) for name in (
        'All46 exact controlled methods pass and four actual Result boundaries are qualified',
        'Original42 ASTs exact scripts narrow and full2053 assertions retained',
        'No CETA effect product test body process profile human approval or Source execution',
        'Candidate predecessor Source E3 parent and author evidence conserved',
        'Future actual authorization full native delivered review and metadata gates remain')],
    exit_status=0,decision='approved')
kwargs=dict(run_id=RUN,node_id='review',executor_id=ACTOR,input_hash=claim['input_hash'],claimed_at=claim['claimed_at'],node=read(R/RUN/'graph.json')['graph']['nodes']['review'])
assert len(receipt)==13;validate_receipt(receipt,**kwargs)
s.write_new(D/'review.json',receipt);validate_receipt(load_receipt(D/'review.json'),**kwargs)
def invoke(args,label):
    command=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',*args,'--runtime-root',str(R)]
    started=s.utc();done=subprocess.run(command,cwd=F,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    for suffix,payload in [('stdout.txt',done.stdout),('stderr.txt',done.stderr)]:s.fs.write_new(D/(label+'.'+suffix),payload)
    response=json.loads(done.stdout.decode('utf-8-sig'))
    s.write_new(D/(label+'.json'),dict(command_argv=command,started_at=started,finished_at=s.utc(),exit_status=done.returncode,response=response))
    assert done.returncode==0 and response['allowed'],response
    return response
invoke(['node','complete',RUN,'review',str(D/'review.json')],'review-complete')
status=invoke(['run','status',RUN],'actual-final-status')
state=read(R/RUN/'state.json');claims=read(R/RUN/'claims.json');stored=read(R/RUN/'receipts/review.json')
assert state['sequence']==9 and state['nodes']['review']['state']=='SUCCEEDED' and claims=={}
assert status['sequence']==9 and status['states']['review']=='SUCCEEDED'
assert len(stored)==16 and set(stored)==set(receipt)|{'receipt_hash','observed_git','git_baseline'}
assert canonical(receipt)==canonical({key:stored[key] for key in receipt})
fingerprint=sha256_json({key:value for key,value in stored.items() if key!='receipt_hash'})
assert fingerprint==stored['receipt_hash']==state['nodes']['review']['receipt_hash']
assert read(R/RUN/'results/review.json')==dict(node_id='review',receipt_hash=fingerprint,result=receipt['result'])
assert state['nodes']['review']['artifact_hash']==sha256_json({'input_hash':receipt['input_hash'],'result':receipt['result']})
assert _snapshot_workspace(Q,Path('T:/'))==snapshot
sys.path.insert(0,str(Q));import complete_authorized as completion
consumer=completion.require_successor_review(completion.runner.support())
assert consumer==s.reference(D/'review.json')
s.write_new(D/'REVIEW-CONSUMER-READBACK.json',dict(at=s.utc(),function='complete_authorized.require_successor_review',
    exact_consumer=s.ordinary(Q/'complete_authorized.py'),actual_review=consumer,
    actual_strict_installed_review_consumed_read_only=True,completion_main_executed=False,
    source_or_native_CETA_execution=False,genuine_operator_authorization=False))
assert all(s.ordinary(Q/name)==row for name,row in audit['candidate6'].items())
assert all(s.ordinary(F/name)==row for name,row in audit['source290'].items())
assert all(s.ordinary(Path(row['path']))==row for row in audit['E33601'].values())
s.write_new(D/'ACTUAL-READBACK.json',dict(at=s.utc(),reviewer=ACTOR,decision='approved',
    local=s.reference(D/'review.json'),persisted=s.reference(R/RUN/'receipts/review.json'),
    result_envelope=s.reference(R/RUN/'results/review.json'),actual_status=s.reference(D/'actual-final-status.json'),
    strict_local13_persisted16_typed_equality=True,official_normalized_fingerprint=fingerprint,
    exact_result_envelope_and_input_result_artifact_verified=True,sequence=9,review_state='SUCCEEDED',claims=claims,
    actual_consumer=s.reference(D/'REVIEW-CONSUMER-READBACK.json'),Source_publication=False,full2053_executed=False))
members={}
for parent,dirs,files in os.walk(D):
    for name in dirs:assert not s.fs.reparse(s.fs.lstat(Path(parent)/name))
    for name in files:
        path=Path(parent)/name;info=s.fs.lstat(path);assert stat.S_ISREG(info.st_mode) and not s.fs.reparse(info)
        members[path.relative_to(D).as_posix()]=s.ordinary(path)
s.write_new(D/'REVIEW-SEAL.json',dict(at=s.utc(),reviewer=ACTOR,decision='approved',
    manifest=s.reference(Q/'TRANSFER-MANIFEST.json'),members=members,
    actual_claim_released=True,sequence=9,review_state='SUCCEEDED',
    scope='Dormant engineering tool qualification only',Source_publication=False,full2053_executed=False))
print(json.dumps(dict(review=s.reference(D/'review.json'),report=s.reference(D/'REPORT.json'),
    readback=s.reference(D/'ACTUAL-READBACK.json'),seal=s.reference(D/'REVIEW-SEAL.json'),
    controlled_methods=46,sequence=9,claims=claims,actual_consumer_read_only=True,
    Source_publication=False,full2053_executed=False)))
