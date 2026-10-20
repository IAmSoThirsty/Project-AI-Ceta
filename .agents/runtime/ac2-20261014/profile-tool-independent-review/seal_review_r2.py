from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, stat, sys
F=Path('T:/00-Active/Project-AI-CETA')
D=F/'.agents/runtime/ac2-20261014/profile-tool-independent-review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reader=F/'.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(reader)=='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec=importlib.util.spec_from_file_location('profile_review_seal_reader',reader)
fs=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fs;spec.loader.exec_module(fs)
prior=json.loads((D/'attempt-r2/INPUTS-BEFORE.json').read_text())['inputs']
prior={Path(k).as_posix():v for k,v in prior.items()}
archive=D/'frozen-inputs-r2';archive.mkdir(exist_ok=False)
for name in ('.agents/runtime/ac1-20261014/native_fixture_support.py',
             '.agents/runtime/ac2-20261014/ac2_support.py'):
    source=F/name;identity=fs.file_identity(fs.lstat(fs.safe_components(source)))
    data=fs.read_bytes(source)
    assert hashlib.sha256(data).hexdigest()==prior[name]['sha256']
    assert identity==prior[name]['native_identity']==fs.file_identity(fs.lstat(source))
    with (archive/source.name).open('xb') as output:output.write(data)
raw='''Traceback (most recent call last):
  File "T:\\00-Active\\Project-AI-CETA\\.agents\\runtime\\ac2-20261014\\profile-tool-independent-review\\review_profile_tool.py", line 177, in <module>
    exec(compile(ast.Module(body=[suffix], type_ignores=[]), str(TOOL), 'exec'), local)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: AST node line range (154, 1) is not valid
'''
with (D/'reader-failure-r1.txt').open('x',encoding='utf-8',newline='\n') as output:output.write(raw)
files={}
for source in sorted(D.rglob('*')):
    info=fs.lstat(fs.safe_components(source));assert not fs.reparse(info)
    if stat.S_ISREG(info.st_mode):
        identity=fs.file_identity(info);size,pin,_=fs.hash_file(source)
        assert size==identity['bytes'] and identity==fs.file_identity(fs.lstat(source))
        files[source.relative_to(D).as_posix()]={'sha256':pin,'native_identity':identity}
seal={'at':datetime.now(timezone.utc).isoformat(),'reviewer':'/root/wt1_reviewer',
      'decision':'REJECTED_REPAIR_REQUIRED','report_sha256':sha(D/'REPORT.json'),
      'ordinary_files':len(files),'files':files,'Source_changes':[],
      'native_profile_mutations':[],'own_processes_or_jobs_created':[],
      'all_captured_inspection_API_resources_retired':True,
      'TAAR_claim_for_tooling_review':'none requested or acquired; library ledger untouched',
      'seal_reader_failure':{'type':'KeyError','key':'.agents/runtime/ac1-20261014/native_fixture_support.py','reason':'Reviewer mapping used native Windows separators; exact key normalized in r2; no source mutation or seal written in r1'},'write_scope_sealed':True}
with (D/'SEAL.json').open('x',encoding='utf-8',newline='\n') as output:
    json.dump(seal,output,indent=2,allow_nan=False);output.write('\n');output.flush();os.fsync(output.fileno())
print(json.dumps({'report':sha(D/'REPORT.json'),'seal':sha(D/'SEAL.json'),'files':len(files)}))
