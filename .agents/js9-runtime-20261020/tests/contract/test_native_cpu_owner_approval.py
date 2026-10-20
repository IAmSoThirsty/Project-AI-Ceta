"""Actual native effect-approval currentness; every genuine auth gate is refused.

An enrollment request and disabled-policy restoration variant below are DATA_ONLY
engineering inputs. No test creates a verified witness, genuine approval/grant,
isolated worker profile or CPU policy Set. Actual SQLite and native custody are
used for denials and pre-gate qualification only.
"""
from contextlib import contextmanager
from dataclasses import replace
import os,threading,time,unittest
from unittest.mock import patch

from ceta.contracts.real_effect import RESTORE_OPERATION
from ceta.contracts.wire import ContractError,canonical_bytes
from ceta.effects.native_cpu_binding import NativeCpuBinding
from ceta.identity import native_approval
from ceta.identity import owner_session as module
from ceta.kernel.transactions import KernelTransactions
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
import test_native_owner_session as base
import test_owner_authority_transactions as data

NATIVE_RECEIPTS=[]


class GateRefused(KeyboardInterrupt):pass


class NativeCpuOwnerApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):base.NativeOwnerSessionTests.setUpClass()

    def setUp(self):
        self.f=base.NativeOwnerSessionTests('test_original_native_peer_designates_frozen_body_and_releases_dispatch')
        self.f.id=self.id
        self.target=self.binding=None;self.gates=[];self.addCleanup(self.retire)
        self.f.setUp();self.f.owner.close()
        self.f.owner=module.NativeCpuOwnerSession(self.f.view,self.f.clock,self.f.code,
            installation_id=base.INSTALLATION,scope_id=base.PROJECT,policy_commitment=base.POLICY,
            helper_name='native/owner_approval.exe',helper_source_name='native/owner_approval.cpp',
            worker_name='native/isolated_worker.exe',temporary_root=self.f.directory)
        self.f.kernel=KernelTransactions(self.f.store,self.f.fixture.codec,base.INSTALLATION,self.f.owner)
        self.target=WindowsOwnedProcess.launch(str(base.WORKER),('hold','30000'),cwd=str(self.f.directory),
            environment={'SystemRoot':os.environ['SystemRoot'],'TEMP':str(self.f.directory),'TMP':str(self.f.directory)},
            expected_image_sha256=base.WORKER_SHA)
        self.binding=NativeCpuBinding(self.target,self.f.clock,maximum_capture_ns=500_000_000)

    def retire(self):
        failures=[]
        if self.binding is not None:self.binding.close()
        if self.target is not None:
            try:
                if self.target.poll() is None:self.target.terminate(126)
                self.assertTrue(self.target.wait(5))
                end=time.perf_counter()+5
                while self.target.active_process_count() and time.perf_counter()<end:time.sleep(.001)
                self.target.close()
            except BaseException as error:failures.append(error)
        try:self.f.retire()
        except BaseException as error:failures.append(error)
        NATIVE_RECEIPTS.append(dict(test_id=self.id(),target=None if self.target is None else
            dict(pid=self.target.pid,creation_time=self.target.creation_time,closed=self.target.lifetime_closed,
                process_closed=self.target._process is None,job_closed=self.target._job is None,thread_closed=self.target._thread is None),
            genuine_gate_attempts=len(self.gates),genuine_gate_forwards=0,cleanup_errors=[repr(e) for e in failures],
            fixture='Actual medium owned hold worker; no CPU Set or genuine ceremony; request/enrollment/restore inputs are DATA_ONLY.'))
        if failures:raise failures[0]

    def prepared(self, context, *, restore=False):
        session,enrollment=self.f.prepare(context)
        # DATA_ONLY fixture reserves 8 KiB read/write for each separate action.
        # The generic enrollment fixture reserves all read bytes for recovery;
        # this bounded split leaves the cap's unchanged 8 KiB request covered.
        enrollment=replace(enrollment,recovery_budget=data.budget(1,wall_time_ms=5000,
            max_bytes_read=8192,max_bytes_written=8192))
        self.f.owner.designate_enrollment(enrollment,session,context)
        session.cancel();self.assertTrue(session.process.wait(5))
        end=time.perf_counter()+5
        while session.process.active_process_count() and time.perf_counter()<end:time.sleep(.001)
        session.close()
        capture=self.binding.capture()
        values=dict(process_identity=self.target.resource_identity,job_digest=capture.observation.job_digest,
            expected_limit=capture.observation,original_limit=capture.observation.limit,
            policy_commitment=enrollment.policy_commitment,adapter_commitment=enrollment.adapter_commitment,
            source_commitment=enrollment.source_commitment,environment_commitment=enrollment.environment_commitment)
        original=data.effect_request(enrollment,**values)
        request=data.effect_request(enrollment,restore=original,**values) if restore else original
        return enrollment,capture,request

    def designate(self, context, *, restore=False):
        enrollment,capture,request=self.prepared(context,restore=restore)
        frozen=self.f.owner.designate_effect(request,self.binding,capture,context)
        return enrollment,capture,request,frozen

    @contextmanager
    def intercepted_gate(self, callback=None):
        original=native_approval._NativeApi.__init__;owner=self.f.owner;primary=GateRefused('OS2_GENUINE_GATE_REFUSED')
        def initialize(api,*args,**kwargs):
            original(api,*args,**kwargs);setter=api.SetEvent
            def guarded(handle):
                session=owner.approval_owner._active
                if session is not None and session.mode=='interactive' and handle==session._handles.get('gate'):
                    self.gates.append(handle)
                    if callback is not None:callback(session)
                    raise primary
                return setter(handle)
            api.SetEvent=guarded
        with patch.object(native_approval._NativeApi,'__init__',initialize):yield primary

    def test_selected_owner_captures_real_bound_approval_port_without_opening_admission(self):
        self.assertEqual(self.f.owner.approval_owner._retain,self.f.owner.retain_native_approval)
        for method,args in ((self.f.owner.require_prepared_basis,(None,None,None)),
                (self.f.owner.require_admission,(None,None,None)),(self.f.owner.require_revocation,(None,None,None))):
            with self.subTest(method=method.__name__),self.assertRaises(ContractError):method(*args)
        with self.assertRaisesRegex(ContractError,'RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE'):self.f.kernel.require_runtime_admission()

    def test_actual_designation_detaches_public_request_and_borrows_same_target(self):
        def body(context):
            _,capture,request,frozen=self.designate(context)
            self.assertIsNot(frozen,request);wire=self.f.owner._effect.wire
            object.__setattr__(request,'request_id','request:changed-public-copy')
            self.assertEqual(self.f.owner._effect.wire,wire)
            self.assertIs(self.f.owner._effect.capture,capture)
            self.assertIs(self.f.owner._effect.target,self.target)
        self.f.call(body)
        self.assertIsNone(self.f.owner._effect);self.assertIsNone(self.f.owner._effect_proof)

    def test_equal_capture_copy_is_not_native_custody(self):
        def body(context):
            _,capture,request=self.prepared(context)
            with self.assertRaisesRegex(ContractError,'OWNER_EFFECT_NATIVE_TARGET_CHANGED'):
                self.f.owner.designate_effect(request,self.binding,replace(capture),context)
            self.assertIsNone(self.f.owner._effect)
        self.f.call(body)

    def test_arbitrary_clock_binding_or_request_ports_are_denied(self):
        def body(context):
            _,capture,request=self.prepared(context)
            for req,binding in ((request,object()),(object(),self.binding)):
                with self.subTest(kind=type(binding).__name__),self.assertRaisesRegex(ContractError,'DESIGNATION_DENIED'):
                    self.f.owner.designate_effect(req,binding,capture,context)
        self.f.call(body)

    def test_source_environment_scope_or_target_substitution_is_denied(self):
        def body(context):
            _,capture,request=self.prepared(context)
            for changes in ({'source_commitment':'sha256:'+'f'*64},{'environment_commitment':'sha256:'+'f'*64},
                {'scope_id':'scope:foreign'},{'job_digest':'sha256:'+'f'*64,'expected_limit':replace(request.expected_limit,job_digest='sha256:'+'f'*64)}):
                with self.subTest(fields=tuple(changes)),self.assertRaises(ContractError):
                    self.f.owner.designate_effect(replace(request,**changes),self.binding,capture,context)
                self.assertIsNone(self.f.owner._effect)
        self.f.call(body)

    def test_duplicate_designation_cannot_replace_pending_capture(self):
        def body(context):
            _,capture,request,_=self.designate(context);first=self.f.owner._effect
            with self.assertRaisesRegex(ContractError,'DESIGNATION_DENIED'):
                self.f.owner.designate_effect(request,self.binding,capture,context)
            self.assertIs(first,self.f.owner._effect)
        self.f.call(body)

    def test_actual_cap_lease_is_current_then_intercepted_before_native_authentication(self):
        def body(context):
            _,_,request,_=self.designate(context)
            def check(session):
                lease=session._lease
                self.assertIs(lease,self.f.owner._effect_lease)
                self.assertIsNone(lease.require_current(request.canonical_wire,session.challenge_id,
                    session.ceremony_nonce,session.helper_evidence,context))
                self.assertIs(lease.helper,session.helper_evidence)
            with self.intercepted_gate(check) as primary:
                with self.assertRaises(GateRefused) as caught:self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertIs(caught.exception,primary);self.assertEqual(len(self.gates),1)
            self.assertTrue(primary.owned_session._closed);self.assertIsNone(self.f.owner._effect_lease)
            self.assertIsNone(self.f.owner._effect_proof)
        self.f.call(body)

    def test_restore_variant_uses_its_distinct_body_and_no_cpu_effect(self):
        def body(context):
            _,_,request,_=self.designate(context,restore=True);self.assertEqual(request.operation,RESTORE_OPERATION)
            def check(session):self.assertEqual(session._lease.designation.wire,request.canonical_wire)
            with self.intercepted_gate(check):
                with self.assertRaises(GateRefused):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.target._cpu_version,0)
        self.f.call(body)

    def test_wrong_nonce_helper_and_context_fail_inside_actual_retained_lease(self):
        def body(context):
            _,_,request,_=self.designate(context)
            def check(session):
                lease=session._lease
                for wire,challenge,nonce,helper,ctx in ((request.canonical_wire,session.challenge_id,'f'*32,session.helper_evidence,context),
                    (request.canonical_wire,session.challenge_id,session.ceremony_nonce,replace(session.helper_evidence),context),
                    (request.canonical_wire,session.challenge_id,session.ceremony_nonce,session.helper_evidence,object())):
                    with self.subTest(nonce=nonce),self.assertRaises(ContractError):lease.require_current(wire,challenge,nonce,helper,ctx)
            with self.intercepted_gate(check):
                with self.assertRaises(GateRefused):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
        self.f.call(body)

    def test_foreign_thread_cannot_use_actual_native_lease(self):
        def body(context):
            _,_,request,_=self.designate(context)
            def check(session):
                errors=[]
                def foreign():
                    try:session._lease.require_current(request.canonical_wire,session.challenge_id,session.ceremony_nonce,session.helper_evidence,context)
                    except ContractError as error:errors.append(error.code)
                thread=threading.Thread(target=foreign);thread.start();thread.join(3)
                self.assertFalse(thread.is_alive());self.assertEqual(errors,['OWNER_SESSION_ORIGINAL_DISPATCH_REQUIRED'])
            with self.intercepted_gate(check):
                with self.assertRaises(GateRefused):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
        self.f.call(body)

    def test_stop_during_final_native_effect_check_wins_before_gate(self):
        def body(context):
            _,_,request,_=self.designate(context);original=self.f.owner._require_native
            def stopped(*args,**kwargs):
                observed=original(*args,**kwargs);self.f.owner.request_stop();return observed
            with self.intercepted_gate(),patch.object(self.f.owner,'_require_native',stopped):
                with self.assertRaises(ContractError):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.gates,[]);self.assertIsNone(self.f.owner._effect_proof)
        self.f.call(body)

    def test_stop_before_designation_publishes_no_effect_state(self):
        def body(context):
            _,capture,request=self.prepared(context);self.f.owner.request_stop()
            with self.assertRaises(ContractError):self.f.owner.designate_effect(request,self.binding,capture,context)
            self.assertIsNone(self.f.owner._effect)
        self.f.call(body)

    def test_actual_exited_target_cannot_start_approval(self):
        def body(context):
            _,_,request,_=self.designate(context);self.target.terminate(125);self.assertTrue(self.target.wait(5))
            with self.intercepted_gate(),self.assertRaises(ContractError):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.gates,[])
        self.f.call(body)

    def test_controlled_policy_version_change_denies_without_a_native_set(self):
        def body(context):
            _,_,request,_=self.designate(context);self.target._cpu_version+=1  # Controlled cached-version invalidation only.
            with self.intercepted_gate(),self.assertRaises(ContractError):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.gates,[])
        self.f.call(body)

    def test_controlled_resume_notification_invalidates_pending_approval(self):
        def body(context):
            _,_,request,_=self.designate(context);self.f.clock._on_power(None,18,None)  # Controlled callback, no host suspend.
            with self.intercepted_gate(),self.assertRaises(ContractError):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.gates,[])
        self.f.call(body)

    def test_cancelled_binding_cannot_start_approval(self):
        def body(context):
            _,_,request,_=self.designate(context);self.binding.cancel()
            with self.intercepted_gate(),self.assertRaises(ContractError):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.gates,[])
        self.f.call(body)

    def test_reentrant_native_query_cannot_replace_or_release_outer_currentness(self):
        def body(context):
            _,capture,request,_=self.designate(context);original=self.target._api.QueryInformationJobObject;seen=[]
            def query(*args):
                if args[1]==15:
                    with self.assertRaisesRegex(ContractError,'REENTRANT'):self.f.owner.designate_effect(request,self.binding,capture,context)
                    seen.append(self.f.owner._effect_busy)
                return original(*args)
            with self.intercepted_gate(),patch.object(self.target._api,'QueryInformationJobObject',query):
                with self.assertRaises(GateRefused):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertTrue(seen and all(seen));self.assertFalse(self.f.owner._effect_busy)
        self.f.call(body)

    def test_controlled_transcript_and_boolean_create_no_witness_or_sql_approval(self):
        def body(context):
            enrollment,_,request,_=self.designate(context);before=self.f.store.store_position()
            for phase in ('APPROVE_CAP','APPROVE_RESTORE'):
                for proof in (True,False,object(),{'approved':True}):
                    with self.subTest(phase=phase),self.assertRaisesRegex(ContractError,'NATIVE_WITNESS_REQUIRED'):
                        self.f.owner.require_owner_authority_current(phase,enrollment,request,None,proof,
                            self.f.owner.authenticate(context),context)
            self.assertEqual(before,self.f.store.store_position());self.assertIsNone(self.f.owner._effect_proof)
        self.f.call(body)

    def test_inspect_only_actual_helper_cannot_create_verified_effect_witness(self):
        def body(context):
            _,_,request,_=self.designate(context)
            session=self.f.owner.approval_owner.inspect_request(request,timeout_ms=5000)
            self.f.sessions.append(session);result=session.wait(10)
            self.assertFalse(result.reported_verified or result.authentication_invoked)
            with self.assertRaisesRegex(ContractError,'GENUINE_CEREMONY_REQUIRED'):self.f.owner.retain_verified_effect(session,context)
            self.assertIsNone(self.f.owner._effect_proof)
        self.f.call(body)

    def test_actual_canonical_challenge_still_writes_no_grant(self):
        def body(context):
            session,enrollment=self.f.prepare(context);self.f.owner.designate_enrollment(enrollment,session,context)
            result=self.f.kernel.begin_owner_enrollment(enrollment.canonical_wire,context)
            self.assertEqual(self.f.fixture.codec.decode(result.record_wire).as_dict()['outcome'],'SEEK_AUTHORITY')
            for method,args in ((self.f.owner.require_prepared_basis,(None,None,None)),(self.f.owner.require_admission,(None,None,None))):
                with self.assertRaises(ContractError):method(*args)
            self.assertIsNone(self.f.owner._effect_proof)
        self.f.call(body)

    def test_owner_close_keeps_borrowed_worker_clock_code_and_store_open(self):
        self.f.owner.close();self.assertTrue(self.f.owner.closed)
        self.assertIsNone(self.target.poll());self.assertEqual(self.f.clock.status().state,'ACTIVE')
        self.assertFalse(self.f.code.closed or self.f.binding.closed or self.f.store._closed)

    def test_original_context_expiry_rejects_reentry_and_retained_designation(self):
        held=[]
        def body(context):held.append(context);self.designate(context)
        self.f.call(body)
        self.assertIsNone(self.f.owner._effect)
        with self.assertRaises(ContractError):
            with self.f.owner.retain_native_approval(b'{}',held[0]):self.fail('expired context retained')

    def test_initial_retention_precedes_actual_helper_process_allocation(self):
        def body(context):
            _,_,request,_=self.designate(context);retain=self.f.owner.approval_owner._retain;seen=[]
            @contextmanager
            def observed(wire,ctx):
                session=self.f.owner.approval_owner._active
                self.assertIsNone(session.process);self.assertIsNone(session.helper_evidence)
                with retain(wire,ctx) as lease:
                    seen.append(lease);yield lease
            with self.intercepted_gate(),patch.object(self.f.owner.approval_owner,'_retain',observed):
                with self.assertRaises(GateRefused):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(len(seen),1);self.assertFalse(seen[0].active)
        self.f.call(body)

    def test_same_native_helper_currentness_can_repeat_without_new_authority(self):
        def body(context):
            _,_,request,_=self.designate(context);before=self.f.store.store_position()
            def check(session):
                lease=session._lease
                for _ in range(3):
                    self.assertIsNone(lease.require_current(request.canonical_wire,session.challenge_id,
                        session.ceremony_nonce,session.helper_evidence,context))
                self.assertEqual(lease.helper_wire,canonical_bytes(session.helper_evidence.as_dict()))
                self.assertEqual(before,self.f.store.store_position())
            with self.intercepted_gate(check):
                with self.assertRaises(GateRefused):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
        self.f.call(body)

    def test_stop_after_cp_binding_return_denies_final_owner_publication(self):
        def body(context):
            _,_,request,_=self.designate(context);original=self.binding.require_current
            def stopped(*args):
                result=original(*args);self.f.owner.request_stop();return result
            with self.intercepted_gate(),patch.object(self.binding,'require_current',stopped):
                with self.assertRaises(ContractError):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.gates,[])
        self.f.call(body)

    def test_stop_after_native_helper_principal_check_denies_gate(self):
        def body(context):
            _,_,request,_=self.designate(context);original=module._require_principal
            def stopped(*args):
                result=original(*args);self.f.owner.request_stop();return result
            with self.intercepted_gate(),patch.object(module,'_require_principal',stopped):
                with self.assertRaises(ContractError):self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
            self.assertEqual(self.gates,[])
        self.f.call(body)

    def test_abandoned_context_preserves_control_exception_and_failed_close_owner(self):
        class Primary(KeyboardInterrupt):
            def __setattr__(self,name,value):
                # contextlib/unittest must retain Python's exception chain.
                if name in ('__traceback__','__cause__','__context__','__suppress_context__'):
                    return BaseException.__setattr__(self,name,value)
                raise RuntimeError('diagnostic setter refused')
            @property
            def add_note(self):raise RuntimeError('diagnostic lookup refused')
        primary=Primary('original abandoned context');cleanup=OSError('controlled session close interruption')
        patches=[];sessions=[]
        def body(context):
            _,_,request,_=self.designate(context)
            session=self.f.owner.approval_owner.inspect_request(request,timeout_ms=5000)
            self.f.sessions.append(session);sessions.append(session)
            self.assertFalse(session.wait(10).authentication_invoked)
            patcher=patch.object(session,'close',side_effect=cleanup);patches.append(patcher);patcher.start()
            raise primary
        try:
            with self.assertRaises(Primary) as caught:self.f.call(body)
        finally:
            for patcher in patches:patcher.stop()
        self.assertIs(caught.exception,primary)
        stored=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(stored['native_owner_session'],self.f.owner)
        self.assertIs(self.f.owner.approval_owner._active,sessions[0])
        self.assertIsNone(self.f.owner._effect);self.assertIsNone(self.f.owner._effect_proof)
        stored['close_cleanup']()
        self.assertTrue(sessions[0]._closed and self.f.owner.closed)


    def test_final_native_session_fence_rejects_body_lease_or_helper_substitution(self):
        def body(context):
            _,_,request,_=self.designate(context)
            def check(session):
                lease=session._lease
                changes=((session,'_bound_request_wire',b'{}'),(session,'_bound_context',object()),
                    (session,'mode','inspect'),(session,'_enrollment',True),(session,'_lease',object()),
                    (lease,'active',False),(lease,'helper',replace(session.helper_evidence)),
                    (lease,'designation',object()),(lease,'context',object()))
                for target,field,value in changes:
                    previous=getattr(target,field)
                    with self.subTest(field=field):
                        try:
                            setattr(target,field,value)
                            with self.assertRaisesRegex(ContractError,'SESSION_CHANGED'):
                                self.f.owner._effect_fence(self.f.owner._effect,session)
                        finally:setattr(target,field,previous)
                self.f.owner._effect_fence(self.f.owner._effect,session)
            with self.intercepted_gate(check):
                with self.assertRaises(GateRefused):
                    self.f.owner.approval_owner.begin_interactive(request,original_context=context,timeout_ms=5000)
        self.f.call(body)


