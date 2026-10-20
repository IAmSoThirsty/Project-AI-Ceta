"""Distinct Root review: immutable ET2 payloads, disposable exact-byte replica."""
from et_support import *
import et_support as author
author.ACTOR = '/root'
D = R / 'independent-root-review'; D.mkdir()
pins = {'TRANSFER-MANIFEST.json': '4d85e8cdf9dafec3c10e923875e0dd9949938d473facb611ac75ae0400f33e60'}
assert sha(Q / 'TRANSFER-MANIFEST.json') == pins['TRANSFER-MANIFEST.json']
for name, expected in {'implement.json': '3d644525243c4a95e7d912bc8d0e30834523e8b2dc79ad59db8478b0595524c5',
    'AUTHOR-READBACK.json': '6235cac4f46305ae59bcac9dc420715525ea933ffb9eee22d49df84fcf6a80fe',
    'AUTHOR-SEAL.json': '32f01a9b7504285e16041791bf443f724f21f0f0fd37f04afecd88836d9d762e'}.items():
    assert sha(R / name) == expected
manifest = json.loads((Q / 'TRANSFER-MANIFEST.json').read_text())
for name, row in manifest['payloads'].items(): assert ordinary(Q / name) == row
inputs = json.loads((R / 'SOURCE-INPUTS.json').read_text())
source = {name: ordinary(F / name) for name in inputs['Source290']}; assert source == inputs['Source290']
claim = author.claim('review'); assert claim['executor_id'] == '/root'
replica = D / 'replica'; replica.mkdir()
copied = {}
for name, row in manifest['payloads'].items():
    target = replica / name; target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as output: output.write(fs.read_bytes(Q / name)); output.flush(); os.fsync(output.fileno())
    copied[name] = ordinary(target); assert copied[name]['sha256'] == row['sha256'] and copied[name]['bytes'] == row['bytes']
write_new(D / 'STAGED-INPUTS.json', {'payloads': copied, 'source': reference(Q / 'TRANSFER-MANIFEST.json')})
support = '''from pathlib import Path
import sys
F=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(F/'.agents/runtime/et2-20261014'))
from et_support import *
Q=F/'.agents/runtime/et2-20261014/independent-root-review/replica'
R=F/'.agents/runtime/et2-20261014/independent-root-review'
ACTOR='/root'
'''
with (D / 'review_support.py').open('x', encoding='utf8') as output: output.write(support)
transforms = {}
for name in ('run_tests.py', 'run_parent_closure.py'):
    original = fs.read_bytes(R / name)
    assert original.count(b'from et_support import *') == 1
    rewritten = original.replace(b'from et_support import *', b'from review_support import *')
    with (D / name).open('xb') as output: output.write(rewritten)
    transforms[name] = {'original': reference(R / name), 'copy': reference(D / name),
        'transform': 'One import changes et_support to review_support; all test method bodies and production payloads are byte-exact.'}
write_new(D / 'PREPARATION.json', {'at': utc(), 'reviewer': '/root', 'author': manifest['author'],
    'claim': claim, 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'Source290': source,
    'author_payloads': manifest['payloads'], 'replica': copied, 'runner_transforms': transforms,
    'profile_operations': [], 'native_cpu_effects': [], 'positive_providers': 'CONTROLLED_TEST_FIXTURES',
    'scope': 'Distinct review only; all fixture writes stay in fresh reviewer replica/runtime. No Source publication or canonical runtime effect.'})
print(json.dumps({'review': 'RUNNING', 'payloads': len(copied), 'Source': len(source), 'reviewer': '/root'}), flush=True)
