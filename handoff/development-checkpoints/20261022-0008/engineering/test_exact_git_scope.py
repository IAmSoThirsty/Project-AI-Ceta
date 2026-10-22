"""Regression controls for scope expansion and preserved stock denials."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import exact_git_scope as e


def declarations():
    return ([e.PREFIX] + [e.PREFIX + '/' + p + s for p in e.REFS for s in ('', '.lock')]
            + [e.PREFIX + '/' + e.CACHE + s for s in ('', '.lock')]
            + [e.PREFIX + '/objects/pack/pack-' + 'a' * 40 + '.' + s for s in ('pack', 'idx', 'rev')]
            + [e.PREFIX + '/objects/pack/tmp_' + p + '_*' for p in ('pack', 'idx', 'rev')])


class ScopeControls(unittest.TestCase):
    def setUp(self):
        self.runtime = e.ExactCheckpointRuntime(e.CONTROL_ROOT)
        self.node = dict(kind='integration', role='integrator', access='write_scoped', write_scope=declarations())
        self.graph = SimpleNamespace(root='T:/', scope=str(e.CONTROL_ROOT), graph_id='t_drive_repository_change', nodes={'integrate': self.node})

    def test_stock_broadening_reproduced_and_corrected(self):
        workspace, stock = e.OrchestrationRuntime._effective_workspace_scope(self.runtime, self.graph, self.node, e.F / '.git')
        self.assertEqual(stock, [e.PREFIX + '/**'])
        actual = self.runtime._effective_workspace_scope(self.graph, self.node, e.F / '.git')
        self.assertEqual(actual, (workspace, declarations()))

    def test_stock_outside_root_denial_retained(self):
        with self.assertRaises(e.TransitionDenied) as caught:
            self.runtime._effective_workspace_scope(self.graph, self.node, Path('C:/outside'))
        self.assertEqual(caught.exception.code, 'WORKSPACE_OUTSIDE_ROOT')

    def test_stock_outside_scope_denial_retained(self):
        self.node['write_scope'] = [e.PREFIX + '/objects/pack/pack-' + 'a' * 40 + '.pack']
        with self.assertRaises(e.TransitionDenied) as caught:
            self.runtime._effective_workspace_scope(self.graph, self.node, e.F / '.git')
        self.assertEqual(caught.exception.code, 'WORKSPACE_OUTSIDE_SCOPE')

    def test_unrelated_workspace_keeps_stock_scope(self):
        path = e.F / '.agents/runtime/example/work'
        self.node['write_scope'] = ['00-Active/Project-AI-CETA/.agents/runtime/example/work/**']
        self.assertEqual(self.runtime._effective_workspace_scope(self.graph, self.node, path)[1], self.node['write_scope'])

    def test_readonly_git_claim_not_silently_expanded(self):
        self.node['access'] = 'read_only'
        with self.assertRaises(e.TransitionDenied):
            self.runtime._effective_workspace_scope(self.graph, self.node, e.F / '.git')

    def test_unexpected_git_node_denied(self):
        for field, value in [('kind', 'agent'), ('role', 'worker')]:
            with self.subTest(field=field):
                original = self.node[field]; self.node[field] = value
                with self.assertRaises(e.TransitionDenied):
                    self.runtime._effective_workspace_scope(self.graph, self.node, e.F / '.git')
                self.node[field] = original

    def test_missing_duplicate_or_broad_declarations_refused(self):
        for scope in [declarations()[1:], declarations() + [e.PREFIX], declarations() + [e.PREFIX + '/**'],
                      declarations() + [e.PREFIX + '/objects/**'], declarations() + [e.PREFIX + '/config'],
                      declarations() + [e.PREFIX + '/lfs/**']]:
            with self.subTest(scope=scope[-1]):
                with self.assertRaises(e.TransitionDenied): e.validate_declarations(scope)

    def test_multiple_pack_identities_refused(self):
        with self.assertRaises(e.TransitionDenied):
            e.validate_declarations(declarations() + [e.PREFIX + '/objects/pack/pack-' + 'b' * 40 + '.pack'])

    def test_wrong_run_node_executor_refused_before_store_access(self):
        for values in [('other', 'integrate', '/root'), (e.CHECKPOINT_RUN, 'implement', '/root'),
                       (e.CHECKPOINT_RUN, 'integrate', '/other')]:
            with self.subTest(values=values), patch.object(e.OrchestrationRuntime, 'claim', side_effect=AssertionError('store access')):
                with self.assertRaises(e.TransitionDenied):
                    self.runtime.claim(*values, workspace=e.F / '.git')

    def test_implicit_or_unrelated_workspace_denied_before_store_access(self):
        for workspace in (None, e.F, e.F / '.git/objects'):
            with self.subTest(workspace=workspace), patch.object(e.OrchestrationRuntime, 'claim', side_effect=AssertionError('store access')):
                with self.assertRaises(e.TransitionDenied):
                    self.runtime.claim(e.CHECKPOINT_RUN, 'integrate', '/root', workspace=workspace)

    def test_alternate_runtime_or_graph_scope_denied(self):
        with patch.object(e.OrchestrationRuntime, 'claim', side_effect=AssertionError('store access')):
            other = e.ExactCheckpointRuntime(e.CONTROL_ROOT / 'other')
            with self.assertRaises(e.TransitionDenied):
                other.claim(e.CHECKPOINT_RUN, 'integrate', '/root', workspace=e.F / '.git')
        self.graph.scope = str(e.CONTROL_ROOT / 'other')
        with self.assertRaises(e.TransitionDenied):
            self.runtime._effective_workspace_scope(self.graph, self.node, e.F / '.git')


if __name__ == '__main__': unittest.main(verbosity=2)
