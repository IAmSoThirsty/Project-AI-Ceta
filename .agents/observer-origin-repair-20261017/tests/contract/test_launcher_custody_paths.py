"""Real disposable Windows custody files/byte locks; no workload launch."""
from pathlib import Path
from types import SimpleNamespace
import ctypes
from ctypes import wintypes
import os
import struct
import unittest
import uuid
from unittest.mock import patch

from ceta.application import lifecycle
from ceta.application.lifecycle import LauncherCustodyIncomplete, LauncherShutdownCustody

ROOT=Path(__file__).resolve().parents[2]
FIXTURE_ROOT=ROOT/'.agents/fixtures/launcher-custody-paths'
NATIVE_FILE_OBSERVATIONS=[]

def io_path(path):
    return Path('\\\\?\\'+str(path))

def units(path):
    return len(str(path).encode('utf-16-le'))//2

def junction(path, target):
    """Create one owned NTFS mount-point fixture without launching a process."""
    io_path(path).mkdir()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,
        wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.DeviceIoControl.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,
        ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    kernel.DeviceIoControl.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    kernel.GetHandleInformation.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.GetHandleInformation.restype=wintypes.BOOL
    handle=kernel.CreateFileW(str(io_path(path)),0x40000000,0,None,3,0x02200000,None)
    if handle in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
    substitute=('\\??\\'+str(target)).encode('utf-16-le');display=str(target).encode('utf-16-le')
    payload=substitute+b'\0\0'+display+b'\0\0'
    raw=struct.pack('<IHHHHHH',0xA0000003,8+len(payload),0,0,len(substitute),len(substitute)+2,len(display))+payload
    buffer=ctypes.create_string_buffer(raw);used=wintypes.DWORD()
    try:
        if not kernel.DeviceIoControl(handle,0x000900A4,buffer,len(raw),None,0,ctypes.byref(used),None):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        if not kernel.CloseHandle(handle):raise ctypes.WinError(ctypes.get_last_error())
    flags=wintypes.DWORD();ctypes.set_last_error(0)
    valid=kernel.GetHandleInformation(handle,ctypes.byref(flags));error=ctypes.get_last_error()
    if valid or error!=6:raise AssertionError(('creation handle retirement unobserved',bool(valid),error))
    facts=io_path(path).lstat()
    if not facts.st_file_attributes & 0x400:raise AssertionError('native junction was not observed')
    NATIVE_FILE_OBSERVATIONS.append(dict(kind='owned-native-junction',path=str(path),target=str(target),
        device=facts.st_dev,inode=facts.st_ino,reparse_attribute=facts.st_file_attributes,
        creation_handle_closed=True,post_close_GetHandleInformation_error=error))

