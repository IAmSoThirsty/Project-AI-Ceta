"""HP5 native case-alias fencing; synthetic proofs remain test-only."""
import copy, json, os, unittest, zipfile
from unittest.mock import patch
import preserve_ceta_complete as tool
import test_provenance as author
import test_preserve_ceta_complete as native

observations = []

class CaseAliasFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native.PreservationTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):
        selected = [entry for entry in observations if entry['test_id'].startswith(__name__ + '.' + cls.__name__ + '.')]
        print(json.dumps({'case_alias_native_observations': selected}, ensure_ascii=True))
    setUp = author.ProvenanceTests.setUp
    write = author.ProvenanceTests.write
    policy_data = author.ProvenanceTests.policy_data
    fixture_command = author.ProvenanceTests.fixture_command
    initialize_git = author.ProvenanceTests.initialize_git
    literal_source = author.ProvenanceTests.literal_source
    pyc = author.ProvenanceTests.pyc
    specimen = author.ProvenanceTests.specimen
    proof_policy = author.ProvenanceTests.proof_policy
    cache_policy = author.ProvenanceTests.cache_policy
    def record(self, **details):
        observations.append({'test_id': self.id(), 'fixture': str(self.area), **details})

class ReusedIndependentCaseAliasTests(CaseAliasFixture):
    def test_windows_same_file_blocked_plain_restore_case_alias_is_denied(self):
        self.write('plain.txt', b'owned independent ordinary source')
        data = self.policy_data()
        self.assertTrue(tool.capture(self.source, self.capture_path, tool.Policy(data))['complete'])
        changed = copy.deepcopy(data)
        changed['classifications'] = [{'source_root': str(self.source), 'path': 'PLAIN.txt', 'kind': 'unknown',
                                      'evidence': 'independent same Windows file blocked case alias'}]
        self.assertTrue((self.source / 'PLAIN.txt').samefile(self.source / 'plain.txt'))
        before = native.PreservationTests.full_hashes(self)
        caught = False
        try:
            tool.restore(self.capture_path, self.restore_path, tool.Policy(changed))
        except tool.PreservationError:
            caught = True
        self.record(same_windows_file=True, blocked_path='PLAIN.txt', enumerated_path='plain.txt',
                    refused=caught, restore_published=self.restore_path.exists())
        self.assertEqual(before, native.PreservationTests.full_hashes(self))
        self.assertTrue(caught, 'Current same-file Windows case alias must block restore before publication')
        self.assertFalse(self.restore_path.exists())


    def test_windows_same_file_blocked_producer_case_alias_is_denied(self):
        original = self.cache_policy()
        changed = copy.deepcopy(original.raw)
        blocked = 'tests/TEST_GENERATOR.py'
        self.assertTrue((self.source / blocked).samefile(self.source / 'tests/test_generator.py'))
        changed['classifications'] = [{'source_root': str(self.source), 'path': blocked, 'kind': 'unknown',
                                      'evidence': 'independent same Windows file blocked case alias'}]
        policy = tool.Policy(changed)
        before = native.PreservationTests.full_hashes(self)
        with patch.object(policy.provenance, 'generator_bytes', wraps=policy.provenance.generator_bytes) as reader:
            manifest = tool.capture(self.source, self.capture_path, policy)
        with zipfile.ZipFile(self.capture_path / 'working-tree.zip') as archive:
            copied = 'cache.pyc' in archive.namelist()
        self.record(same_windows_file=True, blocked_path=blocked, enumerated_path='tests/test_generator.py',
                    complete=manifest['complete'], cache_copied=copied, producer_reads=reader.call_count)
        self.assertEqual(before, native.PreservationTests.full_hashes(self))
        self.assertFalse(manifest['complete'], 'Current block of the same Windows file must not be bypassed by filename case')
        self.assertFalse(copied)
        reader.assert_not_called()


