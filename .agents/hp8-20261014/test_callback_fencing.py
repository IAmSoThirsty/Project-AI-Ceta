"""Exact eight independent callback/alias methods retained as regression oracles."""
import copy, os, unittest, zipfile
from unittest.mock import patch
import preserve_ceta_complete as tool
import test_preserve_ceta_complete as native
import test_provenance as author
import test_case_alias_fencing as cases
observations = []

class CallbackBoundaryTests(cases.CaseAliasFixture):
    kinds=('unknown','private_key','live_profile')
    def state(self,policy):
        rows=[{'key':list(key),'value':copy.deepcopy(value)} for key,value in policy.classifications.items()]
        return {'raw_policy_sha256':tool.sha(tool.canonical_proof(policy.raw)),
                'active_classifications_sha256':tool.sha(tool.canonical_proof(rows)),
                'active_classifications':rows}
    def block(self,policy,events,kind):
        name='tests/TEST_MARKER.py'
        events.append({'event':'callback_enters','current_producer_classification':policy.classify(self.source,'tests/test_marker.py')})
        policy.classifications[(os.path.normcase(str(self.source)),name,'BLOCKED_CURRENT')]={
            'source_root':str(self.source),'path':name,'kind':kind,
            'evidence':'Explicit reviewer-owned callback scheduling; denial inserted before the real producer provider read'}
        events.append({'event':'case_alias_denial_inserted','blocked_kind':policy.classify(self.source,'tests/test_marker.py')['kind']})
    def marker_policy(self,historical):
        if historical:self.initialize_git()
        body=b'def test_marker():\n    value = '+repr(author.MARKER).encode()+b'\n    return value\n'
        self.assertFalse(tool.protected_positions(body)['userinfo'])
        self.assertTrue(tool.protected_positions(body)['private_markers'])
        self.write('tests/test_marker.py',body)
        oid=None
        if historical:
            self.fixture_command('add','tests/test_marker.py')
            self.fixture_command('commit','-m','Owned marker-only exact generator scheduling fixture')
            oid=self.fixture_command('rev-parse','HEAD:tests/test_marker.py').decode().strip()
            (self.source/'tests/test_marker.py').write_bytes(b'current_value=17\n')
        cache=self.pyc(body);self.write('cache.pyc',cache)
        gen={'path':'tests/test_marker.py','payload':body}
        if historical:gen['git_oid']=oid
        specimens=[self.specimen('H001' if historical else 'W050','owned_test_literal',None if historical else 'tests/test_marker.py',body,oid=oid,aliases=['tests/test_marker.py'] if historical else None),
                   self.specimen('W048' if historical else 'W047','generated_cache','cache.pyc',cache,generator=gen)]
        data=self.proof_policy(specimens)
        return data,body,cache
    def observe(self,**fields):
        observations.append({'test_id':self.id(),'fixture':str(self.area),**fields})
    def test_native_greek_case_alias_is_blocked_without_positive_spelling_expansion(self):
        name,alias='greek/σ.txt','GREEK/Σ.TXT'
        self.write(name,b'owned ordinal Greek-case fixture')
        self.assertTrue((self.source/name).samefile(self.source/alias))
        self.assertTrue(tool.equivalent_blocked_path(name,alias))
        for kind in self.kinds:
            data=self.policy_data();data['classifications']=[{'source_root':str(self.source),'path':alias,'kind':kind,'evidence':'Owned Greek ordinal denial fixture'}]
            policy=tool.Policy(data)
            with self.subTest(kind=kind),patch.object(tool,'hash_and_protection',side_effect=AssertionError('blocked path must not be read')) as reader:
                result=tool.assess_file(self.source/name,self.source,name,policy)
                self.assertEqual(result['contents'],'NOT_READ_OR_COPIED');reader.assert_not_called()
                self.assertEqual(policy.classify(self.source,name)['path'],alias)
        self.observe(native_samefile=True,ordinal_equal=True,blocked_kinds=list(self.kinds))
    def test_native_ligature_is_distinct_and_never_receives_positive_alias_admission(self):
        first,second='ﬃ.txt','ffi.txt'
        self.write(first,b'owned ligature name');self.write(second,b'owned three-letter name')
        self.assertEqual(first.casefold(),second.casefold())
        self.assertFalse((self.source/first).samefile(self.source/second))
        self.assertFalse(tool.equivalent_blocked_path(first,second))
        data=self.policy_data();digest=tool.sha(b'owned ligature name')
        data['classifications']=[{'source_root':str(self.source),'path':first,'kind':'fixture_secret_marker','sha256':digest,'evidence':'Positive exact-spelling classification lookup control only'}]
        policy=tool.Policy(data)
        self.assertIsNotNone(policy.classify(self.source,first,digest));self.assertIsNone(policy.classify(self.source,second,digest))
        self.observe(native_samefile=False,ordinal_equal=False,casefold_equal=True,positive_spelling_exact=True,classification_lookup_only=True)
    def direct_callback(self,historical):
        data,body,cache=self.marker_policy(historical)
        baseline=tool.Policy(data);manifest=tool.capture(self.source,self.capture_path,baseline)
        self.assertTrue(manifest['complete'])
        inventory=tool.load_json(self.capture_path/'inventory.json')
        real=tool.checkpoint_generator_provider(self.capture_path,inventory['content_provenance']['generators'])
        source_before=native.PreservationTests.full_hashes(self)
        for kind in self.kinds:
            with self.subTest(kind=kind):
                policy=tool.Policy(copy.deepcopy(data));policy_before=self.state(policy);events=[]
                def provider(descriptor):
                    self.block(policy,events,kind)
                    value=real(descriptor)
                    events.append({'event':'real_archived_generator_read','bytes':len(value),'sha256':tool.sha(value)})
                    return value
                receipt=policy.provenance.validate(self.source,cache,path='cache.pyc',provider=provider)
                events.append({'event':'validate_returns','receipt_present':receipt is not None})
                policy_after=self.state(policy)
                self.observe(operation='direct_validate',historical=historical,kind=kind,policy_before=policy_before,policy_after=policy_after,events=events,
                             source_unchanged=source_before==native.PreservationTests.full_hashes(self),restore_published=self.restore_path.exists(),
                             qualification='Denial deliberately inserted within a trusted provider callback after its caller permission check; real sealed fixture archive provider supplies bytes. This assertion covers an intermediate return, not an unqualified production publication.')
                self.assertEqual(source_before,native.PreservationTests.full_hashes(self))
                self.assertIsNone(receipt,'A denial inserted during the callback must be reflected before returning an admitted validation receipt')
    def test_current_marker_callback_denial_is_rechecked_before_validation_receipt(self):self.direct_callback(False)
    def test_historical_marker_callback_denial_is_rechecked_before_validation_receipt(self):self.direct_callback(True)
    def restore_callback(self,historical):
        data,body,cache=self.marker_policy(historical)
        baseline=tool.Policy(data);self.assertTrue(tool.capture(self.source,self.capture_path,baseline)['complete'])
        source_before=native.PreservationTests.full_hashes(self)
        factory=tool.checkpoint_generator_provider
        for kind in self.kinds:
            with self.subTest(kind=kind):
                target=self.area/('recovered-after-callback-'+kind)
                changed=copy.deepcopy(data);changed['restore_targets']=[str(target)]
                policy=tool.Policy(changed);policy_before=self.state(policy);events=[]
                def wrapped_factory(*args):
                    real=factory(*args)
                    def provider(descriptor):
                        self.block(policy,events,kind)
                        value=real(descriptor)
                        events.append({'event':'real_archived_generator_read','bytes':len(value),'sha256':tool.sha(value)})
                        return value
                    return provider
                caught=None;receipt=None
                with patch.object(tool,'checkpoint_generator_provider',side_effect=wrapped_factory):
                    try:receipt=tool.restore(self.capture_path,target,policy)
                    except tool.PreservationError as exc:caught=str(exc)
                events.append({'event':'restore_returns_or_refuses','refused':caught is not None,'destination_published':target.exists()})
                self.observe(operation='actual_restore_with_injected_callback',historical=historical,kind=kind,policy_before=policy_before,policy_after=self.state(policy),events=events,
                             preservation_error=caught,receipt_present=receipt is not None,source_unchanged=source_before==native.PreservationTests.full_hashes(self),
                             qualification='Real sealed fixture checkpoint, unchanged restoration path, scheduling wrapper around the real provider; no external source or actual user policy touched.')
                self.assertIsNotNone(caught);self.assertFalse(target.exists());self.assertIsNone(receipt)
                self.assertEqual(source_before,native.PreservationTests.full_hashes(self))
    def test_current_callback_denial_refuses_actual_restore_publication(self):self.restore_callback(False)
    def test_historical_callback_denial_refuses_actual_restore_publication(self):self.restore_callback(True)
    def capture_callback(self,historical):
        data,body,cache=self.marker_policy(historical);source_before=native.PreservationTests.full_hashes(self)
        for kind in self.kinds:
            with self.subTest(kind=kind):
                target=self.area/('checkpoint-after-callback-'+kind)
                changed=copy.deepcopy(data);changed['capture_targets']=[str(target)]
                policy=tool.Policy(changed);policy_before=self.state(policy);events=[];real=policy.provenance.generator_bytes
                def reader(descriptor):
                    self.block(policy,events,kind)
                    try:value=real(descriptor)
                    except tool.PreservationError:
                        events.append({'event':'native_generator_gate_refuses_before_read'});raise
                    events.append({'event':'generator_bytes_return','bytes':len(value),'sha256':tool.sha(value)})
                    return value
                with patch.object(policy.provenance,'generator_bytes',side_effect=reader):
                    manifest=tool.capture(self.source,target,policy)
                with zipfile.ZipFile(target/'working-tree.zip') as archive:copied='cache.pyc' in archive.namelist()
                self.observe(operation='actual_capture_with_injected_callback',historical=historical,kind=kind,policy_before=policy_before,policy_after=self.state(policy),events=events,
                             complete=manifest['complete'],cache_copied=copied,source_unchanged=source_before==native.PreservationTests.full_hashes(self),
                             qualification='Real fixture capture with an explicitly injected mutation before generator_bytes delegates to its original gate; it should hold the cache and never return producer bytes.')
                self.assertFalse(manifest['complete']);self.assertFalse(copied)
                self.assertFalse(any(e['event']=='generator_bytes_return' for e in events))
                self.assertEqual(source_before,native.PreservationTests.full_hashes(self))
    def test_current_callback_denial_holds_actual_capture_without_cache_copy(self):self.capture_callback(False)
    def test_historical_callback_denial_holds_actual_capture_without_cache_copy(self):self.capture_callback(True)


