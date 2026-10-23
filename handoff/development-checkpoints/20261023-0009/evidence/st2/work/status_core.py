"""Exact register successor primitives; no command or canonical write at import."""
from pathlib import Path
import hashlib,json,os,stat,sys
F=Path('T:/00-Active/Project-AI-CETA'); S=F/'.agents/runtime/oq23/st2'; W=S/'work'; RUN='ceta-st23-r2'
EXPECTED_IGNORED=frozenset({'.git','.agents','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'})
def sha(path):
 path=Path(path);raw=str(path)
 if raw.startswith('\\\\?\\'):
  logical=Path(raw[4:]);assert physical(logical)==path,'unbound extended alias'
  target=path
 else:target=physical(path)
 return hashlib.sha256(target.read_bytes()).hexdigest()
def save(path,value):
 raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode('utf-8')
 with path.open('xb') as stream:
  assert stream.write(raw)==len(raw);stream.flush();os.fsync(stream.fileno())
def physical(path):
 path=Path(path)
 assert path.is_absolute() and not str(path).startswith('\\\\'),('nonlocal path',str(path))
 return Path('\\\\?\\'+str(path)) if os.name=='nt' else path
def native(path):
 info=os.lstat(physical(path));assert not (getattr(info,'st_file_attributes',0)&0x400),('reparse point',str(path))
 assert stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),'nonordinary entry'
 return dict(device=info.st_dev,inode=info.st_ino,bytes=info.st_size,mtime_ns=info.st_mtime_ns,mode=info.st_mode,attributes=getattr(info,'st_file_attributes',0))
