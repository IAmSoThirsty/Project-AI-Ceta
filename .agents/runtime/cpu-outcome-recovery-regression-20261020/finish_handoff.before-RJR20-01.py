"""Package finite verification evidence after the confirmed run is terminal."""
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json
F=Path('T:/00-Active/Project-AI-CETA')
R=Path(__file__).resolve().parent
A=R/'attempt-r2'
O=F/'.agents/runtime/cpu-outcome-recovery-20261017'
Q=F/'.agents/cpu-outcome-recovery-20261017'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=lambda p:dict(path=str(p),sha256=sha(p))
result=json.loads((A/'regression-r1/RESULT.json').read_bytes())
outer=json.loads((A/'OUTER-RESULT.json').read_bytes())
old=json.loads((R/'ATTEMPT1-DIAGNOSIS.json').read_bytes())
assert result['tests_run']==169 and outer['exact_original169_sequence']
assert all(sha(R/name)==pin for name,pin in old['first_attempt']['evidence'].items())
assert outer['candidate_unchanged'] and outer['Source_unchanged']
rows=[]
for test_id in result['expected_ids']:
    module,cls,method=test_id.split('.')
    path=Q/'tests/contract'/(module+'.py')
    tree=ast.parse(path.read_bytes())
    definition=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    unit=next(n for n in definition.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==method)
    failures=[v for v in result['failures']+result['errors'] if v['id']==test_id or v['id'].startswith(test_id+' ')]
    rows.append(dict(id=test_id,source_path=str(path),source_sha256=sha(path),line=unit.lineno,
        test_class=cls,writer='/root/full_report_repair',verifier='/root/recovery_regression20',
        proof='existing controlled regression test body executed unchanged, with actual canonical SQLite',
        result='FAIL' if failures else 'PASS',failure_entries=len(failures),
        canonical_component_ownership='No architecture owner or requirement acceptance is reassigned by this verification.'))
passed=outer['exit_status']==0 and result['exit_status']==0 and not result['failures'] and not result['errors']
record=dict(at=datetime.now(timezone.utc).isoformat(),actor='/root/recovery_regression20',role='ROLE-09 Verifier',coordinator='/root',
    claim='The exact original controlled169 cohort passes against frozen recovery cut-r3 after the authorized one-method timing fixture correction.',
    state='VERIFIED_WITHIN_STATED_LIMITS' if passed else 'FAILED',
    project=str(F),candidate=str(Q),manifest=ref(O/'cut-r3/MANIFEST.json'),original_handoff=ref(O/'HANDOFF.json'),
    changed_product_files=[],source_publication=False,requirements_closed_by_this_job=[],
    effect='This receipt resolves only the missing corrected169 regression evidence. Integration and full-product acceptance remain with Root.',
    subject_source_payloads=outer['candidate_payloads'],accepted_Source_payloads=outer['Source_payloads'],
    command=outer['command'],started_at=outer['started_at'],finished_at=outer['finished_at'],pid=outer['pid'],
    result=ref(A/'regression-r1/RESULT.json'),outer_result=ref(A/'OUTER-RESULT.json'),raw=ref(A/'regression-r1/RAW.txt'),
    before=ref(A/'BEFORE.json'),events=ref(A/'EVENTS.jsonl'),command_record=ref(A/'COMMAND.json'),
    prior_failed_attempt=ref(R/'ATTEMPT1-DIAGNOSIS.json'),
    observer_repair=ref(R/'OBSERVER-REPAIR.diff'),pure_checks=ref(R/'OBSERVER-REPAIR-PURE-CHECKS.json'),
    distinct_observer_review=ref(F/'.agents/runtime/cpu-outcome-recovery-review-20261020/OBSERVER-PURE-REVIEW.json'),
    original_gates_self_check=ref(R/'HARNESS-SELF-CHECK.json'),
    source_unchanged=outer['Source_unchanged'],candidate_unchanged=outer['candidate_unchanged'],
    exact_original169_sequence=outer['exact_original169_sequence'],coverage=rows,exclusions=result['excluded_ids'],
    tests_run=result['tests_run'],failures=len(result['failures']),errors=len(result['errors']),skips=result['skips'],
    sqlite_lifetimes=len(result['sqlite_lifetimes']),
    all_sqlite_closed=all(v['closed'] and v['refusal']=='closed connection refusal' and not v['retained_capacity'] for v in result['sqlite_lifetimes']),
    residual_threads=outer['residual_threads'],prohibited_operations=result['prohibited_operations'],scope_violations=outer['scope_violations'],
    terminal_session=dict(exec_session_id=88449,result='Root must bind the separately observed terminal command exit to this file.'),
    limitations=outer['limits'],
    independence='I authored the runner adaptation and outer observer, while preserving frozen product/test bodies. A separate reviewer reviewed the observer before Root released this fresh run. Final result and implementation acceptance require that reviewer/Root to inspect the records; this receipt does not self-certify independent approval.',
    remaining=[dict(classification='requires separate follow-up work',issue='Joint integration with independently frozen retainer/capacity/observer/provenance and actual native Windows qualification remain outstanding.'),
        dict(classification='requires separate follow-up work',issue='Original subprocess crash case remains excluded; RE-T25/26 surviving custody, durable Stop/checkpoint, restart, ambiguous native release and restoration remain within original handoff limitations.'),
        dict(classification='not blocking current verification',issue='The first attempt failed in the author-added URI observer. It remains immutable and is not counted as product evidence.')],
    next_action='Distinct reviewer inspects this terminal result and frozen implementation, Root determines whether the regression blocker is closed and integrates through the canonical publication process.')
with (R/'HANDOFF.json').open('x',encoding='utf8') as s:json.dump(record,s,indent=2);s.write('\n')
print(json.dumps(dict(state=record['state'],handoff=ref(R/'HANDOFF.json'),tests=record['tests_run'],failures=record['failures'],errors=record['errors'],sqlite=record['sqlite_lifetimes'])))
