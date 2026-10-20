"""Freeze exact repaired bytes and complete only the actual narrow writer lease."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json
import subprocess

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent
Q=F/'.agents/js9-runtime-20261020';L=R/'repair-r2'
RUN='js9-composition-repair-r2-20261020';ACTOR='/root/recovery_regression20'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def save(path,value):
    with path.open('x',encoding='utf8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')

pre=R/'MANIFEST-PRETEST-R4.json';result_path=R/'controlled_r3/RESULT.json'
m=json.loads(pre.read_bytes());result=json.loads(result_path.read_bytes())
assert result['passed'] and result['tests_run']==45 and result['all_journals_closed']
assert result['candidate_unchanged'] and result['Source352_unchanged']
assert result['runner_sha256']==sha(R/'run_controlled_composition_v2.py')
assert all(sha(Q/name)==pin for name,pin in m['payload_hashes'].items())
assembled=json.loads((R/'ASSEMBLED-INPUTS.json').read_bytes())
changes={}
for name,pin in m['payload_hashes'].items():
    origin=assembled['origins'].get(name)
    before_pin=None if origin is None else origin['sha256']
    if pin==before_pin:continue
    before=[] if origin is None else Path(origin['path']).read_text(encoding='utf8').splitlines()
    if origin is not None:assert sha(Path(origin['path']))==before_pin
    after=(Q/name).read_text(encoding='utf8').splitlines()
    delta=list(difflib.ndiff(before,after))
    category='source' if name.startswith('src/') else 'test' if name.startswith('tests/') else 'contract'
    changes[name]=dict(before_sha256=before_pin,after_sha256=pin,
        physical_lines_added=sum(line.startswith('+ ') for line in delta),
        physical_lines_removed=sum(line.startswith('- ') for line in delta),
        nonblank_lines_added=sum(line.startswith('+ ') and bool(line[2:].strip()) for line in delta),
        category=category)
    diff=''.join(difflib.unified_diff([s+'\n' for s in before],[s+'\n' for s in after],
        fromfile='assembled/'+name,tofile='js9/'+name))
    target=L/('cumulative-'+Path(name).name+'.diff')
    with target.open('x',encoding='utf8',newline='\n') as stream:stream.write(diff)
m.update(at=now(),changes=changes,unchanged_copied_payloads=len(m['payload_hashes'])-len(changes),
    controlled_result=dict(path=str(result_path),sha256=sha(result_path),tests=45,passed=True),
    independent_review='PENDING /root/ac7_native_artifact_review20')
m['prior_repair']=m.pop('repair',None)
m.pop('metadata_successor',None)
m['narrow_repair'].update(test_result=dict(path=str(result_path),sha256=sha(result_path),
    tests=45,passed=True),scope='Preregistered file-open output and existing API-queue enrollment custody')
manifest=R/'MANIFEST-R4.json';save(manifest,m)
terminal=dict(tool_chunk_id='c3d5ac',terminal_exit_status=0,started_at=result['started_at'],
    finished_at=result['finished_at'],observed_process_argv=result['command'],
    interpreter=result['interpreter'],result_sha256=sha(result_path),tests_run=45)
save(R/'TERMINAL-CONTROLLED-R3.json',terminal)
narrow={}
for name in sorted(m['narrow_repair']['changed']):
    old=(L/'before'/name).read_text(encoding='utf8').splitlines(keepends=True)
    new=(Q/name).read_text(encoding='utf8').splitlines(keepends=True)
    diff=''.join(difflib.unified_diff(old,new,fromfile='frozen-r3/'+name,tofile='repaired-r4/'+name))
    target=L/(Path(name).name+'.diff')
    with target.open('x',encoding='utf8',newline='\n') as stream:stream.write(diff)
    narrow[name]=dict(before=sha(L/'before'/name),after=sha(Q/name),diff_sha256=sha(target))
claim=json.loads((L/'LEASE-ACQUIRED.json').read_bytes())['claim']
command="& '"+str(F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe')+"' -B -X utf8 '.agents/runtime/js9-runtime-20261020/run_controlled_composition_v2.py' --attempt controlled_r3 --manifest MANIFEST-PRETEST-R4.json --cases CONTROLLED-CASESET-R4.json"
receipt=L/'implement-receipt.json'
save(receipt,dict(schema_version=1,run_id=RUN,node_id='implement',executor_id=ACTOR,
    started_at=claim['claimed_at'],finished_at=now(),input_hash=claim['input_hash'],
    changed_files=['.agents/js9-runtime-20261020/'+name for name in sorted(narrow)],
    result=dict(manifest=str(manifest),manifest_sha256=sha(manifest),narrow_repair=narrow,
        controlled_result_sha256=sha(result_path),independent_review='PENDING',
        native_execution=False,Source_publication=False),
    commands=[dict(command=command,exit_status=0)],validations=[
        dict(name='45_controlled_cases_45_actual_SQLite_journals_closed',passed=True),
        dict(name='actual_queue_preappend_and_postappend_faults_known_and_unknown_open_custody',passed=True),
        dict(name='all_other528_candidate_pins_and_Source352_preserved_no_native_attempts',passed=True)],
    exit_status=0))
argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
      'node','complete',RUN,'implement',str(receipt),'--runtime-root',str(L)]
completed=subprocess.run(argv,cwd=F,capture_output=True)
for suffix,raw in [('stdout',completed.stdout),('stderr',completed.stderr)]:
    with (L/('implement-complete.'+suffix)).open('xb') as stream:stream.write(raw)
response=json.loads(completed.stdout.decode('utf-8-sig'))
save(L/'implement-complete.json',dict(command=argv,exit_status=completed.returncode,response=response))
assert completed.returncode==0 and response['allowed'] is True,response
print(json.dumps(dict(manifest_sha256=sha(manifest),result_sha256=sha(result_path),
    implement_receipt_sha256=sha(receipt),narrow=narrow,
    cumulative_source_added=sum(v['physical_lines_added'] for v in changes.values() if v['category']=='source'),
    cumulative_source_removed=sum(v['physical_lines_removed'] for v in changes.values() if v['category']=='source'),
    test_lines_added=sum(v['physical_lines_added'] for v in changes.values() if v['category']=='test')),
    indent=2),flush=True)