class WindowsCaseAliasTests(CaseAliasFixture):
    kinds = ('unknown', 'private_key', 'live_profile')

    def blocked_data(self, data, name, kind):
        changed = copy.deepcopy(data)
        changed['classifications'] = [{'source_root': str(self.source), 'path': name, 'kind': kind,
                                      'evidence': 'owned HP5 native case-alias adverse fixture'}]
        return changed

    def historical_cache(self):
        self.initialize_git()
        body = self.literal_source()
        aliases = ['tests/test_generator.py', 'tests/second_generator.py']
        for name in aliases:
            self.write(name, body)
        self.fixture_command('add', *aliases)
        self.fixture_command('commit', '-m', 'owned exact historical generator aliases')
        oid = self.fixture_command('rev-parse', 'HEAD:' + aliases[0]).decode().strip()
        for name in aliases:
            (self.source / name).write_bytes(b'current_value=17\n')
        cache = self.pyc(body)
        self.write('cache.pyc', cache)
        data = self.proof_policy([
            self.specimen('H001', 'owned_test_literal', None, body, oid=oid, aliases=sorted(aliases)),
            self.specimen('W048', 'generated_cache', 'cache.pyc', cache,
                          generator={'path': aliases[0], 'payload': body, 'git_oid': oid}),
        ])
        return data, body, cache, oid, sorted(aliases)

    def provider_observer(self, calls):
        original = tool.checkpoint_generator_provider
        def factory(*args):
            real = original(*args)
            def provider(descriptor):
                calls.append(descriptor['member'])
                return real(descriptor)
            return provider
        return factory

    def test_native_case_comparison_matches_actual_samefile_without_record_rewrite(self):
        results = []
        for original, alias in (('plain.txt', 'PLAIN.txt'), ('folder/source.py', 'FOLDER/SOURCE.py'),
                                ('accent/über.txt', 'ACCENT/ÜBER.TXT')):
            self.write(original, b'owned case-equivalence probe')
            same = (self.source / alias).samefile(self.source / original)
            equal = tool.equivalent_blocked_path(original, alias)
            self.assertTrue(same)
            self.assertTrue(equal)
            data = self.blocked_data(self.policy_data(), alias, 'unknown')
            entry = tool.Policy(data).classify(self.source, original)
            self.assertEqual(entry['path'], alias)
            results.append({'original': original, 'alias': alias, 'samefile': same, 'ordinal_equal': equal})
        self.record(native_case_equivalence=results, original_record_spellings_preserved=True)

    def test_python_casefold_expansion_does_not_merge_distinct_native_files(self):
        first, second = 'straße.txt', 'strasse.txt'
        self.write(first, b'owned first distinct path')
        self.write(second, b'owned second distinct path')
        self.assertEqual(first.casefold(), second.casefold())
        self.assertFalse((self.source / first).samefile(self.source / second))
        self.assertFalse(tool.equivalent_blocked_path(first, second))
        data = self.blocked_data(self.policy_data(), first, 'unknown')
        policy = tool.Policy(data)
        self.assertIsNone(policy.classify(self.source, second))
        self.assertIsNotNone(policy.classify(self.source, first))
        self.record(python_casefold_equal=True, native_samefile=False, ordinal_equal=False)

    def test_python_lowercase_unicode_expansion_does_not_merge_distinct_native_files(self):
        first, second = 'İ.txt', 'i\u0307.txt'
        self.write(first, b'owned first unicode path')
        self.write(second, b'owned second unicode path')
        self.assertEqual(first.lower(), second.lower())
        self.assertFalse((self.source / first).samefile(self.source / second))
        self.assertFalse(tool.equivalent_blocked_path(first, second))
        data = self.blocked_data(self.policy_data(), first, 'unknown')
        self.assertIsNone(tool.Policy(data).classify(self.source, second))
        self.record(python_lowercase_equal=True, current_ntpath_normcase_equal=os.path.normcase(first) == os.path.normcase(second),
                    native_samefile=False, ordinal_equal=False)

    def test_composed_unicode_names_are_not_normalized_into_authorization(self):
        first, second = 'å.txt', 'a\u030a.txt'
        self.write(first, b'owned composed name')
        self.write(second, b'owned decomposed name')
        self.assertFalse((self.source / first).samefile(self.source / second))
        self.assertFalse(tool.equivalent_blocked_path(first, second))
        self.assertIsNone(tool.Policy(self.blocked_data(self.policy_data(), first, 'unknown')).classify(self.source, second))

    def test_every_blocked_kind_fences_direct_case_alias_before_source_read(self):
        self.write('plain.txt', b'owned ordinary classified source')
        before = native.PreservationTests.full_hashes(self)
        for kind in self.kinds:
            policy = tool.Policy(self.blocked_data(self.policy_data(), 'PLAIN.txt', kind))
            with self.subTest(kind=kind), patch.object(tool, 'hash_and_protection',
                    side_effect=AssertionError('blocked source content must not be read')) as reader:
                result = tool.assess_file(self.source / 'plain.txt', self.source, 'plain.txt', policy)
                self.assertEqual(result['kind'], 'pending_sensitive')
                self.assertEqual(result['contents'], 'NOT_READ_OR_COPIED')
                self.assertEqual((result['path'], result['classification']['path']), ('plain.txt', 'PLAIN.txt'))
                reader.assert_not_called()
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_every_blocked_kind_fences_current_generator_and_callback_before_read(self):
        original = self.cache_policy()
        before = native.PreservationTests.full_hashes(self)
        cache = (self.source / 'cache.pyc').read_bytes()
        self.assertTrue((self.source / 'TESTS/TEST_GENERATOR.py').samefile(self.source / 'tests/test_generator.py'))
        results = []
        for kind in self.kinds:
            policy = tool.Policy(self.blocked_data(original.raw, 'TESTS/TEST_GENERATOR.py', kind))
            calls = []
            def provider(descriptor):
                calls.append(descriptor)
                raise AssertionError('blocked generator provider must not execute')
            with self.subTest(kind=kind), patch.object(policy.provenance, 'generator_bytes',
                                                     wraps=policy.provenance.generator_bytes) as reader:
                self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc'))
                self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc', provider=provider))
                self.assertEqual(calls, [])
                reader.assert_not_called()
            results.append({'kind': kind, 'generator_reads': 0, 'provider_calls': len(calls)})
        self.assertEqual(before, native.PreservationTests.full_hashes(self))
        self.record(cases=results)

    def test_every_historical_case_alias_and_blocked_kind_fences_generator_and_callback(self):
        data, body, cache, oid, aliases = self.historical_cache()
        before = native.PreservationTests.full_hashes(self)
        results = []
        for name in aliases:
            self.assertTrue((self.source / name.upper()).samefile(self.source / name))
            for kind in self.kinds:
                policy = tool.Policy(self.blocked_data(data, name.upper(), kind))
                view = tool.create_read_view(self.source, policy, self.area / ('view-' + str(len(results))))
                policy.provenance.observe_generator_aliases(self.source, view)
                self.assertEqual(policy.provenance.observed_generator_aliases[oid], aliases)
                calls = []
                def provider(descriptor):
                    calls.append(descriptor['git_oid'])
                    return body
                with self.subTest(name=name, kind=kind), patch.object(policy.provenance, 'generator_bytes',
                                                       wraps=policy.provenance.generator_bytes) as reader:
                    self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc'))
                    self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc', provider=provider))
                    self.assertEqual(calls, [])
                    reader.assert_not_called()
                results.append({'blocked_alias': name.upper(), 'kind': kind, 'generator_reads': 0, 'provider_calls': 0})
        self.assertEqual(before, native.PreservationTests.full_hashes(self))
        self.record(cases=results)

    def test_direct_provenance_case_block_precedes_literal_validation(self):
        body = self.literal_source()
        self.write('tests/test_literal.py', body)
        data = self.proof_policy([self.specimen('W001', 'owned_test_literal', 'tests/test_literal.py', body)])
        for kind in self.kinds:
            policy = tool.Policy(self.blocked_data(data, 'TESTS/TEST_LITERAL.py', kind))
            with self.subTest(kind=kind), patch.object(tool, 'python_literal_constraints',
                       side_effect=AssertionError('blocked literal must not be inspected')) as validator:
                self.assertIsNone(policy.provenance.validate(self.source, body, path='tests/test_literal.py'))
                validator.assert_not_called()

    def test_every_blocked_kind_closes_plain_capture_and_restore_case_alias(self):
        self.write('plain.txt', b'owned ordinary preservation fixture')
        original = self.policy_data()
        self.assertTrue(tool.capture(self.source, self.capture_path, tool.Policy(original))['complete'])
        before = native.PreservationTests.full_hashes(self)
        for kind in self.kinds:
            changed = self.blocked_data(original, 'PLAIN.txt', kind)
            target = self.area / ('capture-' + kind)
            restored = self.area / ('restore-' + kind)
            changed['capture_targets'].append(str(target))
            changed['restore_targets'] = [str(restored)]
            policy = tool.Policy(changed)
            with self.subTest(kind=kind):
                manifest = tool.capture(self.source, target, policy)
                self.assertFalse(manifest['complete'])
                with zipfile.ZipFile(target / 'working-tree.zip') as archive:
                    self.assertNotIn('plain.txt', archive.namelist())
                with self.assertRaises(tool.PreservationError):
                    tool.verify_checkpoint(self.capture_path, policy)
                with self.assertRaises(tool.PreservationError):
                    tool.restore(self.capture_path, restored, policy)
                self.assertFalse(restored.exists())
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_every_blocked_kind_refuses_current_cache_restore_before_archive_provider(self):
        original = self.cache_policy()
        self.assertTrue(tool.capture(self.source, self.capture_path, original)['complete'])
        before = native.PreservationTests.full_hashes(self)
        results = []
        for kind in self.kinds:
            changed = self.blocked_data(original.raw, 'TESTS/TEST_GENERATOR.py', kind)
            destination = self.area / ('restored-' + kind)
            changed['restore_targets'] = [str(destination)]
            calls = []
            with self.subTest(kind=kind), patch.object(tool, 'checkpoint_generator_provider', self.provider_observer(calls)):
                with self.assertRaises(tool.PreservationError):
                    tool.restore(self.capture_path, destination, tool.Policy(changed))
                self.assertFalse(destination.exists())
                self.assertEqual(calls, [])
            results.append({'kind': kind, 'provider_calls': 0, 'output_exists': False})
        self.assertEqual(before, native.PreservationTests.full_hashes(self))
        self.record(cases=results)

    def test_every_blocked_kind_refuses_historical_cache_restore_before_provider(self):
        data, body, cache, oid, aliases = self.historical_cache()
        self.assertTrue(tool.capture(self.source, self.capture_path, tool.Policy(data))['complete'])
        before = native.PreservationTests.full_hashes(self)
        for kind in self.kinds:
            changed = self.blocked_data(data, aliases[1].upper(), kind)
            destination = self.area / ('restored-history-' + kind)
            changed['restore_targets'] = [str(destination)]
            calls = []
            with self.subTest(kind=kind), patch.object(tool, 'checkpoint_generator_provider', self.provider_observer(calls)):
                with self.assertRaises(tool.PreservationError):
                    tool.restore(self.capture_path, destination, tool.Policy(changed))
                self.assertFalse(destination.exists())
                self.assertEqual(calls, [])
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_every_blocked_kind_fences_native_git_metadata_case_alias_on_restore(self):
        self.initialize_git()
        data = self.policy_data()
        data['source_roots'].append(str(self.source / '.git'))
        self.assertTrue(tool.capture(self.source, self.capture_path, tool.Policy(data))['complete'])
        self.assertTrue((self.source / '.git/CONFIG').samefile(self.source / '.git/config'))
        before = native.PreservationTests.full_hashes(self)
        for kind in self.kinds:
            changed = copy.deepcopy(data)
            changed['classifications'] = [{'source_root': str(self.source / '.git'), 'path': 'CONFIG',
                                           'kind': kind, 'evidence': 'owned native Git metadata case alias'}]
            destination = self.area / ('restored-metadata-' + kind)
            changed['restore_targets'] = [str(destination)]
            with self.subTest(kind=kind), self.assertRaises(tool.PreservationError):
                tool.restore(self.capture_path, destination, tool.Policy(changed))
            self.assertFalse(destination.exists())
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_duplicate_equivalent_blocked_classifications_are_rejected(self):
        for first_kind in self.kinds:
            for second_kind in self.kinds:
                data = self.blocked_data(self.policy_data(), 'plain.txt', first_kind)
                other = copy.deepcopy(data['classifications'][0])
                other.update(path='PLAIN.txt', kind=second_kind)
                data['classifications'].append(other)
                with self.subTest(first=first_kind, second=second_kind), self.assertRaises(tool.PreservationError):
                    tool.Policy(data)

    def test_duplicate_equivalent_same_hash_is_rejected_but_distinct_versions_remain(self):
        original = self.policy_data()
        entries = [{'source_root': str(self.source), 'path': 'fixtures/marker.key', 'kind': 'fixture_secret_marker',
                    'sha256': tool.sha(author.MARKER + b'\n'), 'evidence': 'owned exact marker-only historical fixture'}]
        original['classifications'] = entries
        duplicate = copy.deepcopy(entries[0])
        duplicate['path'] = 'FIXTURES/MARKER.key'
        original['classifications'].append(duplicate)
        with self.assertRaises(tool.PreservationError):
            tool.Policy(original)
        duplicate['path'] = entries[0]['path']
        duplicate['sha256'] = tool.sha(author.MARKER + b'\n# second marker-only fixture\n')
        policy = tool.Policy(original)
        for entry in entries:
            self.assertEqual(policy.classify(self.source, entry['path'], entry['sha256']), entry)
        self.assertIsNone(policy.classify(self.source, 'FIXTURES/MARKER.key', entries[0]['sha256']))

    def test_current_block_wins_over_hash_specific_positive_classification(self):
        for kind in self.kinds:
            data = self.blocked_data(self.policy_data(), 'FIXTURES/MARKER.key', kind)
            permitted = {'source_root': str(self.source), 'path': 'fixtures/marker.key', 'kind': 'fixture_secret_marker',
                         'sha256': tool.sha(author.MARKER + b'\n'), 'evidence': 'owned marker fixture version'}
            data['classifications'].insert(0, permitted)
            policy = tool.Policy(data)
            with self.subTest(kind=kind):
                self.assertEqual(policy.classify(self.source, permitted['path'], permitted['sha256'])['kind'], kind)

    def test_block_equivalence_does_not_expand_to_other_roots_or_positive_spellings(self):
        self.write('plain.txt', b'owned first root fixture')
        other = self.area / 'other-owned-root'
        other.mkdir()
        (other / 'plain.txt').write_bytes(b'owned second root fixture')
        data = self.blocked_data(self.policy_data(), 'PLAIN.txt', 'unknown')
        data['source_roots'].append(str(other))
        policy = tool.Policy(data)
        self.assertIsNone(policy.classify(other, 'plain.txt'))
        self.assertFalse((other / 'plain.txt').samefile(self.source / 'plain.txt'))
        unrelated = self.area / 'unapproved-owned-root'
        unrelated.mkdir()
        with self.assertRaises(tool.PreservationError):
            policy.authorize(unrelated, 'source_roots')

    def test_in_memory_case_alias_block_is_rechecked_without_cached_decision(self):
        original = self.cache_policy()
        original.classifications[(os.path.normcase(str(self.source)), 'TESTS/TEST_GENERATOR.py', 'BLOCKED_CURRENT')] = {
            'source_root': str(self.source), 'path': 'TESTS/TEST_GENERATOR.py', 'kind': 'unknown',
            'evidence': 'owned late in-memory current case-alias block'}
        with patch.object(original.provenance, 'generator_bytes', wraps=original.provenance.generator_bytes) as reader:
            result = tool.capture(self.source, self.capture_path, original)
            reader.assert_not_called()
        self.assertFalse(result['complete'])
        with zipfile.ZipFile(self.capture_path / 'working-tree.zip') as archive:
            self.assertNotIn('cache.pyc', archive.namelist())

    def test_native_comparison_failure_closes_before_any_source_content_read(self):
        self.write('plain.txt', b'owned native comparator fault fixture')
        policy = tool.Policy(self.blocked_data(self.policy_data(), 'PLAIN.txt', 'unknown'))
        with patch.object(tool, 'windows_ordinal_comparator', return_value=lambda *args: 0), \
             patch.object(tool, 'hash_and_protection', side_effect=AssertionError('source read after failed comparator')) as reader:
            with self.assertRaises(tool.PreservationError):
                tool.assess_file(self.source / 'plain.txt', self.source, 'plain.txt', policy)
            reader.assert_not_called()

    def test_unsafe_or_excessive_path_spellings_refuse_before_comparator(self):
        for unsafe in ('../plain.txt', 'folder\\plain.txt', 'plain.txt:stream', 'plain.txt\0tail', 'CON', 'plain.txt.',
                       'x' * 32768):
            with self.subTest(path=unsafe[:40]), patch.object(tool, 'windows_ordinal_comparator') as comparator:
                with self.assertRaises(tool.PreservationError):
                    tool.equivalent_blocked_path(unsafe, 'plain.txt')
                comparator.assert_not_called()


