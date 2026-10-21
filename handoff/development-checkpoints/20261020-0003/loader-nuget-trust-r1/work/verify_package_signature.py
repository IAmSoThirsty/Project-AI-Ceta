"""Bounded verification of one retained archive with the installed .NET SDK.

No package download, install, target-DLL execution, or persistent configuration
write is requested. All explicitly configured CLI/cache/temp paths are local.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

W = Path(__file__).resolve().parent
S = W.parent
F = Path(r'T:\00-Active\Project-AI-CETA')
DOTNET = Path(r'C:\Program Files\dotnet\dotnet.exe')
INPUTS_SHA256 = '73ec4de8310dad1e0d95f213b93fc656c1a575184215ac49010c0fba0dfea5c1'
TIMEOUT_SECONDS = 180
OUTPUT_LIMIT_BYTES = 8 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def pin(path):
    path = Path(path)
    before = path.stat()
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and not path.is_junction(), 'FILE_PATH_INVALID')
    for item in (path, *path.parents):
        require(not item.stat().st_file_attributes & 0x400, 'FILE_REPARSE_PATH')
    value = digest(path)
    after = path.stat()
    identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
    require(identity(before) == identity(after), 'FILE_CHANGED_DURING_PIN')
    return dict(path=str(path), bytes=before.st_size, sha256=value,
                device=before.st_dev, inode=before.st_ino, mtime_ns=before.st_mtime_ns)


def write_json_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def environment():
    paths = {
        'DOTNET_CLI_HOME': W / '_state/dotnet-home',
        'APPDATA': W / '_state/appdata',
        'LOCALAPPDATA': W / '_state/localappdata',
        'USERPROFILE': W / '_state/userprofile',
        'MSBUILDUSEREXTENSIONSPATH': W / '_state/msbuild',
        'NUGET_PACKAGES': W / '_cache/packages',
        'NUGET_HTTP_CACHE_PATH': W / '_cache/http',
        'NUGET_SCRATCH': W / '_cache/scratch',
        'NUGET_PLUGINS_CACHE_PATH': W / '_cache/plugins',
        'NUGET_FALLBACK_PACKAGES': W / '_cache/fallback',
        'TEMP': W / '_tmp', 'TMP': W / '_tmp', 'TMPDIR': W / '_tmp',
    }
    for path in paths.values():
        require(path.is_relative_to(W), 'ENVIRONMENT_PATH_OUTSIDE_WORK')
        path.mkdir(parents=True, exist_ok=True)
    changes = {key: str(path) for key, path in paths.items()}
    changes.update({
        'DOTNET_CLI_TELEMETRY_OPTOUT': '1', 'DOTNET_SKIP_FIRST_TIME_EXPERIENCE': '1',
        'DOTNET_NOLOGO': '1', 'DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE': 'true',
        'DOTNET_GENERATE_ASPNET_CERTIFICATE': 'false', 'DOTNET_ADD_GLOBAL_TOOLS_TO_PATH': '0',
        'DOTNET_CLI_USE_MSBUILD_SERVER': '0', 'MSBUILDDISABLENODEREUSE': '1',
        'DOTNET_MULTILEVEL_LOOKUP': '0', 'DOTNET_CLI_UI_LANGUAGE': 'en-US',
        'NUGET_CLI_LANGUAGE': 'en-us', 'NUGET_EXE_NO_PROMPT': '1',
        'NUGET_CERT_REVOCATION_MODE': 'online',
        'NUGET_ENHANCED_MAX_NETWORK_TRY_COUNT': '1',
        'NUGET_ENHANCED_NETWORK_RETRY_DELAY_MILLISECONDS': '100',
        'NUGET_CREDENTIALPROVIDER_SESSIONTOKENCACHE_ENABLED': 'false',
        'NUGET_PLUGIN_PATHS': '', 'NUGET_NETCORE_PLUGIN_PATHS': '', 'NUGET_NETFX_PLUGIN_PATHS': '',
        'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0',
    })
    # Avoid inherited extension hooks/profilers or forced-interactive behavior.
    removed_names = ('DOTNET_STARTUP_HOOKS', 'DOTNET_ADDITIONAL_DEPS', 'DOTNET_SHARED_STORE',
                     'COR_ENABLE_PROFILING', 'COR_PROFILER', 'COR_PROFILER_PATH',
                     'CORECLR_ENABLE_PROFILING', 'CORECLR_PROFILER', 'CORECLR_PROFILER_PATH',
                     'FORCE_NUGET_EXE_INTERACTIVE', 'NUGET_API_KEY', 'NUGET_SYMBOL_API_KEY')
    child = os.environ.copy()
    removed = []
    for key in removed_names:
        if key in child:
            removed.append(dict(name=key, original_value_sha256=hashlib.sha256(child[key].encode('utf-8')).hexdigest()))
            del child[key]
    previous = {key: (dict(present=True, value_sha256=hashlib.sha256(child[key].encode('utf-8')).hexdigest())
                      if key in child else dict(present=False)) for key in changes}
    child.update(changes)
    return child, dict(process_only=True, set=changes, removed=removed,
                       inherited_replaced_value_hashes=previous,
                       explicit_paths={key: str(path) for key, path in paths.items()},
                       limits='This redirects declared CLI caches/temp paths. OS-managed chain caches, trust-store reads and network traffic are not independently traced.')


def run(label, arguments, child_env, archive_before, environment_path=None):
    environment_path = Path(environment_path) if environment_path is not None else W / 'ENVIRONMENT.json'
    command = [str(DOTNET), *arguments]
    invocation = dict(schema_version=1, label=label, argv=command,
                      command=subprocess.list2cmdline(command), cwd=str(W), started_at=utc(),
                      timeout_seconds=TIMEOUT_SECONDS, stdout_limit_bytes=OUTPUT_LIMIT_BYTES,
                      stderr_limit_bytes=OUTPUT_LIMIT_BYTES, archive_before=archive_before,
                      environment_reference=dict(path=str(environment_path), sha256=digest(environment_path)))
    write_json_new(W / (label + '-INVOKED.json'), invocation)
    stdout_path, stderr_path = W / (label + '.stdout.log'), W / (label + '.stderr.log')
    deadline = time.monotonic() + TIMEOUT_SECONDS
    stopped = None
    with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
        process = subprocess.Popen(command, cwd=W, env=child_env, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    stopped = 'TIMEOUT'
                elif stdout_path.stat().st_size > OUTPUT_LIMIT_BYTES or stderr_path.stat().st_size > OUTPUT_LIMIT_BYTES:
                    stopped = 'OUTPUT_BOUND_EXCEEDED'
                if stopped:
                    process.kill()
                    break
                time.sleep(0.1)
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    after = pin(archive_before['path'])
    result = dict(invocation, ended_at=utc(), pid=process.pid, exit_status=process.returncode,
                  terminated_for_bound=stopped, archive_after=after,
                  archive_unchanged=(after == archive_before),
                  stdout=dict(path=str(stdout_path), bytes=stdout_path.stat().st_size, sha256=digest(stdout_path)),
                  stderr=dict(path=str(stderr_path), bytes=stderr_path.stat().st_size, sha256=digest(stderr_path)))
    write_json_new(W / (label + '-RESULT.json'), result)
    require(after == archive_before, 'ORIGINAL_ARCHIVE_CHANGED')
    require(stopped is None, 'DOTNET_COMMAND_' + str(stopped))
    return result


def main():
    input_path = S / 'packet/INPUTS.json'
    require(digest(input_path) == INPUTS_SHA256, 'INPUT_PACKET_CHANGED')
    inputs = json.loads(input_path.read_text(encoding='utf-8'))
    require(Path(inputs['scope']) == W, 'ASSIGNED_SCOPE_CHANGED')
    before = pin(inputs['archive']['path'])
    require(before['bytes'] == inputs['archive']['size'] and before['sha256'] == inputs['archive']['sha256'],
            'RETAINED_ARCHIVE_PIN_CHANGED')
    dotnet_pin = pin(DOTNET)
    write_json_new(W / 'INPUT-PINS-BEFORE.json', dict(archive=before, installed_dotnet=dotnet_pin,
        input_packet=dict(path=str(input_path), sha256=INPUTS_SHA256), recorded_at=utc()))
    child_env, delta = environment()
    write_json_new(W / 'ENVIRONMENT.json', delta)
    with (W / 'global.json').open('x', encoding='utf-8', newline='\n') as out:
        json.dump(dict(sdk=dict(version='10.0.302', rollForward='disable', allowPrerelease=False)), out, indent=2)
        out.write('\n')
    config = '''<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources><clear /></packageSources>
  <fallbackPackageFolders><clear /></fallbackPackageFolders>
  <disabledPackageSources><clear /></disabledPackageSources>
  <trustedSigners><clear /></trustedSigners>
  <config>
    <add key="signatureValidationMode" value="require" />
    <add key="globalPackagesFolder" value="''' + str(W / '_cache/packages') + '''" />
    <add key="updatePackageLastAccessTime" value="false" />
  </config>
</configuration>
'''
    with (W / 'NuGet.Config').open('x', encoding='utf-8', newline='\n') as out:
        out.write(config)
    inventory = run('sdk-inventory', ['--list-sdks'], child_env, before)
    require(inventory['exit_status'] == 0, 'INSTALLED_SDK_INVENTORY_FAILED')
    version = run('sdk-version', ['--version'], child_env, before)
    require(version['exit_status'] == 0 and (W / 'sdk-version.stdout.log').read_text(encoding='utf-8').strip() == '10.0.302',
            'EXACT_INSTALLED_SDK_NOT_SELECTED')
    result = run('nuget-verify', ['nuget', 'verify', before['path'], '--all', '--verbosity', 'detailed',
                                '--configfile', str(W / 'NuGet.Config')], child_env, before)
    require(pin(DOTNET) == dotnet_pin, 'INSTALLED_DOTNET_CHANGED')
    # The detailed SDK log, not this Boolean, determines signer/chain/timestamp scope.
    write_json_new(W / 'VERIFICATION-EXECUTION.json', dict(schema_version=1, recorded_at=utc(),
        status=('COMMAND_SUCCEEDED_PENDING_LOG_ADJUDICATION' if result['exit_status'] == 0 else 'COMMAND_FAILED'),
        exit_status=result['exit_status'], archive_before=before, archive_after=result['archive_after'],
        installed_dotnet_before=dotnet_pin, installed_dotnet_after=pin(DOTNET),
        selected_sdk='10.0.302', explicit_config=dict(path=str(W / 'NuGet.Config'), sha256=digest(W / 'NuGet.Config')),
        revocation_mode_requested='online', command_result=dict(path=str(W / 'nuget-verify-RESULT.json'), sha256=digest(W / 'nuget-verify-RESULT.json')),
        no_package_redownload_requested=True, target_dlls_loaded=False,
        explicit_certificate_store_changes_requested=False, persistent_configuration_changes_requested=False,
        limitations=['Actual signer, chain, timestamp, warnings and errors must be read from the retained detailed logs.',
                     'Online mode requests online revocation processing; no network trace proves a fresh CRL/OCSP transaction.',
                     'OS-managed certificate caches, root acquisition, existing trust-store state and unrelated concurrent OS activity are not independently traced.',
                     'This command neither executes package payloads nor qualifies native/product behavior.']))
    print(json.dumps(dict(exit_status=result['exit_status'], selected_sdk='10.0.302', archive_unchanged=True,
                         stdout_bytes=result['stdout']['bytes'], stderr_bytes=result['stderr']['bytes'],
                         outcome='LOG_ADJUDICATION_REQUIRED')))
    raise SystemExit(result['exit_status'])


if __name__ == '__main__':
    main()
