"""Preserve and run the exact six rejected native custody subcases first."""
from ac2_support import *

root = R / 'baseline-r1'; root.mkdir()
(root / 'build-r2').mkdir()
binary = PRIOR_R / 'build-r2/isolated_worker.exe'
assert sha(binary) == '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
fs.write_new(root / 'build-r2/isolated_worker.exe', fs.read_bytes(binary))
original = PRIOR_R / 'independent-review/hostile_cleanup.py'
target = root / 'hostile_cleanup.py'; fs.write_new(target, fs.read_bytes(original))
fs.write_new(root / 'ac_support.py', fs.read_bytes(R / 'ac_support.py'))
command = [str(PY), '-B', '-X', 'utf8', str(target)]
done = subprocess.run(command, cwd='T:/00-Active', capture_output=True,
    env=dict(os.environ, CETA_AC2_PROBE_ROOT=str(root), PYTHONPATH=str(R)))
for suffix, raw in [('stdout.txt', done.stdout), ('stderr.txt', done.stderr)]:
    with (root / ('driver.' + suffix)).open('xb') as output: output.write(raw)
proof = json.loads((root / 'hostile-cleanup-r1.json').read_text())
assert done.returncode == proof['exit_status'] == 1
assert proof['tests_run'] == 3 and len(proof['failures']) == 6 and not proof['errors'] and not proof['skipped']
assert sha(target) == sha(original)
write_new(R / 'baseline-reproduction.json', {'observed_at': utc(), 'command': command,
    'exit_status': done.returncode, 'code': reference(target), 'original_code': reference(original),
    'exact_original_body': True, 'proof': reference(root / 'hostile-cleanup-r1.json'),
    'source_module': ordinary(Q / 'src/ceta/supervisor/isolated_worker.py'),
    'classification': 'Verified unchanged AC1 defect reproduction before candidate source edits',
    'three_methods': 3, 'failed_control_subcases': 6, 'native_resources_recovered': True})
print(json.dumps({'baseline_failed_methods': 3, 'failed_control_subcases': 6,
                  'proof': reference(root / 'hostile-cleanup-r1.json')}), flush=True)
