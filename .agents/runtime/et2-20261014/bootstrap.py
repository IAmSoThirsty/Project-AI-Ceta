"""Fresh exact successor; parent/source remain immutable inputs."""
from et_support import *
assert not Q.exists(); Q.mkdir()
parent = F / '.agents/et1-20261014'
manifest_path = parent / 'TRANSFER-MANIFEST.json'
assert sha(manifest_path) == 'ba5f5ceea225d9b1b3f96cce04bd4f55ee24f8ad23a8d222fcd1fbd136db9cec'
manifest = json.loads(manifest_path.read_text())
inputs = json.loads((F / '.agents/runtime/et1-20261014/SOURCE-INPUTS.json').read_text())
source = {name: ordinary(F / name) for name in inputs['Source290']}
assert source == inputs['Source290'] and len(source) == 290
scope = manifest['eligible_application_paths']
probe = F / '.agents/runtime/et1-20261014/independent-review/probe_cumulative_budget.py'
assert sha(probe) == '8d28ba91b34795876ea8010951791cec53434d485fd119d69fbbb149f2b79c7a'
invoke(['run','init','--root','T:/','--scope',str(Q),'--run-id',RUN], 'run-init')
claim('discover')
write_new(R / 'SOURCE-INPUTS.json', {'at': utc(), 'parent_manifest': reference(manifest_path),
    'Source290': source, 'eligible_paths': scope, 'rejected_parent_probe': reference(probe),
    'parent_probe_result': reference(probe.parent / 'CUMULATIVE-BUDGET-PROBE.json'),
    'HEAD': fs.text_git(F,'rev-parse','HEAD'), 'dirty_tracked': fs.text_git(F,'status','--porcelain=v1','-uno'),
    'Source_application': False, 'scope': 'Cumulative request evidence capacity; same canonical journal and unchanged public methods.'})
cmd = {'command': subprocess.list2cmdline([str(PY),'-B','-X','utf8',str(Path(__file__))]), 'exit_status':0}
complete('discover', {'inputs': reference(R / 'SOURCE-INPUTS.json')}, [cmd], [('Exact frozen rejected parent and Source290 inspected',True)])
claim('plan')
write_new(R / 'TASK-BINDING.json', {'at':utc(), 'eligible_paths':scope,
    'repair':'Cumulative canonical event/payload/projection/evidence writes across attempt/outcomes/reconciliation; authenticated accounting, atomic overflow, exact retry read-only.',
    'unchanged':'Unique kernel/journal issuer/writer, charged consumed liability, public APIs, no native replay/refund or production capacity widening.',
    'required_tests':['Unchanged two-method hostile baseline','Finite8KiB overflow','Exact cumulative bytes','Restart','Concurrency','Tampered counts','Repeated UNAVAILABLE','Prior385 intentional fixture amendments transparent']})
complete('plan', {'binding':reference(R / 'TASK-BINDING.json')}, [cmd], [('Finite same-owner capacity repair bound',True)])
claim('implement')
rows = {}
for name, row in manifest['payloads'].items():
    assert ordinary(parent / name) == row
    destination = Q / name; destination.parent.mkdir(parents=True,exist_ok=True)
    fs.write_new(destination, fs.read_bytes(parent / name)); rows[name] = ordinary(destination)
    assert rows[name]['sha256'] == row['sha256']
assert len(rows) == 316
for name in scope:
    destination = R / 'before-images' / name; destination.parent.mkdir(parents=True,exist_ok=True)
    fs.write_new(destination, fs.read_bytes(parent / name))
write_new(R / 'STAGED-INPUTS.json', {'at':utc(), 'payloads':rows, 'parent_manifest':reference(manifest_path),
    'eligible_paths':scope, 'reused_payloads_LOC_credit':0})
print(json.dumps({'implement':'RUNNING','payloads':316,'Source':290,'parent_mutation':False}))
