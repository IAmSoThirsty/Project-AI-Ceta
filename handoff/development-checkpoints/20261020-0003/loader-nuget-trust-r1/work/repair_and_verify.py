"""Repair an empty trusted-signer policy using separately fetched official metadata.

The original unsuccessful invocation/configuration remain unchanged. Root trust
and online revocation are retained; no package-supplied fingerprint is promoted
to trust without a match in authenticated official repository metadata.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET

from verify_package_signature import (W, S, DOTNET, INPUTS_SHA256, require, digest,
                                      pin, write_json_new, environment, run, utc)

METADATA_URL = 'https://api.nuget.org/v3-index/repository-signatures/5.0.0/index.json'
METADATA_LIMIT = 2 * 1024 * 1024
SIGNER_OID = '2.16.840.1.101.3.4.2.1'


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    require(digest(S / 'packet/INPUTS.json') == INPUTS_SHA256, 'INPUT_PACKET_CHANGED')
    original_pins = json.loads((W / 'INPUT-PINS-BEFORE.json').read_text(encoding='utf-8'))
    before = pin(original_pins['archive']['path'])
    require(before == original_pins['archive'], 'ORIGINAL_ARCHIVE_CHANGED')
    require(pin(DOTNET) == original_pins['installed_dotnet'], 'INSTALLED_DOTNET_CHANGED')
    first_result = json.loads((W / 'nuget-verify-RESULT.json').read_text(encoding='utf-8'))
    first_log = (W / 'nuget-verify.stdout.log').read_text(encoding='utf-8')
    require(first_result['exit_status'] == 1 and 'NU3034:' in first_log
            and 'no trusted signers were specified' in first_log, 'ORIGINAL_POLICY_FAILURE_NOT_PRESERVED')
    original_config = ET.parse(W / 'NuGet.Config')
    config = original_config.getroot()
    trusted = config.find('trustedSigners')
    require(trusted is not None and len(list(trusted)) == 1 and trusted[0].tag == 'clear',
            'ORIGINAL_EMPTY_TRUST_POLICY_CHANGED')
    require(config.find("config/add[@key='signatureValidationMode']").get('value') == 'require',
            'REQUIRED_SIGNATURE_MODE_CHANGED')
    context = ssl.create_default_context()
    require(context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED,
            'METADATA_TLS_VALIDATION_REQUIRED')
    invocation = dict(schema_version=1, request_url=METADATA_URL, started_at=utc(),
                      max_body_bytes=METADATA_LIMIT, timeout_seconds=30,
                      tls_hostname_check=True, tls_certificate_validation='CERT_REQUIRED',
                      redirects_allowed=False, automatic_retries=0, package_download=False)
    write_json_new(W / 'METADATA-INVOKED.json', invocation)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects(),
                                        urllib.request.HTTPSHandler(context=context))
    result = dict(invocation, status='FAILED')
    raw = b''
    try:
        request = urllib.request.Request(METADATA_URL, headers={'Accept-Encoding': 'identity',
                                         'User-Agent': 'CETA-retained-package-signature-verification/1'})
        with opener.open(request, timeout=30) as response:
            result.update(response_status=response.status, final_url=response.geturl(),
                          response_headers=list(response.headers.items()))
            require(response.status == 200 and response.geturl() == METADATA_URL,
                    'OFFICIAL_METADATA_RESPONSE_CHANGED')
            require(response.headers.get('Content-Encoding', 'identity').lower() == 'identity',
                    'METADATA_CONTENT_ENCODING')
            length = response.headers.get('Content-Length')
            require(length is None or (length.isdecimal() and int(length) <= METADATA_LIMIT),
                    'METADATA_CONTENT_LENGTH_LIMIT')
            raw = response.read(METADATA_LIMIT + 1)
            with (W / 'OFFICIAL-REPOSITORY-SIGNATURES.json').open('xb') as output:
                output.write(raw)
            require(0 < len(raw) <= METADATA_LIMIT, 'METADATA_BODY_BOUND')
            require(length is None or len(raw) == int(length), 'METADATA_BODY_TRUNCATED')
        metadata = json.loads(raw.decode('utf-8'))
        require(metadata['allRepositorySigned'] is True
                and type(metadata['signingCertificates']) is list
                and 1 <= len(metadata['signingCertificates']) <= 64, 'METADATA_CERTIFICATE_LIST_INVALID')
        certificates = metadata['signingCertificates']
        fingerprints = []
        for cert in certificates:
            fingerprint = cert['fingerprints'][SIGNER_OID]
            require(re.fullmatch('[0-9a-f]{64}', fingerprint) is not None
                    and cert['subject'] == 'CN=NuGet.org Repository by Microsoft, O=NuGet.org Repository by Microsoft, L=Redmond, S=Washington, C=US',
                    'OFFICIAL_REPOSITORY_CERTIFICATE_METADATA_INVALID')
            fingerprints.append(fingerprint.upper())
        require(len(set(fingerprints)) == len(fingerprints), 'DUPLICATE_REPOSITORY_FINGERPRINT')
        result.update(status='AUTHENTICATED_OFFICIAL_HTTPS_METADATA_RETAINED',
                      certificate_count=len(certificates), fingerprints_sha256=fingerprints,
                      body=dict(path=str(W / 'OFFICIAL-REPOSITORY-SIGNATURES.json'), bytes=len(raw),
                                sha256=digest(W / 'OFFICIAL-REPOSITORY-SIGNATURES.json')))
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        result['ended_at'] = utc()
        write_json_new(W / 'METADATA-ACQUISITION.json', result)
    # This policy is derived solely from the separately fetched service metadata.
    repository = ET.SubElement(trusted, 'repository',
                               name='official-nuget-org', serviceIndex='https://api.nuget.org/v3/index.json')
    for fingerprint in fingerprints:
        ET.SubElement(repository, 'certificate', fingerprint=fingerprint,
                      hashAlgorithm='SHA256', allowUntrustedRoot='false')
    ET.SubElement(repository, 'owners').text = 'Microsoft'
    ET.indent(original_config, space='  ')
    target_config = W / 'NuGet.Repository.Config'
    with target_config.open('xb') as output:
        original_config.write(output, encoding='utf-8', xml_declaration=True)
        output.write(b'\n')
    env, delta = environment()
    write_json_new(W / 'ENVIRONMENT-R2.json', delta)
    repair = dict(schema_version=1, recorded_at=utc(), reason='NU3034 from require mode plus empty trustedSigners',
                  original_config=dict(path=str(W / 'NuGet.Config'), sha256=digest(W / 'NuGet.Config')),
                  original_command_result=dict(path=str(W / 'nuget-verify-RESULT.json'), sha256=digest(W / 'nuget-verify-RESULT.json')),
                  original_source=dict(path=str(W / 'attempt1/verify_package_signature.py'), sha256=digest(W / 'attempt1/verify_package_signature.py')),
                  corrected_config=dict(path=str(target_config), sha256=digest(target_config)),
                  trust_source=dict(path=str(W / 'METADATA-ACQUISITION.json'), sha256=digest(W / 'METADATA-ACQUISITION.json')),
                  signature_validation_mode='require', trusted_repository='https://api.nuget.org/v3/index.json',
                  trusted_owners=['Microsoft'], certificate_fingerprints_sha256=fingerprints,
                  allow_untrusted_root=False, revocation_mode='online',
                  publisher_fingerprint_source='Official HTTPS repository metadata, not the package-reported signer.',
                  host_store_or_persistent_config_changes_requested=False)
    write_json_new(W / 'POLICY-REPAIR.json', repair)
    second = run('nuget-verify-r2', ['nuget', 'verify', before['path'], '--all', '--verbosity', 'detailed',
                                  '--configfile', str(target_config)], env, before,
                 environment_path=W / 'ENVIRONMENT-R2.json')
    print(json.dumps(dict(exit_status=second['exit_status'], metadata_fingerprints=len(fingerprints),
                         archive_unchanged=second['archive_unchanged'], revocation_mode_requested='online',
                         signature_validation_mode='require', outcome='LOG_ADJUDICATION_REQUIRED')))
    raise SystemExit(second['exit_status'])


if __name__ == '__main__':
    main()
