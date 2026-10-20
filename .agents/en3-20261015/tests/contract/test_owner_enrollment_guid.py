"""Canonical GUID language equivalence and unchanged contract-leaf boundary."""
from dataclasses import replace
import hashlib
from pathlib import Path
import unittest
import uuid

import test_owner_enrollment as prior
import test_source_coverage as coverage
from ceta.contracts.owner_enrollment import NativeObjectIdentity
from ceta.contracts.wire import ContractError

ROOT = Path(__file__).resolve().parents[2]


class EnrollmentGuidTests(unittest.TestCase):
    def identity(self, guid):
        return NativeObjectIdentity('\\\\?\\Volume{' + guid + '}\\CETA\\private',
            'directory', '0' * 16, '0' * 32)

    def test_all_guid_nibbles_and_unassigned_versions_keep_prior_uuid_semantics(self):
        for index in range(256):
            raw = hashlib.sha256(index.to_bytes(2, 'big')).hexdigest()[:32]
            guid = str(uuid.UUID(hex=raw))
            with self.subTest(guid=guid):
                self.assertEqual(self.identity(guid).path.split('{')[1].split('}')[0], guid)
                request = prior.request()
                self.assertEqual(replace(request, deadline=replace(request.deadline,
                    boot_id='boot:' + guid + ':session:' + request.clock_session_nonce)).deadline.boot_id,
                    'boot:' + guid + ':session:' + request.clock_session_nonce)

    def test_zero_volume_guid_is_preserved_but_zero_boot_witness_is_rejected(self):
        zero = str(uuid.UUID(int=0))
        self.identity(zero)
        request = prior.request()
        with self.assertRaisesRegex(ContractError, 'ENROLLMENT_BOOT_WITNESS_INVALID'):
            replace(request, deadline=replace(request.deadline,
                boot_id='boot:' + zero + ':session:' + request.clock_session_nonce))

    def test_alias_case_shape_and_nonhex_spellings_remain_rejected(self):
        guid = '12345678-1234-4234-8234-123456789abc'
        invalid = (guid.upper(), guid.replace('-', ''), '{' + guid + '}', 'urn:uuid:' + guid,
            guid.replace('-', '', 1) + '-', '-' + guid[1:], guid[:-1] + 'g',
            guid[:-1] + '\uff10', guid + '\n', guid.replace('-', '\u2010'))
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ContractError):
                self.identity(value)

    def test_boot_hyphen_positions_and_noncanonical_case_remain_rejected(self):
        request = prior.request()
        guid = '12345678-1234-4234-8234-123456789abc'
        for bad in (guid.upper(), guid.replace('-', '', 1) + '-', '-' + guid[1:],
                guid[:-1] + 'g', guid + '-', guid[:-1]):
            with self.subTest(guid=bad), self.assertRaises(ContractError):
                replace(request, deadline=replace(request.deadline,
                    boot_id='boot:' + bad + ':session:' + request.clock_session_nonce))

    def test_shifted_hyphens_do_not_gain_uuid_alias_acceptance(self):
        canonical = '12345678-1234-4234-8234-123456789abc'
        # uuid.UUID ignores hyphen placement; this wire contract never did.
        for position in (0, 1, 7, 9, 34, 35):
            moved = canonical.replace('-', '', 1)
            moved = moved[:position] + '-' + moved[position:]
            if moved == canonical: continue
            self.assertEqual(str(uuid.UUID(moved)), canonical)
            with self.subTest(position=position), self.assertRaises(ContractError):
                self.identity(moved)

    def test_unchanged_leaf_guard_accepts_actual_enrollment_contract(self):
        guard = coverage.SourceCoverageTests()
        path = ROOT / 'src/ceta/contracts/owner_enrollment.py'
        guard.assert_contract_leaf_imports(path.read_text(encoding='utf-8'), path)