class ControlledCpuOwnerGuardTests(unittest.TestCase):
    """DATA_ONLY pure denial oracles; no native witness, registry or authority."""
    def fixture(self):
        from types import SimpleNamespace
        from test_native_cpu_binding import ControlledHost,request
        host=ControlledHost();binding=host.binding();self.addCleanup(binding.close)
        capture=binding.capture();item=request(capture);context=object()
        owner=object.__new__(module.NativeCpuOwnerSession)
        owner._closed=False;owner._stopped=threading.Event();owner._effect_serial=1
        owner._effect_busy=owner._effect_retaining=False;owner._effect_lease=owner._effect_proof=None
        owner._native_clock=host.clock;owner._view=SimpleNamespace(_store=SimpleNamespace(closed=False))
        owner._dispatch=(context,threading.get_ident(),SimpleNamespace(require_current=lambda:None))
        designation=module._EffectDesignation(item.canonical_wire,binding,capture,context,1)
        owner._effect=designation
        return owner,designation,host,binding,context

    def test_controlled_pure_fence_denies_every_known_lifetime_loss(self):
        for field,value in (('_closed',True),('_termination_requested',True),('_exit_code',7),
                ('_cpu_lifetime_unavailable',True),('_process',None),('_job',None),('_cpu_version',1)):
            with self.subTest(field=field):
                owner,item,host,_,_=self.fixture();setattr(host.target,field,value)
                with self.assertRaisesRegex(ContractError,'NATIVE_TARGET_CHANGED'):owner._effect_fence(item)

    def test_controlled_fence_denies_clock_epoch_resume_and_registration_loss(self):
        for field,value in (('_state','CLOSED'),('_reason','CONTROLLED_LOSS'),('_registration',None),
                ('_epoch',2),('_resume',1),('_session','2'*32)):
            with self.subTest(field=field):
                owner,item,host,_,_=self.fixture();setattr(host.clock,field,value)
                with self.assertRaisesRegex(ContractError,'CLOCK_CHANGED'):owner._effect_fence(item)

    def test_controlled_fence_denies_binding_stop_and_replaced_capture(self):
        for changed in ('cancel','close','capture'):
            with self.subTest(changed=changed):
                owner,item,host,binding,_=self.fixture()
                if changed=='cancel':binding.cancel()
                elif changed=='close':binding.close()
                else:binding.capture()
                with self.assertRaisesRegex(ContractError,'NATIVE_TARGET_CHANGED'):owner._effect_fence(item)

    def test_controlled_stop_after_last_code_fence_is_observed(self):
        owner,item,_,_,_=self.fixture()
        owner._dispatch[2].require_current=owner._stopped.set
        with self.assertRaisesRegex(ContractError,'STOPPED_OR_CHANGED'):owner._effect_fence(item)

    def test_controlled_store_closure_is_observed_before_publication(self):
        owner,item,_,_,_=self.fixture();owner._view._store.closed=True
        with self.assertRaisesRegex(ContractError,'STORE_CLOSED'):owner._effect_fence(item)

    def test_controlled_designation_context_serial_active_and_thread_changes_deny(self):
        for field,value in (('context',object()),('serial',2),('active',False),('thread',-1)):
            with self.subTest(field=field):
                owner,item,_,_,_=self.fixture();setattr(item,field,value)
                with self.assertRaisesRegex(ContractError,'STOPPED_OR_CHANGED'):owner._effect_fence(item)

    def test_controlled_invalidation_removes_no_cleanup_owner(self):
        from types import SimpleNamespace
        owner,item,_,_,_=self.fixture();session=object()
        owner._approval=SimpleNamespace(_active=session)
        owner._effect_lease=SimpleNamespace(active=True);owner._effect_proof=SimpleNamespace(active=True)
        owner._invalidate_effect()
        self.assertFalse(item.active or owner._effect_lease.active or owner._effect_proof.active)
        self.assertIs(owner._approval._active,session)

    def lease_fixture(self):
        from types import SimpleNamespace
        owner,item,_,_,context=self.fixture()
        # Explicit controlled dispatch port, not WindowsPeerRegistry evidence.
        owner._require_dispatch=lambda ctx:None
        session=object.__new__(native_approval.NativeApprovalSession)
        session._closed=session._enrollment=False;session.mode='interactive';session._stop=threading.Event()
        session._bound_request_wire=item.wire;session._bound_context=context
        session.challenge_id='controlled:challenge';session.ceremony_nonce='3'*64
        session.helper_evidence=None
        owner._approval=SimpleNamespace(_active=session);session._owner=owner._approval
        lease=module._NativeEffectApprovalLease(owner,item,session,context)
        session._lease=lease;owner._effect_lease=lease
        def must_not_reach(*args):raise AssertionError('No controlled case may qualify native currentness')
        owner._require_effect=must_not_reach
        return owner,item,session,lease,context

    def test_controlled_lease_wrong_wire_challenge_nonce_and_context_deny(self):
        for changed in ('wire','challenge','nonce','context'):
            with self.subTest(changed=changed):
                _,item,session,lease,context=self.lease_fixture()
                args=[item.wire,session.challenge_id,session.ceremony_nonce,None,context]
                args[{'wire':0,'challenge':1,'nonce':2,'context':4}[changed]]=b'{}' if changed=='wire' else object()
                with self.assertRaises(ContractError):lease.require_current(*args)

    def test_controlled_lease_rejects_untyped_nonce_before_equality_callbacks(self):
        class Untyped:
            def __eq__(self,other):raise AssertionError('untyped equality callback executed')
        for changed in ('challenge','nonce'):
            with self.subTest(changed=changed):
                _,item,session,lease,context=self.lease_fixture()
                args=[item.wire,session.challenge_id,session.ceremony_nonce,None,context]
                args[1 if changed=='challenge' else 2]=Untyped()
                with self.assertRaisesRegex(ContractError,'BODY_CHANGED'):lease.require_current(*args)

    def test_controlled_lease_inactive_closed_cancelled_and_inspect_sessions_deny(self):
        for changed in ('lease','closed','cancelled','inspect','enrollment'):
            with self.subTest(changed=changed):
                _,item,session,lease,context=self.lease_fixture()
                if changed=='lease':lease.active=False
                elif changed=='closed':session._closed=True
                elif changed=='cancelled':session._stop.set()
                elif changed=='inspect':session.mode='inspect'
                else:session._enrollment=True
                with self.assertRaisesRegex(ContractError,'LEASE_INVALID'):
                    lease.require_current(item.wire,session.challenge_id,session.ceremony_nonce,None,context)

    def test_controlled_non_native_helper_is_rejected_before_currentness(self):
        _,item,session,lease,context=self.lease_fixture()
        with self.assertRaisesRegex(ContractError,'HELPER_CHANGED'):
            lease.require_current(item.wire,session.challenge_id,session.ceremony_nonce,object(),context)

    def test_controlled_reentry_does_not_release_outer_busy_flag(self):
        owner,_,_,_,context=self.fixture();owner._require_dispatch=lambda ctx:None
        with owner._effect_operation(context):
            with self.assertRaisesRegex(ContractError,'REENTRANT'):
                with owner._effect_operation(context):self.fail('nested entry')
            self.assertTrue(owner._effect_busy)
        self.assertFalse(owner._effect_busy)

    def test_controlled_witness_retention_reentry_is_closed_before_any_transcript(self):
        owner,_,_,_,context=self.fixture();owner._require_dispatch=lambda ctx:None
        owner._effect_retaining=True
        with self.assertRaisesRegex(ContractError,'REENTRANT'):owner.retain_verified_effect(None,context)
        with self.assertRaisesRegex(ContractError,'REENTRANT'):
            with owner._effect_operation(context):self.fail('concurrent designation during transcript')
        self.assertTrue(owner._effect_retaining);self.assertFalse(owner._effect_busy)

    def test_selected_constructor_rejects_untyped_native_owners(self):
        with self.assertRaisesRegex(ContractError,'NATIVE_OWNERS_REQUIRED'):
            module.NativeCpuOwnerSession(object(),object(),object(),installation_id='installation:test',
                scope_id='scope:test',policy_commitment='sha256:'+'a'*64,helper_name='helper',
                helper_source_name='source',worker_name='worker',temporary_root='controlled')


if __name__=='__main__':unittest.main()
