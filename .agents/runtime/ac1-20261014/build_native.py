from ac_support import *

label = sys.argv[1] if len(sys.argv) == 2 else 'build-r1'
assert label in ('build-r1', 'build-r2', 'build-r3')
target = R / label
assert not target.exists()
target.mkdir()
source = Q / 'native/windows_broker/isolated_worker.rs'
rust = Path('T:/03-Toolchains/.cargo/bin/rustc.exe')
command = [str(rust), '--edition=2024', '-C', 'target-feature=+crt-static', '-O',
           str(source), '-o', str(target / 'isolated_worker.exe')]
env = dict(os.environ, TEMP=str(target), TMP=str(target), PYTHONDONTWRITEBYTECODE='1')
version = subprocess.run([str(rust), '-vV'], cwd='T:/00-Active', env=env, capture_output=True)
sysroot = subprocess.run([str(rust), '--print', 'sysroot'], cwd='T:/00-Active', env=env, capture_output=True)
assert version.returncode == 0 and sysroot.returncode == 0
actual = (Path(sysroot.stdout.decode().strip()) / 'bin/rustc.exe').resolve(strict=True)
resolved_rustup = rust.resolve(strict=True)
assert resolved_rustup.name.lower() == 'rustup.exe'
started = utc()
done = subprocess.run(command, cwd=str(target), env=env, capture_output=True)
(target / 'stdout.txt').write_bytes(done.stdout)
(target / 'stderr.txt').write_bytes(done.stderr)
receipt = {'command_argv': command, 'started_at': started, 'finished_at': utc(),
           'exit_status': done.returncode, 'source': ordinary(source),
           'declared_rustc_alias': {'path': str(rust), 'link_target': os.readlink(rust)},
           'resolved_rustup_command_image': ordinary(resolved_rustup), 'actual_rustc': ordinary(actual),
           'version_output': version.stdout.decode('utf-8', 'replace'),
           'sysroot': str(actual.parent.parent),
           'stdout': reference(target / 'stdout.txt'), 'stderr': reference(target / 'stderr.txt'),
           'environment_scope': 'Only process-local TEMP/TMP point to this fresh build directory; no E3/download/install/configuration changes'}
if done.returncode == 0:
    receipt['native_image'] = ordinary(target / 'isolated_worker.exe')
write_new(target / 'build.json', receipt)
print(json.dumps({'exit_status': done.returncode, 'receipt': str(target / 'build.json'),
                  'stderr': done.stderr.decode('utf-8', 'replace')[:5000],
                  'native_image': receipt.get('native_image')}, indent=2))
sys.exit(done.returncode)
