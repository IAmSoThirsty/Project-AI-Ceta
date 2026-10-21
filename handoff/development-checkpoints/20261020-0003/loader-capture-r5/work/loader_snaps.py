"""Dormant, identity-bound loader-snaps producer and conservative text evidence.

No native function is loaded or called on import. _PEB.NtGlobalFlag is private:
its offset must be resolved from the exact local, pinned NTDLL PDB, never a
hard-coded Windows offset. This is diagnostic instrumentation, not product code.
"""
from dataclasses import dataclass
import ctypes as C
import ntpath
import re
import threading
import struct
from pathlib import Path
from capture_core import CaptureError, OwnedIdentity, require, retain

DWORD = C.c_uint32
U64 = C.c_uint64
HANDLE = C.c_void_p
SIZE_T = C.c_size_t
SHOW_LOADER_SNAPS = 2


class PROCESS_BASIC_INFORMATION(C.Structure):
    _fields_ = [('exit_status', C.c_int32), ('peb', HANDLE), ('affinity', SIZE_T),
                ('priority', C.c_int32), ('pid', SIZE_T), ('parent_pid', SIZE_T)]


class SYMBOL_INFOW(C.Structure):
    _fields_ = [('size', DWORD), ('type_index', DWORD), ('reserved', U64 * 2),
                ('index', DWORD), ('symbol_size', DWORD), ('base', U64),
                ('flags', DWORD), ('value', U64), ('address', U64),
                ('register', DWORD), ('scope', DWORD), ('tag', DWORD),
                ('name_length', DWORD), ('max_name_length', DWORD), ('name', C.c_wchar * 1)]


@dataclass(frozen=True, slots=True)
class PebLayout:
    ntdll_sha256: str
    pdb_sha256: str
    peb_size: int
    offset: int
    field_size: int

    def __post_init__(self):
        for value in (self.ntdll_sha256, self.pdb_sha256):
            require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'SNAPS_LAYOUT_PIN_INVALID')
        require(type(self.peb_size) is int and 4 <= self.peb_size <= 65536,
                'SNAPS_PEB_SIZE_INVALID')
        require(type(self.offset) is int and 0 <= self.offset <= self.peb_size - 4
                and self.offset % 4 == 0 and type(self.field_size) is int and self.field_size == 4,
                'SNAPS_FIELD_LAYOUT_INVALID')


