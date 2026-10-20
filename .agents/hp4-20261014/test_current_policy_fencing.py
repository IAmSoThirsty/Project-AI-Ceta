import copy, marshal, unittest, zipfile
from unittest.mock import patch
import preserve_ceta_complete as tool
import test_provenance as author
import test_preserve_ceta_complete as native
observations = []

class CurrentPolicyFencingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        native.PreservationTests.setUpClass.__func__(cls)
    setUp = author.ProvenanceTests.setUp
    write = author.ProvenanceTests.write
    policy_data = author.ProvenanceTests.policy_data
    fixture_command = author.ProvenanceTests.fixture_command
    initialize_git = author.ProvenanceTests.initialize_git
    literal_source = author.ProvenanceTests.literal_source
    pyc = author.ProvenanceTests.pyc
    specimen = author.ProvenanceTests.specimen
    proof_policy = author.ProvenanceTests.proof_policy
    complete_capture = author.ProvenanceTests.complete_capture
    cache_policy = author.ProvenanceTests.cache_policy

    def test_new_blocked_producer_alias_is_not_read_or_copied(self):
        self.initialize_git()
        body = self.literal_source()
        self.write('tests/test_generator.py', body)
        self.fixture_command('add', 'tests/test_generator.py')
        self.fixture_command('commit', '-m', 'owned generator before new blocked alias')
        oid = self.fixture_command('rev-parse', 'HEAD:tests/test_generator.py').decode().strip()
        (self.source / 'tests/test_generator.py').write_bytes(b'current_value=17\n')
        cache = self.pyc(body)
        self.write('cache.pyc', cache)
        data = self.proof_policy([
            self.specimen('H001', 'owned_test_literal', None, body, oid=oid, aliases=['tests/test_generator.py']),
            self.specimen('W048', 'generated_cache', 'cache.pyc', cache,
                          generator={'path': 'tests/test_generator.py', 'payload': body, 'git_oid': oid}),
        ])
        self.write('new-producer-alias.py', body)
        self.fixture_command('add', 'new-producer-alias.py')
        data['classifications'] = [{'source_root': str(self.source), 'path': 'new-producer-alias.py',
                                   'kind': 'unknown', 'evidence': 'owned new blocked producer alias'}]
        policy = tool.Policy(data)
        before = native.PreservationTests.full_hashes(self)
        with patch.object(policy.provenance, 'generator_bytes', wraps=policy.provenance.generator_bytes) as reader:
            manifest = tool.capture(self.source, self.capture_path, policy)
        self.assertFalse(manifest['complete'])
        reader.assert_not_called()
        with zipfile.ZipFile(self.capture_path / 'working-tree.zip') as archive:
            self.assertNotIn('cache.pyc', archive.namelist())
            self.assertNotIn('new-producer-alias.py', archive.namelist())
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_all_explicit_blocked_kinds_refuse_producer_before_read(self):
        policy = self.cache_policy()
        binding = policy.provenance.entries['W047']
        for kind in ('unknown', 'private_key', 'live_profile'):
            changed = copy.deepcopy(policy.raw)
            changed['classifications'] = [{'source_root': str(self.source), 'path': 'tests/test_generator.py',
                                          'kind': kind, 'evidence': 'owned blocked producer classification'}]
            denied = tool.Policy(changed)
            with self.subTest(kind=kind), patch.object(denied.provenance, 'generator_bytes',
                    wraps=denied.provenance.generator_bytes) as reader:
                with self.assertRaises(tool.PreservationError):
                    denied.provenance.cache_constraints(binding, (self.source / 'cache.pyc').read_bytes())
                reader.assert_not_called()

    def test_current_blocked_plain_file_refuses_restore_publication(self):
        self.write('plain.txt', b'owned ordinary source')
        original = self.policy_data()
        tool.capture(self.source, self.capture_path, tool.Policy(original))
        changed = copy.deepcopy(original)
        changed['classifications'] = [{'source_root': str(self.source), 'path': 'plain.txt',
                                      'kind': 'unknown', 'evidence': 'owned current blocked restoration'}]
        before = native.PreservationTests.full_hashes(self)
        with self.assertRaises(tool.PreservationError):
            tool.restore(self.capture_path, self.restore_path, tool.Policy(changed))
        self.assertFalse(self.restore_path.exists())
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def blocked_generator(self, historical=False):
        body = self.literal_source()
        oid = None
        if historical:
            self.initialize_git()
        self.write('tests/test_generator.py', body)
        if historical:
            self.fixture_command('add', 'tests/test_generator.py')
            self.fixture_command('commit', '-m', 'owned historical generator')
            oid = self.fixture_command('rev-parse', 'HEAD:tests/test_generator.py').decode().strip()
            (self.source / 'tests/test_generator.py').write_bytes(b'current_value=17\n')
        cache = self.pyc(body)
        self.write('cache.pyc', cache)
        gen = {'path': 'tests/test_generator.py', 'payload': body}
        if historical:
            gen['git_oid'] = oid
        specimens = [self.specimen('H001' if historical else 'W050', 'owned_test_literal', None if historical else 'tests/test_generator.py', body, oid=oid, aliases=['tests/test_generator.py'] if historical else None), self.specimen('W048' if historical else 'W047', 'generated_cache', 'cache.pyc', cache, generator=gen)]
        data = self.proof_policy(specimens)
        data['classifications'] = [{'source_root': str(self.source), 'path': 'tests/test_generator.py', 'kind': 'unknown', 'evidence': 'reviewer-owned explicit blocked generator fixture'}]
        policy = tool.Policy(data)
        before = self.full_hashes() if hasattr(self, 'full_hashes') else native.PreservationTests.full_hashes(self)
        producer_reads = []
        real = policy.provenance.generator_bytes

        def watched(desc):
            producer_reads.append(copy.deepcopy(desc))
            return real(desc)
        with patch.object(policy.provenance, 'generator_bytes', side_effect=watched):
            manifest = tool.capture(self.source, self.capture_path, policy)
        with zipfile.ZipFile(self.capture_path / 'working-tree.zip') as z:
            members = z.namelist()
        inventory = tool.load_json(self.capture_path / 'inventory.json')
        unchanged = before == native.PreservationTests.full_hashes(self)
        observations.append({'test_id': self.id(), 'fixture': str(self.area), 'historical': historical, 'complete': manifest['complete'], 'pending': manifest['pending'], 'working_archive_members': members, 'producer_reads': producer_reads, 'cache_inventory': [e for e in inventory['entries'] if e['path'] == 'cache.pyc'], 'source_hashes_unchanged': unchanged, 'source_hashes': before})
        self.assertTrue(unchanged)
        self.assertFalse(manifest['complete'])
        self.assertNotIn('cache.pyc', members, 'explicitly blocked generator must not authorize copying its protected derived cache')
        self.assertEqual(producer_reads, [], 'blocked generator must not be reopened through cache validation')

    def blocked_restore(self, cache=False, historical=False):
        body = self.literal_source()
        if historical:
            self.initialize_git()
        self.write('tests/test_generator.py', body)
        oid = None
        if historical:
            self.fixture_command('add', 'tests/test_generator.py')
            self.fixture_command('commit', '-m', 'owned exact generator before blocked restore')
            oid = self.fixture_command('rev-parse', 'HEAD:tests/test_generator.py').decode().strip()
            (self.source / 'tests/test_generator.py').write_bytes(b'current_value=17\n')
        specimens = [self.specimen('H001' if historical else 'W050', 'owned_test_literal', None if historical else 'tests/test_generator.py', body, oid=oid, aliases=['tests/test_generator.py'] if historical else None)]
        if cache:
            value = self.pyc(body)
            self.write('cache.pyc', value)
            gen = {'path': 'tests/test_generator.py', 'payload': body}
            if historical:
                gen['git_oid'] = oid
            specimens.append(self.specimen('W048' if historical else 'W047', 'generated_cache', 'cache.pyc', value, generator=gen))
        data = self.proof_policy(specimens)
        self.complete_capture(data)
        data = copy.deepcopy(data)
        data['classifications'] = [{'source_root': str(self.source), 'path': 'tests/test_generator.py', 'kind': 'unknown', 'evidence': 'reviewer-owned newly explicit blocked restoration location'}]
        policy = tool.Policy(data)
        before = native.PreservationTests.full_hashes(self)
        caught = None
        result = None
        try:
            result = tool.restore(self.capture_path, self.restore_path, policy)
        except tool.PreservationError as exc:
            caught = str(exc)
        observations.append({'test_id': self.id(), 'fixture': str(self.area), 'cache': cache, 'historical': historical, 'blocked_location': 'tests/test_generator.py', 'caught_preservation_error': caught, 'restore_published': self.restore_path.exists(), 'actual_restore_result': result, 'source_hashes_unchanged': before == native.PreservationTests.full_hashes(self)})
        self.assertEqual(before, native.PreservationTests.full_hashes(self))
        self.assertIsNotNone(caught, 'current explicit blocked classification must reject restoration before publication')
        self.assertFalse(self.restore_path.exists())

    def test_current_blocked_generator_cache_is_not_copied(self):
        self.blocked_generator(False)

    def test_historical_blocked_generator_cache_is_not_copied(self):
        self.blocked_generator(True)

    def test_nested_cache_filename_protected_content_is_held(self):
        body = self.literal_source()
        code = compile(body, 'ordinary-name', 'exec', dont_inherit=True, optimize=0)
        constants = tuple((v.replace(co_filename=author.URI.decode()) if hasattr(v, 'co_filename') else v for v in code.co_consts))
        policy = self.cache_policy(cache_change=lambda c: c[:16] + marshal.dumps(code.replace(co_consts=constants)))
        before = native.PreservationTests.full_hashes(self)
        manifest = tool.capture(self.source, self.capture_path, policy)
        with zipfile.ZipFile(self.capture_path / 'working-tree.zip') as z:
            members = z.namelist()
        observations.append({'test_id': self.id(), 'fixture': str(self.area), 'complete': manifest['complete'], 'working_archive_members': members, 'source_hashes_unchanged': before == native.PreservationTests.full_hashes(self)})
        self.assertFalse(manifest['complete'])
        self.assertNotIn('cache.pyc', members)
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_orphan_tree_new_generator_alias_is_not_copied(self):
        self.initialize_git()
        body = self.literal_source()
        self.write('tests/test_generator.py', body)
        self.fixture_command('add', 'tests/test_generator.py')
        self.fixture_command('commit', '-m', 'old exact generator')
        oid = self.fixture_command('rev-parse', 'HEAD:tests/test_generator.py').decode().strip()
        (self.source / 'tests/test_generator.py').write_bytes(b'current_value=17\n')
        cache = self.pyc(body)
        self.write('cache.pyc', cache)
        policy = tool.Policy(self.proof_policy([self.specimen('H001', 'owned_test_literal', None, body, oid=oid, aliases=['tests/test_generator.py']), self.specimen('W048', 'generated_cache', 'cache.pyc', cache, generator={'path': 'tests/test_generator.py', 'payload': body, 'git_oid': oid})]))
        tree = self.fixture_command('mktree', data=('100644 blob ' + oid + '\treviewer-orphan-generator.py\n').encode()).decode().strip()
        before = native.PreservationTests.full_hashes(self)
        manifest = tool.capture(self.source, self.capture_path, policy)
        inv = tool.load_json(self.capture_path / 'inventory.json')
        with zipfile.ZipFile(self.capture_path / 'working-tree.zip') as z:
            members = z.namelist()
        observations.append({'test_id': self.id(), 'fixture': str(self.area), 'orphan_tree': tree, 'generator_oid': oid, 'actual_aliases': inv['git']['object_path_provenance']['blobs'][oid], 'complete': manifest['complete'], 'working_archive_members': members, 'patches_withheld': inv['git']['working_patch_b64'] is None and inv['git']['staged_patch_b64'] is None, 'source_hashes_unchanged': before == native.PreservationTests.full_hashes(self)})
        self.assertFalse(manifest['complete'])
        self.assertIn('reviewer-orphan-generator.py', inv['git']['object_path_provenance']['blobs'][oid])
        self.assertNotIn('cache.pyc', members)
        self.assertIsNone(inv['git']['working_patch_b64'])
        self.assertIsNone(inv['git']['staged_patch_b64'])
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_restore_blocked_current_generator_does_not_publish(self):
        self.blocked_restore(True, False)

    def test_restore_blocked_direct_literal_does_not_publish(self):
        self.blocked_restore(False, False)

    def test_restore_blocked_historical_generator_does_not_publish(self):
        self.blocked_restore(True, True)
