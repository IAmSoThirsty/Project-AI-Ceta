"""ET3 distinct reviewer evidence and actual installed lifecycle transport."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, stat, subprocess, sys
F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/et3-20261015'
R = F / '.agents/runtime/et3-20261015'
D = R / 'independent-review'
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
RUN, ACTOR = 'et3-20261015', '/root/history_preservation'
assert Path(sys.executable) == PY and os.name == 'nt' and not sys.flags.optimize
sys.dont_write_bytecode = True; os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
utc = lambda: datetime.now(timezone.utc).isoformat()
digest = lambda raw: hashlib.sha256(raw).hexdigest()
sha = lambda p: digest(Path(p).read_bytes())
def write(path, value):
    path = Path(path); assert path.is_relative_to(D)
    with path.open('x', encoding='utf8', newline='\n') as out:
        json.dump(value, out, indent=2, allow_nan=False); out.write('\n'); out.flush(); os.fsync(out.fileno())
P4 = F / '.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(P4) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec = importlib.util.spec_from_file_location('et3_review_native_reader', P4)
fs = importlib.util.module_from_spec(spec); sys.modules[spec.name] = fs; spec.loader.exec_module(fs)
def ordinary(path):
    path = fs.safe_components(Path(path)); info = fs.lstat(path)
    assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    native = fs.file_identity(info); size, value, _ = fs.hash_file(path)
    assert fs.file_identity(fs.lstat(path)) == native and size == native['bytes']
    return {'path': str(path), 'bytes': size, 'sha256': value, 'native_identity': native}
def invoke(args, label):
    argv = ['powershell.exe', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1', *args, '--runtime-root', str(R)]
    started = utc(); done = subprocess.run(argv, cwd='T:/00-Active', capture_output=True,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', PYTHONDONTWRITEBYTECODE='1'))
    for suffix, raw in [('stdout.txt',done.stdout),('stderr.txt',done.stderr)]:
        with (D/(label+'.'+suffix)).open('xb') as out: out.write(raw)
    response = json.loads(done.stdout.decode('utf-8-sig'))
    write(D/(label+'.json'), {'command_argv':argv,'started_at':started,'finished_at':utc(),
        'exit_status':done.returncode,'response':response})
    assert done.returncode == 0 and response['allowed'], response
    return response

if __name__ == '__main__':
    manifest = Q/'TRANSFER-MANIFEST.json'
    assert sha(manifest) == 'b061311cf6f52c89b9af93845258ca061043ef6ef60d8530b9048983351e5c9a'
    state = json.loads((R/RUN/'state.json').read_text())
    assert state['nodes']['implement']['state']=='SUCCEEDED' and state['nodes']['review']['state']=='READY'
    assert json.loads((R/RUN/'claims.json').read_text()) == {}
    claim = invoke(['node','claim',RUN,'review','--executor',ACTOR,'--workspace',str(Q)],'review-claim')['claim']
    write(D/'TASK-BINDING.json', {'at':utc(),'actor':ACTOR,'run':RUN,'candidate':str(Q),
        'output_scope':str(D),'claim':claim,'manifest':ordinary(manifest),
        'job':'Distinct review of ET3 fresh observer child reconciliation and retained finite accounting',
        'forbidden':['Source/E3/candidate edits','profile operations','Hello','restricted worker','class15Set'],
        'authorship':'Reviewer authored KA1 dependency; rely on Root accepted KA1 review, independently assess ET3 delta.'})
    print(json.dumps({'claimed':True,'executor':ACTOR,'run':RUN,'workspace':str(Q)}),flush=True)
