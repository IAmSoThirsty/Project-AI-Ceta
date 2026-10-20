"""Exact release-body DATA_ONLY controls; no real proof or native execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
F=Path(r'T:\00-Active\Project-AI-CETA');R=F/'.agents/runtime/js9-runtime-20261020/successor-r2'
D=F/'.agents/runtime/js9-successor-tools-review-20261020/R2'
p=json.loads((R/'PACKET.json').read_text());packet_ref={'repository_relative_path':(R/'PACKET.json').relative_to(F).as_posix(),'sha256':hashlib.sha256((R/'PACKET.json').read_bytes()).hexdigest()}
node=next(n for n in ast.parse((R/'js9_support.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='require_release')
results=[]
for phase in ('native-store','native-observer','candidate-full','destination-full','publish'):
    release=dict(schema_version=1,executor='/root',run_id=p['run_id'],phase=phase,packet=packet_ref,
      candidate_manifest=p['candidate_manifest'],reviewed_scripts=p['scripts'],case_set=p['case_set'],
      Source_before=p['Source_before'],automatic_retry=False,create_profiles=False,Source_publication=phase=='publish',
      all_conflicting_Source_pinned_runs_released=True,issued_at_ns=90,expires_at_ns=300,
      independent_review='review',native_case_release='native-case',native_store_corroboration='store',native_observer_corroboration='observer')
    review=dict(reviewer='/root/independent_review',author=p['author'],decision='approved',exit_status=0,
      packet=packet_ref,reviewed_scripts=p['scripts'],candidate_manifest=p['candidate_manifest'])
    selected=[];rejected=set()
    def corroborate(reference,required_phase):
        selected.append((reference,required_phase))
        assert reference not in rejected,'CORROBORATION_REJECTED'
    n={'R':R,'RUN':p['run_id'],'AUTHOR':p['author'],'Path':Path,'time':SimpleNamespace(time_ns=lambda:100),
       's':SimpleNamespace(fs=SimpleNamespace(safe_components=lambda path:path)),
       'pinned_json':lambda path,pin:release,'packet':lambda:p,'exact_ref':lambda path:packet_ref,
       'proof':lambda reference:(None,review),'proof_bytes':lambda reference:(R/'releases/native-case',b'no-execution'),
       'require_native_corroboration':corroborate}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(R/'js9_support.py')+'#PURE-RELEASE','exec'),n)
    def check(name,expect):
        selected.clear();error=None
        try:n['require_release'](R/'releases/release','synthetic-pin',phase);allowed=True
        except BaseException as caught:allowed=False;error=type(caught).__name__
        assert allowed is expect,(name,error)
        results.append(dict(name=name,allowed=allowed,expected=expect,corroboration_calls=selected.copy(),error=error,passed=True))
    check(phase+'_complete_admission',True)
    if phase in ('candidate-full','destination-full','publish'):
        assert selected==[('store','native-store'),('observer','native-observer')]
        for key in ('native_store_corroboration','native_observer_corroboration'):
            value=release.pop(key);check(phase+'_missing_'+key,False);release[key]=value
        for value in ('store','observer'):
            rejected.add(value);check(phase+'_failed_'+value,False);rejected.clear()
    else:assert selected==[]
out=dict(status='PASS',scope='Exact require_release AST body with explicit in-memory proof and corroboration transports; no authority issued',controls=results,count=len(results),source_sha256=hashlib.sha256((R/'js9_support.py').read_bytes()).hexdigest())
with (D/'DOWNSTREAM-RELEASE-CONTROLS.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS',controls=len(results))))
