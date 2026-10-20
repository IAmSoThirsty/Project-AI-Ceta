"""Read-only verification of this frozen signature-evidence dataset.

Does not rerun dotnet, access the network, mutate a trust store or execute package
payloads. A successful evidence check is scoped to the retained command result.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

W = Path(__file__).resolve().parent
S = W.parent
INPUTS_SHA256 = '73ec4de8310dad1e0d95f213b93fc656c1a575184215ac49010c0fba0dfea5c1'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def read(name):
    return json.loads((W / name).read_text(encoding='utf-8'))


def actual_pin(path):
    path = Path(path)
    before = path.stat()
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and not path.is_junction(), 'PIN_PATH_INVALID')
    for item in (path, *path.parents):
        require(not item.stat().st_file_attributes & 0x400, 'PIN_REPARSE_PATH')
    digest = sha256(path)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'PIN_CHANGED_DURING_READ')
    return dict(path=str(path), bytes=before.st_size, sha256=digest,
                device=before.st_dev, inode=before.st_ino, mtime_ns=before.st_mtime_ns)


def verify():
    require(sha256(S / 'packet/INPUTS.json') == INPUTS_SHA256, 'INPUT_PACKET_CHANGED')
    inputs = json.loads((S / 'packet/INPUTS.json').read_text(encoding='utf-8'))
    manifest = read('FREEZE-MANIFEST.json')
    require(manifest['schema_version'] == 1 and manifest['scope'] == str(W), 'MANIFEST_SCOPE')
    for name, row in manifest['files'].items():
        path = W / name
        require(path.is_relative_to(W) and '..' not in Path(name).parts
                and path.stat().st_size == row['bytes'] and sha256(path) == row['sha256'],
                'FROZEN_FILE_CHANGED:' + name)
    actual_files = {p.relative_to(W).as_posix() for p in W.rglob('*') if p.is_file()}
    extra_allowed = {'FREEZE-MANIFEST.json', *manifest['post_freeze_receipt_files']}
    require(set(manifest['files']) <= actual_files
            and actual_files <= set(manifest['files']) | extra_allowed, 'UNBOUND_WORK_FILE')
    before = read('INPUT-PINS-BEFORE.json')
    result = read('nuget-verify-r2-RESULT.json')
    trust = read('TRUST-RESULT.json')
    archive_pin = actual_pin(inputs['archive']['path'])
    require(archive_pin == before['archive'] == result['archive_before'] == result['archive_after']
            and archive_pin['bytes'] == inputs['archive']['size']
            and archive_pin['sha256'] == inputs['archive']['sha256'], 'ORIGINAL_ARCHIVE_CHANGED')
    require(actual_pin(before['installed_dotnet']['path']) == before['installed_dotnet'], 'DOTNET_EXECUTABLE_CHANGED')
    require((W / 'sdk-version.stdout.log').read_text(encoding='utf-8').strip() == '10.0.302', 'SDK_VERSION')
    for name in ('sdk-inventory', 'sdk-version', 'nuget-verify-r2'):
        execution = read(name + '-RESULT.json')
        require(execution['exit_status'] == 0 and execution['terminated_for_bound'] is None
                and execution['archive_unchanged'] is True, 'COMMAND_DID_NOT_SUCCEED:' + name)
        for stream in ('stdout', 'stderr'):
            ref = execution[stream]
            require(Path(ref['path']) == W / (name + '.' + stream + '.log')
                    and Path(ref['path']).stat().st_size == ref['bytes']
                    and sha256(ref['path']) == ref['sha256'], 'COMMAND_LOG_CHANGED')
        duration = (datetime.fromisoformat(execution['ended_at'])
                    - datetime.fromisoformat(execution['started_at'])).total_seconds()
        require(0 <= duration <= execution['timeout_seconds'] + 11, 'COMMAND_TIME_BOUND')
    require(result['argv'] == [before['installed_dotnet']['path'], 'nuget', 'verify', archive_pin['path'],
            '--all', '--verbosity', 'detailed', '--configfile', str(W / 'NuGet.Repository.Config')],
            'FINAL_COMMAND_CHANGED')
    log = (W / 'nuget-verify-r2.stdout.log').read_text(encoding='utf-8')
    stderr = (W / 'nuget-verify-r2.stderr.log').read_text(encoding='utf-8')
    require("Successfully verified package 'Microsoft.Debugging.Platform.DbgEng.20260319.1511.0'." in log
            and not stderr and not any(line.startswith(('error:', 'warn:', 'warning:')) for line in log.splitlines()),
            'FINAL_SIGNATURE_DISPOSITION_CHANGED')
    for section in ('author', 'repository'):
        for observed in trust[section]['required_log_fragments']:
            require(observed in log, 'OBSERVED_SIGNATURE_LOG_FRAGMENT_MISSING')
    require(trust['status'] == 'SDK_VERIFIED_RETAINED_PACKAGE_UNDER_EXPLICIT_POLICY'
            and trust['sdk_exit_status'] == 0 and trust['warnings_observed'] == []
            and trust['errors_observed'] == [] and trust['independent_review_required'] is True
            and trust['fresh_crl_or_ocsp_transaction_proven'] is False
            and trust['native_qualification'] is False, 'TRUST_RESULT_SCOPE_CHANGED')
    metadata = read('METADATA-ACQUISITION.json')
    body = read('OFFICIAL-REPOSITORY-SIGNATURES.json')
    url = 'https://api.nuget.org/v3-index/repository-signatures/5.0.0/index.json'
    require(metadata['request_url'] == metadata['final_url'] == url
            and metadata['response_status'] == 200 and metadata['redirects_allowed'] is False
            and metadata['tls_hostname_check'] is True
            and metadata['tls_certificate_validation'] == 'CERT_REQUIRED'
            and metadata['package_download'] is False
            and metadata['body']['sha256'] == sha256(W / 'OFFICIAL-REPOSITORY-SIGNATURES.json')
            and metadata['body']['bytes'] == (W / 'OFFICIAL-REPOSITORY-SIGNATURES.json').stat().st_size,
            'OFFICIAL_METADATA_BINDING_CHANGED')
    published = [row['fingerprints']['2.16.840.1.101.3.4.2.1'].upper() for row in body['signingCertificates']]
    require(body['allRepositorySigned'] is True and published == metadata['fingerprints_sha256'],
            'OFFICIAL_FINGERPRINT_LIST_CHANGED')
    config = ET.parse(W / 'NuGet.Repository.Config').getroot()
    require(config.find("config/add[@key='signatureValidationMode']").get('value') == 'require'
            and len(config.findall('trustedSigners/repository')) == 1
            and not config.findall('trustedSigners/author') and not config.findall('packageSources/add'),
            'TRUST_POLICY_WEAKENED_OR_PACKAGE_SOURCE_ENABLED')
    repository = config.find('trustedSigners/repository')
    require(repository.get('serviceIndex') == 'https://api.nuget.org/v3/index.json'
            and repository.findtext('owners') == 'Microsoft'
            and [cert.get('fingerprint') for cert in repository.findall('certificate')] == published
            and all(cert.get('hashAlgorithm') == 'SHA256' and cert.get('allowUntrustedRoot') == 'false'
                    for cert in repository.findall('certificate')),
            'REPOSITORY_TRUST_NOT_DERIVED_FROM_AUTHENTICATED_METADATA')
    require(trust['repository']['certificate_sha256'] in published, 'USED_REPOSITORY_CERTIFICATE_NOT_PUBLISHED')
    env = read('ENVIRONMENT-R2.json')
    require(env['process_only'] is True and env['set']['NUGET_CERT_REVOCATION_MODE'] == 'online'
            and env['set']['DOTNET_CLI_TELEMETRY_OPTOUT'] == '1'
            and env['set']['DOTNET_GENERATE_ASPNET_CERTIFICATE'] == 'false', 'PROCESS_ENVIRONMENT_WEAKENED')
    require(all(Path(path).is_absolute() and Path(path).is_relative_to(W)
                for path in env['explicit_paths'].values()), 'CLI_PATH_OUTSIDE_SCOPE')
    failure = read('nuget-verify-RESULT.json')
    require(failure['exit_status'] == 1 and 'NU3034:' in (W / 'nuget-verify.stdout.log').read_text(encoding='utf-8'),
            'ORIGINAL_FAILURE_NOT_PRESERVED')
    old = ET.parse(W / 'NuGet.Config').getroot()
    require(old.find('trustedSigners/repository') is None
            and old.find('trustedSigners/author') is None
            and old.find("config/add[@key='signatureValidationMode']").get('value') == 'require',
            'INITIAL_CONFIG_NOT_PRESERVED')
    for ref in trust['unchanged_historical_s1'].values():
        require(sha256(ref['path']) == ref['sha256'], 'HISTORICAL_S1_FILE_CHANGED')
    return dict(status='PASS_FROZEN_SIGNATURE_EVIDENCE', frozen_files=len(manifest['files']),
                archive_sha256=archive_pin['sha256'], selected_sdk='10.0.302', sdk_signature_exit_status=0,
                official_repository_metadata_sha256=metadata['body']['sha256'],
                signature_validation_mode='require', trusted_repository_owners=['Microsoft'],
                allow_untrusted_root=False, revocation_mode_requested='online',
                fresh_crl_or_ocsp_transaction_proven=False, prior_NU3034_preserved=True,
                native_qualification=False, independent_review_required=True)


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2, sort_keys=True))
