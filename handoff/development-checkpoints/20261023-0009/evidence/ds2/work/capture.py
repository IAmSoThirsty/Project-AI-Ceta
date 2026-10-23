"""Create-only actual work-local process capture."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,subprocess,sys,time
W=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('script');p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args()
script=(W/a.script).resolve();assert script.is_relative_to(W) and script.is_file()
command=[sys.executable,'-B','-X','utf8',str(script),*a.arguments]
started=datetime.now(timezone.utc).isoformat();tick=time.perf_counter_ns();result=subprocess.run(command,cwd=W,capture_output=True)
for suffix,raw in (('stdout',result.stdout),('stderr',result.stderr)):
    with (W/(a.label+'.'+suffix)).open('xb') as stream:stream.write(raw)
record=dict(command=command,cwd=str(W),started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),elapsed_ns=time.perf_counter_ns()-tick,exit_status=result.returncode)
with (W/(a.label+'-PROCESS.json')).open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(record));raise SystemExit(result.returncode)
