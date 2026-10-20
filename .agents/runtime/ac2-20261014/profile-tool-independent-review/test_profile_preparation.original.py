"""Native read-only profile probe plus negative operator-gate checks; never call Create/Delete."""
from pathlib import Path
from unittest.mock import patch
import hashlib, importlib.util, json, sys, unittest, uuid

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('root_profile_preparation', R / 'profile_qualification.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module; spec.loader.exec_module(module)

class ProfilePreparationTests(unittest.TestCase):
    def test_actual_inspection_measures_exact_identity_without_profile_mutation(self):
        facts = module.inspect()
        self.assertEqual(facts['name'], module.NAME)
        self.assertEqual(facts['SID'], module.SID)
        self.assertEqual(facts['user_sid'], module.USER)
        self.assertFalse(facts['native_Create_or_Delete_executed'])
        self.assertFalse(facts['activation_ready'])

    def test_approval_outside_owned_evidence_scope_cannot_prepare_or_call_native(self):
        with patch.object(module, 'prepare_probe', side_effect=AssertionError('FORBIDDEN_PREPARATION')) as prepare:
            with self.assertRaises(AssertionError):
                module.qualify(module.F / 'unapproved.json', '0' * 64)
            prepare.assert_not_called()

    def test_unapproved_or_wrong_identity_records_fail_before_native_preparation(self):
        directory = R / ('profile-negative-fixtures-' + uuid.uuid4().hex)
        directory.mkdir()
        for label, changes in (
            ('unapproved', {'source': 'CONTROLLED_NOT_AN_ACTUAL_HUMAN_REPLY'}),
            ('wrong_name', {'profile_name': 'CETA.Wrong.Profile'}),
            ('wrong_sid', {'profile_sid': 'S-1-15-2-1'}),
            ('cleanup_not_authorized', {'delete_only_profile_created_by_this_run': False})):
            with self.subTest(case=label):
                # This is invalid test data, never an operator authorization record.
                value = {'profile_name': module.NAME, 'profile_sid': module.SID, 'user_sid': module.USER,
                    'proposal_sha256': module.sha(module.PROPOSAL),
                    'prepared_script_sha256': module.sha(R / 'profile_qualification.py'),
                    'create_exact_new_profile': True, 'delete_only_profile_created_by_this_run': True,
                    'source': 'CONTROLLED_NOT_AN_ACTUAL_HUMAN_REPLY', 'human_reply': ''}
                value.update(changes)
                path = directory / (label + '.json')
                with path.open('x', encoding='utf-8') as out:
                    json.dump(value, out)
                with patch.object(module, 'prepare_probe', side_effect=AssertionError('FORBIDDEN_PREPARATION')) as prepare:
                    with self.assertRaises(AssertionError):
                        module.qualify(path, module.sha(path))
                    prepare.assert_not_called()

    def test_approval_hash_mismatch_is_rejected_before_reading_body(self):
        path = R / 'PROFILE-CREATION-PROPOSAL-NONAPPROVAL.txt'
        with path.open('x', encoding='utf-8') as out:
            out.write('Controlled invalid data; no authorization.\n')
        with patch.object(module, 'prepare_probe') as prepare:
            with self.assertRaises(AssertionError):
                module.qualify(path, '0' * 64)
            prepare.assert_not_called()

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProfilePreparationTests)
    ids = [test.id() for test in suite]
    with (R / 'profile-preparation-tests-r1.txt').open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    value = {'expected_ids': ids, 'tests_run': result.testsRun,
        'failures': [{'id': test.id(), 'traceback': trace} for test, trace in result.failures],
        'errors': [{'id': test.id(), 'traceback': trace} for test, trace in result.errors],
        'skips': result.skipped, 'exit_status': 0 if result.wasSuccessful() else 1,
        'CreateAppContainerProfile_or_Delete_executed': False,
        'prepared_script_sha256': module.sha(R / 'profile_qualification.py'),
        'raw_sha256': module.sha(R / 'profile-preparation-tests-r1.txt')}
    module.save(R / 'profile-preparation-tests-r1.json', value)
    print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures),
                     'errors': len(result.errors), 'Create_or_Delete_executed': False}))
    sys.exit(value['exit_status'])
