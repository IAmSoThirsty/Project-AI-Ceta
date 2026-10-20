"""Actual canonical SQLite and bounded threads; controlled authority, no Set.

The first regression method is byte-for-byte source reuse from the independent
KA2 entry probe. All native/provider bindings in these domain tests are
controlled. No native process is allocated or dispatched by this module.
"""
import threading
import time
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError
from ceta.kernel.transactions import KernelTransactions
import ceta.kernel.cpu_execution as execution
import test_cpu_execution_admission as parent
import test_owner_authority_transactions as authority

entry_facts = []
REGISTRATION_OBSERVATIONS = []


class CrossKernelAdmissionTests(unittest.TestCase):
    fixture = parent.CpuExecutionAdmissionTests.fixture
    lease = parent.CpuExecutionAdmissionTests.lease
    status = parent.CpuExecutionAdmissionTests.status
    arm_domain_fence = parent.CpuExecutionAdmissionTests.arm_domain_fence

    @classmethod
    def setUpClass(cls):
        parent.CpuExecutionAdmissionTests.setUpClass.__func__(cls)

    def second_kernel(self, fixture, *, store=None, owners=None):
        return KernelTransactions(fixture.store if store is None else store,
            fixture.codec, authority.INSTALLATION, fixture.owners if owners is None else owners)

    def occupancy(self, coordinator):
        with execution._LIVENESS_LOCK:
            return dict(owner_count=execution._MUTATING_OWNERS.get(id(coordinator.owners),(None,0))[1],
                store_count=execution._MUTATING_STORES.get(id(coordinator.store),(None,0))[1],
                local_count=coordinator.mutating, active=coordinator.active,
                owner_active=execution._ACTIVE_OWNERS.get(id(coordinator.owners)),
                store_active=execution._ACTIVE_STORES.get(id(coordinator.store)), allowed=coordinator.allowed)

    def assert_idle(self, coordinator):
        row = self.occupancy(coordinator)
        self.assertEqual((row['owner_count'],row['store_count'],row['local_count']),(0,0,0))
        self.assertIsNone(row['active']); self.assertIsNone(row['owner_active'])
        self.assertIsNone(row['store_active']); self.assertIsNone(row['allowed'])

    def paused_revoke(self, fixture, kernel=None):
        kernel = fixture.kernel if kernel is None else kernel
        entered, release = threading.Event(), threading.Event()
        ids, errors, results, once = [], [], [], []
        original = kernel._peer
        grant = fixture.cell(authority.grant_key_for(fixture.request)).value_wire
        def peer(context):
            if threading.get_ident() == ids[0] and not once:
                once.append(True); entered.set()
                if not release.wait(5): raise AssertionError('owned mutation thread not released')
            return original(context)
        def invoke():
            ids.append(threading.get_ident())
            try:
                context = fixture.owners.issue_stop_context()
                results.append(kernel.revoke(grant,context,'reason:owner-revoke'))
            except BaseException as error: errors.append(error)
        kernel._peer = peer
        thread = threading.Thread(target=invoke,name='ka3-owned-paused-canonical-revoke')
        def retire():
            release.set(); thread.join(5); kernel._peer = original
            self.assertFalse(thread.is_alive())
        thread.start(); self.addCleanup(retire)
        self.assertTrue(entered.wait(2))
        return release, thread, errors, results

    def test_same_store_inflight_public_mutation_prevents_other_kernel_entry(self):
        f=self.fixture();kernel_a=f.kernel
        kernel_b=KernelTransactions(f.store,f.codec,authority.INSTALLATION,f.owners)
        grant_wire=f.cell(authority.grant_key_for(f.request)).value_wire
        paused,resume,finished=threading.Event(),threading.Event(),threading.Event()
        worker_ident=[];worker_errors=[];worker_results=[];pause_used=[]
        original_peer=kernel_a._peer
        def pause_at_peer(context):
            if threading.get_ident()==worker_ident[0] and not pause_used:
                pause_used.append(True);paused.set()
                if not resume.wait(5):raise AssertionError('reviewer failed to release own thread')
            return original_peer(context)
        kernel_a._peer=pause_at_peer
        def mutation():
            worker_ident.append(threading.get_ident())
            context=f.owners.issue_stop_context()
            try:worker_results.append(kernel_a.revoke(grant_wire,context,'reason:owner-revoke'))
            except BaseException as error:worker_errors.append(error)
            finally:finished.set()
        thread=threading.Thread(target=mutation,name='review-only-prestarted-public-revoke')
        thread.start();self.assertTrue(paused.wait(1))
        self.assertEqual(kernel_a._cpu_execution.mutating,1)
        self.assertEqual(kernel_b._cpu_execution.mutating,0)
        f.kernel=kernel_b;lease=self.lease(f);admitted=False;entry_errors=[];during={}
        started=time.perf_counter_ns()
        try:
            try:
                with lease:
                    admitted=True
                    during=dict(A_mutating=kernel_a._cpu_execution.mutating,
                        B_mutating=kernel_b._cpu_execution.mutating,
                        B_active_is_exact_lease=kernel_b._cpu_execution.active is lease,
                        A_thread_still_paused=not finished.is_set(),
                        consumed_permit=lease.inspection()['consumed_permit'] is not None,
                        attempt_state=lease.inspection()['attempt'].as_dict()['state'],
                        dispatch_admitted=lease.inspection()['dispatch_admitted'])
                    # Deliberately stop before dispatch or any final native fence.
            except BaseException as error:entry_errors.append(error)
        finally:
            elapsed=time.perf_counter_ns()-started
            resume.set();thread.join(5);kernel_a._peer=original_peer
        self.assertFalse(thread.is_alive());self.assertTrue(finished.is_set())
        row=dict(admitted=admitted,entry_errors=[getattr(e,'code',type(e).__name__) for e in entry_errors],
            during_admission=during,actual_entry_elapsed_ns=elapsed,elapsed_source='Unmodified actual perf_counter_ns; no timing patch',
            worker_native_thread_id=thread.native_id,worker_joined=not thread.is_alive(),
            worker_committed_only_after_lease_exit=bool(worker_results),
            worker_errors=[getattr(e,'code',type(e).__name__) for e in worker_errors],
            lease_closed=lease.inspection()['closed'],lease_pending_cleanup=lease.inspection()['pending_cleanup'],
            final_dispatch_admitted=lease.inspection()['dispatch_admitted'],
            actual_native_target=False,native_Set_calls=0,
            fixture='Actual disposable canonical SqliteJournal shared by two public kernel instances; private original-thread contexts and retained owner/capacity are controlled.')
        entry_facts.append(row)
        self.assertFalse(admitted,'Same-store kernel B entered/consumed/reserved while an already-started public mutation remained registered only in kernel A')

    def test_shared_store_with_distinct_owners_denies_before_any_peer_callback(self):
        f = self.fixture(); other = parent.ControlledExecutionOwners(f.request)
        second = self.second_kernel(f,owners=other)
        release, thread, errors, results = self.paused_revoke(f)
        f.kernel = second
        def forbidden(context): raise AssertionError('busy admission authenticated a different owner')
        with patch.object(second,'_peer',forbidden):
            lease = self.lease(f,native_proof=other.execution_proof,request_context=other.context)
            with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_SHARED_MUTATION_BUSY'): lease.__enter__()
        self.assertTrue(lease.inspection()['closed']); self.assertIsNone(second._cpu_execution.active)
        release.set(); thread.join(5); self.assertFalse(thread.is_alive()); self.assertFalse(errors)
        self.assertEqual(len(results),1); self.assert_idle(second._cpu_execution)

    def test_shared_owner_with_distinct_stores_denies_before_prepared_reads(self):
        f, other = self.fixture(), self.fixture()
        second = self.second_kernel(f,store=other.store)
        release, thread, errors, results = self.paused_revoke(f)
        f.kernel = second; lease = self.lease(f)
        def forbidden(): raise AssertionError('busy admission read a different journal')
        with patch.object(execution._RetainedCpuExecution,'_prepared_identity',lambda instance: forbidden()):
            with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_SHARED_MUTATION_BUSY'): lease.__enter__()
        release.set(); thread.join(5); self.assertFalse(thread.is_alive()); self.assertFalse(errors)
        second._cpu_execution.require_available(); self.assert_idle(second._cpu_execution)

    def test_unrelated_owner_and_store_can_enter_while_other_mutation_is_paused(self):
        first, second = self.fixture(), self.fixture()
        release, thread, errors, results = self.paused_revoke(first)
        with self.lease(second) as lease:
            self.assertEqual(first.kernel._cpu_execution.mutating,1)
            self.assertFalse(lease.inspection()['dispatch_admitted'])
            self.assertFalse(lease.inspection()['closed'])
        self.assert_idle(second.kernel._cpu_execution)
        release.set(); thread.join(5); self.assertFalse(thread.is_alive()); self.assertFalse(errors)

    def test_ordinary_two_kernel_mutations_are_concurrent_and_both_retire(self):
        f = self.fixture(); first = f.kernel; second = self.second_kernel(f)
        a_release, a_thread, a_errors, a_results = self.paused_revoke(f,first)
        b_release, b_thread, b_errors, b_results = self.paused_revoke(f,second)
        row = self.occupancy(first._cpu_execution)
        self.assertEqual((row['owner_count'],row['store_count']),(2,2))
        self.assertEqual(first._cpu_execution.mutating,1); self.assertEqual(second._cpu_execution.mutating,1)
        a_release.set(); b_release.set(); a_thread.join(5); b_thread.join(5)
        self.assertFalse(a_thread.is_alive()); self.assertFalse(b_thread.is_alive())
        self.assertEqual(len(a_results)+len(a_errors),1); self.assertEqual(len(b_results)+len(b_errors),1)
        self.assertGreaterEqual(len(a_results)+len(b_results),1)
        self.assert_idle(first._cpu_execution); self.assert_idle(second._cpu_execution)

    def test_nested_ordinary_registrations_keep_counts_until_each_finally(self):
        f = self.fixture(); first = f.kernel._cpu_execution; second = self.second_kernel(f)._cpu_execution
        observations = []; initial = (first.generation,second.generation)
        def inner(kernel): observations.append(self.occupancy(first)); return 'inner-result'
        def outer(kernel):
            observations.append(self.occupancy(first))
            self.assertEqual(second.mutate(inner,(),{}),'inner-result')
            observations.append(self.occupancy(first))
            return first.mutate(inner,(),{})
        self.assertEqual(first.mutate(outer,(),{}),'inner-result')
        self.assertEqual([r['owner_count'] for r in observations],[1,2,1,2])
        self.assertEqual(first.generation-initial[0],2); self.assertEqual(second.generation-initial[1],1)
        self.assert_idle(first); self.assert_idle(second)

    def test_public_mutation_primary_failures_retire_every_registered_identity(self):
        for primary in (KeyboardInterrupt('ka3-auth-interrupt'),SystemExit('ka3-auth-exit'),RuntimeError('ka3-auth-error')):
            with self.subTest(primary=type(primary).__name__):
                f = self.fixture(); second = self.second_kernel(f)
                grant = f.cell(authority.grant_key_for(f.request)).value_wire
                def rejected(context): raise primary
                with patch.object(f.kernel,'_peer',rejected):
                    try: f.kernel.revoke(grant,f.owners.context,'reason:owner-revoke')
                    except BaseException as observed: self.assertIs(observed,primary)
                    else: self.fail('original failure was lost')
                self.assert_idle(f.kernel._cpu_execution); self.assert_idle(second._cpu_execution)
                second._cpu_execution.require_available()

    def test_active_lease_denial_does_not_register_or_clear_winner(self):
        f = self.fixture(); second = self.second_kernel(f)
        grant = f.cell(authority.grant_key_for(f.request)).value_wire
        with self.lease(f) as lease:
            with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_OTHER_KERNEL_ACTIVE'):
                second.revoke(grant,f.owners.context,'reason:owner-revoke')
            with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_MUTATION_BUSY'):
                f.kernel.prepare(f.proposal,f.owners.context)
            row = self.occupancy(f.kernel._cpu_execution)
            self.assertEqual((row['owner_count'],row['store_count'],row['local_count']),(0,0,0))
            self.assertIs(row['active'],lease); self.assertIs(row['owner_active'][3],lease)
            self.assertIsNone(row['allowed'])
        self.assert_idle(f.kernel._cpu_execution)

    def test_mutation_registered_after_prepared_reads_wins_final_admission(self):
        f = self.fixture(); first = f.kernel; second = self.second_kernel(f)
        f.kernel = second; lease = self.lease(f); paused = []
        original = execution._RetainedCpuExecution._prepared_identity
        def prepared(instance):
            original(instance)
            if instance is lease: paused.append(self.paused_revoke(f,first))
        try:
            with patch.object(execution._RetainedCpuExecution,'_prepared_identity',prepared):
                with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_SHARED_MUTATION_BUSY'): lease.__enter__()
            self.assertTrue(lease.inspection()['closed']); self.assertFalse(lease.inspection()['pending_cleanup'])
            self.assertIsNone(second._cpu_execution.active); self.assertEqual(self.status(f),'PREPARED')
        finally:
            for release,thread,errors,results in paused:
                release.set(); thread.join(5); self.assertFalse(thread.is_alive())
        self.assert_idle(second._cpu_execution)

    def test_admission_registration_wins_before_competing_mutation_callback(self):
        f = self.fixture(); first = f.kernel; second = self.second_kernel(f)
        grant = f.cell(authority.grant_key_for(f.request)).value_wire
        f.kernel = second; failures = []; callbacks = []
        original_claim = second._cpu_execution.claim_liveness
        def forbidden(context): callbacks.append(context); raise AssertionError('losing mutation authenticated')
        def claim(lease):
            original_claim(lease)
            def mutation():
                try: first.revoke(grant,f.owners.issue_stop_context(),'reason:owner-revoke')
                except BaseException as error: failures.append(error)
            thread = threading.Thread(target=mutation,name='ka3-owned-losing-mutation')
            thread.start(); thread.join(2); self.assertFalse(thread.is_alive())
        with patch.object(first,'_peer',forbidden), patch.object(second._cpu_execution,'claim_liveness',claim):
            with self.lease(f) as lease:
                self.assertIs(second._cpu_execution.active,lease)
                self.assertEqual(len(failures),1); self.assertEqual(failures[0].code,'CPU_EXECUTION_OTHER_KERNEL_ACTIVE')
                self.assertFalse(callbacks); self.assertEqual(first._cpu_execution.mutating,0)
        self.assert_idle(second._cpu_execution)

    def test_nested_entry_between_prepared_read_and_claim_cannot_steal_winner(self):
        f = self.fixture(); loser, winner = self.lease(f), self.lease(f)
        original = execution._RetainedCpuExecution._prepared_identity; entered = []
        def prepared(instance):
            original(instance)
            if instance is loser: winner.__enter__(); entered.append(True)
        try:
            with patch.object(execution._RetainedCpuExecution,'_prepared_identity',prepared):
                with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_STOPPED_OR_BUSY'): loser.__enter__()
            self.assertTrue(entered); self.assertTrue(loser.inspection()['closed'])
            row = self.occupancy(f.kernel._cpu_execution)
            self.assertIs(row['active'],winner); self.assertIs(row['owner_active'][3],winner)
            self.assertIs(row['store_active'][3],winner); self.assertIsNone(row['allowed'])
            self.assertFalse(winner.inspection()['closed']); self.assertIsNotNone(winner.inspection()['attempt'])
        finally:
            if entered: winner.__exit__(None,None,None)
        self.assert_idle(f.kernel._cpu_execution)

    def test_retainer_creation_failure_retires_only_its_admission(self):
        f = self.fixture(); primary = KeyboardInterrupt('ka3-retainer-create-failed')
        coordinator = f.kernel._cpu_execution; original = coordinator.retain
        def failed(*args): raise primary
        coordinator.retain = failed; lease = self.lease(f)
        try:
            try: lease.__enter__()
            except BaseException as observed: self.assertIs(observed,primary)
            else: self.fail('creation failure escaped classification')
        finally: coordinator.retain = original
        self.assertTrue(lease.inspection()['closed']); self.assert_idle(coordinator)
        self.assertEqual(self.status(f),'PREPARED')
        with self.lease(f): pass
        self.assert_idle(coordinator)

    def test_failed_retained_entry_keeps_pending_identity_until_explicit_fixture_cleanup(self):
        f = self.fixture(); coordinator = f.kernel._cpu_execution
        f.owners.entry_error = KeyboardInterrupt('ka3-retained-entry-pending'); lease = self.lease(f)
        try:
            with self.assertRaises(KeyboardInterrupt) as raised: lease.__enter__()
            self.assertIs(raised.exception,f.owners.entry_error)
            self.assertIs(raised.exception.owned_cpu_execution,lease)
            self.assertTrue(lease.inspection()['pending_cleanup']); self.assertIs(coordinator.active,lease)
            second = self.second_kernel(f)
            with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_OTHER_KERNEL_ACTIVE'):
                second._cpu_execution.require_available()
        finally:
            # Controlled test-only teardown: settle its actual RLock custody
            # first, then remove only this fixture's private liveness record.
            f.owners.managers[-1].recover_cleanup()
            self.assertFalse(f.owners.managers[-1].locked)
            coordinator.release_liveness(lease)
        self.assert_idle(coordinator)

    def test_failed_retained_exit_does_not_release_other_kernel_admission(self):
        f = self.fixture(); coordinator = f.kernel._cpu_execution
        primary = SystemExit('ka3-retained-exit-pending'); lease = self.lease(f); lease.__enter__()
        f.owners.exit_error = primary
        try:
            with self.assertRaises(SystemExit) as raised: lease.__exit__(None,None,None)
            self.assertIs(raised.exception,primary); self.assertIs(primary.owned_cpu_execution,lease)
            self.assertTrue(lease.inspection()['pending_cleanup']); self.assertIs(coordinator.active,lease)
            with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_OTHER_KERNEL_ACTIVE'):
                self.second_kernel(f)._cpu_execution.require_available()
        finally:
            f.owners.managers[-1].recover_cleanup()
            self.assertFalse(f.owners.managers[-1].locked)
            coordinator.release_liveness(lease)
        self.assert_idle(coordinator)

    def test_successful_exit_retires_both_keys_before_next_public_mutation(self):
        f = self.fixture(); second = self.second_kernel(f)
        grant = f.cell(authority.grant_key_for(f.request)).value_wire
        with self.lease(f): pass
        self.assert_idle(f.kernel._cpu_execution); second._cpu_execution.require_available()
        second.revoke(grant,f.owners.context,'reason:owner-revoke')
        self.assert_idle(second._cpu_execution)

    def test_delegation_is_single_use_and_nested_public_writes_remain_denied(self):
        f = self.fixture(); coordinator = f.kernel._cpu_execution; original = f.kernel._peer
        counts = []; nested = []
        def peer(context):
            if coordinator.mutating:
                row = self.occupancy(coordinator); counts.append((row['owner_count'],row['store_count'],row['local_count']))
                self.assertIsNone(row['allowed'])
                with self.assertRaisesRegex(ContractError,'CPU_EXECUTION_MUTATION_BUSY'):
                    f.kernel.prepare(f.proposal,context)
                nested.append(True)
            return original(context)
        with patch.object(f.kernel,'_peer',peer):
            with self.lease(f) as lease:
                self.assertIsNotNone(lease.inspection()['attempt'])
                self.assertEqual(coordinator.mutating,0); self.assertIsNone(coordinator.allowed)
        self.assertTrue(nested); self.assertTrue(all(value==(1,1,1) for value in counts))
        self.assert_idle(coordinator)

    def test_failed_delegated_consume_retires_counts_and_exact_delegation(self):
        f = self.fixture(); coordinator = f.kernel._cpu_execution; original = f.kernel._peer
        primary = KeyboardInterrupt('ka3-consume-auth-refusal')
        def peer(context):
            if coordinator.mutating: raise primary
            return original(context)
        lease = self.lease(f)
        with patch.object(f.kernel,'_peer',peer):
            try: lease.__enter__()
            except BaseException as observed: self.assertIs(observed,primary)
            else: self.fail('delegated failure was not preserved')
        self.assertTrue(lease.inspection()['closed']); self.assertEqual(self.status(f),'PREPARED')
        self.assert_idle(coordinator)

    def test_no_metadata_lock_is_retained_across_auth_retainer_or_cleanup(self):
        f = self.fixture(); coordinator = f.kernel._cpu_execution; observations = []
        def probe(label):
            row = []
            def inspect():
                for lock in (execution._LIVENESS_LOCK,coordinator.lock):
                    acquired = lock.acquire(blocking=False); row.append(acquired)
                    if acquired: lock.release()
            thread = threading.Thread(target=inspect,name='ka3-owned-metadata-lock-probe')
            thread.start(); thread.join(2); self.assertFalse(thread.is_alive())
            observations.append((label,row)); self.assertEqual(row,[True,True])
        original_peer = f.kernel._peer; original_enter = parent.ControlledRetainer.__enter__
        original_exit = parent.ControlledRetainer.__exit__
        def peer(context): probe('authenticate'); return original_peer(context)
        def enter(manager): probe('retainer-enter'); return original_enter(manager)
        def exit(manager,*args): probe('retainer-exit'); return original_exit(manager,*args)
        f.owners.on_execution = lambda phase: probe('current-'+phase)
        with patch.object(f.kernel,'_peer',peer), patch.object(parent.ControlledRetainer,'__enter__',enter), \
                patch.object(parent.ControlledRetainer,'__exit__',exit):
            with self.lease(f): pass
        self.assertIn('retainer-enter',[label for label,row in observations])
        self.assertIn('retainer-exit',[label for label,row in observations])
        REGISTRATION_OBSERVATIONS.append(dict(metadata_lock_checks=observations,native_Set_calls=0))
        self.assert_idle(coordinator)

    def test_public_stop_during_capacity_remains_nonblocking_and_does_not_consume(self):
        f = self.fixture(); errors = []; started = []; elapsed = []
        def at_capacity(phase):
            if phase != 'CAPACITY': return
            def stop():
                started.append(time.perf_counter_ns())
                try: f.kernel.stop_owner_authority(f.request.request_id,
                    f.owners.issue_stop_context(),'reason:owner-stop')
                except BaseException as error: errors.append(error)
                finally: elapsed.append(time.perf_counter_ns()-started[0])
            thread = threading.Thread(target=stop,name='ka3-owned-public-stop-during-capacity')
            thread.start(); thread.join(2); self.assertFalse(thread.is_alive())
        f.owners.on_execution = at_capacity; lease = self.lease(f)
        coordinator = f.kernel._cpu_execution; original_elapsed = coordinator.elapsed; samples = []
        def observe_elapsed():
            value = original_elapsed(); samples.append(value); return value
        with patch.object(coordinator,'elapsed',observe_elapsed):
            try:
                with self.assertRaises(ContractError) as entry: lease.__enter__()
            finally:
                if lease._entered: lease.__exit__(None,None,None)
        self.assertEqual(len(samples),5)
        callback_elapsed = samples[4]-samples[3]+2*coordinator.resolution
        if entry.exception.code == 'CPU_EXECUTION_OWNER_TOO_SLOW':
            self.assertGreater(callback_elapsed,execution.MAXIMUM_CHECK_NS)
        else:
            self.assertLessEqual(callback_elapsed,execution.MAXIMUM_CHECK_NS)
        self.assertIn(entry.exception.code,('CPU_EXECUTION_STOPPED','CPU_EXECUTION_OWNER_TOO_SLOW'))
        self.assertEqual(len(errors),1); self.assertEqual(errors[0].code,'CPU_EXECUTION_CONTROL_DURABLE_PENDING')
        self.assertTrue(errors[0].immediate_cancellation); self.assertFalse(errors[0].durable_completed)
        self.assertIs(errors[0].owned_cpu_execution,lease); self.assertEqual(self.status(f),'PREPARED')
        self.assertLess(elapsed[0],2_000_000_000); self.assertFalse(lease.inspection()['dispatch_admitted'])
        self.assertTrue(lease.inspection()['stopped'])
        REGISTRATION_OBSERVATIONS.append(dict(public_stop_entry_denial=entry.exception.code,
            actual_stop_elapsed_ns=elapsed[0],canonical_stop_preflight_ns=errors[0].stop_preflight_elapsed_ns,
            stopped=True,prepared=True,native_Set_calls=0,owner_50ms_bound_unchanged=True,
            actual_owner_elapsed_samples=samples,elapsed_resolution_ns=coordinator.resolution,
            observed_current_callback_elapsed_ns=callback_elapsed,maximum_callback_ns=execution.MAXIMUM_CHECK_NS,
            actual_elapsed_values_passed_through_unchanged=True))
        self.assert_idle(f.kernel._cpu_execution)
