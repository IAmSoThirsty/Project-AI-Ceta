"""Actual disposable Windows file pins and finite retained-lease failure cases."""
from dataclasses import replace
from pathlib import Path
import ctypes as C
import hashlib
import os
import threading
import unittest
from unittest.mock import patch
import uuid

from ceta.contracts.wire import ContractError
from ceta.identity import native_code_binding as binding

ROOT = Path(__file__).resolve().parents[2]
NATIVE_RECEIPTS = []


class NativeCodeBindingTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT/'.agents/fixtures'/('code-'+uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.source = self.root/'source.py';self.environment = self.root/'runtime.dll'
        self.source.write_bytes(b'VALUE = 37\n');self.environment.write_bytes(b'CETA-DISPOSABLE-RUNTIME-BYTES\0')
        self.pins = tuple(binding.CodePin(group,name,str(path),hashlib.sha256(path.read_bytes()).hexdigest())
            for group,name,path in (('source','source.py',self.source),('environment','runtime.dll',self.environment)))
        self.owners = []

    def tearDown(self):
        for owner in self.owners:
            owner.close()
            self.assertTrue(owner.closed);self.assertFalse(owner.pending_native_resources)
        NATIVE_RECEIPTS.append({'test_id':self.id(),'root':str(self.root),
            'all_bindings_closed':all(owner.closed and not owner.pending_native_resources for owner in self.owners)})

    def opened(self,pins=None):
        try: owner = binding.NativeCodeBinding(self.pins if pins is None else pins)
        except BaseException as error:
            retained = BaseException.__dict__['__dict__'].__get__(error).get('native_code_binding')
            if retained is not None:self.owners.append(retained)
            raise
        self.owners.append(owner)
        return owner

    def test_actual_hashes_native_full_ids_and_group_commitments_are_measured(self):
        owner = self.opened();snapshot = owner.snapshot()
        self.assertEqual(len(snapshot),2)
        self.assertNotEqual(owner.source_commitment,owner.environment_commitment)
        for group,name,pin,size,facts in snapshot:
            expected = next(row for row in self.pins if row.group==group and row.logical_name==name)
            self.assertEqual(pin,expected.sha256);self.assertEqual(size,Path(expected.path).stat().st_size)
            self.assertEqual(len(facts[1]),16);self.assertEqual(len(facts[2]),32)
            self.assertTrue(facts[0].startswith('\\\\?\\Volume{'))
        self.assertIsNone(owner.require_current())

    def test_repeated_bindings_have_stable_commitments_and_manifest_order_is_irrelevant(self):
        first = self.opened();second = self.opened(tuple(reversed(self.pins)))
        self.assertEqual(first.source_commitment,second.source_commitment)
        self.assertEqual(first.environment_commitment,second.environment_commitment)
        self.assertEqual(first.snapshot(),second.snapshot())

    def test_actual_write_delete_replacement_and_ancestor_rename_are_denied_while_pinned(self):
        owner = self.opened();replacement = self.root/'replacement.py';replacement.write_bytes(self.source.read_bytes())
        with self.assertRaises(OSError):self.source.write_bytes(b'CHANGED\n')
        with self.assertRaises(OSError):os.replace(replacement,self.source)
        with self.assertRaises(OSError):self.source.unlink()
        with self.assertRaises(OSError):self.root.rename(self.root.with_name(self.root.name+'-renamed'))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),self.pins[0].sha256)
        owner.require_current()

    def test_release_allows_write_and_same_byte_replacement_changes_native_commitment(self):
        owner = self.opened();before = owner.source_commitment;owner.close()
        replacement = self.root/'replacement.py';replacement.write_bytes(self.source.read_bytes())
        os.replace(replacement,self.source)
        later = self.opened();self.assertNotEqual(later.source_commitment,before)
        self.assertEqual(later.snapshot()[1][2],self.pins[0].sha256)

    def test_missing_file_is_denied_without_creation_and_constructor_custody_retires(self):
        pins = (replace(self.pins[0],path=str(self.root/'missing.py')),self.pins[1])
        with self.assertRaises(ContractError) as caught:self.opened(pins)
        self.assertFalse((self.root/'missing.py').exists())
        self.assertTrue(caught.exception.native_code_binding.closed)

    def test_wrong_hash_denies_and_retains_exact_closed_constructor_owner(self):
        with self.assertRaisesRegex(ContractError,'HASH_MISMATCH') as caught:
            self.opened((replace(self.pins[0],sha256='0'*64),self.pins[1]))
        self.assertTrue(caught.exception.native_code_binding.closed)
        self.assertFalse(caught.exception.native_code_binding.pending_native_resources)

    def test_manifest_shape_duplicates_and_group_coverage_are_denied(self):
        for pins in (list(self.pins),(),(self.pins[0],),self.pins+(self.pins[0],),
                (self.pins[0],replace(self.pins[1],group='source')),
                (self.pins[0],replace(self.pins[1],path=self.pins[0].path))):
            with self.subTest(pins_type=type(pins).__name__),self.assertRaises(ContractError):self.opened(pins)
        for name in ('../source.py','source//file','source.','/absolute','source:ads'):
            with self.subTest(name=name),self.assertRaises(ContractError):replace(self.pins[0],logical_name=name)

    def test_byte_bound_is_checked_before_hashing_and_cleanup_is_complete(self):
        with patch.object(binding,'MAXIMUM_FILE_BYTES',1):
            with self.assertRaisesRegex(ContractError,'BYTES_BOUND') as caught:self.opened()
        self.assertTrue(caught.exception.native_code_binding.closed)

    def test_every_retained_file_and_ancestor_handle_is_noninheritable(self):
        owner = self.opened()
        for row in owner._ancestors+owner._files:
            flags = binding.DWORD(999)
            self.assertTrue(owner._api.GetHandleInformation(row['handle'],C.byref(flags)))
            self.assertEqual(flags.value&1,0)

    def test_unavailable_native_currentness_is_denied_and_recovery_is_explicit(self):
        owner = self.opened()
        with patch.object(owner._api,'GetFileInformationByHandleEx',return_value=0):
            with self.assertRaisesRegex(ContractError,'FACTS_UNAVAILABLE'):owner.require_current()
        owner.require_current()

    def test_retained_lease_is_exact_same_thread_pure_and_expires_on_exit(self):
        owner = self.opened()
        with owner.retained() as lease:
            with patch.object(owner._api,'facts',side_effect=AssertionError('NO_NATIVE_CALL_IN_FINAL_FENCE')):
                self.assertIsNone(lease.require_current())
            foreign = []
            def other():
                try:lease.require_current()
                except ContractError as error:foreign.append(error.code)
            thread = threading.Thread(target=other);thread.start();thread.join(5)
            self.assertFalse(thread.is_alive());self.assertEqual(foreign,['CODE_BINDING_LEASE_INVALID'])
            forged = binding._RetainedBinding(owner)
            with self.assertRaisesRegex(ContractError,'LEASE_INVALID'):forged.require_current()
        with self.assertRaisesRegex(ContractError,'LEASE_INVALID'):lease.require_current()

    def test_close_invalidates_active_lease_before_refusing_unsafe_retirement(self):
        owner = self.opened()
        with owner.retained() as lease:
            with self.assertRaisesRegex(ContractError,'LEASE_ACTIVE'):owner.close()
            self.assertFalse(owner.closed);self.assertTrue(owner.pending_native_resources)
            with self.assertRaisesRegex(ContractError,'LEASE_INVALID'):lease.require_current()
        owner.close();self.assertTrue(owner.closed)

    def test_other_thread_close_is_bounded_and_invalidates_lease_without_losing_handles(self):
        owner = self.opened();outcomes = []
        with owner.retained() as lease:
            def close():
                try:owner.close()
                except ContractError as error:outcomes.append(error.code)
            thread = threading.Thread(target=close);thread.start();thread.join(5)
            self.assertFalse(thread.is_alive());self.assertEqual(outcomes,['CODE_BINDING_BUSY'])
            with self.assertRaisesRegex(ContractError,'LEASE_INVALID'):lease.require_current()
            self.assertTrue(owner.pending_native_resources)
        owner.close()

    def test_control_exception_preserves_exact_primary_and_recoverable_native_custody(self):
        owner = self.opened()
        class Primary(KeyboardInterrupt):
            def __setattr__(self,name,value):raise RuntimeError('REFUSING_SETTER')
            @property
            def add_note(self):raise RuntimeError('REFUSING_NOTE_LOOKUP')
        primary = Primary('NATIVE_BINDING_PRIMARY')
        with patch.object(owner._api,'retry_cleanup',side_effect=primary):
            with self.assertRaises(Primary) as caught:owner.close()
        self.assertIs(caught.exception,primary)
        custody = BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(custody['native_code_binding'],owner);self.assertTrue(owner.pending_native_resources)
        custody['close_cleanup']();self.assertTrue(owner.closed)

    def test_context_control_exception_survives_cleanup_failure(self):
        owner = self.opened();primary = SystemExit('CONTEXT_PRIMARY')
        with patch.object(owner._api,'retry_cleanup',side_effect=OSError('CLEANUP_REFUSED')):
            with self.assertRaises(SystemExit) as caught:
                with owner:raise primary
        self.assertIs(caught.exception,primary);self.assertIs(primary.native_code_binding,owner)
        owner.close()

    def test_closed_binding_never_renews_and_snapshot_is_immutable_data(self):
        owner = self.opened();snapshot = owner.snapshot()
        self.assertIs(type(snapshot),tuple);self.assertTrue(all(type(row) is tuple for row in snapshot))
        owner.close();owner.close()
        with self.assertRaisesRegex(ContractError,'CLOSED'):owner.require_current()
        with self.assertRaisesRegex(ContractError,'CLOSED'):owner.snapshot()
        with self.assertRaisesRegex(ContractError,'CLOSED'):
            with owner.retained():self.fail('closed owner renewed')


if __name__ == '__main__':unittest.main()