def resolve_layout(symbols, kernel, *, context, pdb_path, module_base, module_size,
                   ntdll_sha256, pdb_sha256):
    """Resolve a LOCAL PDB loaded directly (no symbol server/search path).

    The caller pins the exact PDB and checks its CodeView GUID/age against NTDLL
    before this function. DbgHelp is serialized on the calling creator thread.
    Native cleanup failures are retained and never silently retried.
    """
    require(C.sizeof(HANDLE) == 8 and C.sizeof(C.c_wchar) == 2
            and C.sizeof(SYMBOL_INFOW) == 88, 'SNAPS_SYMBOL_X64_ABI_REQUIRED')
    require(type(module_base) is int and module_base > 0, 'SNAPS_SYMBOL_BASE_INVALID')
    require(type(module_size) is int and 0 < module_size <= 64 * 1024 * 1024,
            'SNAPS_SYMBOL_IMAGE_SIZE_INVALID')
    require(type(pdb_path) is str and ntpath.isabs(pdb_path) and '\x00' not in pdb_path
            and not ntpath.splitdrive(pdb_path)[0].startswith('\\\\'),
            'SNAPS_LOCAL_PDB_REQUIRED')
    initialized = False
    primary = None
    custody=dict(state='NOT_ATTEMPTED',context=int(context),pdb_path=pdb_path,
                 module_base=module_base,automatic_retry=False,returned=False)
    def invoke(name,*args):
        custody.update(state=name+'_IN_FLIGHT',returned=False)
        result=getattr(symbols,name)(*args)
        custody.update(state=name+'_RETURNED',returned=True)
        return result
    try:
        require(invoke('SymInitializeW',context, '', False), 'SNAPS_SYMBOL_INITIALIZE_FAILED')
        initialized = True
        # A .pdb itself is the input. This does not request an image's missing
        # symbols, configure a server, or fall back to another module's PDB.
        base = invoke('SymLoadModuleExW',context, None, pdb_path, 'ntdll_local_types', module_base, module_size, None, 0)
        require(base == module_base, 'SNAPS_LOCAL_PDB_LOAD_FAILED')
        storage = C.create_string_buffer(C.sizeof(SYMBOL_INFOW) + 1024)
        info = C.cast(storage, C.POINTER(SYMBOL_INFOW)).contents
        info.size = C.sizeof(SYMBOL_INFOW)
        info.max_name_length = 512
        require(invoke('SymGetTypeFromNameW',context, base, '_PEB', C.byref(info)), 'SNAPS_PEB_TYPE_MISSING')

        def query(index, kind, value):
            require(invoke('SymGetTypeInfo',context, base, index, kind, C.byref(value)),
                    'SNAPS_TYPE_QUERY_FAILED:' + str(kind))
            return value.value

        peb_size = query(info.type_index, 2, U64())  # TI_GET_LENGTH
        count = query(info.type_index, 13, DWORD())  # TI_GET_CHILDRENCOUNT
        require(0 < count <= 1024, 'SNAPS_TYPE_CHILD_COUNT_INVALID')
        class Children(C.Structure):
            _fields_ = [('count', DWORD), ('start', DWORD), ('children', DWORD * count)]
        children = Children(count, 0)
        require(invoke('SymGetTypeInfo',context, base, info.type_index, 7, C.byref(children)),
                'SNAPS_TYPE_CHILDREN_FAILED')
        matches = []
        for index in children.children:
            pointer = HANDLE()
            require(invoke('SymGetTypeInfo',context, base, index, 1, C.byref(pointer)),
                    'SNAPS_FIELD_NAME_FAILED')
            require(pointer.value is not None, 'SNAPS_NULL_FIELD_NAME')
            try:
                # Names come from the pinned PDB; bound the native string read.
                characters = []
                for position in range(128):
                    char = C.c_wchar.from_address(pointer.value + position * 2).value
                    if char == '\x00':
                        break
                    characters.append(char)
                else:
                    raise CaptureError('SNAPS_FIELD_NAME_UNBOUNDED')
                name = ''.join(characters)
                if name == 'NtGlobalFlag':
                    offset = query(index, 10, DWORD())
                    type_id = query(index, 4, DWORD())
                    length = query(type_id, 2, U64())
                    matches.append((offset, length))
            finally:
                custody.update(state='LocalFree_IN_FLIGHT',returned=False,name_pointer=pointer.value)
                freed=kernel.LocalFree(pointer)
                custody.update(state='LocalFree_RETURNED',returned=True)
                require(not freed, 'SNAPS_SYMBOL_NAME_FREE_FAILED')
        require(len(matches) == 1, 'SNAPS_EXACT_GLOBAL_FLAG_FIELD_REQUIRED')
        return PebLayout(ntdll_sha256, pdb_sha256, peb_size, *matches[0])
    except BaseException as error:
        primary = error
        data=BaseException.__dict__['__dict__'].__get__(error)
        dict.update(data,loader_symbol_custody=custody,loader_symbol_api=symbols)
        raise
    finally:
        if initialized and custody['returned']:
            try:
                require(invoke('SymCleanup',context), 'SNAPS_SYMBOL_CLEANUP_PENDING')
            except BaseException as secondary:
                data=BaseException.__dict__['__dict__'].__get__(secondary)
                dict.update(data,loader_symbol_custody=custody,loader_symbol_api=symbols)
                if primary is None:
                    raise
                retain(primary, secondary=secondary)


