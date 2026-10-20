"""Exact AC1 candidate/native source bindings and actual installed lifecycle."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, importlib.util, json, os, stat, subprocess, sys

P = Path('T:/00-Active/Project-AI-CETA')
Q = P / '.agents/ac1-20261014'
R = P / '.agents/runtime/ac1-20261014'
PY = P / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
ACTOR = '/root/history_preservation'
RUN = 'ac1-20261014'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

def utc(): return datetime.now(timezone.utc).isoformat()
def digest(raw): return hashlib.sha256(raw).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def write_new(path, value):
    path = Path(path)
    assert path.is_relative_to(Q) or path.is_relative_to(R)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
def reference(path):
    path = Path(path)
    return {'repository_relative_path': path.relative_to(P).as_posix(), 'sha256': sha(path)}

P4 = P / '.agents/pr4-20261014/preserve_ceta_complete.py'
assert sha(P4) == '2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618'
spec = importlib.util.spec_from_file_location('ac1_approved_native_reader', P4)
fs = importlib.util.module_from_spec(spec); sys.modules[spec.name] = fs; spec.loader.exec_module(fs)
assert Path(sys.executable) == PY and sys.version_info[:2] == (3, 12) and os.name == 'nt'

def ordinary(path):
    path = fs.safe_components(Path(path)); info = fs.lstat(path)
    assert stat.S_ISREG(info.st_mode) and not fs.reparse(info)
    identity = fs.file_identity(info); size, value, _ = fs.hash_file(path)
    assert fs.file_identity(fs.lstat(path)) == identity and identity['bytes'] == size
    return {'path': str(path), 'bytes': size, 'sha256': value, 'native_identity': identity}

def invoke(arguments, label):
    command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
               *arguments, '--runtime-root', str(R)]
    started = utc(); done = subprocess.run(command, cwd='T:/00-Active', capture_output=True,
                                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    for suffix, raw in [('stdout.txt', done.stdout), ('stderr.txt', done.stderr)]:
        (R / (label + '.' + suffix)).write_bytes(raw)
    response = json.loads(done.stdout.decode('utf-8-sig'))
    write_new(R / (label + '.json'), {'command_argv': command, 'started_at': started,
              'finished_at': utc(), 'exit_status': done.returncode, 'response': response})
    assert done.returncode == 0 and response['allowed'], response
    return response

def claim(node):
    return invoke(['node', 'claim', RUN, node, '--executor', ACTOR, '--workspace', str(Q)],
                  node + '-claim')['claim']

def complete(node, result, commands, validations):
    current = json.loads((R / RUN / 'claims.json').read_text())[node]
    graph = json.loads((R / RUN / 'graph.json').read_text())['graph']
    assert current['executor_id'] == ACTOR
    sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_receipts import validate_receipt, load_receipt
    from taar.orchestration_runtime import _snapshot_workspace, _changed_files
    changed = _changed_files(current['baseline_snapshot'], _snapshot_workspace(Q, Path('T:/')))
    receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': node, 'executor_id': ACTOR,
               'started_at': current['claimed_at'], 'finished_at': utc(), 'input_hash': current['input_hash'],
               'changed_files': changed, 'result': result, 'commands': commands,
               'validations': [{'name': name, 'passed': passed} for name, passed in validations], 'exit_status': 0}
    kwargs = {'run_id': RUN, 'node_id': node, 'executor_id': ACTOR, 'input_hash': current['input_hash'],
              'claimed_at': current['claimed_at'], 'node': graph['nodes'][node]}
    validate_receipt(receipt, **kwargs); write_new(R / (node + '.json'), receipt)
    validate_receipt(load_receipt(R / (node + '.json')), **kwargs)
    return invoke(['node', 'complete', RUN, node, str(R / (node + '.json'))], node + '-complete')

def source_inventory():
    found = {}
    for top in ('src', 'tests', 'contracts'):
        pending = [P / top]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    path = directory / entry.name; info = fs.lstat(path)
                    assert not fs.reparse(info)
                    if stat.S_ISDIR(info.st_mode): pending.append(path)
                    elif stat.S_ISREG(info.st_mode): found[path.relative_to(P).as_posix()] = ordinary(path)
                    else: raise AssertionError('nonordinary active Source')
    return found
