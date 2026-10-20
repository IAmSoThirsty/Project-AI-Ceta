"""Bind and claim one isolated CPB1 candidate; no active Source mutations."""
from pathlib import Path
import json, subprocess, sys
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cpb1-20261014';R=P/'.agents/runtime/cpb1-20261014';RUN='cpb1-20261014'
sys.path.insert(0,str(P/'.agents/runtime/ka1-20261014'));import ka1_support as s
s.Q=Q;s.R=R;s.RUN=RUN
sys.path.insert(0,str(P/'.agents/runtime/re-foundation3-20261014'));import foundation_support as copier
copier.Q=Q;copier.R=R
assert not Q.exists();Q.mkdir()
s.invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN],'run-init')
s.claim('discover')
accepted=P/'.agents/runtime/perf1-20261014/active-application/destination-full-r1.json'
assert s.sha(accepted)=='428c4edff050dc130dfe64e15becff1d9167eb6697687e47c208657d7bbf30c4'
pins=json.loads(accepted.read_text())['after_hashes'];source={name:s.ordinary(P/name) for name in pins}
assert len(source)==290 and all(row['sha256']==pins[name] for name,row in source.items())
parents=[('wt4-20261014','0baf97141b6eb9abc2721a4d4a9fe3ce8e9bfa82cb1e4131ca2860fa524bbb57',
    '.agents/runtime/wt4-20261014/independent-root-review/review.json','0669add2e148151469bb0cbc2e3eeb6c6c72671e67cab467bba2763bc69e9db0',[
    'src/ceta/contracts/workload_throttling.py','src/ceta/supervisor/windows_jobs.py',
    'tests/contract/test_workload_throttling.py','tests/contract/test_windows_throttling.py','contracts/WORKLOAD_THROTTLING_V1.md']),
 ('nc2-20261014','8309104c8a637b628ec40c633df6d840a882b5d8a5b1cde238c7fb11158dac3e',
    '.agents/runtime/nc2-20261014/independent-root-review/review.json','fd5928ded7caef33d10962785aa56ac4ba8c57660e331d073bf796aed3f4cc63',[
    'src/ceta/identity/native_clock.py','tests/contract/test_native_session_clock.py','contracts/NATIVE_SESSION_CLOCK_V1.md']),
 ('rc2-20261014','f1aa5a08bd23a0ffd62f3297d31ee130e45634c23804eb76b74ee71c68d100fb',
    '.agents/runtime/rc2-20261014/qualification-r2/independent-root-review/review.json','e457dc12fda7f9b8bbccc82ce73b3fabb940fb452fba3f484332e64296af162a',[
    'src/ceta/contracts/real_effect.py','tests/contract/test_real_effect_contract.py','contracts/REAL_EFFECT_V1.md'])]
dependencies={};parent_records=[]
for name,manifest_sha,review_path,review_sha,paths in parents:
    base=P/'.agents'/name;manifest=base/'TRANSFER-MANIFEST.json';review=P/review_path
    assert s.sha(manifest)==manifest_sha and s.sha(review)==review_sha
    proof=json.loads(review.read_text());assert proof['decision']=='approved' and proof['exit_status']==0
    payloads=json.loads(manifest.read_text())['payloads']
    if isinstance(payloads,list):payloads={row['relative_path']:row for row in payloads}
    selected={}
    for relative in paths:
        row=s.ordinary(base/relative);expected=payloads[relative]
        assert row['sha256']==expected.get('candidate_sha256',expected.get('sha256'))
        assert row['native_identity']==expected.get('candidate_native_identity',expected.get('native_identity'))
        dependencies[relative]=row;selected[relative]=row
    parent_records.append(dict(name=name,manifest=s.reference(manifest),approved_review=s.reference(review),selected=selected))
