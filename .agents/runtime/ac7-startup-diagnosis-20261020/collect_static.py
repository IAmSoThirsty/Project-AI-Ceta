"""Bounded file-only AC7 evidence collection. Never imports candidate modules or DLLs."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import struct

F = Path(r'T:\00-Active\Project-AI-CETA')
R = F / '.agents/runtime/ac7-token-contract-20261020'
Q = R / 'q-6be3c32cb832461093c6d15dc9c538f8'
C = F / '.agents/ac7-token-contract-20261020'
O = F / '.agents/runtime/ac7-startup-diagnosis-20261020'
FIX = Q / 'native-fixtures/ac1-ec4105bbf9af49028b30c90895b61e3d'
EXPECTED = '3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc'
MAX_FILE = 32 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    raw = path.read_bytes()
    st = path.stat()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw),
            'mtime_ns': st.st_mtime_ns, 'device': st.st_dev, 'inode': st.st_ino}


def write(name, value):
    dest = O / name
    assert dest.parent == O and not dest.exists(), dest
    with dest.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


class PE:
    def __init__(self, path):
        self.path = path
        assert path.stat().st_size <= MAX_FILE
        self.b = path.read_bytes()
        assert self.b[:2] == b'MZ'
        self.nt = self.u(0x3c, 'I')
        assert self.b[self.nt:self.nt + 4] == b'PE\0\0'
        self.opt = self.nt + 24
        self.magic = self.u(self.opt, 'H')
        assert self.magic in (0x10b, 0x20b)
        self.width = 8 if self.magic == 0x20b else 4
        self.base = self.u(self.opt + (24 if self.width == 8 else 28), 'Q' if self.width == 8 else 'I')
        self.headers = self.u(self.opt + 60, 'I')
        nsec = self.u(self.nt + 6, 'H')
        assert 0 < nsec <= 96
        self.sections = []
        start = self.opt + self.u(self.nt + 20, 'H')
        for i in range(nsec):
            at = start + i * 40
            self.check(at, 40)
            self.sections.append({'name': self.b[at:at + 8].split(b'\0')[0].decode('ascii', 'replace'),
                'virtual_size': self.u(at + 8, 'I'), 'rva': self.u(at + 12, 'I'),
                'raw_size': self.u(at + 16, 'I'), 'file_offset': self.u(at + 20, 'I'),
                'characteristics': self.u(at + 36, 'I')})
        ndir_at = self.opt + (108 if self.width == 8 else 92)
        count = self.u(ndir_at, 'I')
        assert count <= 16
        self.dirs = [(self.u(ndir_at + 4 + i * 8, 'I'), self.u(ndir_at + 8 + i * 8, 'I'))
                     for i in range(count)]
        self.dirs += [(0, 0)] * (16 - len(self.dirs))

    def check(self, at, size):
        assert type(at) is int and at >= 0 and size >= 0 and at + size <= len(self.b), (at, size)

    def u(self, at, fmt):
        self.check(at, struct.calcsize('<' + fmt))
        return struct.unpack_from('<' + fmt, self.b, at)[0]

    def off(self, rva, size=1):
        matches = []
        if 0 <= rva and rva + size <= self.headers:
            matches.append(rva)
        for row in self.sections:
            delta = rva - row['rva']
            if 0 <= delta and delta + size <= row['raw_size']:
                matches.append(row['file_offset'] + delta)
        assert len(matches) == 1, (rva, size, matches)
        self.check(matches[0], size)
        return matches[0]

    def z(self, at, limit=1024):
        self.check(at, 1)
        end = self.b.find(b'\0', at, min(len(self.b), at + limit))
        assert end >= at, ('unterminated', at)
        return self.b[at:end].decode('ascii', 'strict')

    def symbols(self, rva):
        rows = []
        for i in range(8192):
            at = self.off(rva + i * self.width, self.width)
            val = self.u(at, 'Q' if self.width == 8 else 'I')
            if not val:
                return rows
            if val & (1 << (self.width * 8 - 1)):
                rows.append({'ordinal': val & 0xffff, 'thunk_file_offset': at})
            else:
                name_at = self.off(val, 3)
                rows.append({'name': self.z(name_at + 2), 'name_file_offset': name_at + 2,
                             'thunk_file_offset': at})
        raise ValueError('thunk bound')

    def imports(self, delay=False):
        rva, size = self.dirs[13 if delay else 1]
        if not rva and not size:
            return []
        assert rva and size
        width = 32 if delay else 20
        rows = []
        for i in range(min(1024, size // width)):
            at = self.off(rva + i * width, width)
            values = [self.u(at + k * 4, 'I') for k in range(width // 4)]
            if not any(values):
                return rows
            if delay:
                attrs, name, _, iat, ilt, *_ = values
                assert attrs in (0, 1)
                if attrs == 0:
                    name -= self.base
                    ilt -= self.base
                    iat -= self.base
            else:
                ilt, _, _, name, iat = values
            symbols = self.symbols(ilt or iat)
            rows.append({'dll': self.z(self.off(name), 256), 'descriptor_file_offset': at,
                         'lookup_rva': ilt or iat, 'iat_rva': iat, 'symbols': symbols,
                         'symbol_count': len(symbols)})
        raise ValueError('no descriptor terminator within directory/bound')

    def forwarded(self, wanted):
        rva, size = self.dirs[0]
        if not rva:
            return []
        at = self.off(rva, 40)
        base, nfun, nname = (self.u(at + k, 'I') for k in (16, 20, 24))
        funcs, names, ords = (self.u(at + k, 'I') for k in (28, 32, 36))
        assert nfun <= 65536 and nname <= 65536
        result = []
        for i in range(nname):
            name_rva = self.u(self.off(names + 4 * i, 4), 'I')
            name = self.z(self.off(name_rva))
            if name not in wanted:
                continue
            ordinal = self.u(self.off(ords + 2 * i, 2), 'H')
            assert ordinal < nfun
            target = self.u(self.off(funcs + 4 * ordinal, 4), 'I')
            if rva <= target < rva + size:
                result.append({'imported_name': name, 'ordinal': ordinal + base,
                               'forwarder': self.z(self.off(target)), 'forwarder_file_offset': self.off(target)})
        return result

    def record(self, wanted=()):
        return {'artifact': identity(self.path), 'machine': hex(self.u(self.nt + 4, 'H')),
            'bits': self.width * 8, 'optional_header_file_offset': self.opt,
            'required_os_header': [self.u(self.opt + 40, 'H'), self.u(self.opt + 42, 'H')],
            'subsystem_version_header': [self.u(self.opt + 48, 'H'), self.u(self.opt + 50, 'H')],
            'subsystem': self.u(self.opt + 68, 'H'), 'dll_characteristics': hex(self.u(self.opt + 70, 'H')),
            'entry_rva': self.u(self.opt + 16, 'I'), 'image_base': self.base,
            'sections': self.sections, 'data_directories': self.dirs,
            'normal_imports': self.imports(), 'delay_imports': self.imports(True),
            'selected_imported_export_forwarders': self.forwarded(set(wanted))}


def main():
    assert O.exists()
    receipts = [R / n for n in ('AUTHORIZED-AC7-TERMINAL.json', 'AUTHORIZED-AC7-COMMAND.json',
        'AUTHORIZED-AC7.stdout', 'AUTHORIZED-AC7.stderr', 'APPROVED-QUALIFICATION.json',
        'APPROVED-QUALIFICATION.stdout', 'APPROVED-QUALIFICATION.stderr', 'build-r2/BUILD.json',
        'startup-diagnostics-r1/EVENT-OBSERVATIONS.json')]
    receipts += [Q / n for n in ('RESULT.json', 'PROFILE-STATE.json', 'RETIREMENT.json',
        'CREATE-RETURN.json', 'DELETE-RETURN.json', 'POST-DELETE-OBSERVATION.json',
        'PROBE-BINDING.json', 'CANDIDATE-BEFORE.json', 'PATH-LAYOUT.json')]
    receipts += [FIX / n for n in ('native-profile-r2.json', 'LAUNCH-PATHS.json', 'SETUP.json', 'ACL-OPERATIONS.jsonl')]
    sources = [C / n for n in ('src/ceta/supervisor/windows_jobs.py', 'src/ceta/supervisor/isolated_worker.py',
        'native/windows_broker/isolated_worker.rs', 'tools/qualify_isolated_worker.py')]
    sources += [Q / 'native_fixture_support.py', Q / 'ac3_support.py',
        F / '.agents/runtime/ac1-20261014/native_fixture_support.py',
        F / '.agents/runtime/ac3-20261014/ac3_support.py']
    images = [R / 'build-r2/isolated_worker.exe', Q / 'build-r2/isolated_worker.exe', FIX / 'assets/isolated_worker.exe']
    before = [identity(p) for p in receipts + sources + images]
    assert all(identity(p)['sha256'] == EXPECTED for p in images)
    frozen = json.loads((Q / 'CANDIDATE-BEFORE.json').read_text(encoding='utf-8'))
    bindings = []
    for p in sources[:3]:
        relative = p.relative_to(C).as_posix()
        entry = frozen.get(relative)
        bindings.append({'path': str(p), 'candidate_relative': relative, 'recorded': entry,
                         'actual_sha256': identity(p)['sha256'],
                         'matches_recorded': bool(entry and entry['sha256'] == identity(p)['sha256'])})
    assert all(row['matches_recorded'] for row in bindings), bindings
    tool_receipt = json.loads((R / 'APPROVED-QUALIFICATION.json').read_text(encoding='utf-8'))
    assert identity(sources[3])['sha256'] == tool_receipt['tool_sha256']
    bindings.append({'path': str(sources[3]), 'binding_source': str(R / 'APPROVED-QUALIFICATION.json'),
        'recorded_sha256': tool_receipt['tool_sha256'], 'actual_sha256': identity(sources[3])['sha256'],
        'matches_recorded': True})
    captures = {}
    for p in receipts:
        if p.suffix.lower() == '.json':
            captures[str(p)] = json.loads(p.read_text(encoding='utf-8-sig'))
    write('INPUT-RECEIPTS.json', {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'identities_before': before, 'source_candidate_snapshot_bindings': bindings,
        'json_receipts': captures, 'scope': 'Historical evidence read; no reenactment or native target execution'})
    selected = {'launch', '_environment', 'environment', '_local_appdata', 'native_volume_path',
                'run_native_probe', 'prepare_fixture', 'check_launch_paths', 'pipe', 'run_probe', '_driver'}
    excerpts = []
    for p in sources:
        if p.suffix != '.py':
            continue
        text = p.read_text(encoding='utf-8-sig')
        lines = text.splitlines()
        tree = ast.parse(text, filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in selected:
                excerpts.append({'path': str(p), 'file_sha256': identity(p)['sha256'], 'name': node.name,
                    'start_line': node.lineno, 'end_line': node.end_lineno,
                    'text': '\n'.join(lines[node.lineno - 1:node.end_lineno])})
    write('SOURCE-EXCERPTS.json', {'method': 'AST ranges from pinned source; candidate modules not imported', 'excerpts': excerpts})
    worker = PE(images[1]).record()
    assert sum(r['symbol_count'] for r in worker['normal_imports']) == 191
    system32 = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
    candidates = []
    for imp in worker['normal_imports']:
        dll = imp['dll']
        assert Path(dll).name == dll
        if dll.lower().startswith(('api-ms-', 'ext-ms-')):
            candidates.append({'import': dll, 'coverage': 'API-set contract; physical-file and host mapping not resolved'})
            continue
        target = system32 / dll
        try:
            parsed = PE(target).record(r.get('name') for r in imp['symbols'] if 'name' in r)
            candidates.append({'import': dll, 'coverage': 'On-disk System32 candidate only; not evidence of actual loader selection', 'pe': parsed})
        except (OSError, AssertionError, ValueError, UnicodeError) as error:
            candidates.append({'import': dll, 'coverage': 'unavailable/unsupported',
                'candidate_path': str(target), 'error_type': type(error).__name__, 'error': str(error)})
    write('PE-DEPENDENCIES.json', {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'method': 'Bounded original-file PE parser; normal/delay imports and selected direct-import forwarders',
        'bounds': {'max_file_bytes': MAX_FILE, 'max_sections': 96, 'max_import_descriptors': 1024,
                   'max_thunks_per_descriptor': 8192, 'max_export_names': 65536, 'max_dependency_files': 7,
                   'depth': 'worker plus one on-disk level; dependency edges reported but not recursively resolved'},
        'limitations': ['No LoadLibrary, process attach, initialization, API-set mapping, SxS or KnownDLL resolution',
            'System32 candidates were read now, not measured from the historical worker address space',
            'Static graph does not establish DLL initialization order, success or the failing DLL',
            'Header OS/subsystem versions do not establish compiler target defaults or platform compatibility'],
        'worker': worker, 'system32_candidates': candidates,
        'asset_directory_entries': [{'name': p.name, 'is_file': p.is_file(), 'bytes': p.stat().st_size}
                                    for p in sorted((FIX / 'assets').iterdir())]})
    after = [identity(p) for p in receipts + sources + images]
    drift = [{'path': a['path'], 'before': b, 'after': a} for b, a in zip(before, after) if b != a]
    write('FINAL-INPUT-PRESERVATION.json', {'identities_after': after, 'drift': drift, 'drift_count': len(drift),
        'target_execution': False, 'configuration_changes': False, 'candidate_changes': False})
    assert not drift
    print(json.dumps({'input_files': len(before), 'source_bindings': len(bindings), 'source_excerpts': len(excerpts),
        'worker_sha256': worker['artifact']['sha256'], 'normal_import_dlls': len(worker['normal_imports']),
        'normal_import_symbols': sum(r['symbol_count'] for r in worker['normal_imports']),
        'system32_candidates_parsed': sum('pe' in x for x in candidates), 'input_drift': len(drift)}, indent=2))


if __name__ == '__main__':
    main()
