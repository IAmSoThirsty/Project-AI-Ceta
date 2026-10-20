"""ER2 distinct component review, exact native/hash conservation and receipts."""
from pathlib import Path
import json
import os
import stat
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = F / '.agents/runtime/er2-20261015'
Q = F / '.agents/er2-20261015'
P = F / '.agents/js3-20261015'
V = Path(__file__).resolve().parent
RUN = Q.name
ACTOR = '/root/wt1_reviewer'
MANIFEST = 'c4017a8189d4706618e6d126cf24a3b971a55eecb43265bb17e969a31eac5d23'
PINS = {'AUTHOR-READBACK.json': '5b4eabbe3e1fa25c8ff73b657ceaf6417576439a72da074ffaef6b01a872211f',
    'AUTHOR-SEAL.json': '7078e6ac820d455f4152ad2eab0de10a29f48aa9e18befd1f76e1cf00d2314b4'}
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, RUN, ACTOR
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
                if stat.S_ISDIR(info.st_mode): pending.append(path)
                else:
                    assert stat.S_ISREG(info.st_mode)
                    result[path.relative_to(root).as_posix()] = s.ordinary(path)
    return result


def conservation():
    assert s.sha(Q / 'TRANSFER-MANIFEST.json') == MANIFEST
    for name, pin in PINS.items(): assert s.sha(R / name) == pin
    manifest = read(Q / 'TRANSFER-MANIFEST.json')
    inputs = read(R / 'SOURCE-INPUTS.json')
    result = {}
    for key, root in (('Source290', F), ('parent294', P), ('E33601', s.PY.parents[1])):
        result[key] = {name: s.ordinary(root / name) for name in inputs[key]}
        assert result[key] == inputs[key], key
    assert inventory(s.PY.parents[1]) == result['E33601']
    result['candidate295'] = {name: s.ordinary(Q / name) for name in manifest['payloads']}
    assert result['candidate295'] == {name: row['candidate'] for name, row in manifest['payloads'].items()}
    assert (len(result['Source290']), len(result['parent294']), len(result['candidate295'])) == (290, 294, 295)
    for row in read(R / 'AUTHOR-SEAL.json')['members']:
        assert s.ordinary(Path(row['path'])) == row
    for name, pin in manifest['scripts'].items(): assert s.sha(R / name) == pin
    for key in ('parent_manifest', 'parent_assembly_review', 'parent_complete_failure', 'actual_full_failure'):
        row = inputs[key]
        assert s.sha(F / row['repository_relative_path']) == row['sha256']
    for key, root in (('auxiliary_source11', F), ('auxiliary_parent11', P)):
        result[key] = {name: s.ordinary(root / name) for name in inputs[key]}
        assert result[key] == inputs[key]
    result['Git'] = {'HEAD': s.fs.text_git(F, 'rev-parse', 'HEAD'),
        'branch': s.fs.text_git(F, 'branch', '--show-current'),
        'dirty': s.fs.text_git(F, 'status', '--porcelain=v1', '-uno')}
    assert result['Git'] == inputs['Git']
    result['sealed_author'] = {name: s.ordinary(R / name) for name in (*PINS, 'implement.json', 'SELF-REVIEW.json')}
    state = read(F / '.agents/runtime/js3-20261015/js3-20261015/state.json')
    assert state['nodes']['validate']['state'] == 'FAILED' and state['sequence'] == 11
    assert read(F / '.agents/runtime/js3-20261015/js3-20261015/claims.json') == {}
    return result


def invoke(arguments, label):
    command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1',
        *arguments, '--runtime-root', str(R)]
    started = s.utc()
    done = subprocess.run(command, cwd=str(F), capture_output=True)
    for suffix, raw in (('stdout.txt', done.stdout), ('stderr.txt', done.stderr)):
        with (V / (label + '.' + suffix)).open('xb') as stream: stream.write(raw)
    response = json.loads(done.stdout.decode('utf-8-sig'))
    actual = read(R / RUN / 'state.json')
    s.write_new(V / (label + '.json'), {'started_at': started, 'finished_at': s.utc(),
        'command_argv': command, 'exit_status': done.returncode, 'response': response,
        'actual_sequence': actual['sequence'], 'actual_review_state': actual['nodes']['review']['state'],
        'actual_claims': read(R / RUN / 'claims.json')})
    assert done.returncode == 0 and response['allowed'], response
    return response


if __name__ == '__main__':
    before = conservation()
    state = read(R / RUN / 'state.json')
    assert state['sequence'] == 7 and state['nodes']['implement']['state'] == 'SUCCEEDED'
    assert state['nodes']['review']['state'] == 'READY' and read(R / RUN / 'claims.json') == {}
    s.write_new(V / 'BEFORE.json', before)
    invoke(['node', 'claim', RUN, 'review', '--executor', ACTOR, '--workspace', str(Q)], 'review-claim')
    print(json.dumps({'state': 'RUNNING', 'manifest': MANIFEST, 'payloads': 295,
        'Source': 290, 'parent': 294, 'E3': 3601}), flush=True)
