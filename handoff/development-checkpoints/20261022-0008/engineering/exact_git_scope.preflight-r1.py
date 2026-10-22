"""Narrow one checkpoint claim; retain every installed runtime transition check.

This is a repository-local correction, not a stock configuration or OS sandbox.
The installed runtime admits the .git workspace but expands its effective scope.
Only that result is narrowed to the explicitly compiled declarations here.
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.errors import TransitionDenied
from taar.orchestration_runtime import OrchestrationRuntime

F = Path('T:/00-Active/Project-AI-CETA').resolve()
PREFIX = '00-Active/Project-AI-CETA/.git'
CHECKPOINT_RUN = 'ceta-checkpoint-0008-publication-20261022'
REFS = ('refs/heads/development/checkpoints',
        'refs/remotes/origin/development/checkpoints',
        'logs/refs/heads/development/checkpoints',
        'logs/refs/remotes/origin/development/checkpoints')
CACHE = 'lfs/cache/locks/refs/heads/development/checkpoints/verifiable'


def validate_declarations(declared):
    fixed = {PREFIX}
    fixed.update(PREFIX + '/' + p + suffix for p in REFS for suffix in ('', '.lock'))
    fixed.update(PREFIX + '/' + CACHE + suffix for suffix in ('', '.lock'))
    # Fixed narrow temporary basenames used by index-pack. No whole-directory glob.
    temporary = {PREFIX + '/objects/pack/tmp_' + p + '_*' for p in ('pack', 'idx', 'rev')}
    if len(declared) != len(set(declared)) or not fixed <= set(declared):
        raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED', 'Missing or duplicate checkpoint declarations')
    packs = set()
    for p in declared:
        if p in fixed or p in temporary:
            continue
        match = re.fullmatch(re.escape(PREFIX) + r'/objects/pack/pack-([a-f0-9]{40})\.(pack|idx|rev)', p)
        if match is None:
            raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED', 'Unexpected Git declaration')
        packs.add((match[1], match[2]))
    if len({p for p, suffix in packs}) != 1 or {s for p, s in packs} != {'pack', 'idx', 'rev'}:
        raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED', 'Exactly one new pack identity is required')
    return list(declared)


class ExactCheckpointRuntime(OrchestrationRuntime):
    def _effective_workspace_scope(self, graph, node, workspace):
        admitted, effective = super()._effective_workspace_scope(graph, node, workspace)
        if Path(workspace).resolve() != F / '.git':
            return admitted, effective
        if (Path(graph.root).resolve() != Path('T:/').resolve()
                or graph.graph_id != 't_drive_repository_change'
                or node != graph.nodes.get('integrate')
                or node.get('kind') != 'integration'
                or node.get('role') != 'integrator'
                or node.get('access') != 'write_scoped'):
            raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED', 'Unexpected checkpoint integration binding')
        return admitted, validate_declarations(node.get('write_scope', []))

    def claim(self, run_id, node_id, executor_id, capabilities=(), workspace=None):
        if workspace is not None and Path(workspace).resolve() == F / '.git':
            if (run_id, node_id, executor_id) != (CHECKPOINT_RUN, 'integrate', '/root'):
                raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED', 'Wrong run, node, or executor')
        return super().claim(run_id, node_id, executor_id, capabilities, workspace)