class LoaderSnaps:
    """One write to exactly four bytes of the fresh child's PEB at CREATE stop.

    State is set BEFORE each effect. Unknown returns retain exact handle/address
    custody, disallow replay, and require an explicit owner-led termination path.
    No rollback write is attempted: the disposable child's lifetime owns flags.
    """
    def __init__(self, kernel, ntdll, identity, layout, *, authorized=False,
                 thread_id=threading.get_ident):
        require(authorized is True, 'SNAPS_EXPLICIT_MEMORY_EFFECT_RELEASE_REQUIRED')
        require(type(identity) is OwnedIdentity and type(layout) is PebLayout, 'SNAPS_TYPED_INPUT_REQUIRED')
        require(C.sizeof(PROCESS_BASIC_INFORMATION) == 48
                and PROCESS_BASIC_INFORMATION.peb.offset == 8
                and PROCESS_BASIC_INFORMATION.pid.offset == 32, 'SNAPS_PBI_X64_ABI_REQUIRED')
        self.kernel, self.ntdll, self.identity, self.layout = kernel, ntdll, identity, layout
        self.thread_id, self.creator_thread = thread_id, thread_id()
        self.state = 'NOT_ATTEMPTED'
        self.process = None
        self.address = None
        self.before = self.after = None
        self.write_count = None

    def _read(self, handle, address):
        output = DWORD()
        count = SIZE_T()
        require(self.kernel.ReadProcessMemory(HANDLE(handle), HANDLE(address), C.byref(output),
                                              4, C.byref(count)) and count.value == 4,
                'SNAPS_EXACT_FLAG_READ_REQUIRED')
        return output.value

    def enable(self, process_handle, pid, creation_time):
        require(self.thread_id() == self.creator_thread, 'SNAPS_CREATOR_THREAD_REQUIRED')
        require(self.state == 'NOT_ATTEMPTED', 'SNAPS_SINGLE_ATTEMPT_REQUIRED')
        require(type(process_handle) is int and process_handle > 0
                and pid == self.identity.pid and creation_time == self.identity.creation_time,
                'SNAPS_EXACT_OWNED_CREATE_STOP_REQUIRED')
        # The port verified GetProcessId/GetProcessTimes on this event handle;
        # repeat the numeric identity before this protected operation.
        require(self.kernel.GetProcessId(HANDLE(process_handle)) == pid, 'SNAPS_HANDLE_PID_CHANGED')
        from win32_debug import FILETIME
        times = [FILETIME() for _ in range(4)]
        require(self.kernel.GetProcessTimes(HANDLE(process_handle), *[C.byref(item) for item in times])
                and times[0].high << 32 | times[0].low == creation_time,
                'SNAPS_HANDLE_CREATION_CHANGED')
        self.process = process_handle
        self.state = 'QUERY_IN_FLIGHT'
        info, length = PROCESS_BASIC_INFORMATION(), DWORD()
        status = self.ntdll.NtQueryInformationProcess(HANDLE(process_handle), 0, C.byref(info),
                                                    C.sizeof(info), C.byref(length))
        self.state = 'QUERY_RETURNED'
        require(status == 0 and length.value == C.sizeof(info) and info.pid == pid,
                'SNAPS_EXACT_PBI_REQUIRED')
        require(info.peb and info.peb % 8 == 0 and info.peb < 0x0000800000000000,
                'SNAPS_PEB_ADDRESS_INVALID')
        self.address = info.peb + self.layout.offset
        self.state = 'PRE_READ_IN_FLIGHT'
        self.before = self._read(process_handle, self.address)
        self.state = 'PRE_READ_CONFIRMED'
        target = self.before | SHOW_LOADER_SNAPS
        if target != self.before:
            value, count = DWORD(target), SIZE_T()
            self.state = 'WRITE_IN_FLIGHT'
            result = self.kernel.WriteProcessMemory(HANDLE(process_handle), HANDLE(self.address),
                                                    C.byref(value), 4, C.byref(count))
            self.write_count = count.value
            self.state = 'WRITE_RETURNED'
            require(result and count.value == 4, 'SNAPS_EXACT_FLAG_WRITE_REQUIRED')
        self.state = 'POST_READ_IN_FLIGHT'
        self.after = self._read(process_handle, self.address)
        require(self.after == target, 'SNAPS_FLAG_READBACK_MISMATCH')
        self.state = 'READBACK_CONFIRMED'
        return self.report()

    def report(self):
        return dict(state=self.state, pid=self.identity.pid, creation_time=self.identity.creation_time,
                    process_handle=self.process, address=self.address, before=self.before, after=self.after,
                    write_count=self.write_count, mask=SHOW_LOADER_SNAPS, automatic_retry=False,
                    restoration='Disposable child exit; no rollback write', layout=dict(
                        ntdll_sha256=self.layout.ntdll_sha256, pdb_sha256=self.layout.pdb_sha256,
                        peb_size=self.layout.peb_size, offset=self.layout.offset, field_size=4))


