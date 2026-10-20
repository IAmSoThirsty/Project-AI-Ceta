"""Freeze the native code/environment binding implementation for peer review."""
from pathlib import Path
import ast,json,sys
R=Path(__file__).resolve().parent;F=R.parents[2];Q=F/'.agents/cb1-20261014'
sys.path.insert(0,str(F/'.agents/runtime/en1-20261014'));import en1_support as s
s.Q=Q;s.R=R;s.RUN='cb1-20261014';s.ACTOR='/root'
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());proof=json.loads((R/'author-r1/RESULT.json').read_text())
assert proof['tests_run']==16 and proof['exit_status']==0 and proof['failures']==proof['errors']==proof['skips']==0
assert proof['candidate_before']==proof['candidate_after'] and proof['Source_before']==proof['Source_after']==inputs['Source290']
assert not proof['remaining_threads'] and all(row['all_bindings_closed'] for row in proof['native_receipts'])
eligible=['src/ceta/identity/native_code_binding.py','tests/contract/test_native_code_binding.py','contracts/NATIVE_CODE_BINDING_V1.md']
dependency='src/ceta/supervisor/isolated_worker.py';names=sorted(set(inputs['Source290'])|{dependency}|set(eligible));assert len(names)==294
rows=[];loc={}
for name in names:
    facts=s.ordinary(Q/name)
    if name in inputs['Source290']:
        assert s.ordinary(F/name)==inputs['Source290'][name] and facts['sha256']==inputs['Source290'][name]['sha256']
    if name==dependency:assert facts==inputs['uncredited_dependency']['copy']
    if name.endswith('.py'):ast.parse((Q/name).read_text(),filename=name)
    rows.append({'relative_path':name,'candidate_sha256':facts['sha256'],'candidate_native_identity':facts['native_identity'],
        'classification':'CREATE' if name in eligible else 'UNCREDITED_DEPENDENCY' if name==dependency else 'REUSE'})
for name in eligible:
    lines=(Q/name).read_text().splitlines()
    loc[name]={'physical_lines':len(lines),'nonblank_noncomment_lines':sum(bool(line.strip()) and not line.lstrip().startswith(('#','//')) for line in lines)}
s.write_new(Q/'TRANSFER-MANIFEST.json',{'schema_version':1,'at':s.utc(),'author':'/root','payload_count':294,
 'payloads':rows,'eligible_application_paths':eligible,'Source290':inputs['Source290'],
 'uncredited_dependency':inputs['uncredited_dependency'],'tests':s.reference(R/'author-r1/RESULT.json'),
 'Source_application':False,'authority_accepted':False,'LOC':loc})
s.write_new(R/'SELF-REVIEW.json',{'at':s.utc(),'author':'/root','independent_review':False,
 'manifest':s.reference(Q/'TRANSFER-MANIFEST.json'),'verified':[
  'Read all new source/tests/contract and reused native image hashing, path checks and duplicate-fenced cleanup call sites.',
  'Finite manifest requires both groups, bounded paths/file count/bytes, duplicate rejection, expected hashes and ordinary retained file/ancestor objects.',
  'Actual Windows write/delete/replace/ancestor rename denials, full native file identities and same-byte-new-object changed commitment are exercised.',
  'Final private lease fence has no native I/O/clock/store/issuer callback, requires exact retained owner, same thread and live cancellation latch.',
  'Close invalidates first, refuses active or foreign-thread retirement, retains recoverable handles and preserves primary control exceptions.',
  'Sixteen tests pass, all recorded bindings close, no new threads remain and Source290/candidate294 native payloads are conserved.'],
 'limits':['Trusted composition must provide a complete approved manifest; the library does not discover or authorize arbitrary code.',
  'Only retained object observations are qualified here. Source/runtime admission, genuine approval, OS isolation, effect and settlement remain separate.'],
 'LOC':loc})
s.complete('implement',{'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'tests_run':16,'LOC':loc,
 'eligible_application_paths':eligible,'self_review':s.reference(R/'SELF-REVIEW.json')},
 [{'command':str(s.PY)+' -B -X utf8 '+str(R/'run_tests.py')+' author-r1','exit_status':0}],
 [('native_pin_and_retained_lease_cases_pass_with_complete_known_closure',True)])
assert json.loads((R/s.RUN/'claims.json').read_text())=={}
print(json.dumps({'manifest_sha256':s.sha(Q/'TRANSFER-MANIFEST.json'),'implement_sha256':s.sha(R/'implement.json'),'tests':16,'LOC':loc}),flush=True)
