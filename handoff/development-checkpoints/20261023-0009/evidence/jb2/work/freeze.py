"""Fresh frozen successor, preserving the entire rejected JB1 work/review cut."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,hashlib,json,subprocess
F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent;B=W.parent;OLD=B.parent/'jb1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):
    with (W/name).open('x',encoding='utf8') as stream:json.dump(v,stream,indent=2);stream.write('\n')
def git(*args):
    p=subprocess.run(['git','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=F,capture_output=True)
    assert p.returncode==0;return p.stdout
j=json.loads((B/'packet/INPUTS.json').read_bytes());before=json.loads((W/'CANONICAL-BEFORE.json').read_bytes());prior=json.loads((W/'PRIOR-REJECTED-JB1.json').read_bytes())
for rel,pin in prior['files'].items():assert sha(OLD/rel)==pin['sha256'] and (OLD/rel).stat().st_size==pin['bytes'],rel
canonical_delta=[]
for rel,pin in before['files'].items():
    p=F/rel;actual=dict(sha256=sha(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)
    if actual!=pin:canonical_delta.append(dict(path=rel,before=pin,after=actual))
assert not canonical_delta,('CANONICAL_DELTA_REQUIRES_FRESH_ROOT_BINDING',canonical_delta)
assert sha(F/'.git/index')==before['Git']['index_sha256']
for name,args in dict(head=('rev-parse','HEAD'),branch=('symbolic-ref','HEAD'),origin=('remote','get-url','origin')).items():assert git(*args).decode()==before['Git'][name]
assert hashlib.sha256(git('status','--porcelain=v1','--untracked-files=all')).hexdigest()==before['Git']['status_sha256']
save('CONSERVATION.json',dict(canonical_inputs=len(before['files']),exact_bytes_sizes_mtimes_unchanged=True,
    canonical_delta=canonical_delta,Git_HEAD_branch_origin_status_index_unchanged=True,
    rejected_JB1_files_preserved=len(prior['files']),rejected_JB1_review_remains_FAILED=True,
    fixture_writes='None admitted by the work-only audit and forbidden native/process/socket controls; no new whole-fixture baseline claim'))
report=json.loads((W/'CONTROLS-FINAL.json').read_bytes());assert report['successful'] and json.loads((W/'CONTROLS-FINAL-PROCESS.json').read_bytes())['exit_status']==0
assert report['selected']==report['started']==report['stopped'] and not any(report[k] for k in ('failures','errors','skips','expected_failures','unexpected_successes','forbidden_call_attempts'))
old_controls=json.loads((OLD/'work/JOINT-CONTROLS-R3.json').read_bytes());assert len(old_controls['selected'])==112
assert set(old_controls['selected'])<=set(report['selected'])
save('CONTROL-COVERAGE.json',dict(total=report['tests_run'],retained_112_ids=old_controls['selected'],
    new_ids=sorted(set(report['selected'])-set(old_controls['selected'])),prior_success_does_not_override_JB1_rejection=True))
parsed=[]
for p in sorted(W.rglob('*.py')):ast.parse(p.read_text(encoding='utf8'),filename=str(p));parsed.append(p.relative_to(W).as_posix())
save('STATIC-CHECKS.json',dict(parsed_files=parsed,unchanged_admission_source_sha256=sha(F/'src/ceta/kernel/cpu_execution.py'),
    admission_bound_ns=50_000_000,unchanged_driver_translation_sha256=sha(F/'src/ceta/effects/native_cpu_binding.py')))
paths=[p.relative_to(W/'candidate').as_posix() for p in (W/'candidate').rglob('*') if p.is_file()]
diff=[];deltas={}
for rel in sorted(paths):
    original=W/'seed-before'/rel
    deltas[rel]=dict(canonical_sha256=sha(F/rel),seed_sha256=sha(original),candidate_sha256=sha(W/'candidate'/rel))
    diff.extend(difflib.unified_diff(original.read_text(encoding='utf8').splitlines(keepends=True),
        (W/'candidate'/rel).read_text(encoding='utf8').splitlines(keepends=True),fromfile='seed/'+rel,tofile='candidate/'+rel))
with (W/'CANDIDATE.diff').open('x',encoding='utf8',newline='') as stream:stream.writelines(diff)
save('SOURCE-DELTA.json',dict(files=deltas,canonical_writes=False,old_rejected_candidate_unchanged=True,
    native_execution=False,AC7_replay=False,full_product_acceptance=False))
external={str(B/'packet/INPUTS.json'):sha(B/'packet/INPUTS.json'),str(B/'packet/PLAN.md'):sha(B/'packet/PLAN.md')}
for rel,pin in j['source_pins'].items():assert sha(F/rel)==pin;external[str(F/rel)]=pin
amendment_path=B/'control/OWNER-CONSUMER-INPUT-AMENDMENT.json'
assert sha(amendment_path)=='6ea1f1e8384d2377ce27285c94dc7048a8b6ceb4f645eb45fe07aeadf541c920'
assert (W/'OWNER-CONSUMER-INPUT-AMENDMENT.json').read_bytes()==amendment_path.read_bytes()
amendment=json.loads(amendment_path.read_bytes());extra=amendment['additional_canonical_source']
assert sha(F/extra['repository_relative_path'])==extra['sha256']
assert set(paths)==set(j['source_pins'])|{extra['repository_relative_path']}
external[str(amendment_path)]=sha(amendment_path)
external[str(F/extra['repository_relative_path'])]=extra['sha256']
for rel,pin in report['unchanged_dependencies'].items():assert sha(F/rel)==pin;external[str(F/rel)]=pin
for rel,pin in prior['files'].items():external[str(OLD/rel)]=pin['sha256']
for p in (B/'packet').iterdir():
    if p.is_file():external[str(p)]=sha(p)
files={p.relative_to(W).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(W.rglob('*')) if p.is_file()}
save('MANIFEST.json',dict(schema_version=1,run_id=j['run_id'],recorded_at=datetime.now(timezone.utc).isoformat(),
    graph_fingerprint=j['graph_fingerprint'],files=files,external_pins=external,controls=report['tests_run'],
    candidate_inputs=len(paths),additional_input_authority_sha256=sha(amendment_path),
    independent_approval=False,full_product_acceptance=False,
    permitted_postfreeze_outputs=['FREEZE-PROCESS.json','FREEZE.stdout','FREEZE.stderr','PREPARED-PROCESS.json','PREPARED.stdout','PREPARED.stderr',
        'AUTHOR-COMPLETION-RECEIPT.json','AUTHOR-COMPLETE-PROCESS.json','AUTHOR-COMPLETE.stdout','AUTHOR-COMPLETE.stderr']))
print(json.dumps(dict(manifest_sha256=sha(W/'MANIFEST.json'),files=len(files),controls=report['tests_run'],canonical_inputs=len(before['files']))))
