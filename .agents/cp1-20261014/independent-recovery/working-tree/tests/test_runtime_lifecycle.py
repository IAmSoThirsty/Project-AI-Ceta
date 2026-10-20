import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from ceta.runtime import IllegalTransition, ManualClock, Refused, Runtime, State


def graph(log, api_drain=None, db_stop=None, policy_start=None):
    r = Runtime(ManualClock())
    r.register('db', start=lambda: log.append('start:db'), stop=db_stop or (lambda: log.append('stop:db')))
    r.register('policy', depends=('db',), start=policy_start or (lambda: log.append('start:policy')), stop=lambda: log.append('stop:policy'))
    r.register('api', depends=('policy',), start=lambda: log.append('start:api'), stop=lambda: log.append('stop:api'), drain=api_drain)
    return r


def overrun_drain(pending, deadline, clock):
    clock.advance(5.0)
    return pending


def instant_drain(pending, deadline, clock):
    return pending


class BootTests(unittest.TestCase):
    def test_positive_valid_installation_reaches_running(self):
        log = []
        r = graph(log)
        res = r.boot(lambda: True)
        self.assertEqual(res.state, State.RUNNING)
        self.assertEqual(res.started, ('db', 'policy', 'api'))
        self.assertEqual(res.diagnostics, ())
        self.assertTrue(r.dispatch_open)
        self.assertEqual(res.lifecycle_generation, 1)
        self.assertEqual(log, ['start:db', 'start:policy', 'start:api'])

    def test_oracle_missing_trust_opens_maintenance_dispatch_closed(self):
        log = []
        r = graph(log)
        res = r.boot(lambda: False)
        self.assertEqual(res.state, State.MAINTENANCE)
        self.assertEqual(res.started, ())
        self.assertEqual(res.diagnostics, ('trust_material_missing',))
        self.assertFalse(r.dispatch_open)
        self.assertEqual(log, [])
        with self.assertRaises(Refused):
            r.token('db')

    def test_negative_trust_check_exception_fails_closed(self):
        def broken():
            raise RuntimeError('keystore unreachable')
        log = []
        res = graph(log).boot(broken)
        self.assertEqual(res.state, State.MAINTENANCE)
        self.assertEqual(res.diagnostics, ('trust_check_error:RuntimeError',))
        self.assertEqual(log, [])

    def test_negative_non_boolean_trust_verdict_fails_closed(self):
        for verdict in ('yes', None, 1):
            log = []
            res = graph(log).boot(lambda v=verdict: v)
            self.assertEqual(res.state, State.MAINTENANCE)
            self.assertEqual(res.diagnostics, ('trust_material_invalid_result',))
            self.assertEqual(log, [])

    def test_negative_missing_dependency_refused_state_unchanged(self):
        r = Runtime(ManualClock())
        r.register('api', depends=('ghost',))
        with self.assertRaises(Refused) as ctx:
            r.boot(lambda: True)
        self.assertEqual(ctx.exception.code, 'missing_dependency')
        self.assertEqual(r.state, State.CREATED)

    def test_negative_dependency_cycle_refused(self):
        r = Runtime(ManualClock())
        r.register('a', depends=('b',))
        r.register('b', depends=('a',))
        with self.assertRaises(Refused) as ctx:
            r.boot(lambda: True)
        self.assertEqual(ctx.exception.code, 'dependency_cycle')
        self.assertEqual(r.state, State.CREATED)

    def test_negative_self_dependency_and_duplicate_rejected(self):
        r = Runtime(ManualClock())
        with self.assertRaises(Refused) as ctx:
            r.register('a', depends=('a',))
        self.assertEqual(ctx.exception.code, 'dependency_cycle')
        r.register('db')
        with self.assertRaises(Refused) as ctx:
            r.register('db')
        self.assertEqual(ctx.exception.code, 'duplicate_component')

    def test_boundary_empty_runtime_boots_to_running(self):
        res = Runtime(ManualClock()).boot(lambda: True)
        self.assertEqual(res.state, State.RUNNING)
        self.assertEqual(res.started, ())

    def test_negative_boot_while_running_is_illegal(self):
        r = graph([])
        r.boot(lambda: True)
        with self.assertRaises(IllegalTransition):
            r.boot(lambda: True)
        self.assertEqual(r.state, State.RUNNING)

    def test_negative_start_failure_rolls_back_started_components(self):
        def boom():
            raise RuntimeError('policy store locked')
        log = []
        r = graph(log, policy_start=boom)
        res = r.boot(lambda: True)
        self.assertEqual(res.state, State.FAILED)
        self.assertEqual(res.started, ())
        self.assertIn('start_failed:policy:RuntimeError', res.diagnostics)
        self.assertEqual(log, ['start:db', 'stop:db'])
        self.assertFalse(r.component('db').ready)
        self.assertFalse(r.dispatch_open)

    def test_recovery_failed_boot_retry_gets_new_generation(self):
        attempts = []
        def flaky():
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError('transient')
        r = graph([], policy_start=flaky)
        self.assertEqual(r.boot(lambda: True).state, State.FAILED)
        res = r.boot(lambda: True)
        self.assertEqual(res.state, State.RUNNING)
        self.assertEqual(res.lifecycle_generation, 2)
        self.assertEqual(r.component('db').generation, 2)

    def test_recovery_maintenance_then_repaired_trust_boots(self):
        trust = {'present': False}
        r = graph([])
        self.assertEqual(r.boot(lambda: trust['present']).state, State.MAINTENANCE)
        trust['present'] = True
        res = r.boot(lambda: trust['present'])
        self.assertEqual(res.state, State.RUNNING)
        self.assertEqual(res.lifecycle_generation, 2)


class ReentrancyTests(unittest.TestCase):
    def test_start_hook_reentrant_boot_fails_closed(self):
        r = Runtime(ManualClock())
        def start_calls_boot():
            r.boot(lambda: True)
        r.register('db', start=start_calls_boot)
        res = r.boot(lambda: True)
        self.assertEqual(res.state, State.FAILED)
        self.assertFalse(r.dispatch_open)
        self.assertTrue(any(d.startswith('start_failed:db') for d in res.diagnostics))

    def test_stop_hook_reentrant_shutdown_fails_closed(self):
        r = Runtime(ManualClock())
        def stop_calls_shutdown():
            r.shutdown(5)
        r.register('db', stop=stop_calls_shutdown)
        r.boot(lambda: True)
        res = r.shutdown(5)
        self.assertEqual(res.state, State.FAILED)
        self.assertFalse(r.dispatch_open)
        self.assertTrue(any(d.startswith('stop_failed:db') for d in res.diagnostics))


if __name__ == '__main__':
    unittest.main()
