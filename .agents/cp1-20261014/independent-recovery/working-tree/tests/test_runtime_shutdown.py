import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from ceta.runtime import ManualClock, Refused, Runtime, State


def graph(log, api_drain=None, db_stop=None):
    r = Runtime(ManualClock())
    r.register('db', start=lambda: log.append('start:db'), stop=db_stop or (lambda: log.append('stop:db')))
    r.register('policy', depends=('db',), start=lambda: log.append('start:policy'), stop=lambda: log.append('stop:policy'))
    r.register('api', depends=('policy',), start=lambda: log.append('start:api'), stop=lambda: log.append('stop:api'), drain=api_drain)
    return r


def running(log, **kw):
    r = graph(log, **kw)
    assert r.boot(lambda: True).state is State.RUNNING
    log.clear()
    return r


def overrun(pending, deadline, clock):
    clock.advance(5.0)
    return pending


def instant(pending, deadline, clock):
    return pending


def raising(pending, deadline, clock):
    raise RuntimeError('worker crashed')


class ShutdownTests(unittest.TestCase):
    def test_clean_shutdown_dependents_first(self):
        log = []
        r = running(log)
        res = r.shutdown(10)
        self.assertEqual(res.state, State.STOPPED)
        self.assertEqual(res.stop_order, ('api', 'policy', 'db'))
        self.assertEqual(log, ['stop:api', 'stop:policy', 'stop:db'])
        self.assertEqual(res.outcomes, ())
        self.assertFalse(r.dispatch_open)

    def test_oracle_overrun_effect_is_uncertain(self):
        log = []
        r = running(log, api_drain=overrun)
        r.submit(r.token('api'), 'write-42')
        res = r.shutdown(3)
        self.assertEqual(res.outcomes, (('api', 'write-42', 'uncertain'),))
        self.assertTrue(res.deadline_exceeded)
        self.assertIn('deadline_exceeded:api', res.diagnostics)
        self.assertEqual(res.state, State.STOPPED)

    def test_fast_drain_completes_effect(self):
        log = []
        r = running(log, api_drain=instant)
        r.submit(r.token('api'), 'quick')
        res = r.shutdown(0)
        self.assertEqual(res.outcomes, (('api', 'quick', 'completed'),))
        self.assertFalse(res.deadline_exceeded)

    def test_effect_without_drain_hook_is_uncertain(self):
        log = []
        r = running(log)
        r.submit(r.token('db'), 'unknown-write')
        res = r.shutdown(5)
        self.assertEqual(res.outcomes, (('db', 'unknown-write', 'uncertain'),))

    def test_stop_failure_marks_failed_and_blocks_reboot(self):
        def broken():
            raise RuntimeError('cannot release handle')
        log = []
        r = running(log, db_stop=broken)
        res = r.shutdown(5)
        self.assertEqual(res.state, State.FAILED)
        self.assertIn('stop_failed:db:RuntimeError', res.diagnostics)
        self.assertTrue(r.component('db').failed)
        with self.assertRaises(Refused) as ctx:
            r.boot(lambda: True)
        self.assertEqual(ctx.exception.code, 'component_unrecovered')

    def test_drain_exception_marks_uncertain_and_failed(self):
        log = []
        r = running(log, api_drain=raising)
        r.submit(r.token('api'), 'write-7')
        res = r.shutdown(5)
        self.assertEqual(res.state, State.FAILED)
        self.assertEqual(res.outcomes, (('api', 'write-7', 'uncertain'),))
        self.assertIn('drain_failed:api:RuntimeError', res.diagnostics)

    def test_dispatch_refused_after_shutdown(self):
        log = []
        r = running(log)
        token = r.token('api')
        r.shutdown(5)
        with self.assertRaises(Refused) as ctx:
            r.submit(token, 'late')
        self.assertEqual(ctx.exception.code, 'dispatch_closed')

    def test_negative_deadline_rejected(self):
        log = []
        r = running(log)
        with self.assertRaises(ValueError):
            r.shutdown(-1)
        self.assertEqual(r.state, State.RUNNING)

    def test_second_shutdown_is_noop(self):
        log = []
        r = running(log)
        r.shutdown(5)
        again = r.shutdown(5)
        self.assertEqual(again.state, State.STOPPED)
        self.assertEqual(again.stop_order, ())
        self.assertEqual(log, ['stop:api', 'stop:policy', 'stop:db'])

    def test_maintenance_shutdown_starts_and_stops_nothing(self):
        log = []
        r = graph(log)
        r.boot(lambda: False)
        res = r.shutdown(5)
        self.assertEqual(res.state, State.STOPPED)
        self.assertEqual(log, [])

    def test_restart_invalidates_old_token(self):
        log = []
        r = running(log)
        old = r.token('db')
        r.shutdown(5)
        res = r.boot(lambda: True)
        self.assertEqual(res.lifecycle_generation, 2)
        with self.assertRaises(Refused) as ctx:
            r.submit(old, 'resumed')
        self.assertEqual(ctx.exception.code, 'stale_readiness')
        r.submit(r.token('db'), 'fresh')

    def test_uncertain_effect_not_replayed_on_restart(self):
        log = []
        r = running(log, api_drain=overrun)
        r.submit(r.token('api'), 'write-42')
        r.shutdown(3)
        r.boot(lambda: True)
        self.assertEqual(r.component('api').pending, {})


if __name__ == '__main__':
    unittest.main()
