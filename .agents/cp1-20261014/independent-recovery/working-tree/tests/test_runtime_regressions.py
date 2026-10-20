# Regression tests for hostile-review findings H-04 (forgeable readiness token) and H-05 (dependency name types) in Subsystem 00.
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from ceta.runtime.lifecycle import Component, ManualClock, Refused, Runtime, State, Token  # noqa: E402


def booted(names=('db',)):
    r = Runtime(ManualClock())
    for n in names:
        r.register(n)
    res = r.boot(lambda: True)
    assert res.state is State.RUNNING
    return r


class H04ForgedTokenTests(unittest.TestCase):
    def test_positive_issued_token_is_accepted(self):
        r = booted()
        r.submit(r.token('db'), 'write-1')
        self.assertEqual(set(r.component('db').pending), {'write-1'})

    def test_negative_plain_tuple_is_refused_as_forged(self):
        r = booted()
        with self.assertRaises(Refused) as ctx:
            r.submit(('db', r.component('db').generation), 'forged-1')
        self.assertEqual(ctx.exception.code, 'forged_token')
        self.assertEqual(r.component('db').pending, {})

    def test_negative_token_with_altered_name_is_refused(self):
        r = booted(('db', 'policy'))
        genuine = r.token('db')
        forged = Token('policy', genuine.generation, genuine.mac)
        with self.assertRaises(Refused) as ctx:
            r.submit(forged, 'forged-2')
        self.assertEqual(ctx.exception.code, 'forged_token')
        self.assertEqual(r.component('policy').pending, {})

    def test_negative_token_with_altered_generation_is_refused(self):
        r = booted()
        genuine = r.token('db')
        forged = Token('db', genuine.generation + 1, genuine.mac)
        with self.assertRaises(Refused) as ctx:
            r.submit(forged, 'forged-3')
        self.assertEqual(ctx.exception.code, 'forged_token')

    def test_negative_token_from_another_runtime_is_refused(self):
        r1 = booted()
        r2 = booted()
        with self.assertRaises(Refused) as ctx:
            r2.submit(r1.token('db'), 'cross-runtime')
        self.assertEqual(ctx.exception.code, 'forged_token')
        self.assertEqual(r2.component('db').pending, {})

    def test_negative_malformed_mac_is_refused(self):
        r = booted()
        genuine = r.token('db')
        with self.assertRaises(Refused) as ctx:
            r.submit(Token('db', genuine.generation, 'not-bytes'), 'forged-4')
        self.assertEqual(ctx.exception.code, 'forged_token')

    def test_recovery_refused_forgery_does_not_block_genuine_token(self):
        r = booted()
        with self.assertRaises(Refused):
            r.submit(('db', 1), 'forged-5')
        r.submit(r.token('db'), 'genuine-after-forgery')
        self.assertEqual(set(r.component('db').pending), {'genuine-after-forgery'})

    def test_boundary_restart_invalidates_previously_issued_token(self):
        r = booted()
        old = r.token('db')
        r.shutdown(0)
        r.boot(lambda: True)
        with self.assertRaises(Refused) as ctx:
            r.submit(old, 'stale')
        self.assertEqual(ctx.exception.code, 'stale_readiness')


class H05DependencyTypeTests(unittest.TestCase):
    def assert_rejected(self, depends, exc_type):
        r = Runtime(ManualClock())
        with self.assertRaises(exc_type):
            r.register('api', depends=depends)
        with self.assertRaises(KeyError):
            r.component('api')

    def test_negative_non_string_dependency_rejected(self):
        self.assert_rejected((42,), TypeError)

    def test_negative_none_dependency_rejected(self):
        self.assert_rejected((None,), TypeError)

    def test_boundary_empty_string_dependency_rejected(self):
        self.assert_rejected(('',), ValueError)

    def test_negative_bare_string_depends_rejected(self):
        self.assert_rejected('db', TypeError)

    def test_recovery_name_reusable_after_rejected_registration(self):
        r = Runtime(ManualClock())
        with self.assertRaises(TypeError):
            r.register('api', depends=(7,))
        r.register('db')
        r.register('api', depends=('db',))
        self.assertEqual(r.boot(lambda: True).state, State.RUNNING)

    def test_positive_valid_text_dependencies_accepted(self):
        c = Component('api', depends=('db', 'policy'))
        self.assertEqual(c.depends, ('db', 'policy'))


if __name__ == '__main__':
    unittest.main()
