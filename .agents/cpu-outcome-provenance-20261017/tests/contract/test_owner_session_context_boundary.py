"""Actual public owner contexts over controlled ports; no native allocation."""
import copy
import inspect
import pickle
import threading
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from ceta.contracts.wire import ContractError
from ceta.identity import owner_session as m

facts = []
raw = lambda error: BaseException.__dict__['__dict__'].__get__(error)
tb = lambda error: BaseException.__dict__['__traceback__'].__get__(error)


class PlainBaseContext:
    def __enter__(self): return self
    def __exit__(self, *args): return None


class ControlledCodeLease:
    def __init__(self, calls, enter_error=None, exit_error=None, decision=False):
        self.calls, self.enter_error, self.exit_error, self.decision = calls, enter_error, exit_error, decision
    def __enter__(self):
        self.calls.append('code-enter')
        if self.enter_error is not None: raise self.enter_error
        return self
    def __exit__(self, kind, primary, trace):
        self.calls.append(('code-exit', kind, primary, trace))
        if self.exit_error is not None: raise self.exit_error
        return self.decision
    def require_current(self): self.calls.append('code-current')


class OwnerContextBoundaryTests(unittest.TestCase):
    def owner(self, cleanup=None):
        calls = []
        class Session:
            _enrollment = False
            def close(self):
                calls.append('close')
                if cleanup is not None: raise cleanup
        owner = object.__new__(m.NativeCpuOwnerSession)
        designation = SimpleNamespace(active=True); proof = SimpleNamespace(active=True)
        owner._effect = designation; owner._effect_lease = None; owner._effect_proof = proof
        owner._approval = SimpleNamespace(_active=Session())
        return owner, calls, designation, proof

    def actual_owner(self, *, cls=m.NativeCpuOwnerSession, session_error=None,
                     code_error=None, entry_error=None, decision=False):
        calls = []; context = object(); owner = object.__new__(cls)
        owner._lock, owner._stopped = threading.RLock(), threading.Event()
        owner._closed, owner._dispatch = False, None
        witness = owner._proof = SimpleNamespace(active=True)
        owner._expected = owner._enrollment_lease = owner._anchor = None
        designation = owner._effect = SimpleNamespace(active=True)
        effect_lease = owner._effect_lease = SimpleNamespace(active=True)
        effect_proof = owner._effect_proof = SimpleNamespace(active=True)
        code = ControlledCodeLease(calls, entry_error, code_error, decision)
        owner._code = SimpleNamespace(retained=lambda: code)
        owner._view = SimpleNamespace(_store=SimpleNamespace(require_current=lambda: calls.append('store-current')))
        def authenticate(supplied):
            if supplied is not context: raise ContractError('CONTROLLED_ORIGINAL_CONTEXT_REQUIRED')
            calls.append('authenticate'); return object()
        owner.authenticate = authenticate
        class Session:
            _enrollment = False
            def close(self):
                calls.append('session-close')
                if session_error is not None: raise session_error
                owner._approval._active = None
        owner._approval = SimpleNamespace(_active=Session(), cancel_current=lambda: calls.append('cancel'))
        return SimpleNamespace(owner=owner, context=context, calls=calls, code=code,
            witness=witness, designation=designation, effect_lease=effect_lease, effect_proof=effect_proof)

    def caught(self, action):
        try: action()
        except BaseException as error: return error
        self.fail('expected exact failure')

    def run_body(self, guard, primary):
        with guard: raise primary

    def released(self, fixture):
        self.assertIsNone(fixture.owner._dispatch)
        acquired = []
        def other_thread():
            held = fixture.owner._lock.acquire(blocking=False); acquired.append(held)
            if held: fixture.owner._lock.release()
        thread = threading.Thread(target=other_thread); thread.start(); thread.join(1)
        self.assertFalse(thread.is_alive()); self.assertEqual(acquired, [True])

    def original_traceback_retained(self, primary):
        expected = dict.__getitem__(raw(primary), 'native_owner_context_original_traceback')
        current = tb(primary); prefix = []
        while current is not None and current is not expected:
            prefix.append(current.tb_frame.f_code.co_name); current = current.tb_next
        self.assertIs(current, expected)
        self.assertEqual(prefix, ['caught', '<lambda>'])
        self.assertEqual(expected.tb_frame.f_code.co_name, 'run_body')
        guard = dict.__getitem__(raw(primary), 'native_owner_context_guard')
        self.assertIs(guard.inspection()['original_traceback'], expected)

    def test_nested_actual_base_preserves_ordinary_and_memory_primaries(self):
        for cls in (m.NativeOwnerSession, m.NativeCpuOwnerSession):
            for primary in (KeyboardInterrupt('body'), SystemExit('body'), MemoryError('body'), ValueError('body')):
                with self.subTest(owner=cls.__name__, primary=type(primary).__name__):
                    f = self.actual_owner(cls=cls); guard = f.owner.native_context(f.context)
                    actual = self.caught(lambda: self.run_body(guard, primary))
                    self.assertIs(actual, primary); self.original_traceback_retained(primary)
                    self.assertEqual(guard.inspection()['state'], 'CLOSED')
                    self.assertFalse(guard.inspection()['pending_cleanup'])
                    self.assertEqual(len([c for c in f.calls if isinstance(c, tuple)]), 1)
                    self.assertFalse(f.witness.active); self.released(f)

    def test_nested_cleanup_and_traceback_traps_keep_all_exact_failures(self):
        for control in (KeyboardInterrupt, SystemExit, MemoryError):
            with self.subTest(control=control.__name__):
                trap = OSError('traceback-setter'); session_error = OSError('session-close'); code_error = OSError('code-close')
                class Primary(control):
                    def __setattr__(self, name, value):
                        if name == '__traceback__': raise trap
                        return super().__setattr__(name, value)
                primary = Primary('body'); f = self.actual_owner(session_error=session_error, code_error=code_error)
                guard = f.owner.native_context(f.context)
                self.assertIs(self.caught(lambda: self.run_body(guard, primary)), primary)
                data = raw(primary); failures = dict.__getitem__(data, 'native_owner_context_boundary_failures')
                self.assertIs(dict.__getitem__(data, 'native_owner_session_cleanup_error'), session_error)
                self.assertTrue(any(error is code_error for error, trace in failures))
                self.assertTrue(any(error is trap for error, trace in failures))
                self.assertTrue(all(trace is not None for error, trace in failures))
                self.original_traceback_retained(primary)
                self.assertIs(dict.__getitem__(data, 'native_owner_session'), f.owner)
                self.assertTrue(guard.inspection()['pending_cleanup']); self.assertEqual(guard.inspection()['state'], 'FAILED')
                self.assertFalse(f.designation.active); self.assertFalse(f.effect_lease.active); self.assertFalse(f.effect_proof.active)
                self.assertEqual(f.calls.count('session-close'), 1); self.released(f)

    def test_session_cleanup_secondary_is_not_replaced_by_context_trap(self):
        primary = KeyboardInterrupt('body'); secondary = SystemExit('session-close')
        f = self.actual_owner(session_error=secondary); guard = f.owner.native_context(f.context)
        self.assertIs(self.caught(lambda: self.run_body(guard, primary)), primary)
        self.assertIs(dict.__getitem__(raw(primary), 'native_owner_session_cleanup_error'), secondary)
        self.assertTrue(guard.inspection()['pending_cleanup']); self.released(f)

    def test_cleanup_only_control_and_memory_errors_escape_exactly(self):
        for primary in (KeyboardInterrupt('close'), SystemExit('close'), MemoryError('close')):
            with self.subTest(primary=type(primary).__name__):
                f = self.actual_owner(session_error=primary); guard = f.owner.native_context(f.context)
                def action():
                    with guard: pass
                self.assertIs(self.caught(action), primary)
                self.assertIs(dict.__getitem__(raw(primary), 'native_owner_context_guard'), guard)
                self.assertFalse(dict.__contains__(raw(primary), 'native_owner_session_cleanup_error'))
                self.assertIs(guard.inspection()['primary'], primary)
                self.assertTrue(guard.inspection()['pending_cleanup']); self.assertEqual(f.calls.count('session-close'), 1)
                self.released(f)

    def test_plain_success_closes_once_and_invalidates_every_witness(self):
        f = self.actual_owner(); guard = f.owner.native_context(f.context)
        with guard as owner: self.assertIs(owner, f.owner)
        self.assertEqual(guard.inspection()['state'], 'CLOSED'); self.assertFalse(guard.inspection()['pending_cleanup'])
        self.assertTrue(all(not item.active for item in (f.witness, f.designation, f.effect_lease, f.effect_proof)))
        self.assertEqual(f.calls.count('session-close'), 1); self.released(f)
        with self.assertRaisesRegex(ContractError, 'SINGLE_USE'): guard.__enter__()
        with self.assertRaisesRegex(ContractError, 'EXIT_ONCE'): guard.__exit__(None, None, None)
        self.assertEqual(f.calls.count('session-close'), 1)

    def test_wrong_original_context_is_denied_before_code_entry(self):
        f = self.actual_owner(); guard = f.owner.native_context(object())
        error = self.caught(guard.__enter__)
        self.assertIsInstance(error, ContractError); self.assertNotIn('code-enter', f.calls)
        self.assertIs(dict.__getitem__(raw(error), 'native_owner_context_guard'), guard)
        self.assertEqual(guard.inspection()['state'], 'FAILED'); self.released(f)

    def test_failed_enter_keeps_manager_and_does_not_guess_exit(self):
        primary = SystemExit('code-enter-failed'); f = self.actual_owner(entry_error=primary)
        guard = f.owner.native_context(f.context)
        self.assertIs(self.caught(guard.__enter__), primary)
        self.assertEqual(f.calls.count('code-enter'), 1); self.assertFalse(any(isinstance(c, tuple) for c in f.calls))
        self.assertTrue(guard.inspection()['pending_cleanup']); self.assertIsNotNone(guard.inspection()['manager'])
        with self.assertRaisesRegex(ContractError, 'SINGLE_USE'): guard.__enter__()
        self.assertEqual(f.calls.count('code-enter'), 1); self.released(f)

    def test_foreign_thread_cannot_enter_but_original_thread_can(self):
        f = self.actual_owner(); guard = f.owner.native_context(f.context); errors = []
        thread = threading.Thread(target=lambda: errors.append(self.caught(guard.__enter__)))
        thread.start(); thread.join(1); self.assertFalse(thread.is_alive())
        self.assertEqual(errors[0].code, 'OWNER_SESSION_CONTEXT_ORIGINAL_THREAD_REQUIRED')
        self.assertEqual(f.calls, []); self.assertEqual(guard.inspection()['state'], 'NEW')
        with guard: pass
        self.released(f)

    def test_foreign_thread_cannot_exit_or_consume_original_exit(self):
        f = self.actual_owner(); guard = f.owner.native_context(f.context); guard.__enter__(); errors = []
        thread = threading.Thread(target=lambda: errors.append(self.caught(lambda: guard.__exit__(None, None, None))))
        thread.start(); thread.join(1); self.assertFalse(thread.is_alive())
        self.assertEqual(errors[0].code, 'OWNER_SESSION_CONTEXT_ORIGINAL_THREAD_REQUIRED')
        self.assertEqual(guard.inspection()['state'], 'ACTIVE'); self.assertEqual(f.calls.count('session-close'), 0)
        self.assertIs(guard.__exit__(None, None, None), False); self.assertEqual(f.calls.count('session-close'), 1); self.released(f)

    def test_public_nested_context_denial_preserves_outer_dispatch(self):
        f = self.actual_owner(); outer = f.owner.native_context(f.context)
        with outer:
            held = f.owner._dispatch
            inner = f.owner.native_context(f.context)
            with self.assertRaisesRegex(ContractError, 'DISPATCH_ALREADY_HELD'): inner.__enter__()
            self.assertIs(f.owner._dispatch, held)
        self.assertEqual(f.calls.count('code-enter'), 1); self.released(f)

    def test_suppression_by_nested_code_context_is_refused(self):
        primary = KeyboardInterrupt('body'); f = self.actual_owner(decision=True); guard = f.owner.native_context(f.context)
        self.assertIs(self.caught(lambda: self.run_body(guard, primary)), primary)
        failures = dict.__getitem__(raw(primary), 'native_owner_context_boundary_failures')
        self.assertTrue(any(getattr(error, 'code', None) == 'OWNER_SESSION_CONTEXT_EXIT_DECISION_INVALID' for error, trace in failures))
        self.assertTrue(guard.inspection()['pending_cleanup']); self.released(f)

    def test_hostile_dictionary_and_diagnostic_hooks_are_not_called(self):
        hits = []; trap = SystemExit('hook')
        class Storage(dict):
            def refuse(self, *args, **kwargs): hits.append('dictionary'); raise trap
            get = update = __getitem__ = __setitem__ = __contains__ = refuse
        class Primary(KeyboardInterrupt):
            def __setattr__(self, name, value): hits.append('setter'); raise trap
            @property
            def add_note(self): hits.append('note'); raise trap
        primary = Primary('body'); BaseException.__dict__['__dict__'].__set__(primary, Storage())
        f = self.actual_owner(session_error=OSError('close')); guard = f.owner.native_context(f.context)
        self.assertIs(self.caught(lambda: self.run_body(guard, primary)), primary)
        self.assertTrue(all(hit == 'setter' for hit in hits))
        self.assertIs(dict.__getitem__(raw(primary), 'native_owner_context_guard'), guard)
        self.assertIs(dict.__getitem__(raw(primary), 'native_owner_session'), f.owner); self.released(f)

    def test_copy_pickle_and_signatures_preserve_single_owned_surface(self):
        f = self.actual_owner(); guard = f.owner.native_context(f.context)
        for action in (lambda: copy.copy(guard), lambda: copy.deepcopy(guard), lambda: pickle.dumps(guard)):
            with self.assertRaises(ContractError): action()
        for cls in (m.NativeOwnerSession, m.NativeCpuOwnerSession):
            self.assertEqual(tuple(inspect.signature(cls.native_context).parameters), ('self', 'original_context'))
        with guard: pass
        self.released(f)

    def test_malformed_exception_arguments_do_not_use_the_one_exit(self):
        f = self.actual_owner(); guard = f.owner.native_context(f.context); guard.__enter__()
        with self.assertRaisesRegex(ContractError, 'EXCEPTION_ARGUMENTS_INVALID'):
            guard.__exit__(KeyboardInterrupt, SystemExit('wrong-kind'), object())
        self.assertEqual(guard.inspection()['state'], 'ACTIVE'); self.assertEqual(f.calls.count('session-close'), 0)
        guard.__exit__(None, None, None); self.assertEqual(f.calls.count('session-close'), 1); self.released(f)

    def test_private_guard_malformed_exit_decisions_are_failures_without_bool(self):
        hits = []
        class Decision:
            def __bool__(self): hits.append('bool'); raise SystemExit('bool hook')
        for response in (True, 0, 1, 0.0, Decision()):
            with self.subTest(response_type=type(response).__name__):
                owner = self.actual_owner().owner; calls = []
                class Manager:
                    def __enter__(self): return owner
                    def __exit__(self, *args): calls.append(args); return response
                guard = m._NativeContextGuard(owner, object(), lambda *args: Manager())
                guard.__enter__()
                with self.assertRaisesRegex(ContractError, 'EXIT_DECISION_INVALID'): guard.__exit__(None, None, None)
                self.assertEqual(len(calls), 1); self.assertTrue(guard.inspection()['pending_cleanup'])
                with self.assertRaisesRegex(ContractError, 'EXIT_ONCE'): guard.__exit__(None, None, None)
                self.assertEqual(len(calls), 1)
        self.assertEqual(hits, [])

    def test_private_guard_invalid_enter_result_exits_once_with_real_failure(self):
        owner = self.actual_owner().owner; calls = []
        class Manager:
            def __enter__(self): return True
            def __exit__(self, *args): calls.append(args); return False
        guard = m._NativeContextGuard(owner, object(), lambda *args: Manager())
        error = self.caught(guard.__enter__)
        self.assertEqual(error.code, 'OWNER_SESSION_CONTEXT_ENTER_RESULT_INVALID')
        self.assertEqual(len(calls), 1); self.assertIs(calls[0][1], error)
        self.assertEqual(guard.inspection()['state'], 'FAILED'); self.assertFalse(guard.inspection()['pending_cleanup'])

    def test_private_guard_reentrant_exit_refusal_cannot_be_silently_swallowed(self):
        owner = self.actual_owner().owner; calls = []
        class Manager:
            def __enter__(self): return owner
            def __exit__(self, *args):
                calls.append(args)
                with self_test.assertRaisesRegex(ContractError, 'EXIT_ONCE'): guard.__exit__(None, None, None)
                return False
        self_test = self; guard = m._NativeContextGuard(owner, object(), lambda *args: Manager())
        guard.__enter__()
        with self.assertRaisesRegex(ContractError, 'EXIT_ONCE'): guard.__exit__(None, None, None)
        self.assertEqual(len(calls), 1); self.assertTrue(guard.inspection()['pending_cleanup'])

    def test_primary_keeps_boundary_failure_when_direct_exit_refuses(self):
        primary = MemoryError('body'); cleanup = SystemExit('exit'); owner = self.actual_owner().owner
        class Manager:
            def __enter__(self): return owner
            def __exit__(self, *args): raise cleanup
        guard = m._NativeContextGuard(owner, object(), lambda *args: Manager())
        self.assertIs(self.caught(lambda: self.run_body(guard, primary)), primary)
        failures = dict.__getitem__(raw(primary), 'native_owner_context_boundary_failures')
        self.assertEqual(len(failures), 1); self.assertIs(failures[0][0], cleanup)
        self.assertIs(failures[0][1], tb(cleanup)); self.assertTrue(guard.inspection()['pending_cleanup'])

    def test_reentrant_entry_marks_attempt_before_call_and_exits_once_with_failure(self):
        owner = self.actual_owner().owner; calls = []; self_test = self
        class Manager:
            def __enter__(self):
                calls.append(guard.inspection()['state'])
                with self_test.assertRaisesRegex(ContractError, 'SINGLE_USE'): guard.__enter__()
                return owner
            def __exit__(self, kind, primary, trace):
                calls.append((guard.inspection()['state'], primary)); return False
        guard = m._NativeContextGuard(owner, object(), lambda *args: Manager())
        primary = self.caught(guard.__enter__)
        self.assertEqual(primary.code, 'OWNER_SESSION_CONTEXT_SINGLE_USE')
        self.assertEqual(calls[0], 'ENTERING'); self.assertEqual(calls[1][0], 'EXITING')
        self.assertIs(calls[1][1], primary); self.assertEqual(len(calls), 2)
        self.assertEqual(guard.inspection()['state'], 'FAILED')

    def test_exposed_owner_recovery_does_not_replay_guard_or_borrowed_code_exit(self):
        primary = KeyboardInterrupt('body'); cleanup = OSError('session-close')
        f = self.actual_owner(session_error=cleanup); guard = f.owner.native_context(f.context)
        self.assertIs(self.caught(lambda: self.run_body(guard, primary)), primary)
        portal = dict.__getitem__(raw(primary), 'close_cleanup')
        self.assertIs(portal.__self__, f.owner); self.assertFalse(f.owner.closed)
        recovered = []
        def controlled_retirement():
            recovered.append('explicit-retire'); f.owner._approval._active = None
        f.owner._approval._active.close = controlled_retirement
        portal()
        self.assertEqual(recovered, ['explicit-retire']); self.assertTrue(f.owner.closed)
        self.assertEqual(len([c for c in f.calls if isinstance(c, tuple)]), 1)
        with self.assertRaisesRegex(ContractError, 'EXIT_ONCE'): guard.__exit__(None, None, None)
        self.assertEqual(recovered, ['explicit-retire']); self.released(f)

    def test_actual_context_successful_cleanup_preserves_primary_and_invalidates(self):
     primary=KeyboardInterrupt('ordinary-control');owner,calls,designation,proof=self.owner()
     actual=None
     with patch.object(m.NativeOwnerSession,'native_context',lambda self,context:PlainBaseContext()):
      try:
       with owner.native_context(object()):raise primary
      except BaseException as error:actual=error
     facts.append({'case':'ordinary-primary','primary_exact':actual is primary,'cleanup_calls':calls.copy(),
      'designation_inactive':not designation.active,'proof_inactive':not proof.active})
     self.assertIs(actual,primary);self.assertEqual(calls,['close'])
     self.assertFalse(designation.active);self.assertFalse(proof.active)
     self.assertIsNone(owner._effect);self.assertIsNone(owner._effect_proof)

    def test_actual_context_boundary_preserves_control_primary_when_traceback_setter_refuses(self):
     for control in (KeyboardInterrupt,SystemExit):
      with self.subTest(control=control.__name__):
       trap=OSError('traceback-assignment-refused');hits=[]
       class Primary(control):
        def __setattr__(self,name,value):
         if name=='__traceback__':hits.append(name);raise trap
         return super().__setattr__(name,value)
       primary=Primary('control-primary');cleanup=OSError('session-close-refusal')
       owner,calls,designation,proof=self.owner(cleanup);actual=None
       with patch.object(m.NativeOwnerSession,'native_context',lambda self,context:PlainBaseContext()):
        try:
         with owner.native_context(object()):raise primary
        except BaseException as error:actual=error
       storage=BaseException.__dict__['__dict__'].__get__(primary)
       facts.append({'case':'traceback-setter','control':control.__name__,'primary_exact':actual is primary,
        'exact_setter_trap_escaped':actual is trap,'actual_type':type(actual).__name__,'setter_calls':hits,
        'escaped_traceback_frames':[{'file':frame.filename,'line':frame.lineno,'function':frame.name} for frame in traceback.extract_tb(BaseException.__dict__['__traceback__'].__get__(actual))],
        'cleanup_calls':calls,'exact_cleanup_secondary_retained':dict.get(storage,'native_owner_session_cleanup_error') is cleanup,
        'exact_owner_retained':dict.get(storage,'native_owner_session') is owner,
        'designation_inactive':not designation.active,'proof_inactive':not proof.active,
        'classification':'Actual product contextmanager boundary over controlled base/session; no native resource allocation.'})
       self.assertIs(actual,primary)
