"""Preserve original adverse body and minimal native recovery adaptation."""
from ac2_support import *
import difflib

label = sys.argv[1] if len(sys.argv) == 2 else 'closure-r1'
assert label in ('closure-r1', 'closure-r2', 'closure-r3', 'closure-r4')
root = R / label; root.mkdir(); (root / 'build-r2').mkdir()
binary = PRIOR_R / 'build-r2/isolated_worker.exe'
fs.write_new(root / 'build-r2/isolated_worker.exe', fs.read_bytes(binary))
fs.write_new(root / 'ac_support.py', fs.read_bytes(R / 'ac_support.py'))
original_path = PRIOR_R / 'independent-review/hostile_cleanup.py'
original = original_path.read_text(encoding='utf-8')
old = """                    for job in api.jobs:
                        accounting = C.create_string_buffer(48); used = module.DWORD()
                        self.assertTrue(api.QueryInformationJobObject(job, 1, accounting, len(accounting), C.byref(used)))
                        active.append(module.DWORD.from_buffer(accounting, 40).value)
"""
new = """                    for job in api.jobs:
                        C.set_last_error(0)
                        is_open = handle_open(api, job)
                        status = C.get_last_error()
                        if is_open:
                            accounting = C.create_string_buffer(48); used = module.DWORD()
                            self.assertTrue(api.QueryInformationJobObject(job, 1, accounting, len(accounting), C.byref(used)))
                            active.append(module.DWORD.from_buffer(accounting, 40).value)
                        else:
                            self.assertEqual(status, 6)
                        observed_job_status.append({'handle': job, 'native_open': is_open, 'last_error': status})
"""
assert original.count(old) == 1
adapted = original.replace(old, new).replace('                active = []\n', '                active = []; observed_job_status = []\n')
adapted = adapted.replace("                       'empty_job_observations': active,", "                       'empty_job_observations': active, 'captured_job_native_status': observed_job_status,")
# Newly retained duplicate custody must be settled through its actual explicit
# recovery API before falling back to the old probe's own direct-handle cleanup.
needle = "                api.close = real_close\n                for handle, is_open in zip(opened, open_before):\n                    if is_open: api.close(handle)\n"
replacement = """                api.close = real_close
                cleanup = getattr(error, 'isolation_cleanup', None)
                if cleanup is not None: cleanup.close_cleanup()
                for handle, is_open in zip(opened, open_before):
                    if is_open and handle_open(api, handle): api.close(handle)
"""
assert adapted.count(needle) == 1
adapted = adapted.replace(needle, replacement)
target = root / 'hostile_cleanup.py'; fs.write_new(target, adapted.encode('utf-8'))
diff = ''.join(difflib.unified_diff(original.splitlines(True), adapted.splitlines(True),
    fromfile='frozen-AC1-hostile_cleanup.py', tofile='AC2-native-closure-adapted-hostile_cleanup.py'))
fs.write_new(root / 'oracle-adaptation.diff', diff.encode('utf-8'))
write_new(root / 'closure-oracle-binding.json', {'observed_at': utc(), 'original': reference(original_path),
    'adapted': reference(target), 'diff': reference(root / 'oracle-adaptation.diff'),
    'all_primary_identity_and_caller_visible_custody_assertions_preserved': True,
    'reasons': ['A correctly closed job cannot be queried as a live job; actual GetHandleInformation/error6 recorded.',
                'New retained duplicate-token custody must use the caller-visible explicit cleanup API; native handle-open/closed assertions stay.'],
    'baseline': reference(R / 'baseline-reproduction.json')})
done = subprocess.run([str(PY), '-B', '-X', 'utf8', str(target)], cwd='T:/00-Active', capture_output=True,
    env=dict(os.environ, CETA_AC2_PROBE_ROOT=str(root), PYTHONPATH=str(R)))
for suffix, raw in [('stdout.txt', done.stdout), ('stderr.txt', done.stderr)]:
    with (root / ('driver.' + suffix)).open('xb') as output: output.write(raw)
print(done.stdout.decode('utf-8'), end='', flush=True)
if done.returncode: print(done.stderr.decode('utf-8'), end='', flush=True)
sys.exit(done.returncode)
