"""Build the repaired fixed worker and execute only its five pure Rust tests."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/ac7-token-contract-20261020'
B = R / 'build-r1'
B.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    with path.open('x', encoding='utf8') as stream: json.dump(value, stream, indent=2)
previous = json.loads((F / '.agents/runtime/ac1-20261014/build-r2/build.json').read_bytes())
compiler = Path(previous['actual_rustc']['path'])
assert sha(compiler) == previous['actual_rustc']['sha256']
source = Q / 'native/windows_broker/isolated_worker.rs'
source_pin = sha(source)
environment = dict(os.environ, TEMP=str(B), TMP=str(B))
records = []
def execute(label, command, timeout=60):
    started = now()
    result = subprocess.run(command, cwd=F, capture_output=True, env=environment, timeout=timeout)
    for suffix, raw in [('stdout', result.stdout), ('stderr', result.stderr)]:
        with (B / (label + '.' + suffix)).open('xb') as stream: stream.write(raw)
    record = dict(label=label, started_at=started, finished_at=now(), command=command,
        exit_status=result.returncode, stdout_sha256=sha(B / (label + '.stdout')),
        stderr_sha256=sha(B / (label + '.stderr')))
    save(B / (label + '.json'), record)
    records.append(record)
    assert result.returncode == 0, record
    return result
version = execute('compiler-version', [str(compiler), '--version', '--verbose']).stdout.decode('utf8')
sysroot = execute('compiler-sysroot', [str(compiler), '--print', 'sysroot']).stdout.decode('utf8').strip()
assert Path(sysroot) == Path(previous['sysroot'])
image = B / 'isolated_worker.exe'
options = [str(compiler), '--edition=2024', '-C', 'target-feature=+crt-static', '-O', str(source)]
execute('fixed-worker-build', options + ['-o', str(image)])
tests = B / 'isolated_worker_token_tests.exe'
execute('pure-test-build', options + ['--test', '-o', str(tests)])
result = execute('pure-rust-tests', [str(tests), '--test-threads=1', '--nocapture'])
assert b'5 passed; 0 failed' in result.stdout and b'0 ignored' in result.stdout
inputs = json.loads((R / 'INPUTS.json').read_bytes())
assert all(sha(F / n) == h for n,h in inputs['payload_hashes'].items())
assert sha(source) == source_pin and sha(compiler) == previous['actual_rustc']['sha256']
save(B / 'BUILD.json', dict(at=now(), source=dict(path=str(source), sha256=source_pin),
    actual_rustc=dict(path=str(compiler), sha256=sha(compiler)), version_output=version, sysroot=sysroot,
    native_image=dict(path=str(image), sha256=sha(image), bytes=image.stat().st_size),
    pure_test_image=dict(path=str(tests), sha256=sha(tests)), commands=records,
    actual_restricted_worker_execution=False, host_profile_operations=False,
    pure_tests=5, source352_unchanged=True, temporary_environment='Process-local TEMP/TMP only'))
print(json.dumps(dict(build_passed=True, rust_pure_tests=5, worker_sha256=sha(image),
    actual_restricted_worker_execution=False, host_profile_operations=False)), flush=True)
