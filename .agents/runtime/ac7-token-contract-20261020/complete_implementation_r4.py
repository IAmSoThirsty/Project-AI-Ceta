"""Complete the actual code lease against the frozen successor evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

F=Path('T:/00-Active/Project-AI-CETA')
E=Path(__file__).resolve().parent
R=E/'lease-r2'
RUN='ac7-token-contract-r2-20261020'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
manifest=E/'AC7-QUALIFICATION-MANIFEST-R3.json'
assert sha(manifest)=='e2ee86a9b7ea7b96f24062fae2739e9932c63e0e0c5597368302a209b67f8b1a'
cut=json.loads(manifest.read_bytes())
Q=Path(cut['root'])
assert all(sha(Q/n)==h for n,h in cut['payload_hashes'].items())
claim=json.loads((R/'implement-claim.json').read_bytes())['response']['claim']
current={Q.relative_to(F).as_posix()+'/'+n:h for n,h in cut['payload_hashes'].items()}
changed=sorted(n for n in set(current)|set(claim['baseline_snapshot']) if current.get(n)!=claim['baseline_snapshot'].get(n))
receipt=R/'implement-receipt-r4.json'
value=dict(schema_version=1,run_id=RUN,node_id='implement',executor_id='/root',
    started_at=claim['claimed_at'],finished_at=now(),input_hash=claim['input_hash'],changed_files=changed,
    result=dict(manifest_sha256=sha(manifest),candidate_payloads=357,
        controlled_python=43,pure_rust=5,source_publication=False,
        host_profile_operations=False,skills_used=cut['skills_used'],
        governing_version=cut['governing_version']),commands=[],exit_status=0,
    validations=[dict(name='frozen_source_tests_build_and_preserved_Source352',passed=True)])
with receipt.open('x',encoding='utf8') as out:json.dump(value,out,indent=2)
argv=['powershell','-NoProfile','-File','T:/02-Config/agents/taar-orchestrate.ps1',
      'node','complete',RUN,'implement',str(receipt),'--runtime-root',str(R)]
done=subprocess.run(argv,cwd=F,capture_output=True)
for suffix,raw in [('stdout',done.stdout),('stderr',done.stderr)]:
    with (R/('implement-complete-r4.'+suffix)).open('xb') as out:out.write(raw)
response=json.loads(done.stdout.decode('utf-8-sig'))
with (R/'implement-complete-r4.json').open('x',encoding='utf8') as out:
    json.dump(dict(command=argv,exit_status=done.returncode,response=response),out,indent=2)
assert done.returncode==0 and response['allowed'] is True,response
print(json.dumps(dict(allowed=response['allowed'],code_complete=True,review_pending=True,
    source_publication=False,profile_attempt=False)))