class ProviderBoundaryTests(cases.CaseAliasFixture):
    """New callback-result and final subject/producer fencing oracles."""
    marker_policy = CallbackBoundaryTests.marker_policy

    def deny(self, policy, name, kind='unknown'):
        policy.classifications[(os.path.normcase(str(self.source)), name, 'BLOCKED_CURRENT')] = {
            'source_root': str(self.source), 'path': name, 'kind': kind,
            'evidence': 'Owned exact final callback boundary scheduling fixture'}

    def test_noncallable_provider_is_refused_as_a_validation_result(self):
        data, body, cache = self.marker_policy(False)
        policy = tool.Policy(data)
        self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc', provider='not-a-provider'))

    def test_provider_must_return_exact_immutable_bytes(self):
        data, body, cache = self.marker_policy(False)
        before = native.PreservationTests.full_hashes(self)
        for value in (None, False, body.decode('utf-8'), bytearray(body), memoryview(body)):
            policy = tool.Policy(data)
            with self.subTest(result_type=type(value).__name__):
                self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc',
                                                           provider=lambda descriptor, value=value: value))
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_subject_denial_inserted_inside_provider_refuses_receipt(self):
        data, body, cache = self.marker_policy(False)
        before = native.PreservationTests.full_hashes(self)
        for kind in ('unknown', 'private_key', 'live_profile'):
            policy = tool.Policy(copy.deepcopy(data))
            calls = []
            def provider(descriptor):
                calls.append(descriptor['member'])
                self.deny(policy, 'CACHE.pyc', kind)
                return body
            with self.subTest(kind=kind):
                self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc', provider=provider))
                self.assertEqual(len(calls), 1)
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_producer_denial_inserted_during_receipt_construction_refuses_return(self):
        data, body, cache = self.marker_policy(False)
        for kind in ('unknown', 'private_key', 'live_profile'):
            policy = tool.Policy(copy.deepcopy(data))
            original = policy.provenance.receipt
            def make_receipt(entry):
                value = original(entry)
                self.deny(policy, 'TESTS/TEST_MARKER.py', kind)
                return value
            with self.subTest(kind=kind), patch.object(policy.provenance, 'receipt', side_effect=make_receipt):
                self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc', provider=lambda descriptor: body))

    def test_subject_denial_inserted_during_receipt_construction_refuses_return(self):
        data, body, cache = self.marker_policy(False)
        for kind in ('unknown', 'private_key', 'live_profile'):
            policy = tool.Policy(copy.deepcopy(data))
            original = policy.provenance.receipt
            def make_receipt(entry):
                value = original(entry)
                self.deny(policy, 'CACHE.pyc', kind)
                return value
            with self.subTest(kind=kind), patch.object(policy.provenance, 'receipt', side_effect=make_receipt):
                self.assertIsNone(policy.provenance.validate(self.source, cache, path='cache.pyc', provider=lambda descriptor: body))

    def test_exact_benign_immutable_provider_preserves_bound_positive_receipt(self):
        data, body, cache = self.marker_policy(False)
        policy = tool.Policy(data)
        before = native.PreservationTests.full_hashes(self)
        receipt = policy.provenance.validate(self.source, cache, path='cache.pyc', provider=lambda descriptor: body)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['identity']['sha256'], tool.sha(cache))
        self.assertEqual(receipt['generator']['sha256'], tool.sha(body))
        self.assertEqual(receipt['generator']['path'], 'tests/test_marker.py')
        self.assertEqual(before, native.PreservationTests.full_hashes(self))

    def test_provider_control_exceptions_propagate_without_receipt_or_publication(self):
        data, body, cache = self.marker_policy(False)
        before = native.PreservationTests.full_hashes(self)
        for exception in (KeyboardInterrupt, SystemExit):
            policy = tool.Policy(copy.deepcopy(data))
            def provider(descriptor):
                raise exception('owned control boundary probe')
            with self.subTest(exception=exception.__name__), self.assertRaises(exception):
                policy.provenance.validate(self.source, cache, path='cache.pyc', provider=provider)
        self.assertEqual(before, native.PreservationTests.full_hashes(self))
        self.assertFalse(self.restore_path.exists())