def stable(path):
 before=native(path);assert stat.S_ISREG(before['mode']);h=hashlib.sha256()
 with physical(path).open('rb') as stream:
  info=os.fstat(stream.fileno());assert (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==(before['device'],before['inode'],before['bytes'],before['mtime_ns'])
  while block:=stream.read(1024*1024):h.update(block)
  info=os.fstat(stream.fileno());assert (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==(before['device'],before['inode'],before['bytes'],before['mtime_ns'])
 assert native(path)==before,'file changed during read'
 return dict(**before,sha256=h.hexdigest())
def snapshot(workspace,graph_root,ignored=EXPECTED_IGNORED):
 """Fail-closed root/nested scandir, extended I/O; exact explicit stock policy."""
 workspace=Path(workspace);graph_root=Path(graph_root);workspace.relative_to(graph_root)
 files={};directories={};excluded_symlinks={};aliases=set();seen=set()
 def listing(directory):
  before=native(directory);assert stat.S_ISDIR(before['mode'])
  with os.scandir(physical(directory)) as entries: rows=sorted((entry.name for entry in entries))
  assert native(directory)==before,'directory changed during enumeration'
  assert len(rows)==len(set(rows)),'duplicate physical name'
  return before,rows
 def visit(directory):
  info,names=listing(directory);rel=directory.relative_to(graph_root).as_posix();identity=(info['device'],info['inode'])
  assert identity not in seen,'physical directory alias';seen.add(identity)
  directories[rel]=info
  if directory.relative_to(workspace).parts[:2]==('.project-ai','automation'):return
  for name in names:
   assert name not in ('.','..') and '/' not in name and '\\' not in name
   path=directory/name;key=path.relative_to(graph_root).as_posix();fold=key.casefold();assert fold not in aliases,'case alias';aliases.add(fold)
   if name in ignored:
    # The installed policy excludes directories only. Files with these names still count.
    probe=os.lstat(physical(path))
    if stat.S_ISDIR(probe.st_mode):continue
   probe=os.lstat(physical(path))
   if stat.S_ISLNK(probe.st_mode):
    before=(probe.st_dev,probe.st_ino,probe.st_size,probe.st_mtime_ns,probe.st_mode,getattr(probe,'st_file_attributes',0))
    target=os.readlink(physical(path));after=os.lstat(physical(path))
    assert before==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_mode,getattr(after,'st_file_attributes',0)),'symlink changed during observation'
    excluded_symlinks[key]=dict(device=probe.st_dev,inode=probe.st_ino,bytes=probe.st_size,mtime_ns=probe.st_mtime_ns,mode=probe.st_mode,attributes=getattr(probe,'st_file_attributes',0),link_text=target,target_followed=False)
    continue
   item=native(path)
   if stat.S_ISDIR(item['mode']):visit(path)
   else:files[key]=stable(path)
  after,again=listing(directory);assert names==again and after==info,'directory changed during snapshot'
 visit(workspace)
 return dict(files=files,directories=directories,excluded_symlinks=excluded_symlinks,policy=dict(ignored_directory_names=sorted(ignored),ignored_root_relative_subtree='.project-ai/automation',symlinks='EXCLUDED_AS_STOCK; OWN_IDENTITY_RECORDED; NEVER_FOLLOWED',unignored_nonsymlink_reparse='REFUSE',root_and_nested_enumeration='FAIL_CLOSED',extended_paths=os.name=='nt',coverage='ALL_ORDINARY_ENTRIES_UNDER_EXPLICIT_STOCK_POLICY; NOT_IGNORED_REPOSITORY_COMPLETENESS'))
def file_map(observation):return {path:item['sha256'] for path,item in observation['files'].items()}
class _QualifiedRuntime:
 """Explicit exit protocol never assigns an existing exception's traceback."""
 def __enter__(self):
  sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
  import taar.orchestration_runtime as runtime
  from taar.orchestration_graph import compile_graph
  binding=json.loads((W/'BINDING.json').read_bytes());graph=compile_graph(F,S/'control')
  assert str(graph.root)==str(F) and graph.fingerprint==binding['graph_fingerprint']
  assert runtime.IGNORED_DIR_NAMES==EXPECTED_IGNORED
  assert sha(Path(runtime.__file__))==binding['runtime_sha256']
  state=json.loads((S/'control'/RUN/'state.json').read_bytes())
  assert state['run_id']==RUN and state['graph_fingerprint']==graph.fingerprint
  assert state['nodes']['review']['state']=='SUCCEEDED' and state['nodes']['review']['decision']=='approved'
  assert state['nodes']['review']['executor_id']!=state['nodes']['implement']['executor_id']
  assert state['nodes']['validate']['state']=='SUCCEEDED' and state['nodes']['validate']['validation_passed'] is True
  original=runtime._snapshot_workspace
  def observed(workspace,graph_root):
   if Path(workspace)==F:
    assert Path(graph_root)==F,'unexpected graph root'
    return file_map(snapshot(F,F))
   return original(workspace,graph_root)
  self.runtime=runtime;self.original=original;self.observed=observed
  runtime._snapshot_workspace=observed
  return runtime
 def __exit__(self,kind,primary,traceback):
  secondary=[];changed=self.runtime._snapshot_workspace is not self.observed
  try:self.runtime._snapshot_workspace=self.original
  except BaseException as fault:secondary.append(fault)
  if changed:secondary.append(RuntimeError('STATUS_SNAPSHOT_HOOK_CHANGED; original hook restoration attempted'))
  if primary is not None:
   storage=BaseException.__dict__['__dict__'].__get__(primary)
   dict.__setitem__(storage,'ceta_status_snapshot_primary_exc_info',(kind,primary,traceback))
   if secondary:dict.__setitem__(storage,'ceta_status_snapshot_secondary_error',secondary[0])
   dict.__setitem__(storage,'ceta_status_snapshot_secondary_errors',tuple(secondary))
   return False
  if secondary:raise secondary[0]
  return False

def qualified_runtime():
 """Process-local F-only snapshot hook with installed stock transitions retained."""
 return _QualifiedRuntime()

def same_json(original,current):
 if type(original) is not type(current):return False
 if type(original) is dict:return original.keys()==current.keys() and all(same_json(value,current[key]) for key,value in original.items())
 if type(original) is list:return len(original)==len(current) and all(same_json(a,b) for a,b in zip(original,current))
 assert type(original) in (str,int,float,bool,type(None)),'non-JSON type'
 return original==current
class _ApplicationJournal:
 def __init__(self,path,describe):self.path=path;self.describe=describe
 def __enter__(self):
  self.journal=self.path.open('xb')
  return self.event
 def event(self,kind,**data):
  from datetime import datetime,timezone
  raw=(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),kind=kind,**data),allow_nan=False)+'\n').encode()
  assert self.journal.write(raw)==len(raw);self.journal.flush();os.fsync(self.journal.fileno())
 def __exit__(self,kind,primary,traceback):
  secondary=[]
  if primary is not None:
   try:self.event('APPLICATION_FAILURE',error=self.describe(primary),partial_bytes_preserved=True)
   except BaseException as fault:secondary.append(fault)
  for action in (self.journal.flush,lambda:os.fsync(self.journal.fileno()),self.journal.close):
   try:action()
   except BaseException as fault:secondary.append(fault)
  if primary is not None:
   storage=BaseException.__dict__['__dict__'].__get__(primary)
   dict.__setitem__(storage,'ceta_status_application_primary_exc_info',(kind,primary,traceback))
   dict.__setitem__(storage,'ceta_status_application_secondary_errors',tuple(secondary))
   return False
  if secondary:
   error=secondary[0];traceback=BaseException.__dict__['__traceback__'].__get__(error);storage=BaseException.__dict__['__dict__'].__get__(error)
   dict.__setitem__(storage,'ceta_status_application_primary_exc_info',(type(error),error,traceback))
   dict.__setitem__(storage,'ceta_status_application_secondary_errors',tuple(secondary))
   raise BaseException.with_traceback(error,traceback)
  return False

def application_journal(path,describe):
 """Explicit exit protocol leaves an existing body exception to the VM."""
 return _ApplicationJournal(path,describe)

def preserve_json(original,current,changed=()):
 assert type(original) is dict and type(current) is dict
 for key,value in original.items():
  assert key in current,'original field removed'
  if key not in changed:assert same_json(value,current[key]),('original field changed',key)
def constructor_successor(original,old_gate,new_gate):
 old=(chr(34)+old_gate+chr(34)).encode();new=(chr(34)+new_gate+chr(34)).encode()
 assert original.count(old)==1,'strict existing gate hash literal not unique'
 assert b'_GATE_SHA = '+old in original,'strict gate binding changed'
 result=original.replace(old,new,1);compile(result,'canonical construction candidate','exec');return result
