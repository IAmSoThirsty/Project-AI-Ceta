"""Preserve the already completed failing case while the full suite continues."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
F=Path('T:/00-Active/Project-AI-CETA');D=F/'.agents/runtime/js9-runtime-20261020/successor-r3'
Q=F/'.agents/js9-runtime-r5-20261020';O=Path(__file__).resolve().parent
case='test_native_effect_observer.NativeEffectObserverTests.test_actual_overlong_native_pipe_output_is_rejected_and_retired'
path=D/'candidate-full/CASE-EVENTS.jsonl'
lines=[line for line in path.read_text(encoding='utf8').splitlines() if case in line]
events=[json.loads(line) for line in lines]
assert [row['event'] for row in events]==['PREPARE','START','FAILURE','STOP']
assert all(row['test_id']==case for row in events)
assert 'OBSERVER_OUTPUT_OVERLONG' in events[2]['traceback'] and 'OBSERVER_PROCESS_TIMEOUT' in events[2]['traceback']
def ref(p):return dict(repository_relative_path=p.relative_to(F).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
record=dict(at=datetime.now(timezone.utc).isoformat(),status='PROVISIONAL_CASE_FAILURE_FULL_RUN_NOT_TERMINAL',
    reviewer='/root/recovery_join_review20',case=case,events=events,
    live_source_path=str(path),captured_case_lines_sha256=hashlib.sha256(('\n'.join(lines)+'\n').encode()).hexdigest(),
    frozen_source=ref(Q/'src/ceta/effects/native_observer.py'),original_test=ref(Q/'tests/contract/test_native_effect_observer.py'),
    packet=ref(D/'PACKET.json'),preflight=ref(D/'candidate-full/PREFLIGHT.json'),
    early_original_case_proof=ref(D/'candidate-full/NATIVE-CASE-EARLY-PROOF.json'),
    source_analysis=dict(deadline_created_at='observe:421-422 before _exchange pipe creation/launch/write',
        deadline_checked_at='_exchange:360 before PeekNamedPipe:364, output bound:370 and process poll:376',
        transport_state_initialized_at='_exchange:356-357 after WriteFile and input closure',
        test_maximum_duration_ns=1_000_000_000,test_required_error='OBSERVER_OUTPUT_OVERLONG'),
    established='The exact original test failed on timeout versus its required overlong-output rejection.',
    hypotheses=['Budget may have expired before the first completed poll; final transport_state is required.'],
    unresolved=['Where time was spent between deadline creation and transport loop.',
        'Final failure count, complete native retirement and full terminal result.'],
    no_wait_before_drain_claim=True,Source_publication_accepted=False,full_candidate_accepted=False,
    native_or_test_rerun=False,deadline_or_test_change=False,actual_review_CLI_claim=False)
with (O/'PROVISIONAL-OBSERVER-FAILURE.json').open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(dict(output=ref(O/'PROVISIONAL-OBSERVER-FAILURE.json'),events=len(events),terminal_acceptance=False)))
