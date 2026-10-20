"""Controlled oracle values; these tests never claim native qualification."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import unittest

path = Path(__file__).resolve().parents[2] / 'tools/isolated_worker_token_oracle.py'
spec = importlib.util.spec_from_file_location('ac7_pure_token_oracle', path)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
SID = 'S-1-15-2-695244707-3853392321-2130098501-3319658173-178928504-1880712989-1319207162'


def token_pair(restricted=False, count=0):
    shared = dict(appcontainer_sid=SID, capability_count=0, restricted=restricted,
                  restricted_sid_count=count, restriction_raw_result=int(restricted),
                  restriction_last_error=0)
    parent = dict(shared, is_appcontainer=True, integrity_rid=4096, observed_monotonic_ns=123)
    worker = dict(shared, schema='ceta-isolation-token-v2', is_appcontainer=1, integrity='S-1-16-4096')
    return parent, worker


def probe():
    parent, worker = token_pair()
    protected = {name: {'sha256': str(index)} for index, name in enumerate(
        ('canonical.db', 'canonical.db-wal', 'canonical.db-shm', 'policy.txt', 'source.txt'))}
    facts = dict(token=worker, job_query=1, job_member=1,
                 allowed_read={'granted': True}, scratch_write={'granted': True},
                 hidden_event={'handle_query': 0, 'signal': 0},
                 child={'created': False}, breakaway={'created': False},
                 process_rights={key: {'granted': False, 'error': 5} for key in oracle.PROCESS_RIGHTS},
                 environment_keys=sorted(oracle.ENVIRONMENT_KEYS))
    for index in range(5):
        facts['denied_file_' + str(index)] = {mode: {'granted': False} for mode in ('read', 'write')}
    for key in ('tcp_connect', 'tcp_loopback_listen', 'tcp_wildcard_listen', 'udp_loopback'):
        facts[key] = {'granted': False}
    return dict(parent_token_facts=parent, facts=facts, worker_exit_code=0, scratch_exists=True,
                trusted_target=dict(pid=101, creation_time=123, alive_before_worker=True, alive_after_worker=True),
                excluded_event_wait=258, setup={'protected_before': protected}, protected_after=deepcopy(protected))


class IsolationQualificationOracleTests(unittest.TestCase):
    def rejected_pair(self, parent, worker, code=None):
        with self.assertRaises(oracle.QualificationError) as caught:
            oracle.assert_token_pair(parent, worker, SID)
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def test_measured_empty_restricting_list_and_positive_list_are_distinct_valid_observations(self):
        for restricted, count in ((False, 0), (True, 1), (True, 4095)):
            with self.subTest(restricted=restricted, count=count):
                oracle.assert_token_pair(*token_pair(restricted, count), SID)

    def test_nonzero_native_bool_is_truth_not_exact_one_and_success_last_error_is_not_an_error(self):
        parent, worker = token_pair(True, 1)
        parent['restriction_raw_result'] = -1
        worker['restriction_raw_result'] = 2
        parent['restriction_last_error'] = 5
        oracle.assert_token_pair(parent, worker, SID)

    def test_missing_unavailable_and_boolean_integer_substitutions_are_rejected(self):
        cases = dict(restricted=(None, 0, 'false'), restricted_sid_count=(None, False, -1, 4096, 4097),
                     restriction_raw_result=(None, False, 1 << 31, -(1 << 31) - 1),
                     restriction_last_error=(None, False, -1, 1 << 32))
        for side in (0, 1):
            for key, values in cases.items():
                pair = token_pair(); del pair[side][key]
                with self.subTest(side=side, key=key, missing=True): self.rejected_pair(*pair)
                for value in values:
                    pair = token_pair(); pair[side][key] = value
                    with self.subTest(side=side, key=key, value=value): self.rejected_pair(*pair)

    def test_false_native_result_with_error_never_becomes_measured_zero(self):
        for side in (0, 1):
            pair = token_pair(); pair[side]['restriction_last_error'] = 5
            self.rejected_pair(*pair, code='RESTRICTION_QUERY_UNAVAILABLE')

    def test_boolean_and_independent_list_must_agree_in_both_processes(self):
        for side in (0, 1):
            for key, value in (('restricted', True), ('restriction_raw_result', 1), ('restricted_sid_count', 1)):
                pair = token_pair(); pair[side][key] = value
                self.rejected_pair(*pair, code='RESTRICTION_OBSERVATIONS_DISAGREE')

    def test_valid_but_different_parent_worker_list_counts_are_rejected(self):
        parent, _ = token_pair(True, 1)
        _, worker = token_pair(True, 2)
        self.rejected_pair(parent, worker, 'PARENT_WORKER_RESTRICTION_DISAGREEMENT')

    def test_identity_capability_integrity_timestamp_and_schema_are_still_mandatory(self):
        changes = ((0, 'is_appcontainer', 1), (1, 'is_appcontainer', True),
                   (0, 'appcontainer_sid', SID + '-1'), (1, 'appcontainer_sid', SID + '-1'),
                   (0, 'capability_count', False), (1, 'capability_count', 1),
                   (0, 'integrity_rid', 8192), (1, 'integrity', 'S-1-16-8192'),
                   (0, 'observed_monotonic_ns', False), (0, 'observed_monotonic_ns', -1),
                   (1, 'schema', 'ceta-isolation-token-v1'))
        for side, key, value in changes:
            pair = token_pair(); pair[side][key] = value
            with self.subTest(side=side, key=key): self.rejected_pair(*pair)

    def test_complete_controlled_probe_passes_without_changing_input(self):
        result = probe(); before = deepcopy(result)
        oracle.assert_isolation(result, SID)
        self.assertEqual(result, before)

    def test_every_file_and_process_denial_remains_required(self):
        for index in range(5):
            for mode in ('read', 'write'):
                result = probe(); result['facts']['denied_file_' + str(index)][mode]['granted'] = True
                with self.subTest(index=index, mode=mode), self.assertRaises(oracle.QualificationError):
                    oracle.assert_isolation(result, SID)
        for key in oracle.PROCESS_RIGHTS:
            for change in ('grant', 'missing'):
                result = probe(); rights = result['facts']['process_rights']
                if change == 'grant': rights[key]['granted'] = True
                else: del rights[key]
                with self.subTest(right=key, change=change), self.assertRaises(oracle.QualificationError):
                    oracle.assert_isolation(result, SID)
        result = probe(); result['facts']['process_rights'] = {}
        with self.assertRaises(oracle.QualificationError): oracle.assert_isolation(result, SID)

    def test_network_denials_and_bounded_environment_cannot_be_omitted(self):
        for key in ('tcp_connect', 'tcp_loopback_listen', 'tcp_wildcard_listen', 'udp_loopback'):
            result = probe(); result['facts'][key]['granted'] = True
            with self.subTest(key=key), self.assertRaises(oracle.QualificationError): oracle.assert_isolation(result, SID)
        for keys in ([], ['PATH'], sorted(oracle.ENVIRONMENT_KEYS) + ['PATH'],
                     sorted(oracle.ENVIRONMENT_KEYS) + ['SECRET'], None):
            result = probe(); result['facts']['environment_keys'] = keys
            with self.subTest(keys=keys), self.assertRaises(oracle.QualificationError): oracle.assert_isolation(result, SID)

    def test_process_failure_requires_exact_typed_access_denied_not_missing_or_invalid_target(self):
        for key in oracle.PROCESS_RIGHTS:
            for error in (None, 0, 87, True, False, '5'):
                result = probe()
                if error is None: del result['facts']['process_rights'][key]['error']
                else: result['facts']['process_rights'][key]['error'] = error
                with self.subTest(right=key, error=error), self.assertRaises(oracle.QualificationError) as caught:
                    oracle.assert_isolation(result, SID)
                self.assertEqual(caught.exception.code, 'PROCESS_ACCESS_DENIED_ERROR_REQUIRED')

    def test_owned_process_identity_and_observed_liveness_bracket_cannot_be_missing_or_false(self):
        for key in ('pid', 'creation_time', 'alive_before_worker', 'alive_after_worker'):
            for value in (None, False, 0, ''):
                result = probe()
                if value is None: del result['trusted_target'][key]
                else: result['trusted_target'][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(oracle.QualificationError):
                    oracle.assert_isolation(result, SID)

    def test_exit_job_asset_scratch_sentinels_handles_and_descendants_remain_required(self):
        changes = (('worker_exit_code', 1), ('worker_exit_code', False), ('scratch_exists', False),
                   ('excluded_event_wait', 0), ('excluded_event_wait', False), ('protected_after', {}))
        for key, value in changes:
            result = probe(); result[key] = value
            with self.subTest(key=key), self.assertRaises(oracle.QualificationError): oracle.assert_isolation(result, SID)
        for key, child, value in (('allowed_read', 'granted', False), ('scratch_write', 'granted', False),
                                  ('hidden_event', 'handle_query', 1), ('hidden_event', 'signal', 1),
                                  ('child', 'created', True), ('breakaway', 'created', True)):
            result = probe(); result['facts'][key][child] = value
            with self.subTest(key=key, child=child), self.assertRaises(oracle.QualificationError):
                oracle.assert_isolation(result, SID)
        for key in ('job_query', 'job_member'):
            for value in (0, True):
                result = probe(); result['facts'][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(oracle.QualificationError):
                    oracle.assert_isolation(result, SID)


if __name__ == '__main__':
    unittest.main()
