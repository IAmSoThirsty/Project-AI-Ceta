"""Controlled DATA_ONLY fixtures: no native enrollment, filesystem or authority."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, fields, replace
import json
import unittest

from ceta.contracts import owner_enrollment as module
from ceta.contracts.kernel_transactions import BUDGET_FIELDS, BudgetVector, digest
from ceta.contracts.real_effect import NativeApprovalTranscript
from ceta.contracts.resource_management import ProcessResourceIdentity, ResourceVector
from ceta.contracts.temporal import ClockSample, Deadline
from ceta.contracts.wire import ContractError, MAX_INTEGER, canonical_bytes, strict_loads

H = 'sha256:'+'a'*64
H2 = 'sha256:'+'b'*64
VOLUME = r'\\?\Volume{12345678-1234-4234-8234-123456789abc}'
PATH = VOLUME+r'\CETA\private\installation1'
BOOT = 'boot:12345678-1234-4234-8234-123456789abc:session:'+'1'*32
WALL = 1_792_000_000_000_000_000


def budget(**changes):
    values = dict(wall_time_ms=10000, max_model_calls=0, max_effects=2, max_input_tokens=0,
                  max_output_tokens=0, max_bytes_read=16384, max_bytes_written=16384)
    values.update(changes)
    return BudgetVector.from_dict(values)


def process(pid=101, **changes):
    return ProcessResourceIdentity(**dict(dict(pid=pid, creation_time=100, image_digest=H), **changes))


def request(**changes):
    facts = module.OwnerTokenFacts(process(), 'S-1-5-21-1-2-3-1001', 'S-1-5-5-1-2', '0'*16, 0,
        '0'*16, '0'*16, 1, 0, 'S-1-16-8192', 0, 1, 0, 0, ())
    value = dict(request_id='enrollment1', installation_id='installation1', scope_id='project1',
        principal_id='owner1', actor_session='interactive1', owner_session_nonce='2'*32,
        clock_session_nonce='1'*32, challenge_id='challenge1', ceremony_nonce='3'*32,
        private_root=module.NativeObjectIdentity(PATH, 'directory', '0'*16, '0'*32),
        database=module.NativeObjectIdentity(PATH+r'\history.sqlite3', 'file', '0'*16, '0'*31+'1'),
        owner_facts=facts, helper_identity=process(102), ui_identity=process(103),
        policy_generation=0, authority_generation=0, policy_commitment=H, source_commitment=H,
        environment_commitment=H, helper_commitment=H, ui_commitment=H, adapter_commitment=H,
        worker_image_commitment=H, authority_budget=budget(), recovery_budget=budget(max_effects=1, wall_time_ms=5000, max_bytes_written=8192),
        resource_limit=ResourceVector(1000, 1048576, 1048576, 10000), evidence_reserve_bytes=8192,
        maximum_session_ns=60_000_000_000, maximum_effect_duration_ns=1_000_000_000,
        maximum_observation_age_ns=5_000_000_000,
        deadline=Deadline(BOOT, 7, 0, 100, 60_000_000_100, WALL, WALL+60_000_000_000))
    value.update(changes)
    return module.EnrollmentRequest(**value)


def clock(monotonic=1000, **changes):
    values = dict(boot_id=BOOT, durable_epoch=7, resume_generation=0, monotonic_ns=monotonic,
                  wall_time_ns=WALL+monotonic, uncertainty_ns=0, wall_trusted=True)
    values.update(changes)
    return ClockSample(**values)


def transcript(value=None, **changes):
    value = value or request()
    args = dict(challenge_id=value.challenge_id, ceremony_nonce=value.ceremony_nonce,
        request_commitment=value.input_commitment, displayed_commitment=module.enrollment_display_commitment(value),
        principal_id=value.principal_id, actor_session=value.actor_session,
        ui_identity=value.ui_identity, ui_commitment=value.ui_commitment,
        helper_identity=value.helper_identity, helper_commitment=value.helper_commitment,
        observed_clock=clock(1500), native_hresult=0, native_result=0)
    args.update(changes)
    return NativeApprovalTranscript(**args)


class EnrollmentContractTests(unittest.TestCase):
    def test_complete_roundtrip_and_ordinary_immutability(self):
        value = request()
        self.assertEqual(module.decode_enrollment_request(value.canonical_wire), value)
        with self.assertRaises(FrozenInstanceError): value.principal_id = 'other'
        with self.assertRaises(FrozenInstanceError): value.private_root.path = PATH+r'\other'
        self.assertIsInstance(value.owner_facts.restricted_sids, tuple)

    def test_display_contains_every_request_field_and_fixed_limits(self):
        value = request(); shown = strict_loads(module.enrollment_display_bytes(value))
        self.assertEqual(shown['request'], value.as_dict())
        self.assertEqual(shown['input_commitment'], value.input_commitment)
        self.assertEqual(shown['request']['allowed_operations'], ['owned-worker.cpu-cap', 'owned-worker.cpu-restore'])
        self.assertEqual((shown['request']['maximum_workers'], shown['request']['maximum_effects']), (1, 2))
        self.assertEqual(shown['request']['operation_limits'], {'owned-worker.cpu-cap': 1, 'owned-worker.cpu-restore': 1})
        self.assertEqual(shown['request']['approval_mode'], 'SEPARATE_CANONICAL_APPROVAL_PER_EFFECT')
        self.assertEqual(shown['request']['assurance'], 'DATA_ONLY')

    def test_input_display_and_transcript_domains_differ(self):
        value = request(); proof = transcript(value)
        commitments = (value.input_commitment, module.enrollment_display_commitment(value),
            module.enrollment_transcript_commitment(proof), proof.transcript_commitment,
            digest('owned-cpu-request-v1', value.as_dict()))
        self.assertEqual(len(set(commitments)), len(commitments))

    def test_every_scalar_binding_change_alters_full_display_and_current_binding(self):
        value = request()
        alternatives = dict(request_id='enrollment2', installation_id='installation2', scope_id='project2',
            principal_id='owner2', actor_session='interactive2', owner_session_nonce='4'*32,
            challenge_id='challenge2', ceremony_nonce='5'*32, policy_generation=1, authority_generation=1,
            policy_commitment=H2, source_commitment=H2, environment_commitment=H2, helper_commitment=H2,
            ui_commitment=H2, adapter_commitment=H2, worker_image_commitment=H2)
        for name, alternate in alternatives.items():
            with self.subTest(field=name):
                changed = replace(value, **{name: alternate})
                self.assertNotEqual(changed.input_commitment, value.input_commitment)
                self.assertNotEqual(module.enrollment_display_commitment(changed), module.enrollment_display_commitment(value))
                with self.assertRaisesRegex(ContractError, 'ENROLLMENT_EXPECTED_BINDING_MISMATCH'):
                    module.require_enrollment_current(changed, value, clock(), clock(2000))

    def test_unknown_missing_and_approval_boolean_fields_rejected(self):
        value = request().as_dict()
        for name in value:
            wire = dict(value); del wire[name]
            with self.subTest(missing=name), self.assertRaises(ContractError): module.decode_enrollment_request(canonical_bytes(wire))
        for name in ('approved', 'command', 'project_path', 'authority', 'extra'):
            with self.subTest(extra=name), self.assertRaises(ContractError):
                module.decode_enrollment_request(canonical_bytes(dict(value, **{name: True})))

    def test_profile_kind_scope_counts_and_operation_injection_rejected(self):
        value = request().as_dict()
        for name, bad in (('profile', 'other'), ('runtime_profile', 'arbitrary'), ('kind', 'CPU_APPROVAL'),
                          ('assurance', 'AUTHENTICATED'), ('maximum_workers', True), ('maximum_effects', True),
                          ('maximum_effects', 3), ('allowed_operations', ['shell.exec']),
                          ('operation_limits', {'owned-worker.cpu-cap': True, 'owned-worker.cpu-restore': 1}),
                          ('operation_limits', {'owned-worker.cpu-cap': 2, 'owned-worker.cpu-restore': 0}),
                          ('approval_mode', 'AUTOMATIC'),
                          ('allowed_operations', ['owned-worker.cpu-cap']*2)):
            with self.subTest(field=name, value=bad), self.assertRaises(ContractError):
                module.decode_enrollment_request(canonical_bytes(dict(value, **{name: bad})))

    def test_nested_unknown_fields_rejected(self):
        for name in ('private_root', 'database', 'owner_facts', 'helper_identity', 'ui_identity',
                     'authority_budget', 'recovery_budget', 'resource_limit', 'deadline'):
            value = request().as_dict(); value[name]['extra'] = 0
            with self.subTest(field=name), self.assertRaises(ContractError):
                module.decode_enrollment_request(canonical_bytes(value))

    def test_noncanonical_duplicate_float_boolean_size_and_wire_type_rejected(self):
        wire = request().canonical_wire
        bad = [bytearray(wire), wire+b' ', b'{"profile":1,"profile":2}', b'{}',
               b' '*32769, wire.replace(b'"policy_generation":0', b'"policy_generation":0.0'),
               wire.replace(b'"policy_generation":0', b'"policy_generation":true')]
        for value in bad:
            with self.subTest(size=len(value)), self.assertRaises(ContractError): module.decode_enrollment_request(value)

    def test_only_volume_guid_absolute_ordinary_path_spelling_accepted(self):
        bad = ['T:\\CETA', r'\\server\share\root', r'\\?\T:\root', r'\\.\device',
               VOLUME+r'\..\root', VOLUME+r'\root\.', VOLUME+r'\root:stream', VOLUME+r'\root\\child',
               VOLUME+r'\root'+chr(92), VOLUME+r'\root.', VOLUME+r'\root ', VOLUME+r'\CON',
               VOLUME+r'\COM1.txt', VOLUME+r'\ROOT~1', VOLUME+r'\røøt', VOLUME+chr(92)+'a'*65,
               VOLUME.replace('Volume', 'volume')+r'\root', VOLUME+chr(92)+('x'+chr(92))*17+'end',
               r'\\?\Volume{------------------------------------}\root']
        for path in bad:
            with self.subTest(path=path), self.assertRaises(ContractError):
                module.NativeObjectIdentity(path, 'directory', '0'*16, '0'*32)

    def test_full_width_native_ids_roundtrip_without_wire_overflow(self):
        value = request()
        root = replace(value.private_root, volume_serial_hex='f'*16, file_id_hex='f'*32)
        database = replace(value.database, volume_serial_hex='f'*16, file_id_hex='e'*32)
        changed = replace(value, private_root=root, database=database)
        self.assertEqual(module.decode_enrollment_request(changed.canonical_wire), changed)

    def test_native_identity_width_case_type_and_kind_rejected(self):
        for change in ({'volume_serial_hex': '0'*15}, {'volume_serial_hex': True},
                       {'file_id_hex': 'F'*32}, {'file_id_hex': '0'*33}, {'kind': 'reparse'}, {'kind': True}):
            with self.subTest(change=change), self.assertRaises(ContractError): replace(request().private_root, **change)

    def test_database_must_be_exact_canonical_store_under_distinct_root(self):
        value = request()
        for change in ({'path': VOLUME+r'\other\history.sqlite3'}, {'path': PATH+r'\different.sqlite3'},
                       {'kind': 'directory'}, {'volume_serial_hex': '1'*16}, {'file_id_hex': value.private_root.file_id_hex}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                replace(value, database=replace(value.database, **change))

    def test_copied_root_fileid_and_exact_path_case_mismatch_rejected(self):
        value = request()
        root = replace(value.private_root, path=PATH.replace('private', 'Private'), file_id_hex='9'*32)
        copied = replace(value, private_root=root, database=replace(value.database, path=root.path+r'\history.sqlite3', file_id_hex='8'*32))
        with self.assertRaisesRegex(ContractError, 'ENROLLMENT_EXPECTED_BINDING_MISMATCH'):
            module.require_enrollment_current(copied, value, clock(), clock(2000))

    def test_token_measured_zero_is_data_and_absent_or_boolean_is_rejected(self):
        facts = request().owner_facts
        self.assertEqual(facts.terminal_session, 0)
        self.assertEqual(facts.authentication_luid_hex, '0'*16)
        for name in ('terminal_session', 'integrity_attributes', 'impersonation_level', 'ui_access', 'has_restrictions', 'token_type', 'elevation_type'):
            for bad in (None, True):
                with self.subTest(field=name, bad=bad), self.assertRaises(ContractError): replace(facts, **{name: bad})

    def test_token_sid_luid_ranges_and_roles_rejected(self):
        facts = request().owner_facts
        for changes in ({'user_sid': 'S-01-5-21-1'}, {'user_sid': 'S-1-5-4294967296'},
                        {'user_sid': 'S-1-281474976710656-1'}, {'user_sid': 'S-1-5-01'},
                        {'logon_sid': 'S-1-5-21-1'}, {'integrity_sid': 'S-1-5-8192'},
                        {'authentication_luid_hex': '1'*15}, {'token_id_hex': 'F'*16}, {'modified_id_hex': 0},
                        {'terminal_session': 2**32}, {'token_type': 0}, {'impersonation_level': 4},
                        {'elevation_type': 4}, {'ui_access': 2}):
            with self.subTest(changes=changes), self.assertRaises(ContractError): replace(facts, **changes)

    def test_restricted_sid_lists_are_bounded_canonical_and_nonduplicated(self):
        facts = request().owner_facts
        valid = replace(facts, has_restrictions=1, restricted_sids=('S-1-5-1', 'S-1-5-2'))
        self.assertEqual(module.decode_enrollment_request(replace(request(), owner_facts=valid).canonical_wire).owner_facts, valid)
        for sids in (['S-1-5-1'], ('S-1-5-1', 'S-1-5-1'), ('S-1-5-2', 'S-1-5-1'), tuple('S-1-5-'+str(x) for x in range(17))):
            with self.subTest(sids=sids), self.assertRaises(ContractError): replace(facts, has_restrictions=1, restricted_sids=sids)
        with self.assertRaises(ContractError): replace(facts, restricted_sids=('S-1-5-1',))

    def test_all_process_roles_obey_signed_wire_domain_and_reject_pid_alias(self):
        value = request(); above = process(104, creation_time=MAX_INTEGER+1)
        for name in ('helper_identity', 'ui_identity'):
            with self.subTest(role=name), self.assertRaises(ContractError): replace(value, **{name: above})
        with self.assertRaises(ContractError): replace(value.owner_facts, process_identity=above)
        with self.assertRaisesRegex(ContractError, 'ENROLLMENT_PROCESS_ALIAS_CONFLICT'):
            replace(value, ui_identity=process(value.helper_identity.pid, creation_time=101))
        maximum = replace(value, helper_identity=process(104, creation_time=MAX_INTEGER))
        self.assertEqual(module.decode_enrollment_request(maximum.canonical_wire), maximum)

    def test_authority_budget_forbids_models_extra_effects_or_unbounded_io(self):
        for changes in ({'max_model_calls': 1}, {'max_input_tokens': 1}, {'max_output_tokens': 1},
                        {'max_effects': 3}, {'wall_time_ms': 60001}, {'max_bytes_read': 16*1024*1024+1},
                        {'max_bytes_written': 1048577}, {'wall_time_ms': 1999}):
            with self.subTest(changes=changes), self.assertRaises(ContractError): request(authority_budget=budget(**changes))

    def test_recovery_and_evidence_reserves_cannot_be_omitted(self):
        value = request()
        for changes in ({'evidence_reserve_bytes': 8191}, {'evidence_reserve_bytes': True},
                        {'evidence_reserve_bytes': 1048577},
                        {'authority_budget': budget(max_bytes_written=8191)},
                        {'recovery_budget': budget(max_effects=1, max_bytes_written=4095)},
                        {'recovery_budget': budget(max_effects=2)}):
            with self.subTest(changes=changes), self.assertRaises(ContractError): replace(value, **changes)

    def test_resource_bounds_and_unsupported_types_rejected(self):
        value = request()
        for changes in ({'cpu_milli': 0}, {'cpu_milli': 1001}, {'memory_bytes': 64*1024*1024+1},
                        {'storage_bytes': 8191}, {'storage_bytes': 16*1024*1024+1}, {'wall_time_ms': 60001}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(value, resource_limit=replace(value.resource_limit, **changes))
        for name in ('resource_limit', 'authority_budget', 'private_root', 'owner_facts', 'helper_identity', 'deadline'):
            with self.subTest(field=name), self.assertRaises(ContractError): replace(value, **{name: None})

    def test_session_effect_observation_and_nonce_bounds_rejected(self):
        for changes in ({'maximum_session_ns': module.MAX_SESSION_NS+1}, {'maximum_session_ns': True},
                        {'maximum_effect_duration_ns': 0}, {'maximum_effect_duration_ns': 1_000_000_001},
                        {'maximum_observation_age_ns': 0}, {'maximum_observation_age_ns': 5_000_000_001},
                        {'owner_session_nonce': '0'*32}, {'ceremony_nonce': 'A'*32}, {'clock_session_nonce': '2'*32}):
            with self.subTest(changes=changes), self.assertRaises(ContractError): request(**changes)

    def test_deadline_cannot_exceed_session_or_omit_real_boot_session_shape(self):
        value = request()
        for changes in ({'expires_monotonic_ns': 60_000_000_101}, {'expires_wall_ns': WALL+60_500_000_001},
                        {'boot_id': 'random-session-label'}, {'boot_id': 'boot:'+'-'*36+':session:'+'1'*32},
                        {'boot_id': 'boot:00000000-0000-0000-0000-000000000000:session:'+'1'*32}):
            with self.subTest(changes=changes), self.assertRaises(ContractError): replace(value, deadline=replace(value.deadline, **changes))

    def test_data_binding_current_positive_does_not_issue_or_consume_authority(self):
        value = request(); before = value.canonical_wire
        for _ in range(2): self.assertIsNone(module.require_enrollment_current(value, value, clock(), clock(2000)))
        self.assertEqual(value.canonical_wire, before)
        self.assertEqual(strict_loads(before)['assurance'], 'DATA_ONLY')

    def test_exact_monotonic_and_wall_expiry_denied(self):
        value = request()
        for current in (clock(value.deadline.expires_monotonic_ns), clock(2000, wall_time_ns=value.deadline.expires_wall_ns)):
            with self.subTest(current=current), self.assertRaisesRegex(ContractError, 'DEADLINE_EXPIRED'):
                module.require_enrollment_current(value, value, clock(), current)

    def test_boot_epoch_resume_rollback_and_untrusted_clock_rejected(self):
        value = request()
        changes = ({'boot_id': BOOT.replace('1'*32, '4'*32)}, {'durable_epoch': 8},
                   {'resume_generation': 1}, {'monotonic_ns': 999}, {'wall_time_ns': WALL-1}, {'wall_trusted': False})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ContractError):
                module.require_enrollment_current(value, value, clock(), clock(2000, **change))

    def test_clock_gap_and_uncertainty_are_bounded(self):
        value = request()
        for current in (clock(5_000_001_001), clock(2000, uncertainty_ns=module.MAX_CLOCK_UNCERTAINTY_NS+1)):
            with self.subTest(current=current), self.assertRaisesRegex(ContractError, 'ENROLLMENT_CLOCK_BOUND_INVALID'):
                module.require_enrollment_current(value, value, clock(), current)

    def test_boundary_revalidates_malformed_clock_values_in_both_positions(self):
        value = request()
        for position in ('previous', 'current'):
            for name, bad in (('wall_trusted', 1), ('wall_trusted', 'YES'), ('uncertainty_ns', -1)):
                with self.subTest(position=position, field=name, bad=bad):
                    previous, current = clock(), clock(2000)
                    object.__setattr__(previous if position == 'previous' else current, name, bad)
                    with self.assertRaises(ContractError):
                        module.require_enrollment_current(value, value, previous, current)

    def test_new_challenge_session_generation_and_copy_recovery_reject_old_request(self):
        value = request()
        for expected in (replace(value, challenge_id='challenge2'), replace(value, ceremony_nonce='6'*32),
                         replace(value, owner_session_nonce='7'*32), replace(value, authority_generation=1),
                         replace(value, database=replace(value.database, file_id_hex='8'*32))):
            with self.subTest(expected=expected.input_commitment), self.assertRaises(ContractError):
                module.require_enrollment_current(module.decode_enrollment_request(value.canonical_wire), expected, clock(), clock(2000))

    def test_transcript_wrapper_roundtrip_full_binding_and_domain_separation(self):
        value = request(); proof = transcript(value)
        wire = module.enrollment_transcript_bytes(proof)
        self.assertEqual(module.decode_enrollment_transcript(wire), proof)
        self.assertIsNone(module.require_enrollment_transcript_binding(value, value, proof, clock(), clock(2000)))
        self.assertEqual(strict_loads(wire)['kind'], 'OWNER_ENROLLMENT_NATIVE_TRANSCRIPT')
        with self.assertRaises(ContractError): module.decode_enrollment_transcript(proof.canonical_wire)
        for change in ({'kind': 'CPU_APPROVAL'}, {'profile': 'other'}, {'assurance': 'AUTHENTICATED'}, {'extra': 0}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                module.decode_enrollment_transcript(canonical_bytes(dict(strict_loads(wire), **change)))

    def test_transcript_wrong_nonce_display_principal_process_or_code_rejected(self):
        value = request()
        changes = ({'challenge_id': 'challenge2'}, {'ceremony_nonce': '4'*32}, {'request_commitment': H2},
                   {'displayed_commitment': H2}, {'principal_id': 'other'}, {'actor_session': 'other'},
                   {'ui_identity': process(104)}, {'helper_identity': process(105)}, {'ui_commitment': H2}, {'helper_commitment': H2})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ContractError):
                module.require_enrollment_transcript_binding(value, value, transcript(value, **change), clock(), clock(2000))

    def test_reported_cancel_unavailable_and_forged_truth_boolean_rejected(self):
        value = request()
        for change in ({'native_result': 6}, {'native_result': 1}, {'native_hresult': -1, 'native_result': None}):
            with self.subTest(change=change), self.assertRaisesRegex(ContractError, 'ENROLLMENT_REPORTED_VERIFIED_REQUIRED'):
                module.require_enrollment_transcript_binding(value, value, transcript(value, **change), clock(), clock(2000))
        with self.assertRaises(ContractError): transcript(value, native_result=True)

    def test_transcript_clock_stale_future_wrong_session_or_uncertainty_rejected(self):
        value = request()
        for observed in (clock(99), clock(3000), clock(1500, durable_epoch=8),
                         clock(1500, uncertainty_ns=module.MAX_CLOCK_UNCERTAINTY_NS+1)):
            with self.subTest(observed=observed), self.assertRaises(ContractError):
                module.require_enrollment_transcript_binding(value, value, transcript(value, observed_clock=observed), clock(), clock(2000))
        with self.assertRaisesRegex(ContractError, 'MONOTONIC_ROLLBACK'):
            module.require_enrollment_transcript_binding(value, value, transcript(value, observed_clock=clock(1000)),
                clock(5_000_001_001), clock(5_000_001_002))
        with self.assertRaisesRegex(ContractError, 'ENROLLMENT_TRANSCRIPT_STALE'):
            module.require_enrollment_transcript_binding(value, value, transcript(value, observed_clock=clock(75)),
                clock(50), clock(2000))

    def test_recovery_reserve_leaves_cap_evidence_and_time_available(self):
        value = request()
        for changes in ({'max_bytes_written': value.recovery_budget.as_dict()['max_bytes_written']},
                        {'wall_time_ms': value.recovery_budget.as_dict()['wall_time_ms']}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(value, authority_budget=budget(**changes))

    def test_returned_display_and_dictionary_mutation_do_not_alias_request(self):
        value = request(); original = value.canonical_wire
        view = value.as_dict(); view['owner_facts']['restricted_sids'].append('S-1-5-1')
        view['private_root']['file_id_hex'] = 'f'*32
        shown = strict_loads(module.enrollment_display_bytes(value)); shown['request']['principal_id'] = 'other'
        self.assertEqual(value.canonical_wire, original)

    def test_concurrent_decode_display_and_binding_have_no_shared_mutable_state(self):
        value = request(); wire = value.canonical_wire
        def inspect(index):
            decoded = module.decode_enrollment_request(wire)
            module.require_enrollment_current(decoded, value, clock(), clock(2000))
            return decoded.input_commitment, module.enrollment_display_commitment(decoded)
        with ThreadPoolExecutor(max_workers=4) as pool: results = list(pool.map(inspect, range(32)))
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(value.canonical_wire, wire)


if __name__ == '__main__': unittest.main()