_PREFIX = r'(?P<pid>[0-9a-fA-F]+):(?P<tid>[0-9a-fA-F]+)\s+@\s+[0-9]+\s+-\s+'
_FAILED = re.compile(_PREFIX + r'LdrpInitializeNode - ERROR: Init routine (?P<entry>[0-9a-fA-F]+) '
                     r'for DLL "(?P<module>[^"\r\n\x00]+)" failed during (?P<phase>DLL_PROCESS_ATTACH)')
_STATUS = re.compile(_PREFIX + r'LdrpInitializationFailure - ERROR: Process initialization failed '
                     r'with status (?P<status>0x[0-9a-fA-F]{8})')


def initialization_evidence(events, identity, exit_status, producer):
    """Exact explicit diagnostics, not last-DLL or exception-address inference.

    Loader text is a version-sensitive, child-origin report, not a guaranteed
    Win32 protocol or proof of underlying root cause. Return UNKNOWN for absent,
    incomplete, conflicting or mismatched evidence. Raw event indexes survive.
    """
    unknown = dict(failure_attribution='UNKNOWN', failed_module=None, failed_phase=None,
                   initialization_status=None, evidence=[], root_cause='UNKNOWN')
    if not producer or producer.get('state') != 'READBACK_CONFIRMED':
        return unknown
    if producer.get('pid') != identity.pid or producer.get('creation_time') != identity.creation_time:
        return unknown
    failures, statuses, modules = [], [], set()
    for row in events:
        data = row['data']
        if row['event_code'] in (3, 6):
            image = data.get('image', {})
            if image.get('state') == 'OBSERVED' and image.get('path'):
                modules.add(ntpath.normcase(image['path'].removeprefix('\\\\?\\')))
        if row['event_code']==1 and data.get('exception_code')==0x40010006 and data.get('first_chance') is True:
            data=data.get('debug_output',{})
        elif row['event_code']!=8:
            continue
        if data.get('read_state') != 'COMPLETE_REPORTED_LENGTH' or data.get('truncated'):
            continue
        try:
            raw = bytes.fromhex(data['raw_hex'])
            text = raw.decode('utf-16-le' if data['unicode'] else 'ascii')
        except (KeyError, ValueError, UnicodeError):
            continue
        # A bare, unterminated prefix may be truncated, including WORD wrap.
        if not text.endswith(('\n', '\x00')):
            continue
        for line in text.rstrip('\x00').splitlines():
            match = _FAILED.fullmatch(line) or _STATUS.fullmatch(line)
            if not match or int(match['pid'], 16) != identity.pid or int(match['tid'], 16) != row['tid']:
                continue
            record = dict(event_index=row['index'], raw_line=line, **match.groupdict())
            if 'module' in record:
                if ntpath.isabs(record['module']):
                    failures.append(record)
            else:
                statuses.append(record)
    choices = {(ntpath.normcase(row['module']), row['phase']) for row in failures}
    codes = {int(row['status'], 16) for row in statuses}
    if len(choices) != 1 or len(codes) != 1 or exit_status not in codes:
        return unknown
    if not all(any(status['event_index'] > failure['event_index'] and status['tid'] == failure['tid']
                   for status in statuses) for failure in failures):
        return unknown
    module, phase = next(iter(choices))
    if module not in modules or not exit_status & 0x80000000:
        return unknown
    return dict(failure_attribution='EXPLICIT_OWNED_CHILD_INITIALIZATION_DIAGNOSTIC',
                failed_module=failures[0]['module'], failed_phase=phase, initialization_status=exit_status,
                evidence=failures + statuses, root_cause='UNKNOWN',
                qualification='Version-sensitive loader diagnostic text corroborated by observed module and exit; '
                              'not proof of the underlying cause or independence from the child.')


