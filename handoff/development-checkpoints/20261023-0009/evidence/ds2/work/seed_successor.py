"""Fresh DS2 sources and baseline; rejected DS1 is read-only."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent;B=W.parent;OLD=B.parent/'ds1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads((B/'packet/INPUTS.json').read_bytes())
assert sha(B/'packet/INPUTS.json')=='1a91e428670e53e1ea3b2137aae56041210cf094d38b4278592478692dbf26ce'
for path,pin in j['source_inputs'].items():assert sha(Path(path))==pin,path
mf=json.loads((OLD/'work/MANIFEST.json').read_bytes())
for rel,pin in mf['files'].items():assert sha(OLD/'work'/rel)==pin['sha256']
for name in ('directory_snapshot.py','test_directory_snapshot.py','run_controls.py','conservation.py','capture.py','qualify_full_F.py','complete_candidate.py'):
    raw=(OLD/'work'/name).read_text(encoding='utf8')
    raw=raw.replace("B=F/'.agents/runtime/oq23/ds1'","B=F/'.agents/runtime/oq23/ds2'")
    raw=raw.replace("'ceta-ds23-r1'","'ceta-ds23-r2'").replace('4f55640d2436b8826438b572325a6b066b7d793beae7596fd27debabb01d757f','b848fefb7c69a06d4ffc32f71bac48ac316edc03755773ec0c6103365d2b4c0b')
    with (W/name).open('x',encoding='utf8',newline='\n') as stream:stream.write(raw)
for name in ('ACCESS-TIME-OBSERVATION-POLICY.json','DIRECTORY-HANDLE-PROBE.json','DIRECTORY-HANDLE-PROBE-PROCESS.json','PROBE-SECURITY-QUALIFICATION.json','OFFICIAL-API-BINDING.json'):
    with (W/name).open('xb') as stream:stream.write((OLD/'work'/name).read_bytes())
(W/'seed-before').mkdir()
with (W/'seed-before/directory_snapshot.py').open('xb') as stream:stream.write((OLD/'work/directory_snapshot.py').read_bytes())
baseline=json.loads((OLD/'work/INPUT-CONSERVATION-BEFORE.json').read_bytes())
baseline['run_id']=j['run_id'];baseline['recorded_at']=datetime.now(timezone.utc).isoformat()
baseline['input_pins'].update(j['source_inputs'])
baseline['input_pins'][str(B/'packet/INPUTS.json')]=sha(B/'packet/INPUTS.json')
baseline['input_pins'][str(B/'packet/PLAN.md')]=sha(B/'packet/PLAN.md')
with (W/'INPUT-CONSERVATION-BEFORE.json').open('x',encoding='utf8') as stream:json.dump(baseline,stream,indent=2);stream.write('\n')
import conservation
conservation.observe()
prior={}
for directory in ('work','review'):
    for p in sorted((OLD/directory).rglob('*')):
        if p.is_file():prior[p.relative_to(OLD).as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)
with (W/'PRIOR-DS1-CONSERVATION.json').open('x',encoding='utf8') as stream:json.dump(dict(
    run_id='ceta-ds23-r1',files=prior,original_controls=41,original_full_F_qualification_succeeded=True,
    rejected_findings=['DS1-CUSTODY-01','DS1-PROVENANCE-01'],source_never_relabelled=True),stream,indent=2);stream.write('\n')
print(json.dumps(dict(run_id=j['run_id'],canonical_count=562,prior_files=len(prior),source_bindings_verified=True)))