class LauncherCustodyPathTests(unittest.TestCase):
    def profile(self, *, temporary_units=None, root_units=None):
        self.assertEqual(os.name,'nt')
        root=FIXTURE_ROOT/uuid.uuid4().hex
        target=(temporary_units-(1+len(LauncherShutdownCustody._RECORD_NAME)+1+32+4)
            if temporary_units is not None else root_units)
        if target is not None:
            self.assertGreater(target,units(root)+1)
            while target-units(root)>82:root=root/('p'*80)
            root=root/('p'*(target-units(root)-1))
            self.assertEqual(units(root),target)
        io_path(root).mkdir(parents=True,exist_ok=False)
        return root

    def custody(self, root):
        value=LauncherShutdownCustody(root);self.addCleanup(value.close);return value

    def test_native_temporary_boundary259_260_261_preserves_pending_profile(self):
        for length in (259,260,261):
            with self.subTest(temporary_units=length):
                root=self.profile(temporary_units=length);custody=self.custody(root)
                opened=[];original=os.open
                def observe(path,flags,*args,**kwargs):
                    if str(path).endswith('.tmp'):opened.append(str(path))
                    return original(path,flags,*args,**kwargs)
                with patch.object(lifecycle.os,'open',observe):record=custody.reserve_launch()
                self.assertEqual(custody.path,root/LauncherShutdownCustody._RECORD_NAME)
                self.assertEqual(record['state'],'PENDING');self.assertEqual(len(opened),1)
                logical=opened[0][4:] if opened[0].startswith('\\\\?\\') else opened[0]
                self.assertEqual(units(logical),length)
                wire=io_path(custody.path).read_bytes();info=io_path(custody.path).stat()
                custody.close();self.assertIsNone(custody._lock_descriptor)
                restart=self.custody(root)
                self.assertEqual(restart.record,record)
                with self.assertRaises(LauncherCustodyIncomplete):restart.reserve_launch()
                self.assertEqual(io_path(custody.path).read_bytes(),wire)
                NATIVE_FILE_OBSERVATIONS.append(dict(kind='temporary-boundary',logical_units=length,
                    opened_path=opened[0],profile_path=str(root),record_device=info.st_dev,record_inode=info.st_ino,
                    pending_fence_observed=True,lock_released=restart._lock_descriptor is None))

    def test_native_root_record_and_lock_above260_reopen_exact_pending_record(self):
        root=self.profile(root_units=350);first=self.custody(root)
        record=first.reserve_launch();self.assertGreater(units(first._lock_path),260)
        descriptor=first._lock_descriptor;info=os.fstat(descriptor)
        second=self.custody(root)
        with self.assertRaisesRegex(RuntimeError,'LAUNCHER_CUSTODY_LOCK_UNAVAILABLE'):second.acquire()
        self.assertIsNone(second._lock_descriptor)
        changed=first.mark_start_requested();self.assertEqual(changed['revision'],2)
        first.close()
        with self.assertRaises(OSError):os.fstat(descriptor)
        third=self.custody(root);self.assertEqual(third.record,changed)
        with self.assertRaises(LauncherCustodyIncomplete):third.reserve_launch()
        self.assertEqual(record['record_id'],changed['record_id'])
        NATIVE_FILE_OBSERVATIONS.append(dict(kind='long-profile-and-byte-lock',root_units=units(root),
            lock_units=units(first._lock_path),record_units=units(first.path),lock_device=info.st_dev,
            lock_inode=info.st_ino,competing_handle_denied=True,closed_descriptor_observed=True))

    def test_preexisting_temporary_collision_is_never_deleted(self):
        root=self.profile();custody=self.custody(root);fixed='a'*32
        temporary=custody.path.with_name(custody.path.name+'.'+fixed+'.tmp')
        sentinel=b'Owned negative fixture: preserve this preexisting file.'
        with io_path(temporary).open('xb') as stream:stream.write(sentinel)
        before=io_path(temporary).stat()
        with patch.object(lifecycle.uuid,'uuid4',return_value=SimpleNamespace(hex=fixed)):
            with self.assertRaises(FileExistsError):custody.reserve_launch()
        self.assertEqual(io_path(temporary).read_bytes(),sentinel)
        after=io_path(temporary).stat()
        self.assertEqual((before.st_dev,before.st_ino,before.st_size),(after.st_dev,after.st_ino,after.st_size))
        self.assertFalse(io_path(custody.path).exists());self.assertIsNone(custody._lock_descriptor)

    def test_primary_survives_partial_write_and_simultaneous_close_refusal(self):
        for kind in (KeyboardInterrupt,SystemExit):
            with self.subTest(primary=kind.__name__):
                root=self.profile();custody=self.custody(root)
                primary,secondary=kind('owned-partial-write-primary'),RuntimeError('controlled-close-refusal')
                original_open,original_write,original_close=os.open,os.write,os.close
                descriptors=[];close_calls=[];observed=[]
                def opened(path,flags,*args,**kwargs):
                    descriptor=original_open(path,flags,*args,**kwargs)
                    if str(path).endswith('.tmp'):descriptors.append(descriptor)
                    return descriptor
                def written(descriptor,wire):
                    if descriptor in descriptors:original_write(descriptor,wire[:1]);raise primary
                    return original_write(descriptor,wire)
                def closed(descriptor):
                    if descriptor in descriptors:close_calls.append(descriptor);raise secondary
                    return original_close(descriptor)
                try:
                    with patch.object(lifecycle.os,'open',opened),patch.object(lifecycle.os,'write',written),patch.object(lifecycle.os,'close',closed):
                        try:custody.reserve_launch()
                        except BaseException as error:observed.append(error)
                    self.assertEqual(len(descriptors),1)
                    descriptor=descriptors[0];pending=os.fstat(descriptor)
                    self.assertEqual(pending.st_size,1);self.assertEqual(len(close_calls),1)
                    self.assertEqual(len(observed),1);self.assertIs(observed[0],primary)
                    facts=BaseException.__dict__['__dict__'].__get__(primary)
                    self.assertIs(dict.__getitem__(facts,'launcher_custody'),custody)
                    self.assertIn(secondary,dict.__getitem__(facts,'launcher_custody_io_errors'))
                    NATIVE_FILE_OBSERVATIONS.append(dict(kind='partial-write-close-refusal',primary=kind.__name__,
                        temporary_device=pending.st_dev,temporary_inode=pending.st_ino,temporary_bytes=pending.st_size,
                        descriptor_live_before_reviewer_cleanup=True,close_attempts=len(close_calls)))
                finally:
                    for descriptor in descriptors:
                        try:os.fstat(descriptor)
                        except OSError:continue
                        original_close(descriptor)
                        with self.assertRaises(OSError):os.fstat(descriptor)

    def test_actual_close_then_lost_response_is_never_closed_twice(self):
        root=self.profile();custody=self.custody(root)
        primary=KeyboardInterrupt('actual-close-complete-response-lost')
        original_open,original_close=os.open,os.close;descriptors=[];close_calls=[];observed=[]
        def opened(path,flags,*args,**kwargs):
            descriptor=original_open(path,flags,*args,**kwargs)
            if str(path).endswith('.tmp'):descriptors.append(descriptor)
            return descriptor
        def closed(descriptor):
            if descriptor in descriptors:
                close_calls.append(descriptor);original_close(descriptor);raise primary
            return original_close(descriptor)
        with patch.object(lifecycle.os,'open',opened),patch.object(lifecycle.os,'close',closed):
            try:custody.reserve_launch()
            except BaseException as error:observed.append(error)
        self.assertEqual(len(descriptors),1);self.assertEqual(len(observed),1)
        with self.assertRaises(OSError):os.fstat(descriptors[0])
        self.assertIs(observed[0],primary);self.assertEqual(len(close_calls),1)
        self.assertIsNone(custody._lock_descriptor)
        NATIVE_FILE_OBSERVATIONS.append(dict(kind='real-close-response-loss',close_attempts=len(close_calls),
            actual_closed_descriptor_observed=True,exact_primary_preserved=True))

    def test_native_short_writes_are_completed_before_atomic_publication(self):
        root=self.profile(temporary_units=261);custody=self.custody(root);original=os.write;counts=[]
        def short(descriptor,wire):
            amount=original(descriptor,wire[:7]);counts.append(amount);return amount
        with patch.object(lifecycle.os,'write',short):record=custody.reserve_launch()
        self.assertGreater(len(counts),2);self.assertTrue(all(0<n<=7 for n in counts))
        self.assertEqual(lifecycle.strict_loads(io_path(custody.path).read_bytes()),record)
        self.assertEqual(list(io_path(root).glob('*.tmp')),[])

    def test_zero_write_denies_publication_and_cleans_only_owned_temporary(self):
        root=self.profile(temporary_units=260);custody=self.custody(root)
        original_open,original_write=os.open,os.write;temporary=[]
        def opened(path,flags,*args,**kwargs):
            descriptor=original_open(path,flags,*args,**kwargs)
            if str(path).endswith('.tmp'):temporary.append(descriptor)
            return descriptor
        def zero(descriptor,wire):
            return 0 if descriptor in temporary else original_write(descriptor,wire)
        with patch.object(lifecycle.os,'open',opened),patch.object(lifecycle.os,'write',zero):
            with self.assertRaisesRegex(OSError,'LAUNCHER_CUSTODY_WRITE_FAILED'):custody.reserve_launch()
        self.assertFalse(io_path(custody.path).exists());self.assertEqual(list(io_path(root).glob('*.tmp')),[])
        self.assertIsNone(custody._lock_descriptor)
        with self.assertRaises(OSError):os.fstat(temporary[0])

    def test_replace_refusal_preserves_existing_pending_bytes_and_revision(self):
        root=self.profile(root_units=320);custody=self.custody(root);record=custody.reserve_launch()
        before=io_path(custody.path).read_bytes();primary=OSError('controlled-replace-refusal')
        with patch.object(lifecycle.os,'replace',side_effect=primary):
            try:custody.mark_start_requested()
            except BaseException as observed:self.assertIs(observed,primary)
            else:self.fail('replace failure was hidden')
        self.assertEqual(io_path(custody.path).read_bytes(),before);self.assertEqual(custody.record,record)
        self.assertEqual(list(io_path(root).glob('*.tmp')),[])
        self.assertIs(primary.launcher_custody,custody)
        self.assertTrue(primary.launcher_custody_replacement_attempted)

    def test_actual_replace_response_loss_keeps_durable_pending_fence(self):
        root=self.profile(root_units=320);custody=self.custody(root);first=custody.reserve_launch()
        original=os.replace;primary=KeyboardInterrupt('replace-complete-response-lost');calls=[]
        def replaced(source,destination):
            calls.append((str(source),str(destination)));original(source,destination);raise primary
        with patch.object(lifecycle.os,'replace',replaced):
            try:custody.mark_start_requested()
            except BaseException as observed:self.assertIs(observed,primary)
            else:self.fail('replace response loss was hidden')
        self.assertEqual(len(calls),1);self.assertTrue(primary.launcher_custody_replacement_attempted)
        custody.close();restart=self.custody(root);record=restart.record
        self.assertEqual(record['record_id'],first['record_id']);self.assertEqual(record['revision'],2)
        self.assertEqual(record['state'],'PENDING')
        with self.assertRaises(LauncherCustodyIncomplete):restart.reserve_launch()
        NATIVE_FILE_OBSERVATIONS.append(dict(kind='actual-replace-response-loss',replace_calls=1,
            durable_pending_revision=record['revision'],replacement_not_replayed=True))

    def test_cleanup_unlink_failure_retains_exact_primary_secondary_and_path(self):
        root=self.profile(temporary_units=261);custody=self.custody(root)
        primary,secondary=SystemExit('write-primary'),PermissionError('controlled-unlink-refusal')
        original_write,original_unlink=os.write,Path.unlink;temporary=[]
        def write(descriptor,wire):
            if len(wire)>1:original_write(descriptor,wire[:1]);raise primary
            return original_write(descriptor,wire)
        def unlink(path,*args,**kwargs):
            if str(path).endswith('.tmp'):temporary.append(path);raise secondary
            return original_unlink(path,*args,**kwargs)
        try:
            with patch.object(lifecycle.os,'write',write),patch.object(Path,'unlink',unlink):
                try:custody.reserve_launch()
                except BaseException as observed:self.assertIs(observed,primary)
                else:self.fail('write failure was hidden')
            self.assertEqual(len(temporary),1);self.assertTrue(temporary[0].is_file())
            facts=BaseException.__dict__['__dict__'].__get__(primary)
            self.assertIs(dict.__getitem__(facts,'launcher_custody'),custody)
            self.assertIn(secondary,dict.__getitem__(facts,'launcher_custody_io_errors'))
            self.assertEqual(io_path(dict.__getitem__(facts,'launcher_custody_temporary_path')),temporary[0])
            self.assertFalse(io_path(custody.path).exists())
        finally:
            for path in temporary:original_unlink(path)

    def test_native_temporary_replacement_is_not_published_or_deleted(self):
        root=self.profile();custody=self.custody(root)
        original_open,original_close,original_replace=os.open,os.close,os.replace
        temporary=[];descriptors=[];sentinel=b'preserve newly appeared owned negative fixture'
        def opened(path,flags,*args,**kwargs):
            descriptor=original_open(path,flags,*args,**kwargs)
            if str(path).endswith('.tmp'):temporary.append(Path(path));descriptors.append(descriptor)
            return descriptor
        def closed(descriptor):
            original_close(descriptor)
            if descriptor in descriptors:
                original_replace(temporary[0],temporary[0].with_suffix('.preserved'))
                with temporary[0].open('xb') as stream:stream.write(sentinel)
        with patch.object(lifecycle.os,'open',opened),patch.object(lifecycle.os,'close',closed):
            with self.assertRaisesRegex(RuntimeError,'LAUNCHER_CUSTODY_TEMPORARY_CHANGED'):custody.reserve_launch()
        self.assertEqual(temporary[0].read_bytes(),sentinel)
        self.assertTrue(temporary[0].with_suffix('.preserved').is_file())
        self.assertFalse(io_path(custody.path).exists())

    def test_native_hardlinked_record_or_lock_is_denied_without_touching_alias(self):
        for name in (LauncherShutdownCustody._RECORD_NAME,LauncherShutdownCustody._LOCK_NAME):
            with self.subTest(name=name):
                root=self.profile();source=io_path(root/'owned-sentinel')
                sentinel=b'preserve native hardlink target';source.write_bytes(sentinel)
                os.link(source,io_path(root/name))
                custody=self.custody(root)
                with self.assertRaisesRegex(RuntimeError,'LAUNCHER_CUSTODY_LINK_REJECTED'):custody.reserve_launch()
                self.assertEqual(source.read_bytes(),sentinel);self.assertEqual(source.stat().st_nlink,2)
                self.assertIsNone(custody._lock_descriptor)

    def test_native_reparse_root_and_ancestor_are_rejected(self):
        target=self.profile(root_units=320);io_path(target/'child').mkdir()
        container=self.profile();link=container/'owned-junction';junction(link,target)
        for root in (link,link/'child'):
            with self.subTest(root=str(root)):
                with self.assertRaisesRegex(ValueError,'LAUNCHER_CUSTODY_ROOT_REQUIRED'):LauncherShutdownCustody(root)
        self.assertEqual(list(io_path(target).glob('.ceta-*')),[])

    def test_native_reparse_record_and_lock_are_rejected(self):
        for name in (LauncherShutdownCustody._RECORD_NAME,LauncherShutdownCustody._LOCK_NAME):
            with self.subTest(name=name):
                root,target=self.profile(),self.profile();junction(root/name,target)
                custody=self.custody(root)
                with self.assertRaisesRegex(RuntimeError,'LAUNCHER_CUSTODY_LINK_REJECTED'):custody.acquire()
                self.assertIsNone(custody._lock_descriptor);self.assertEqual(list(io_path(target).iterdir()),[])

    def test_actual_root_identity_replacement_is_rejected_before_lock_creation(self):
        root=self.profile();custody=self.custody(root);before=io_path(root).stat()
        preserved=root.with_name(root.name+'-preserved')
        os.replace(io_path(root),io_path(preserved));io_path(root).mkdir()
        with self.assertRaisesRegex(RuntimeError,'LAUNCHER_CUSTODY_ROOT_CHANGED'):custody.acquire()
        self.assertEqual(list(io_path(root).iterdir()),[])
        after=io_path(preserved).stat();self.assertEqual((before.st_dev,before.st_ino),(after.st_dev,after.st_ino))

    def test_namespace_conversion_preserves_normal_and_already_extended_paths(self):
        root=self.profile();ordinary=LauncherShutdownCustody._io_path(root)
        self.assertEqual(ordinary,io_path(root));self.assertEqual(LauncherShutdownCustody._io_path(ordinary),ordinary)
        unc=Path('\\\\server\\share\\ordinary\\profile')
        self.assertEqual(str(LauncherShutdownCustody._io_path(unc)),'\\\\?\\UNC\\server\\share\\ordinary\\profile')
        self.assertEqual(LauncherShutdownCustody._io_path(LauncherShutdownCustody._io_path(unc)),LauncherShutdownCustody._io_path(unc))
        # UNC spelling is inspected only; this test performs no network I/O.

    def test_unsafe_namespace_components_are_denied_without_file_creation(self):
        root=self.profile()
        unsafe=(str(root/'..'/'escape'),str(root/'NUL'),str(root/'stream:alternate'),
            str(root/'trailing.'),str(root/'trailing '),str(root/'bad\0name'),
            'relative\\profile','\\\\.\\pipe\\unowned','\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1')
        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'LAUNCHER_CUSTODY_ROOT_REQUIRED'):LauncherShutdownCustody._io_path(value)
        self.assertEqual(list(io_path(root).iterdir()),[])

    def test_unknown_record_shape_is_preserved_and_denies_reservation(self):
        root=self.profile(root_units=320);path=io_path(root/LauncherShutdownCustody._RECORD_NAME)
        original=b'{"unrecognized":"preserve"}';path.write_bytes(original);before=path.stat()
        custody=self.custody(root)
        with self.assertRaisesRegex(RuntimeError,'LAUNCHER_CUSTODY_RECORD_UNREADABLE'):custody.reserve_launch()
        self.assertEqual(path.read_bytes(),original);after=path.stat()
        self.assertEqual((before.st_dev,before.st_ino,before.st_size),(after.st_dev,after.st_ino,after.st_size))
        self.assertIsNone(custody._lock_descriptor)

    def test_controlled_lock_entry_primary_and_close_secondary_are_both_retained(self):
        import msvcrt
        root=self.profile(root_units=320);custody=self.custody(root)
        primary,secondary=KeyboardInterrupt('lock-initialization-primary'),SystemExit('close-refused')
        original_open,original_close=os.open,os.close;descriptors=[];observed=[]
        def opened(*args,**kwargs):
            descriptor=original_open(*args,**kwargs);descriptors.append(descriptor);return descriptor
        try:
            with patch.object(lifecycle.os,'open',opened),patch.object(msvcrt,'locking',side_effect=primary), \
                    patch.object(lifecycle.os,'close',side_effect=secondary):
                try:custody.acquire()
                except BaseException as error:observed.append(error)
            self.assertEqual(len(observed),1);self.assertIs(observed[0],primary)
            self.assertEqual(primary.launcher_custody_uncertain_close,descriptors[0])
            self.assertIn(secondary,primary.launcher_custody_io_errors);self.assertIsNone(custody._lock_descriptor)
            self.assertGreaterEqual(os.fstat(descriptors[0]).st_size,1)
        finally:
            for descriptor in descriptors:
                original_close(descriptor)
                with self.assertRaises(OSError):os.fstat(descriptor)

    def _read_fault(self, primary, secondary, *, body_fails=True):
        root=self.profile(root_units=320);writer=self.custody(root)
        record=writer.reserve_launch();writer.close();reader=self.custody(root)
        path=reader._io_path(reader.path);before=path.stat();wire=path.read_bytes()
        original=Path.open;streams=[];descriptors=[];calls=[]
        class Stream:
            def __init__(self):
                self.actual=original(path,'rb');streams.append(self)
                descriptors.append(self.actual.fileno())
            def read(self,*args):
                if body_fails:
                    self.actual.read(1);raise primary
                return self.actual.read(*args)
            def close(self):
                calls.append(self);self.actual.close()
                raise secondary
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        def opened(selected,*args,**kwargs):
            return Stream() if selected==path else original(selected,*args,**kwargs)
        escaped=None
        with patch.object(Path,'open',opened):
            try:reader.record
            except BaseException as error:escaped=error
        self.assertEqual(len(streams),1);self.assertEqual(calls,streams)
        self.assertTrue(streams[0].actual.closed)
        with self.assertRaises(OSError):os.fstat(descriptors[0])
        after=path.stat()
        self.assertEqual((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns),
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns))
        self.assertEqual(path.read_bytes(),wire)
        expected=primary if body_fails else secondary
        if isinstance(expected,OSError):
            self.assertIs(type(escaped),RuntimeError)
            self.assertEqual(str(escaped),'LAUNCHER_CUSTODY_RECORD_UNREADABLE')
            self.assertIs(escaped.launcher_custody_read_failure,expected)
        else:self.assertIs(escaped,expected)
        data=BaseException.__dict__['__dict__'].__get__(escaped)
        self.assertIs(dict.__getitem__(data,'launcher_custody_read_stream'),streams[0])
        self.assertTrue(dict.__getitem__(data,'launcher_custody_read_close_attempted'))
        self.assertFalse(dict.__getitem__(data,'launcher_custody_read_close_returned'))
        if body_fails:self.assertIn(secondary,dict.__getitem__(data,'launcher_custody_io_errors'))
        NATIVE_FILE_OBSERVATIONS.append(dict(kind='public-read-cleanup',body_fails=body_fails,
            primary=type(primary).__name__,secondary=type(secondary).__name__,
            one_close=True,actual_stream_closed=True,record_identity_and_bytes_unchanged=True,
            ordinary_error_mapping_preserved=isinstance(expected,OSError)))

    def test_public_record_read_preserves_control_primary_and_ordinary_error_custody(self):
        for kind in (KeyboardInterrupt,SystemExit,MemoryError,OSError):
            for cleanup in (OSError,SystemExit):
                with self.subTest(primary=kind.__name__,cleanup=cleanup.__name__):
                    self._read_fault(kind('controlled partial read'),cleanup('actual close; response lost'))

    def test_public_record_read_close_only_failure_keeps_exact_stream_and_error(self):
        for kind in (KeyboardInterrupt,SystemExit,MemoryError,OSError):
            with self.subTest(cleanup=kind.__name__):
                self._read_fault(None,kind('actual close; response lost'),body_fails=False)

    def test_public_record_read_is_bounded_before_oversized_wire_rejection(self):
        root=self.profile(root_units=320);path=io_path(root/LauncherShutdownCustody._RECORD_NAME)
        sentinel=b' '*(lifecycle.MAX_WIRE_BYTES+1)
        with path.open('xb') as stream:stream.write(sentinel)
        reader=self.custody(root);original=Path.open;reads=[];closes=[];descriptors=[]
        class Stream:
            def __init__(self):self.actual=original(path,'rb');descriptors.append(self.actual.fileno())
            def read(self,*args):reads.append(args);return self.actual.read(*args)
            def close(self):closes.append(self);self.actual.close()
        def opened(selected,*args,**kwargs):
            return Stream() if selected==path else original(selected,*args,**kwargs)
        with patch.object(Path,'open',opened):
            with self.assertRaisesRegex(RuntimeError,'LAUNCHER_CUSTODY_RECORD_UNREADABLE') as caught:
                reader.record
        self.assertEqual(reads,[(lifecycle.MAX_WIRE_BYTES+1,)]);self.assertEqual(len(closes),1)
        self.assertEqual(caught.exception.launcher_custody_read_failure.code,'WIRE_SIZE_LIMIT')
        with self.assertRaises(OSError):os.fstat(descriptors[0])
        self.assertEqual(path.read_bytes(),sentinel)

    def test_lock_exit_primary_and_secondary_preserve_one_shot_native_custody(self):
        root=self.profile();custody=self.custody(root);custody.reserve_launch()
        descriptor,original_unlock,original_close=custody._lock_descriptor,custody._unlock,os.close
        primary,secondary=KeyboardInterrupt('unlock-primary'),SystemExit('lock-close-refused');attempts=[];observed=[]
        def closed(value):attempts.append(value);raise secondary
        custody._unlock=lambda value:(_ for _ in ()).throw(primary)
        try:
            with patch.object(lifecycle.os,'close',closed):
                try:custody.close()
                except BaseException as error:observed.append(error)
            self.assertEqual(len(observed),1);self.assertIs(observed[0],primary)
            self.assertIn(secondary,primary.launcher_custody_io_errors)
            self.assertEqual(primary.launcher_custody_uncertain_close,descriptor)
            self.assertEqual(attempts,[descriptor]);self.assertIsNone(custody._lock_descriptor)
            self.assertGreaterEqual(os.fstat(descriptor).st_size,1);custody.close();self.assertEqual(attempts,[descriptor])
        finally:
            original_unlock(descriptor);original_close(descriptor)
            with self.assertRaises(OSError):os.fstat(descriptor)
        replacement=self.custody(root);replacement.acquire();replacement.close()

    def test_native_unicode_profile_keeps_exact_logical_name_and_pending_bytes(self):
        root=self.profile(root_units=320)/'profile-\U0001f9e0-e\u0301'
        io_path(root).mkdir();custody=self.custody(root);record=custody.reserve_launch()
        self.assertEqual(custody.path,root/LauncherShutdownCustody._RECORD_NAME)
        self.assertGreater(units(root),len(str(root)))
        custody.close();self.assertEqual(self.custody(root).record,record)

    def test_refused_exception_and_dictionary_hooks_cannot_replace_native_cleanup_custody(self):
        calls=[];trap=RuntimeError('refused-hook-must-not-run')
        class Storage(dict):
            def refuse(self,*args,**kwargs):calls.append('dictionary');raise trap
            get=update=__getitem__=__setitem__=__contains__=refuse
        class Primary(KeyboardInterrupt):
            def __setattr__(self,*args):calls.append('setter');raise trap
            @property
            def add_note(self):calls.append('note-lookup');raise trap
        primary=Primary('owned-hostile-primary');storage=Storage()
        BaseException.__dict__['__dict__'].__set__(primary,storage)
        secondary=PermissionError('owned-close-refused');root=self.profile();custody=self.custody(root)
        original_open,original_write,original_close=os.open,os.write,os.close;descriptors=[];observed=[]
        def opened(path,flags,*args,**kwargs):
            descriptor=original_open(path,flags,*args,**kwargs)
            if str(path).endswith('.tmp'):descriptors.append(descriptor)
            return descriptor
        def written(descriptor,wire):
            if descriptor in descriptors:original_write(descriptor,wire[:1]);raise primary
            return original_write(descriptor,wire)
        def closed(descriptor):
            if descriptor in descriptors:raise secondary
            return original_close(descriptor)
        try:
            with patch.object(lifecycle.os,'open',opened),patch.object(lifecycle.os,'write',written),patch.object(lifecycle.os,'close',closed):
                try:custody.reserve_launch()
                except BaseException as error:observed.append(error)
            self.assertEqual(len(observed),1);self.assertIs(observed[0],primary);self.assertEqual(calls,[])
            self.assertIs(dict.__getitem__(storage,'launcher_custody'),custody)
            self.assertIn(secondary,dict.__getitem__(storage,'launcher_custody_io_errors'))
            self.assertEqual(dict.__getitem__(storage,'launcher_custody_uncertain_close'),descriptors[0])
            self.assertEqual(os.fstat(descriptors[0]).st_size,1)
        finally:
            for descriptor in descriptors:
                original_close(descriptor)
                with self.assertRaises(OSError):os.fstat(descriptor)