def pe_codeview(raw):
    """Read the exact PE32+ RSDS GUID/age, rejecting malformed RVA mappings."""
    require(type(raw) is bytes and 256 <= len(raw) <= 64 * 1024 * 1024, 'SNAPS_PE_SIZE_INVALID')
    def unpack(fmt, offset):
        require(0 <= offset <= len(raw) - struct.calcsize(fmt), 'SNAPS_PE_BOUNDS')
        return struct.unpack_from(fmt, raw, offset)
    require(raw[:2] == b'MZ', 'SNAPS_PE_DOS_INVALID')
    pe, = unpack('<I', 0x3c)
    require(raw[pe:pe + 4] == b'PE\x00\x00', 'SNAPS_PE_SIGNATURE_INVALID')
    machine, count = unpack('<HH', pe + 4)
    optional_size, = unpack('<H', pe + 20)
    optional = pe + 24
    magic, = unpack('<H', optional)
    require(machine == 0x8664 and magic == 0x20b and 0 < count <= 96
            and optional_size >= 112 + 7 * 8, 'SNAPS_PE_X64_REQUIRED')
    directories, = unpack('<I', optional + 108)
    require(directories >= 7, 'SNAPS_PE_DEBUG_DIRECTORY_MISSING')
    rva, size = unpack('<II', optional + 112 + 6 * 8)
    require(size and size % 28 == 0 and size <= 28 * 128, 'SNAPS_PE_DEBUG_DIRECTORY_INVALID')
    mappings = []
    for index in range(count):
        section = optional + optional_size + index * 40
        virtual_size, virtual_address, file_size, file_offset = unpack('<IIII', section + 8)
        if virtual_address <= rva and rva + size <= virtual_address + min(virtual_size, file_size):
            mappings.append(file_offset + rva - virtual_address)
    require(len(mappings) == 1, 'SNAPS_PE_DEBUG_RVA_AMBIGUOUS')
    identities = []
    for offset in range(mappings[0], mappings[0] + size, 28):
        kind, amount, _, location = unpack('<IIII', offset + 12)
        if kind != 2:
            continue
        require(24 <= amount <= 4096 and location + amount <= len(raw), 'SNAPS_PE_CODEVIEW_BOUNDS')
        value = raw[location:location + amount]
        require(value[:4] == b'RSDS' and value[-1:] == b'\x00', 'SNAPS_PE_RSDS_REQUIRED')
        identities.append(dict(guid_hex=value[4:20].hex(), age=struct.unpack_from('<I', value, 20)[0]))
    require(len(identities) == 1, 'SNAPS_EXACT_CODEVIEW_IDENTITY_REQUIRED')
    return identities[0]


