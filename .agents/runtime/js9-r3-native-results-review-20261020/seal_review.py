"""Seal the finite actual native engineering evidence review, without new effects."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
F=Path('T:/00-Active/Project-AI-CETA');O=Path(__file__).resolve().parent
D=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(repository_relative_path=p.relative_to(F).as_posix(),sha256=sha(p))
def save(name,value):
    with (O/name).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
v=json.loads((O/'VERIFICATION.json').read_bytes())
assert v['passed']==65 and v['failed']==0
assert v['packet']==ref(D/'PACKET.json')
assert v['packet']['sha256']=='32575147e478c63ead51c6269af9e22eebe06ccdc74619cdb04e46231fe9ac82'
for row in v['evidence']:
    assert sha(F/row['repository_relative_path'])==row['sha256']
command_python=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
commands=[dict(argv=[str(command_python),'-I','-B','-S',str(O/name)],exit_status=code,tool_chunk_id=chunk)
    for name,code,chunk in [('verify_native_results.py',1,'974649'),('prepare_verifier_r2.py',0,'615027'),('verify_native_results_r2.py',0,'a138c3')]]
save('VERIFIER-COMMAND-PROVENANCE.json',dict(commands=commands,
    clarification='VERIFIER-REPAIR.json first_command used a basename label. The exact executable and arguments are preserved here from the actual tool calls.',
    first_failure_preserved=True,first_failure_field_cause='Not captured. Complete stat equality exceeded the declared CAS identity contract; no exact stat-field cause is claimed.',
    reviewer_observer_repair_only=True,native_or_test_execution=False))
review=dict(schema_version=1,at=datetime.now(timezone.utc).isoformat(),review_type='Independent Collaborative Review of actual native engineering results',
    reviewer='/root/recovery_join_review20',executor='/root',tool_author='/root/recovery_regression20',
    decision='approved',exit_status=0,packet=v['packet'],candidate_manifest=v['candidate_manifest'],
    scope='Actual R3 native-store18 and native-observer6 terminal results, retirement and separate parent corroboration only',
    verification=ref(O/'VERIFICATION.json'),verification_checks=65,cohorts=v['cohorts'],
    Source_baseline=v['Source_baseline'],accepted_Source352_bytes_unchanged=True,
    actual_execution_receipts_verified=True,actual_Parent_Git_witness_verified=True,
    current_read_only_Source_environment_fixture_native_facts_verified=True,
    proof_limits=v['limits'],remaining_blocking_findings=[],
    existing_issue_classification=[dict(id='R3-NATIVE-EVIDENCE-LIMIT-01',classification='not blocking current task',
        evidence='resource_observer.py:_connection_row records a database path only for an exact str; all19 store SQLite rows have database:null.',
        consequence='The physical closed-object probes support closure; these receipts do not establish an exact SQLite database-path inventory.')],
    preserved_verifier_failure=ref(O/'VERIFIER-REPAIR.json'),verifier_command_provenance=ref(O/'VERIFIER-COMMAND-PROVENANCE.json'),
    skill_used=dict(name='epistemic-status-enforcer',version='0.1.0',governing_version='thirsty-constitution-v0.1'),
    remaining_required_product_gates=['Terminal accepted candidate-full2622 result and independent review',
        'Leased CAS publication of exactly31 Source paths and destination verification',
        'Terminal accepted destination-full2622 and new accepted Source baseline',
        'Separate application startup, intended-interface operation and governed authorization-to-effect evidence'],
    native_test_rerun=False,live_process_handle_or_profile_scan=False,actual_CLI_review_claim=False,
    Source_publication=False,new_Source_accepted=False,full_product_complete=False,
    human_profile_or_no_profile_permission_issued=False)
save('review.json',review)
text='''# Independent Collaborative Review — actual R3 native results

**Decision: approved for the two native engineering evidence gates.** Reviewer `/root/recovery_join_review20`; actual executor `/root`. Binding: packet `32575147e478c63ead51c6269af9e22eebe06ccdc74619cdb04e46231fe9ac82`, Q5 manifest `cce2c8e2c3a31fbedf5c2d83b2d15d499a93030c38ebe0c1e4545b868ef99acf`.

## Verified findings

| Gate | Exact cases | Child lifetime | Child / Root exit | Root execution window (UTC) |
|---|---:|---|---|---|
| native-store | 18 | PID2444, creation134369675927407106 | 0 / 0 | 10:59:43.207330–11:00:30.405365 |
| native-observer | 6 | PID5656, creation134369676303550359 | 0 / 0 | 11:00:18.168592–11:01:06.542235 |

All windows are on 2026-10-20. Every exact case has its passing raw-log entry and expected recorded sequence; failures, errors and skips are empty. Store has the exact alternating 18 START/STOP pairs; observer has the exact expected/executed/stopped six IDs. The cohorts are disjoint.

Each Root command and terminal record matches the reviewed R3 parent launcher and release hash. The actual stdout ends with the exact corroboration reference and child_exit0. Root raw stdout/stderr hashes, create-only launch attempt, child owner PID/creation/image, child terminal bytes and parent corroboration references all match. Both parent retirement snapshots record process, thread, job and startup handles closed, with no primary or retirement error.

The child receipts accurately keep acceptance_complete:false and post-Git corroboration pending. Their separate parent corroborations record the actual default post-verification Git result, Source native facts, full environment commitment, exact native fixture inputs and stable child bytes. The actual source-bound receipt-admission function ASTs accepted both retained receipt pairs using file-only proof readers. No Git subprocess or native operation was rerun by the reviewer.

Fresh file-only checks verified all541 candidate hashes, all12 runner hashes, every Source-before native row and preserved absence, the full E3 environment inventory, current interpreter/base-interpreter/native helper facts, the Git HEAD/ref files and accepted Source352 bytes. The recorded parent Git observation is supported by launch_native.py:48–55, where actual child terminal0 and retirement precede complete default verification. The default verification invokes both Git commands (js9_support.py:104–125).

For store, the retained resource evidence records20 binding owners closed with no pending native resources,19 SQLite objects with the affirmative closed-database probe,4 streams with closed and fileno-denied probes, no remaining captured resources and no remaining threads. The database fields are null for these19 objects; this supports physical closure without providing an exact SQLite-path inventory. This evidence limitation is classified **not blocking this finite native acceptance**.

For observer, the source-bound records identify8 disposable targets and9 observer helpers,17 distinct captured process lifetimes total. All17 process/thread/job handle designations and query exports retired. The custody groups report9 observer custody owners,10 query leases,16 source pins,6 clocks and7 observer owners closed. All six original fixture cleanup receipts have no cleanup failures;9 retained raw observation frames match their byte hashes. The8 target exits are125 and the9 helper exits are0. The OSError and ContractError observation failures appear in deliberate negative cases whose original tests passed; they remain preserved as negative evidence. No forbidden audit events, new threads or candidate hash changes are recorded.

## Limitations and unresolved execution

This is a read-only review of retained actual results, with65 passing verification checks. It performed no test bodies, fixture preparation, native API calls, workers, listeners, profiles, database connections or coordinator transitions. Closure findings are limited to exact captured objects and source-bound retirement/probe records; no current or system-wide process/handle/profile scan occurred.

The native observer receipt intentionally has no exit_status field. Its actual parent child_exit0 and Root terminal0 establish the process result. Both child and parent evidence are required together.

The first reviewer file reader exited1 on whole os.stat_result equality. That comparison included fields outside the declared CAS identity contract; its exact changed field was not captured. The original verifier and failure remain preserved. The successor compares exactly size/mtime/mode/device/inode/attributes and still requires every current Source/E3/helper identity row to match. It passed65checks. This was a reviewer-observer correction, with no product or historical receipt edit.

Candidate-full remains a separate gate. This review establishes no Source publication, destination-full result, installed application startup, successful governed real effect, isolation qualification or whole-product acceptance. No new profile/no-profile authorization is issued, and no actual review-node CLI claim was made.

The finite native engineering gate evidence is accepted. Continue to the exact candidate-full terminal result and independent review, then the leased31-path publication/destination gates.
'''
with (O/'REVIEW.md').open('x',encoding='utf8') as stream:stream.write(text)
save('HANDOFF.json',dict(at=datetime.now(timezone.utc).isoformat(),reviewer=review['reviewer'],decision='approved',scope=review['scope'],
    review=ref(O/'review.json'),report=ref(O/'REVIEW.md'),verification=ref(O/'VERIFICATION.json'),
    verifier_repair=ref(O/'VERIFIER-REPAIR.json'),command_provenance=ref(O/'VERIFIER-COMMAND-PROVENANCE.json'),
    source_scripts={n:ref(O/n) for n in ('verify_native_results.py','prepare_verifier_r2.py','verify_native_results_r2.py','seal_review.py')},
    packet=v['packet'],candidate_manifest=v['candidate_manifest'],Source_publication=False,new_Source_acceptance=False,
    actual_CLI_claim=False,native_test_rerun=False))
print(json.dumps(dict(review=ref(O/'review.json'),report=ref(O/'REVIEW.md'),handoff=ref(O/'HANDOFF.json'))))