comparison=P/'.agents/runtime/real-effect-20261014/ACTUAL-WINDOWS-CLOCK-COMPARISON.json'
plan=P/'.agents/runtime/real-effect-20261014/plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md'
assert s.sha(plan)=='d99cbc87dd5430b6287b3a77759fd75b8cdb0276a372c9a4cca8ba1bc047119c'
eligible=['src/ceta/effects/native_cpu_binding.py','tests/contract/test_native_cpu_binding.py','contracts/NATIVE_CPU_BINDING_V1.md']
assert all(not (P/name).exists() and name not in dependencies for name in eligible)
s.write_new(R/'SOURCE-INPUTS.json',dict(recorded_at=s.utc(),Source290=source,parents=parent_records,
    dependency_files=dependencies,accepted_Source=s.reference(accepted),clock_comparison=s.reference(comparison),
    approved_plan=s.reference(plan),python_image=s.ordinary(s.PY),
    HEAD=s.fs.text_git(P,'rev-parse','HEAD'),branch=s.fs.text_git(P,'branch','--show-current'),
    tracked_status=s.fs.text_git(P,'status','--porcelain=v1','-uno'),
    prior_read_probe_error='A read-only guessed test_windows_cpu_rate.py path did not exist; actual test_windows_throttling.py was located. No product failure or edits.',
    author_prior_dependency='Author wrote NC2/RC2; rely on exact distinct Root approved reviews, reuse has zero newLOC.'))
command=subprocess.list2cmdline([str(s.PY),'-B','-X','utf8',str(Path(__file__))])
s.complete('discover',dict(source_inputs=s.reference(R/'SOURCE-INPUTS.json'),Source_count=290),
    [dict(command=command,exit_status=0)],[('Exact current Source290 and reviewed dependencies inspected',True)])
s.claim('plan')
s.write_new(R/'TASK-BINDING.json',dict(recorded_at=s.utc(),job=RUN,author=s.ACTOR,coordinator='/root',
    roles=['R02 implementation','R18 acceptance','R19 verification','R20 hostile self-review'],
    candidate=str(Q),runtime=str(R),eligible_paths=eligible,source_application=False,
    objective='RE-S5 observation-only same-worker native session-clock/driver policy bridge with conservative bounded timing translation.',
    public_API=['NativeCpuBinding.capture','NativeCpuBinding.require_current','NativeCpuBinding.driver_arguments','NativeCpuBinding.cancel','NativeCpuBinding.close'],
    requirements=['Original driver timestamps preserved','Native bracketing and private capture identity',
        'Actual owned-job query/version/lifetime currentness','Conservative clock-domain/deadline/age/duration translation',
        'Unavailable/rollback/resume/stale/overlong/expiry/cancellation rejection','Borrowed target and clock never closed by binding'],
    prohibited=['Source/E3/previous-evidence modifications','Native CPU Set/apply/restore','AppContainer profiles or isolation launch','Hello','Authority/store/issuer/scheduler creation'],
    tests='Domain-negative and concurrency tests; actual own disposable medium workers and clock registrations for policy queries only. Relevant WT4 observation and RC2/NC2 contracts; no native Set tests admitted.',
    ownership='Only three CREATE paths; existing Source and approved dependency bytes REUSE, no stale overlay publication.',
    review='Separate Root-assigned reviewer after exact implement release; author proof is self-review only.',
    template_refs=[s.reference(P/'.local-build-cache/subagent-templates-20261011'/n) for n in ('COMMON_CONTRACT.md','TASK_BINDING.md','HANDOFF_RECORD.md')]))
s.complete('plan',dict(binding=s.reference(R/'TASK-BINDING.json'),eligible_paths=eligible),
    [dict(command=command,exit_status=0)],[('One additive observation-only bridge; no native Set or authority',True)])
claim=s.claim('implement');assert claim['baseline_snapshot']=={}
staged={}
for relative,row in sorted(source.items()):staged[relative]=copier.bytes_copy(P/relative,Q/relative,row)
for relative,row in sorted(dependencies.items()):
    if (Q/relative).exists():
        before=R/'before'/relative;before.parent.mkdir(parents=True,exist_ok=True)
        s.fs.write_new(before,s.fs.read_bytes(Q/relative))
        raw=s.fs.read_bytes(Path(row['path']));assert s.digest(raw)==row['sha256']
        (Q/relative).write_bytes(raw)
        staged[relative]=s.ordinary(Q/relative)
    else:staged[relative]=copier.bytes_copy(Path(row['path']),Q/relative,row)
s.write_new(R/'IMPLEMENTATION-STARTED.json',dict(recorded_at=s.utc(),claim=claim,staged_payloads=staged,
    eligible_paths=eligible,reused_LOC_credit=0,Source290_retained=all(s.ordinary(P/n)==r for n,r in source.items())))
print(json.dumps(dict(implement_claimed=True,staged_payloads=len(staged),Source290_retained=True,eligible=eligible)),flush=True)