def pdb_codeview(raw):
    """Read distinct MSF7 information/DBI identities, without a native load.

    NewDBIHdr is the 64-byte Microsoft microsoft-pdb PDB/dbi/dbi.h layout.
    Only modern AMD64 DBI version 19990903 is admitted; age-zero/legacy files
    are deliberately unsupported rather than admitted through a fallback.
    """
    require(type(raw) is bytes and 56 <= len(raw) <= 256 * 1024 * 1024,
            'SNAPS_PDB_SIZE_INVALID')
    require(raw[:32] == b'Microsoft C/C++ MSF 7.00\r\n\x1aDS\x00\x00\x00', 'SNAPS_PDB_MSF7_REQUIRED')
    block, free_map, count, directory_size, reserved, directory_map = struct.unpack_from('<6I', raw, 32)
    require(block in (512, 1024, 2048, 4096) and count * block == len(raw)
            and free_map in (1,2) and reserved == 0 and 4 <= directory_size <= 4 * 1024 * 1024,
            'SNAPS_PDB_SUPERBLOCK_INVALID')
    def page(number):
        require(type(number) is int and 0 <= number < count, 'SNAPS_PDB_PAGE_BOUNDS')
        return raw[number * block:(number + 1) * block]
    pages = (directory_size + block - 1) // block
    require(pages * 4 <= block, 'SNAPS_PDB_DIRECTORY_MAP_UNSUPPORTED')
    indices = struct.unpack_from('<' + 'I' * pages, page(directory_map))
    directory = b''.join(page(i) for i in indices)[:directory_size]
    require(len(directory) >= 4, 'SNAPS_PDB_DIRECTORY_MISSING')
    streams, = struct.unpack_from('<I', directory)
    require(4 <= streams <= 65536 and 4 + streams * 4 <= len(directory), 'SNAPS_PDB_STREAM_COUNT_INVALID')
    sizes = struct.unpack_from('<' + 'I' * streams, directory, 4)
    cursor = 4 + streams * 4
    selected = {}
    for stream, amount in enumerate(sizes):
        pieces = 0 if amount == 0xffffffff else (amount + block - 1) // block
        require(pieces * 4 <= len(directory) - cursor, 'SNAPS_PDB_STREAM_MAP_BOUNDS')
        pieces_indices = struct.unpack_from('<' + 'I' * pieces, directory, cursor)
        cursor += pieces * 4
        require(all(number < count for number in pieces_indices), 'SNAPS_PDB_PAGE_BOUNDS')
        if stream in (1,3):
            minimum=28 if stream==1 else 64
            require(minimum <= amount <= 4 * 1024 * 1024, 'SNAPS_PDB_REQUIRED_STREAM_SIZE_INVALID')
            selected[stream]=b''.join(page(i) for i in pieces_indices)[:amount]
    require(cursor==len(directory), 'SNAPS_PDB_DIRECTORY_TRAILING_BYTES')
    require(set(selected)=={1,3}, 'SNAPS_PDB_INFORMATION_OR_DBI_MISSING')
    information,dbi=selected[1],selected[3]
    version, signature, age = struct.unpack_from('<III', information)
    require(version >= 20000404 and age > 0, 'SNAPS_PDB_INFO_VERSION_INVALID')
    dbi_signature,dbi_version,dbi_age=struct.unpack_from('<iII',dbi)
    flags,machine,reserved=struct.unpack_from('<HHI',dbi,56)
    require(dbi_signature==-1 and dbi_version==19990903 and machine==0x8664
            and reserved==0 and not flags&~7, 'SNAPS_PDB_DBI_HEADER_INVALID')
    require(dbi_age>0, 'SNAPS_PDB_DBI_NONZERO_AGE_REQUIRED')
    sizes=[struct.unpack_from('<i',dbi,offset)[0] for offset in (24,28,32,36,40,48,52)]
    require(all(amount>=0 for amount in sizes) and sum(sizes)<=len(dbi)-64,
            'SNAPS_PDB_DBI_SUBSTREAM_BOUNDS')
    return dict(guid_hex=information[12:28].hex(),info_age=age,dbi_age=dbi_age,
                dbi_signature=dbi_signature,dbi_version=dbi_version,dbi_machine=machine)


def match_codeview(image,pdb):
    """Microsoft PDB1::OpenValidate4 GUID/age rule with mandatory modern DBI.

    Primary source: microsoft/microsoft-pdb PDB/dbi/pdb.cpp:762-815.
    A PDB information age can increase without a relink. DBI age still must
    equal the image age. Keep all three observations instead of overwriting
    one age with another. The vendor's old age-zero fallback is not admitted.
    """
    require(type(image) is dict and set(image)=={'guid_hex','age'}
            and type(pdb) is dict and set(pdb)=={'guid_hex','info_age','dbi_age',
                'dbi_signature','dbi_version','dbi_machine'}, 'SNAPS_CODEVIEW_SHAPE_INVALID')
    for guid in (image['guid_hex'],pdb['guid_hex']):
        require(type(guid) is str and re.fullmatch('[0-9a-f]{32}',guid) and guid!='0'*32,
                'SNAPS_CODEVIEW_GUID_INVALID')
    for age in (image['age'],pdb['info_age'],pdb['dbi_age']):
        require(type(age) is int and 0<age<=0xffffffff, 'SNAPS_CODEVIEW_AGE_INVALID')
    require(pdb['dbi_signature']==-1 and pdb['dbi_version']==19990903 and pdb['dbi_machine']==0x8664,
            'SNAPS_PDB_DBI_HEADER_INVALID')
    require(image['guid_hex']==pdb['guid_hex'] and pdb['info_age']>=image['age']
            and pdb['dbi_age']==image['age'], 'SNAPS_PDB_NTDLL_MISMATCH')
    return dict(rule='MICROSOFT_OPENVALIDATE4_REQUIRED_MODERN_DBI_V1',guid_hex=image['guid_hex'],
        image_age=image['age'],info_age=pdb['info_age'],dbi_age=pdb['dbi_age'],
        dbi_signature=pdb['dbi_signature'],dbi_version=pdb['dbi_version'],dbi_machine=pdb['dbi_machine'])


