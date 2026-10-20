"""Final evidence consistency and immutable-input checks; no native execution."""
from pathlib import Path
import hashlib
import json
import subprocess

F = Path(r'T:\00-Active\Project-AI-CETA')
O = F / '.agents/runtime/ac7-startup-diagnosis-20261020'
R = F / '.agents/runtime/ac7-token-contract-20261020'
Q = R / 'q-6be3c32cb832461093c6d15dc9c538f8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(name, data):
    with (O / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


inputs = read(O / 'INPUT-RECEIPTS.json')['identities_before']
source_supplement = read(O / 'SUPPLEMENTAL-SOURCE-EXCERPTS.json')['excerpts'][0]
inputs.append({'path': source_supplement['path'], 'sha256': source_supplement['sha256']})
pe = read(O / 'PE-DEPENDENCIES.json')
inputs.extend(row['pe']['artifact'] for row in pe['system32_candidates'] if 'pe' in row)
checks = [{'path': row['path'], 'expected': row['sha256'], 'actual': sha(Path(row['path']))} for row in inputs]
binding = read(Q / 'PROBE-BINDING.json')
for relative, expected in binding['captured_dependencies'].items():
    checks.append({'path': str(F / relative), 'expected': expected['sha256'], 'actual': sha(F / relative)})
for key, path in [('image_copy', Q / 'build-r2/isolated_worker.exe'),
                  ('driver_copy', Q / 'native_fixture_support.py'), ('support_copy', Q / 'ac3_support.py')]:
    checks.append({'path': str(path), 'expected': binding[key]['sha256'], 'actual': sha(path)})
assert all(c['expected'] == c['actual'] for c in checks)
# Git metadata inspection only. Never runs candidate/application/native target code.
git = ['git', '-c', 'safe.directory=T:/00-Active/Project-AI-CETA', '-C', str(F)]
tracked = subprocess.run([*git, 'status', '--porcelain', '--untracked-files=no'], check=True, capture_output=True, text=True).stdout
branch = subprocess.run([*git, 'branch', '--show-current'], check=True, capture_output=True, text=True).stdout.strip()
head = subprocess.run([*git, 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
write('FINAL-REVIEW-CHECKS.json', {'input_digest_checks': checks, 'matched_checks': len(checks), 'mismatch_count': 0,
    'distinct_input_paths': len({r['path'].lower() for r in checks}), 'branch': branch, 'head': head,
    'tracked_status': tracked.splitlines(), 'native_target_executions': 0, 'candidate_mutations': 0,
    'configuration_or_policy_changes': 0, 'rea_closed': True,
    'disposition': 'DIAGNOSIS_COMPLETE_CAUSE_UNRESOLVED_NATIVE_QUALIFICATION_FAILED',
    'remaining_issue': 'C0000142 requires a separately reviewed bounded measurement; no cause repair established'})
files = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(O.iterdir()) if p.is_file()]
write('OUTPUT-MANIFEST.json', {'scope': str(O), 'files_excluding_this_manifest': files,
    'worker_sha256_before_and_after': '3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc',
    'verified_cause': None, 'task_complete': True, 'native_qualification_accepted': False})
print(json.dumps({'final_digest_checks': len(checks), 'mismatches': 0, 'distinct_inputs': len({r['path'].lower() for r in checks}),
    'output_files_in_manifest': len(files), 'disposition': 'DIAGNOSIS_COMPLETE_CAUSE_UNRESOLVED'}))
