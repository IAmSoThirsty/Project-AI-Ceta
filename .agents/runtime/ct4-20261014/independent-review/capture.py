"""Append-only evidence for a reviewer-owned Python command."""
from ct4_support import *
label=sys.argv[1];target=V/sys.argv[2]
assert target.is_file() and target.is_relative_to(V) and '/' not in label and '\\' not in label
argv=[str(PY),'-B','-X','utf8',str(target),*sys.argv[3:]]
started=utc()
done=subprocess.run(argv,cwd=F,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
for suffix,data in [('stdout.txt',done.stdout),('stderr.txt',done.stderr)]:
    with (V/(label+'.'+suffix)).open('xb') as out:out.write(data)
save(V/(label+'-command.json'),{'argv':argv,'started_at':started,'finished_at':utc(),'exit_status':done.returncode,
    'stdout':ref(V/(label+'.stdout.txt')),'stderr':ref(V/(label+'.stderr.txt'))})
print(done.stdout.decode('utf-8-sig',errors='replace')[-4500:]);print(done.stderr.decode('utf-8-sig',errors='replace')[-4500:])
raise SystemExit(done.returncode)