def prepare_producer(kernel, pins, *, authorized=False):
    """Dormant protected boundary; exact local PDB and acquired DbgHelp required.

    Only the already-created debug-event process handle is subsequently used.
    No OpenProcess/attach/symbol-server/profile/registry API exists here.
    """
    require(authorized is True, 'SNAPS_EXPLICIT_MEMORY_EFFECT_RELEASE_REQUIRED')
    from win32_debug import file_pin
    require(type(pins) is dict and set(pins) == {'ntdll', 'pdb', 'dbghelp', 'dbgcore'},
            'SNAPS_COMPLETE_LOCAL_INPUT_PINS_REQUIRED')
    for row in pins.values():
        require(file_pin(row['path']) == row, 'SNAPS_INPUT_PIN_CHANGED')
    ntdll, pdb, dbghelp, dbgcore = (Path(pins[name]['path']) for name in ('ntdll', 'pdb', 'dbghelp', 'dbgcore'))
    require(ntdll.name.lower() == 'ntdll.dll' and pdb.suffix.lower() == '.pdb'
            and dbghelp.name.lower() == 'dbghelp.dll' and dbgcore.name.lower() == 'dbgcore.dll'
            and dbghelp.parent == dbgcore.parent, 'SNAPS_INPUT_PATH_INVALID')
    project=Path('T:/00-Active/Project-AI-CETA')
    require(all(path.resolve().is_relative_to(project) for path in (pdb,dbghelp,dbgcore)),
            'SNAPS_PROJECT_LOCAL_DEPENDENCIES_REQUIRED')
    import os
    require(ntdll == Path(os.environ['SystemRoot'])/'System32/ntdll.dll', 'SNAPS_SYSTEM_NTDLL_REQUIRED')
    match_codeview(pe_codeview(ntdll.read_bytes()),pdb_codeview(pdb.read_bytes()))
    # Explicit full paths, DLL_LOAD_DIR | SYSTEM32. The extracted bytes must
    # separately match the already acquired official package member hashes.
    native = C.WinDLL(str(ntdll), use_last_error=True, winmode=0x800)
    symbols = C.WinDLL(str(dbghelp), use_last_error=True, winmode=0x900)
    declarations = dict(SymInitializeW=([HANDLE, C.c_wchar_p, C.c_int32], C.c_int32),
        SymLoadModuleExW=([HANDLE, HANDLE, C.c_wchar_p, C.c_wchar_p, U64, DWORD, HANDLE, DWORD], U64),
        SymGetTypeFromNameW=([HANDLE, U64, C.c_wchar_p, C.POINTER(SYMBOL_INFOW)], C.c_int32),
        SymGetTypeInfo=([HANDLE, U64, DWORD, C.c_int, HANDLE], C.c_int32),
        SymCleanup=([HANDLE], C.c_int32))
    for name, (args, result) in declarations.items():
        function = getattr(symbols, name); function.argtypes = args; function.restype = result
    native.NtQueryInformationProcess.argtypes = [HANDLE, DWORD, HANDLE, DWORD, C.POINTER(DWORD)]
    native.NtQueryInformationProcess.restype = C.c_int32
    for name, args, result in (
        ('WriteProcessMemory', [HANDLE, HANDLE, HANDLE, SIZE_T, C.POINTER(SIZE_T)], C.c_int32),
        ('GetCurrentProcess', [], HANDLE), ('LocalFree', [HANDLE], HANDLE)):
        function = getattr(kernel, name); function.argtypes = args; function.restype = result
    layout = resolve_layout(symbols, kernel, context=kernel.GetCurrentProcess(),
                            pdb_path=str(pdb), module_base=0x10000000,
                            module_size=struct.unpack_from('<I',ntdll.read_bytes(),
                                struct.unpack_from('<I',ntdll.read_bytes(),0x3c)[0]+24+56)[0],
                            ntdll_sha256=pins['ntdll']['sha256'], pdb_sha256=pins['pdb']['sha256'])
    for row in pins.values():
        require(file_pin(row['path']) == row, 'SNAPS_INPUT_CHANGED_AFTER_TYPE_RESOLUTION')
    return native, layout


def open_producer(kernel, identity, pins, *, authorized=False):
    native, layout = prepare_producer(kernel, pins, authorized=authorized)
    return LoaderSnaps(kernel, native, identity, layout, authorized=authorized)
