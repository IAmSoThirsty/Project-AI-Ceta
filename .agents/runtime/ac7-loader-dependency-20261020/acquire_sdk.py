"""Acquire and inspect the official debugger SDK archive without executing it."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import ssl
import urllib.request
import zipfile

R = Path(__file__).resolve().parent
VERSION = '20260319.1511.0'
NAME = 'microsoft.debugging.platform.dbgeng'
URL = f'https://api.nuget.org/v3-flatcontainer/{NAME}/{VERSION}/{NAME}.{VERSION}.nupkg'
LIMIT = 64 * 1024 * 1024


def write_new(path, raw):
    with path.open('xb') as stream:
        if stream.write(raw) != len(raw):
            raise RuntimeError('SHORT_DEPENDENCY_WRITE')


def main():
    archive = R / f'{NAME}.{VERSION}.nupkg'
    total = 0
    with urllib.request.urlopen(URL, timeout=30, context=ssl.create_default_context()) as response:
        final = response.geturl()
        if not final.startswith('https://api.nuget.org/'):
            raise RuntimeError('UNEXPECTED_PACKAGE_ORIGIN')
        headers = dict(response.headers)
        with archive.open('xb') as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > LIMIT:
                    raise RuntimeError('DEBUGGER_ARCHIVE_TOO_LARGE')
                if output.write(block) != len(block):
                    raise RuntimeError('SHORT_ARCHIVE_WRITE')
    raw = archive.read_bytes()
    assert len(raw) == total
    members = []
    names = set()
    with zipfile.ZipFile(archive) as package:
        if len(package.infolist()) > 4096:
            raise RuntimeError('TOO_MANY_SDK_MEMBERS')
        for item in package.infolist():
            path = PurePosixPath(item.filename)
            if (item.filename in names or path.is_absolute() or '\\' in item.filename
                    or ':' in item.filename or '..' in path.parts
                    or item.file_size > 128 * 1024 * 1024):
                raise RuntimeError('UNSAFE_SDK_MEMBER')
            names.add(item.filename)
            content = package.read(item)  # Includes ZIP CRC validation; no file execution.
            members.append(dict(name=item.filename, bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest()))
            if item.filename.endswith('.nuspec'):
                write_new(R / 'PACKAGE.nuspec', content)
        if sum(item['bytes'] for item in members) > 256 * 1024 * 1024:
            raise RuntimeError('SDK_EXPANDED_BOUND')
    result = dict(source=URL, final_url=final, headers=headers, archive=str(archive),
        archive_bytes=total, archive_sha256=hashlib.sha256(raw).hexdigest(),
        archive_sha512=hashlib.sha512(raw).hexdigest(), members=members,
        package_signature_present='.signature.p7s' in names,
        signature_verification='NOT_RUN', extracted_native_files=False,
        dll_loads=0, debugger_or_worker_launches=0, profile_operations=0,
        installed=False, registry_or_configuration_changed=False)
    write_new(R / 'ACQUISITION.json', (json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(dict(archive_sha256=result['archive_sha256'], bytes=total,
        member_count=len(members), signature_present=result['package_signature_present'],
        debugger_members=[item['name'] for item in members if item['name'].lower().endswith(('dbgeng.h','cdb.exe','windbg.exe'))],
        native_executions=0)))


if __name__ == '__main__':
    main()
