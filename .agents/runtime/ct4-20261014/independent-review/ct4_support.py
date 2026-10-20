"""CT3 reviewer-owned native reads and append-only installed runtime operations."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,importlib.util,json,os,stat,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');RUN='ct4-20261014';Q=F/'.agents'/RUN;R=F/'.agents/runtime'/RUN;V=R/'independent-review'
E3=F/'.agents/source-assembly-20261014T021300Z/.agents/e3';PY=E3/'Scripts/python.exe';ACTOR='/root/wt1_reviewer'
sys.dont_write_bytecode=True
assert os.name=='nt' and Path(sys.executable)==PY and sys.flags.optimize==0
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
utc=lambda:datetime.now(timezone.utc).isoformat()
def pairs(items):
 result={}
 for key,value in items:
  if key in result:raise ValueError('DUPLICATE_JSON_KEY:'+key)
  result[key]=value
 return result
def read(path):
 return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError('NONFINITE_JSON:'+v)))
def save(path,value):
 path=Path(path);assert path.is_relative_to(V)
 with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,indent=2,allow_nan=False);out.write('\n');out.flush();os.fsync(out.fileno())
def ref(path):
 path=Path(path);return {'repository_relative_path':path.relative_to(F).as_posix(),'sha256':sha(path)}
P4=F/'.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(P4)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec=importlib.util.spec_from_file_location('ct4_review_native_reader',P4);fs=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fs;spec.loader.exec_module(fs)
def ordinary(path):
 path=fs.safe_components(Path(path));info=fs.lstat(path);assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
 identity=fs.file_identity(info);size,digest,_=fs.hash_file(path)
 assert fs.file_identity(fs.lstat(path))==identity and size==identity['bytes']
 return {'sha256':digest,'native_identity':identity,'bytes':size}
def invoke(label,args):
 argv=['powershell','-NoProfile','-File',r'T:\02-Config\agents\taar-orchestrate.ps1',*args,'--runtime-root',str(R)]
 started=utc();done=subprocess.run(argv,cwd='T:/00-Active',env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True)
 for suffix,data in [('stdout.txt',done.stdout),('stderr.txt',done.stderr)]:
  with (V/(label+'.'+suffix)).open('xb') as out:out.write(data)
 response=json.loads(done.stdout.decode('utf-8-sig'));save(V/(label+'.json'),{'command_argv':argv,'started_at':started,'finished_at':utc(),'exit_status':done.returncode,'response':response})
 assert done.returncode==0 and response['allowed'] is True,response
 return response
