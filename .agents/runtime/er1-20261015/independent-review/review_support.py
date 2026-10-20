"""Independent ER1 readback and installed lifecycle, no Source/candidate writes."""
from pathlib import Path
import ast
import json
import os
import stat
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/er1-20261015'
P = F / '.agents/js2-20261015'
R = F / '.agents/runtime/er1-20261015'
V = Path(__file__).resolve().parent
RUN = 'er1-20261015'
ACTOR = '/root/wt1_reviewer'
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, RUN, ACTOR

MANIFEST = '0d00ab72103eab15319ae2266e63a5834bea378e4422df5d475a0240a26c1f25'
read = lambda path: json.loads(Path(path).read_bytes())


def inventory(root):
    result = {}
    pending = [root]
    while pending:
        parent = pending.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                path = parent / entry.name
                info = s.fs.lstat(path)
                assert not s.fs.reparse(info)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                else:
                    assert stat.S_ISREG(info.st_mode)
                    result[path.relative_to(root).as_posix()] = s.ordinary(path)
    return result


def conservation():
    assert s.sha(Q / 'TRANSFER-MANIFEST.json') == MANIFEST
    manifest = read(Q / 'TRANSFER-MANIFEST.json')
    inputs = read(R / 'SOURCE-INPUTS.json')
    candidate = {name: s.ordinary(Q / name) for name in manifest['payloads']}
    parent = {name: s.ordinary(P / name) for name in inputs['parent292']}
    source = {name: s.ordinary(F / name) for name in inputs['Source290']}
    assert len(candidate) == 293 and len(parent) == 292 and len(source) == 290
    assert candidate == {name: row['candidate'] for name, row in manifest['payloads'].items()}
    assert parent == inputs['parent292'] and source == inputs['Source290']
    seal = read(R / 'AUTHOR-SEAL.json')
    for row in seal['critical_members']:
        assert s.sha(F / row['repository_relative_path']) == row['sha256']
    assert s.sha(R / 'AUTHOR-READBACK.json') == '35568df1200a9c93ad322908fb6a5a092fe8b3f8ff647f410303748f6a6afd13'
    assert s.sha(R / 'AUTHOR-SEAL.json') == 'c1042380d39308cfc0bbbfcb6f5166c8076516b0e33f70f4ebcd202126ca3c67'
    state = read(R / RUN / 'state.json')
    assert state['nodes']['implement']['state'] == 'SUCCEEDED'
    prior = read(F / '.agents/runtime/js2-20261015/js2-20261015/state.json')
    assert prior['nodes']['validate']['state'] == 'FAILED' and prior['nodes']['integrate']['state'] == 'BLOCKED'
    return {'candidate293': candidate, 'parent292': parent, 'Source290': source,
        'manifest': s.ordinary(Q / 'TRANSFER-MANIFEST.json'),
        'author_seal': s.ordinary(R / 'AUTHOR-SEAL.json'),
        'author_inputs': s.ordinary(R / 'SOURCE-INPUTS.json'),
        'E3': inventory(s.PY.parents[1]), 'interpreter': s.ordinary(s.PY),
        'base_interpreter': s.ordinary(Path(sys._base_executable)),
        'HEAD': s.fs.text_git(F, 'rev-parse', 'HEAD'),
        'branch': s.fs.text_git(F, 'branch', '--show-current'),
        'dirty_tracked': s.fs.text_git(F, 'status', '--porcelain=v1', '-uno')}


def invoke(arguments, label):
    command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
        *arguments, '--runtime-root', str(R)]
    started = s.utc()
    done = subprocess.run(command, cwd=str(F), capture_output=True)
    for suffix, data in (('stdout.txt', done.stdout), ('stderr.txt', done.stderr)):
        with (V / (label + '.' + suffix)).open('xb') as stream:
            stream.write(data)
    response = json.loads(done.stdout.decode('utf-8-sig'))
    s.write_new(V / (label + '.json'), {'started_at': started, 'finished_at': s.utc(),
        'command_argv': command, 'exit_status': done.returncode, 'response': response})
    assert done.returncode == 0 and response['allowed'], response
    return response


def function(path, name):
    return next(node for node in ast.parse(Path(path).read_bytes()).body
        if isinstance(node, ast.FunctionDef) and node.name == name)
