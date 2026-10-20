"""Reviewer-owned AC1 resource/evidence support; no candidate writes."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, importlib.util, json, os, stat, subprocess, sys

P = F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/ac1-20261014'
AUTHOR_R = F / '.agents/runtime/ac1-20261014'
R = D = AUTHOR_R / 'independent-review'
PY = F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
ACTOR, RUN = '/root/pressure_writer', 'ac1-20261014'
assert Path(sys.executable) == PY and sys.version_info[:2] == (3, 12) and os.name == 'nt'
assert not sys.flags.optimize
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def reference(path):
    return {'repository_relative_path': Path(path).relative_to(F).as_posix(), 'sha256': sha(path)}
ref = reference

def write_new(path, value):
    path = Path(path)
    assert path.is_relative_to(D)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())

P4 = F / '.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(P4) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec = importlib.util.spec_from_file_location('ac1_independent_native_reader', P4)
fs = importlib.util.module_from_spec(spec); sys.modules[spec.name] = fs; spec.loader.exec_module(fs)

def ordinary(path):
    path = fs.safe_components(Path(path)); info = fs.lstat(path)
    assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    identity = fs.file_identity(info); size, value, _ = fs.hash_file(path)
    assert fs.file_identity(fs.lstat(path)) == identity and identity['bytes'] == size
    return {'path': str(path), 'bytes': size, 'sha256': value, 'native_identity': identity}

def invoke(arguments, label):
    command = ['powershell.exe', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
               *arguments, '--runtime-root', str(AUTHOR_R)]
    started = utc()
    done = subprocess.run(command, cwd='T:/00-Active', capture_output=True,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'))
    for suffix, raw in [('stdout.txt', done.stdout), ('stderr.txt', done.stderr)]:
        with (D / (label + '.' + suffix)).open('xb') as stream: stream.write(raw)
    response = json.loads(done.stdout.decode('utf-8-sig'))
    write_new(D / (label + '.json'), {'command_argv': command, 'started_at': started,
              'finished_at': utc(), 'exit_status': done.returncode, 'response': response})
    return done, response

def candidate_cut():
    binding = json.loads((D / 'FROZEN-BINDING.json').read_text())
    manifest_path = Q / 'TRANSFER-MANIFEST.json'
    assert sha(manifest_path) == binding['manifest_sha256']
    manifest = json.loads(manifest_path.read_text())
    declared = dict(manifest['payloads'])
    assert len(declared) == manifest['payload_count'] == 249
    assert not set(declared) & set(manifest['candidate_fixture_members'])
    declared.update(manifest['candidate_fixture_members'])
    rows = {name: ordinary(Q / name) for name in declared}
    for name, row in declared.items():
        found = rows[name]
        assert found['sha256'] == row['sha256']
        assert found['native_identity'] == row['native_identity']
    rows['TRANSFER-MANIFEST.json'] = ordinary(manifest_path)
    actual = set()
    pending = [Q]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as children:
            for entry in children:
                path = directory / entry.name; info = fs.lstat(path); assert not fs.reparse(info)
                if stat.S_ISDIR(info.st_mode): pending.append(path)
                elif stat.S_ISREG(info.st_mode): actual.add(path.relative_to(Q).as_posix())
                else: raise AssertionError('nonordinary candidate entry')
    assert actual == set(rows)
    return rows

def source_cut():
    rows = {}
    for prefix in ('src', 'tests', 'contracts', 'native'):
        base = F / prefix
        if not base.exists(): continue
        pending = [base]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as children:
                for entry in children:
                    path = directory / entry.name
                    if entry.name == '__pycache__': continue
                    info = fs.lstat(path); assert not fs.reparse(info)
                    if stat.S_ISDIR(info.st_mode): pending.append(path)
                    elif stat.S_ISREG(info.st_mode): rows[path.relative_to(F).as_posix()] = ordinary(path)
                    else: raise AssertionError('nonordinary Source member')
    return rows
