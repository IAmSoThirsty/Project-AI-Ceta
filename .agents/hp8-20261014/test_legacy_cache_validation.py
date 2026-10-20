"""Exact legacy data-only checks; real owned children, no source admission.

Only the two explicitly authorized external input bytes are read into memory.
They never become files, argv, logs, executable code, or a live policy receipt.
Direct ContentProvenance seam tests use declared synthetic policy objects and
only the refusal/constraint boundary. Native scheduling injections are labeled.
"""
from contextlib import contextmanager
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch
import uuid

import preserve_ceta_complete as tool
import legacy_cache_validation as legacy
import legacy_cache_worker311 as worker

Q=Path(__file__).parent.absolute()
R=Q.parent/'runtime'/Q.name
FIXTURES=R/'native-review-fixtures'
NATIVE_OBSERVATIONS=[]
OBSERVATION_LOCK=threading.Lock()

def identity(path):
    first=tool.file_identity(tool.lstat(path));size,sha,_=tool.hash_file(path)
    if first!=tool.file_identity(tool.lstat(path)) or first['bytes']!=size:raise RuntimeError('native input drift')
    return {'sha256':sha,'bytes':size,'native_identity':first}

@contextmanager
def watch_native(test_id):
    """Observe the actual canonical port; every operation still calls Windows."""
    port=legacy._port(tool);launch,close=port.launch,port.close
    launched=[]
    def observed_launch(image,arguments,**options):
        owned=launch(image,arguments,**options)
        row={'test_id':test_id,'pid':owned.pid,'creation_time_100ns':owned.creation_time,
             'image':image,'argv':list(arguments),'expected_image_sha256':options['expected_image_sha256'],
             'standard_handles_count':len(options['standard_handles']),'closed':False}
        with OBSERVATION_LOCK:launched.append((owned,row));NATIVE_OBSERVATIONS.append(row)
        return owned
    def observed_close(owned):
        row=next(row for obj,row in launched if obj is owned)
        row.update(exit_status=owned.poll(),active_processes_before_close=owned.active_process_count())
        close(owned);row['closed']=True
    with patch.object(port,'launch',side_effect=observed_launch),patch.object(port,'close',observed_close):
        yield launched

class LegacyCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name!='nt' or sys.version_info[:2]!=(3,12):raise RuntimeError('requires exact native parent3.12')
        if Q.name!='hp8-20261014' or Path(os.environ.get('CETA_PRESERVATION_TEST_FIXTURE_ROOT',str(FIXTURES))).absolute()!=FIXTURES:
            raise RuntimeError('exact assigned native fixture root required')
        tool.safe_components(FIXTURES,allow_missing=True);FIXTURES.mkdir(exist_ok=True)
        cls.cache_before=identity(legacy.X/legacy.CACHE_PATH)
        with tool.open_source(legacy.X/legacy.CACHE_PATH,exclusive=True) as handle:cls.cache=handle.read(10573)
        cls.source=tool.git(legacy.X,'cat-file','blob',legacy.SOURCE_OID)
        if len(cls.cache)!=10572 or legacy.digest(cls.cache)!=legacy.CACHE_SHA256:raise RuntimeError('exact authorized cache changed')
        if len(cls.source)!=6316 or legacy.digest(cls.source)!=legacy.SOURCE_SHA256:raise RuntimeError('exact authorized source changed')
        cls.pins_before={str(path):identity(path) for path in (legacy.IMAGE,legacy.WORKER,legacy.NATIVE_PORT,legacy.READER,legacy.REVIEW)}

    @classmethod
    def tearDownClass(cls):
        if identity(legacy.X/legacy.CACHE_PATH)!=cls.cache_before:raise RuntimeError('authorized input conservation failed')
        if {str(path):identity(path) for path in (legacy.IMAGE,legacy.WORKER,legacy.NATIVE_PORT,legacy.READER,legacy.REVIEW)}!=cls.pins_before:
            raise RuntimeError('pinned dependency conservation failed')

    def setUp(self):
        self.area=FIXTURES/('legacy-'+tool.sha(self.id().encode())[:8]+'-'+uuid.uuid4().hex[:8])
        self.area.mkdir()

    def verify(self,**changes):
        values={'aliases':list(legacy.ALIASES),'permitted':lambda:True};values.update(changes)
        return legacy.verify(tool,self.cache,self.source,**values)

    def assert_error(self,code,function):
        with self.assertRaises(legacy.LegacyValidationError) as result:function()
        self.assertEqual(result.exception.code,code)
        return result.exception

    def assert_closed(self,launched):
        self.assertTrue(launched)
        for _,row in launched:
            self.assertTrue(row['closed']);self.assertEqual(row['active_processes_before_close'],0)
            self.assertIsNotNone(row['exit_status'])
            self.assertEqual(row['argv'],['-I','-S','-B','-X','utf8',str(legacy.WORKER)])
            self.assertEqual(row['standard_handles_count'],3)

    def synthetic_provenance(self):
        """Synthetic local policy only; no actual W045 policy entry is activated."""
        source=self.area/'source';source.mkdir()
        obj=tool.ContentProvenance.__new__(tool.ContentProvenance)
        obj.source_root=source
        obj.policy=tool.Policy({'schema_version':1,'source_roots':[str(source)],'git_roots':[],
                                'capture_targets':[],'restore_targets':[],'classifications':[],'declared_inputs':[]})
        obj.aliases={legacy.SOURCE_OID:list(legacy.ALIASES)}
        obj.observed_generator_aliases=None
        obj.entries={};obj.locations={};obj.records={};obj.inputs={}
        entry={'entry_id':'W045','kind':'generated_cache','path':legacy.CACHE_PATH,'sha256':legacy.CACHE_SHA256,'source_root':str(source)}
        return obj,entry

    def block(self,obj,name,kind='unknown'):
        obj.policy.classifications[(os.path.normcase(str(obj.source_root)),name,'BLOCKED_CURRENT')]={'kind':kind}

    def test_accepted_proof_is_exact_finite_structural_basis(self):
        cache,producer=legacy.proof(tool)
        self.assertEqual(producer['git_oid'],legacy.SOURCE_OID);self.assertEqual(producer['aliases'],legacy.ALIASES)
        self.assertEqual(producer['sha256'],legacy.SOURCE_SHA256)
        self.assertEqual(cache['legacy_structural_proof']['original_producer_custody'],'UNPROVED')
        self.assertEqual(cache['legacy_structural_proof']['original_optimization'],'UNPROVED')

    def test_entry_requires_exact_root_current_record_and_all_aliases(self):
        entry={'entry_id':'W045','kind':'generated_cache','path':legacy.CACHE_PATH,'sha256':legacy.CACHE_SHA256}
        record={'classification':'LEGACY_CACHE_GENERATOR_UNRESOLVED','kind':'working','path':legacy.CACHE_PATH,'whole_file_sha256':legacy.CACHE_SHA256,'bytes':10572}
        self.assertTrue(legacy.exact_entry(tool,entry,record,legacy.X,{legacy.SOURCE_OID:list(legacy.ALIASES)}))
        for key,value in [('entry_id','W044'),('kind','owned_test_literal'),('path',legacy.CACHE_PATH.upper()),('sha256','0'*64)]:
            altered=dict(entry);altered[key]=value
            self.assertFalse(legacy.exact_entry(tool,altered,record,legacy.X,{legacy.SOURCE_OID:list(legacy.ALIASES)}))
        self.assertFalse(legacy.exact_entry(tool,entry,record,self.area,{legacy.SOURCE_OID:list(legacy.ALIASES)}))
        self.assertFalse(legacy.exact_entry(tool,entry,dict(record,bytes=10571),legacy.X,{legacy.SOURCE_OID:list(legacy.ALIASES)}))
        self.assertFalse(legacy.exact_entry(tool,entry,record,legacy.X,{legacy.SOURCE_OID:legacy.ALIASES+['extra.py']}))

    def test_cache_changed_truncated_extended_wrong_magic_denied_before_child(self):
        with patch.object(legacy,'_exchange') as exchange:
            for data in (self.cache[:-1],self.cache+b'x',b'xxxx'+self.cache[4:],bytearray(self.cache)):
                self.assert_error('LEGACY_CACHE_IDENTITY',lambda:legacy.verify(tool,data,self.source,aliases=legacy.ALIASES,permitted=lambda:True))
            exchange.assert_not_called()

    def test_source_changed_truncated_extended_or_mutable_denied_before_child(self):
        with patch.object(legacy,'_exchange') as exchange:
            for data in (self.source[:-1],self.source+b'x',bytearray(self.source)):
                self.assert_error('LEGACY_SOURCE_IDENTITY',lambda:legacy.verify(tool,self.cache,data,aliases=legacy.ALIASES,permitted=lambda:True))
            exchange.assert_not_called()

    def test_aliases_are_exact_spelling_complete_and_typed(self):
        with patch.object(legacy,'_exchange') as exchange:
            for names in ([],['SCRIPTS/HOSTILE_AUDIT.PY'],legacy.ALIASES+['extra.py'],tuple(legacy.ALIASES)):
                self.assert_error('LEGACY_GENERATOR_ALIASES',lambda:self.verify(aliases=names))
            exchange.assert_not_called()

    def test_permission_requires_boolean_true_before_child(self):
        with patch.object(legacy,'_exchange') as exchange:
            for callback in (None,lambda:False,lambda:1):self.assert_error('LEGACY_CURRENT_DENIAL',lambda:self.verify(permitted=callback))
            exchange.assert_not_called()

    def test_permission_control_exception_propagates_before_child(self):
        error=KeyboardInterrupt('explicit test control')
        def stopped():raise error
        with patch.object(legacy,'_exchange') as exchange:
            with self.assertRaises(KeyboardInterrupt) as caught:self.verify(permitted=stopped)
            self.assertIs(caught.exception,error);exchange.assert_not_called()

    def test_native_exact_structural_match_has_empty_job_and_no_data_argv(self):
        with watch_native(self.id()) as launched:result=self.verify()
        self.assert_closed(launched)
        self.assertEqual(result['matching_compile_levels'],[0,1,2]);self.assertEqual(result['private_marker_constants_validated'],2)
        self.assertTrue(result['marshal_all_body_consumed']);self.assertFalse(result['source_or_cache_execution'])
        self.assertTrue(result['native']['observed_empty_job']);self.assertTrue(result['native']['pipe_threads_joined'])
        self.assertEqual(result['native']['image_sha256'],legacy.IMAGE_SHA256)

    def test_native_permission_revocation_after_child_refuses_return(self):
        calls=[]
        def current():calls.append(len(calls));return len(calls)==1
        with watch_native(self.id()) as launched:self.assert_error('LEGACY_CURRENT_DENIAL',lambda:self.verify(permitted=current))
        self.assertEqual(len(calls),2);self.assert_closed(launched)

    def test_native_concurrent_calls_have_distinct_lifetimes(self):
        barrier=threading.Barrier(2);results=[];errors=[]
        def run():
            try:barrier.wait(2);results.append(self.verify())
            except BaseException as error:errors.append(type(error).__name__)
        with watch_native(self.id()) as launched:
            threads=[threading.Thread(target=run) for _ in range(2)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(15)
            self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors,[]);self.assertEqual(len(results),2)
        self.assertEqual(len({(r['native']['pid'],r['native']['creation_time_100ns']) for r in results}),2)
        self.assert_closed(launched)

    def test_native_deadline_injection_closes_owned_job_and_recovers(self):
        port=legacy._port(tool);real_wait=port.wait;calls=[]
        def first_timeout(owned,seconds):
            calls.append(seconds)
            if len(calls)==1:return False  # injected scheduling observation, not measured OS timeout
            return real_wait(owned,seconds)
        with watch_native(self.id()) as launched:
            with patch.object(port,'wait',first_timeout):self.assert_error('LEGACY_WORKER_DEADLINE',self.verify)
            self.assertEqual(self.verify()['validation'],'EXACT_LEGACY_STRUCTURAL_EQUIVALENCE')
        self.assert_closed(launched);self.assertEqual(len(launched),2)

    def test_native_unresolved_wait_retains_owner_and_lease_for_recovery(self):
        port=legacy._port(tool)
        with watch_native(self.id()) as launched:
            with patch.object(port,'wait',return_value=False):error=self.assert_error('LEGACY_CUSTODY_UNRESOLVED',self.verify)
            self.assertIsNotNone(error.owned_process);self.assertIsNotNone(error.worker_lease)
            owned=error.owned_process
            self.assertTrue(owned.wait(5));self.assertEqual(owned.active_process_count(),0)
            for thread in error.threads:thread.join(5)
            self.assertFalse(any(thread.is_alive() for thread in error.threads))
            owned.close()
            for descriptor in error.pipe_descriptors:os.close(descriptor)
            error.worker_lease.__exit__(None,None,None)
        self.assert_closed(launched)

    def test_native_output_bound_refuses_and_recovers(self):
        with watch_native(self.id()) as launched:
            with patch.object(legacy,'MAX_RESPONSE',100):self.assert_error('LEGACY_OUTPUT_BOUND',self.verify)
            self.assertEqual(self.verify()['matching_compile_levels'],[0,1,2])
        self.assert_closed(launched);self.assertEqual(len(launched),2)

    def test_native_thread_start_failure_cleans_exact_descriptors_and_recovers(self):
        start=threading.Thread.start;calls=[]
        def second_start_failed(thread):
            calls.append(thread)
            if len(calls)==2:raise RuntimeError('explicit thread-start test control')
            return start(thread)
        with watch_native(self.id()) as launched:
            with patch.object(threading.Thread,'start',second_start_failed):self.assert_error('LEGACY_PIPE_THREAD_FAILED',self.verify)
            self.assertEqual(self.verify()['matching_compile_levels'],[0,1,2])
        self.assert_closed(launched)

    def test_native_primary_close_error_survives_successful_cleanup(self):
        port=legacy._port(tool);real_close=port.close;calls=[]
        with watch_native(self.id()) as launched:
            watched_close=port.close
            primary=OSError('explicit close test control')
            def first_close_failed(owned):
                calls.append(owned)
                if len(calls)==1:raise primary
                return watched_close(owned)
            with patch.object(port,'close',first_close_failed):error=self.assert_error('LEGACY_NATIVE_OPERATION_FAILED',self.verify)
            self.assertIs(error.primary_failure,primary)
        self.assert_closed(launched);self.assertEqual(len(calls),2)

    def test_native_cleanup_failure_retains_primary_owner_and_lease(self):
        port=legacy._port(tool);primary=OSError('explicit retained close control')
        with watch_native(self.id()) as launched:
            with patch.object(port,'close',side_effect=primary):error=self.assert_error('LEGACY_CLEANUP_UNRESOLVED',self.verify)
            self.assertIs(error.primary_failure,primary);self.assertIsNotNone(error.owned_process)
            self.assertTrue(error.owned_process.wait(5));self.assertEqual(error.owned_process.active_process_count(),0)
            for thread in error.threads:thread.join(5)
            error.owned_process.close()
            for descriptor in error.pipe_descriptors:os.close(descriptor)
            error.worker_lease.__exit__(None,None,None)
        self.assert_closed(launched)

    def test_native_pipe_close_failure_retains_exact_descriptor_and_recovers(self):
        real_close=os.close;failed={};primary=OSError('explicit receive descriptor-close control')
        def first_receive_close_failed(descriptor):
            if 'receive' in threading.current_thread().name and not failed:
                failed['descriptor']=descriptor;raise primary
            return real_close(descriptor)
        with watch_native(self.id()) as launched:
            with patch.object(os,'close',first_receive_close_failed):error=self.assert_error('LEGACY_PIPE_DESCRIPTOR_UNRESOLVED',self.verify)
            self.assertIs(error.primary_failure,primary);self.assertEqual(error.pipe_descriptors,(failed['descriptor'],))
            os.fstat(failed['descriptor'])  # actual retained descriptor is still open
            self.assertTrue(error.owned_process.wait(5));self.assertEqual(error.owned_process.active_process_count(),0)
            for thread in error.threads:thread.join(5)
            self.assertFalse(any(thread.is_alive() for thread in error.threads))
            real_close(failed['descriptor']);error.owned_process.close();error.worker_lease.__exit__(None,None,None)
            with self.assertRaises(OSError):os.fstat(failed['descriptor'])
            self.assertEqual(self.verify()['matching_compile_levels'],[0,1,2])
        self.assert_closed(launched);self.assertEqual(len(launched),2)

    def test_image_worker_and_native_port_pin_fail_closed_without_launch(self):
        port=legacy._port(tool)
        with patch.object(port,'launch') as launch:
            for name,code in [('IMAGE_SHA256','LEGACY_IMAGE_CHANGED'),('WORKER_SHA256','LEGACY_WORKER_CHANGED'),('NATIVE_PORT_SHA256','NATIVE_CUSTODY_PORT_CHANGED')]:
                with patch.object(legacy,name,'0'*64):self.assert_error(code,lambda:legacy._exchange(tool,b'{}'))
            launch.assert_not_called()

    def test_frozen_reader_and_review_hashes_are_required(self):
        for name in ('READER_SHA256','REVIEW_SHA256'):
            with patch.object(legacy,name,'0'*64):self.assert_error('LEGACY_PROOF_CHANGED',lambda:legacy.proof(tool))

    def test_native_post_child_proof_change_refuses_return(self):
        calls=[];original=legacy.READER_SHA256
        def current():
            calls.append(len(calls))
            if len(calls)==2:legacy.READER_SHA256='0'*64
            return True
        try:
            with watch_native(self.id()) as launched:self.assert_error('LEGACY_PROOF_CHANGED',lambda:self.verify(permitted=current))
        finally:legacy.READER_SHA256=original
        self.assert_closed(launched)

    def test_typed_protocol_boolean_levels_counts_and_extra_fields_are_refused(self):
        # Negative protocol unit controls start from an actual native response.
        # No substituted successful result is accepted as production evidence.
        request=json.dumps({'schema':legacy.SCHEMA,'cache_base64':__import__('base64').b64encode(self.cache).decode(),
                            'source_base64':__import__('base64').b64encode(self.source).decode()},separators=(',',':')).encode()
        with watch_native(self.id()) as launched:original,native=legacy._exchange(tool,request)
        self.assert_closed(launched)
        mutations=[('matching_compile_levels',[False,True,2]),('cache_bytes',True),('source_or_cache_execution',True),
                   ('marshal_all_body_consumed',1),('comparisons',[{'optimization':0,'code_pairs':True,'constant_pairs':119}]*3),
                   ('unexpected',True),('private_marker_constants_validated',True)]
        for key,value in mutations:
            response=copy.deepcopy(original);response[key]=value
            with patch.object(legacy,'_exchange',return_value=(response,native)):
                with self.assertRaises(legacy.LegacyValidationError):self.verify()

    def test_native_malformed_duplicate_and_extra_protocol_requests_are_safe(self):
        with watch_native(self.id()) as launched:
            for request in (b'{',b'{"schema":"a","schema":"b"}',b'{"schema":"ceta.w045.data-only.v1","extra":1}'):
                self.assert_error('LEGACY_DATA_REJECTED',lambda:legacy._exchange(tool,request))
        self.assert_closed(launched);self.assertEqual(len(launched),3)

    def test_request_bound_rejects_without_native_launch(self):
        port=legacy._port(tool)
        with patch.object(port,'launch') as launch:
            for request in (b'x'*65537,'{}',bytearray(b'{}')):self.assert_error('REQUEST_BOUND',lambda:legacy._exchange(tool,request))
            launch.assert_not_called()

    def test_worker_marker_only_context_rejects_extended_constant_and_protected_filename(self):
        marker=b'-----BEGIN PRIVATE KEY-----'
        positive=compile('x='+repr(marker.decode()),'<synthetic-only>','exec')
        self.assertEqual(worker.literal_context(positive),1)
        for code in (compile('x='+repr((marker+b' payload').decode()),'<synthetic-only>','exec'),
                     compile('x=1',marker.decode(),'exec'),compile('x=1','https://user:password@example.invalid/x','exec')):
            with self.assertRaises(worker.Rejected):worker.literal_context(code)

    def test_worker_structural_comparison_matches_fields_and_typed_nested_constants(self):
        first=compile('def f():\n return (True,1,"a")\n','a','exec')
        same=compile('def f():\n return (True,1,"a")\n','b','exec')
        changed=compile('def f():\n return (1,True,"a")\n','b','exec')
        self.assertTrue(worker.compare(first,same)[0]);self.assertFalse(worker.compare(first,changed)[0])
        self.assertFalse(worker.compare(first,compile('def f():\n return 4\n','a','exec'))[0])
        set_bool=compile('x=1','<synthetic-type-control>','exec').replace(co_consts=(frozenset({True}),None))
        set_int=set_bool.replace(co_consts=(frozenset({1}),None))
        self.assertFalse(worker.compare(set_bool,set_int)[0])
        self.assertTrue(worker.compare(set_bool,set_bool)[0])

    def test_worker_duplicate_json_fields_and_credential_filename_predicate(self):
        with self.assertRaises(worker.Rejected):worker.unique_pairs([('a',1),('a',2)])
        self.assertTrue(worker.credential_like(b'https://u:p@example.invalid/'))
        self.assertFalse(worker.credential_like(b'https://example.invalid/path@text'))

    def test_synthetic_policy_blocked_generator_prevents_provider_read(self):
        obj,entry=self.synthetic_provenance();self.block(obj,legacy.ALIASES[0].upper(),'private_key')
        with patch.object(legacy,'verify') as verify:
            provider=unittest.mock.Mock(return_value=self.source)
            with self.assertRaises(tool.PreservationError):obj.cache_constraints(entry,self.cache,provider)
            provider.assert_not_called();verify.assert_not_called()

    def test_synthetic_policy_missing_fresh_aliases_prevents_generator_read(self):
        obj,entry=self.synthetic_provenance()
        with patch.object(obj,'generator_bytes') as read,patch.object(legacy,'verify') as verify:
            with self.assertRaises(tool.PreservationError):obj.cache_constraints(entry,self.cache)
            read.assert_not_called();verify.assert_not_called()
        obj.observed_generator_aliases={legacy.SOURCE_OID:legacy.ALIASES+['extra.py']}
        with patch.object(obj,'generator_bytes') as read:
            with self.assertRaises(tool.PreservationError):obj.cache_constraints(entry,self.cache)
            read.assert_not_called()

    def test_synthetic_provider_new_subject_or_producer_denial_prevents_child(self):
        for name in [legacy.CACHE_PATH,legacy.ALIASES[0]]:
            obj,entry=self.synthetic_provenance()
            def provider(descriptor):self.block(obj,name.upper());return self.source
            with patch.object(legacy,'verify') as verify:
                with self.assertRaises(tool.PreservationError):obj.cache_constraints(entry,self.cache,provider)
                verify.assert_not_called()
            # Separate policy fixtures for the second kind; no source bytes are written.
            self.area=FIXTURES/('legacy-subcase-'+uuid.uuid4().hex[:8]);self.area.mkdir()

    def test_synthetic_constraint_calls_real_worker_and_post_callback_scope(self):
        obj,entry=self.synthetic_provenance()
        with watch_native(self.id()) as launched:obj.cache_constraints(entry,self.cache,lambda descriptor:self.source)
        self.assert_closed(launched)
        self.assertEqual(obj.policy.paths['capture_targets'],[]);self.assertEqual(obj.policy.paths['restore_targets'],[])
        self.assertEqual(obj.entries,{})  # no policy receipt or admission was created

    def test_synthetic_subject_denial_after_native_verifier_refuses_constraint_return(self):
        obj,entry=self.synthetic_provenance();real=legacy.verify
        def verified_then_blocked(*args,**kwargs):
            result=real(*args,**kwargs);self.block(obj,legacy.CACHE_PATH.upper(),'live_profile');return result
        with watch_native(self.id()) as launched,patch.object(legacy,'verify',side_effect=verified_then_blocked):
            with self.assertRaises(tool.PreservationError):obj.cache_constraints(entry,self.cache,lambda descriptor:self.source)
        self.assert_closed(launched)

    def test_synthetic_worker_lease_close_failure_is_retained_and_recoverable(self):
        obj,entry=self.synthetic_provenance();real_open=tool.open_source;leases=[]
        class ControlledLease:
            def __init__(lease,context):lease.context=context;lease.failed=False
            def __enter__(lease):return lease.context.__enter__()
            def __exit__(lease,*args):
                if not lease.failed:lease.failed=True;raise OSError('explicit retained file-lease control')
                return lease.context.__exit__(*args)
        def controlled_open(path,*args,**kwargs):
            context=real_open(path,*args,**kwargs)
            if path==legacy.WORKER:
                lease=ControlledLease(context);leases.append(lease);return lease
            return context
        with watch_native(self.id()) as launched,patch.object(tool,'open_source',side_effect=controlled_open):
            error=self.assert_error('LEGACY_CLEANUP_UNRESOLVED',lambda:obj.cache_constraints(entry,self.cache,lambda descriptor:self.source))
            self.assertIs(error.worker_lease,leases[0]);self.assertIsNone(error.owned_process)
            error.worker_lease.__exit__(None,None,None)
        self.assert_closed(launched)

    def test_synthetic_native_unresolved_error_is_not_swallowed_as_none(self):
        obj,entry=self.synthetic_provenance();port=legacy._port(tool)
        with watch_native(self.id()) as launched:
            with patch.object(port,'wait',return_value=False):
                error=self.assert_error('LEGACY_CUSTODY_UNRESOLVED',lambda:obj.cache_constraints(entry,self.cache,lambda descriptor:self.source))
            self.assertTrue(error.owned_process.wait(5));self.assertEqual(error.owned_process.active_process_count(),0)
            for thread in error.threads:thread.join(5)
            error.owned_process.close()
            for descriptor in error.pipe_descriptors:os.close(descriptor)
            error.worker_lease.__exit__(None,None,None)
        self.assert_closed(launched)

    def test_legacy_receipt_keeps_proof_and_unproved_custody_explicit(self):
        obj,entry=self.synthetic_provenance();obj.records={'W045':{'source_positions':tool.protected_positions(self.cache)}}
        # Shape-only receipt method on a synthetic object; never validate/admit real X.
        receipt=obj.receipt(entry)
        basis=receipt['legacy_validation_basis']
        self.assertEqual(basis['review_sha256'],legacy.REVIEW_SHA256);self.assertEqual(basis['worker_sha256'],legacy.WORKER_SHA256)
        self.assertEqual(basis['original_producer_custody'],'UNPROVED');self.assertEqual(basis['original_optimization'],'UNPROVED')

if __name__=='__main__':unittest.main(verbosity=2)
