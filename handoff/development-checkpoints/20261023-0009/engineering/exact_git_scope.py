"""One later checkpoint9 Git claim; stock admission runs before exact narrowing."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path
import json,re,sys
import checkpoint_core as c
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar.errors import TransitionDenied
from taar.orchestration_runtime import OrchestrationRuntime

CONTROL=c.P/'publication-control';PACKET=c.P/'publication-packet/INPUTS.json';PREFIX='00-Active/Project-AI-CETA/.git'
REFS=('refs/heads/development/checkpoints','refs/remotes/origin/development/checkpoints','logs/refs/heads/development/checkpoints','logs/refs/remotes/origin/development/checkpoints')
CACHE='lfs/cache/locks/refs/heads/development/checkpoints/verifiable'

def scope_paths(pack_id):
    if type(pack_id) is not str or re.fullmatch('[a-f0-9]{40}',pack_id) is None:raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED','Invalid new pack identity')
    return ([PREFIX]+[PREFIX+'/'+name+suffix for name in REFS for suffix in ('','.lock')]+[PREFIX+'/'+CACHE+suffix for suffix in ('','.lock')]+[PREFIX+'/objects/pack/pack-'+pack_id+'.'+suffix for suffix in ('pack','idx','rev')]+[PREFIX+'/objects/pack/tmp_'+suffix+'_*' for suffix in ('pack','idx','rev')])

def validate_declarations(declared,pack_id):
    expected=scope_paths(pack_id)
    if type(declared) is not list or len(declared)!=17 or len(set(declared))!=17 or set(declared)!=set(expected):raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED','Exactly17 Git declarations required; no unrelated metadata')
    return declared

def packet(expected_sha):
    raw,pin=c.stable(PACKET)
    if pin['sha256']!=expected_sha:raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED','Publication packet drift')
    value=json.loads(raw)
    if value['run_id']!=c.PUBLICATION_RUN or value['preparation_run']!=c.RUN or value['parent']!=c.PARENT or value['ref']!=c.REF or value['origin']!=c.ORIGIN:raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED','Wrong publication identity')
    validate_declarations(value['git_scope'],value['pack_id']);return value

class ExactCheckpointRuntime(OrchestrationRuntime):
    def __init__(self,runtime_root,packet_sha256):
        super().__init__(runtime_root);self.packet_sha256=packet_sha256
    def _effective_workspace_scope(self,graph,node,workspace):
        admitted,effective=super()._effective_workspace_scope(graph,node,workspace)
        if Path(workspace).resolve()!=c.F/'.git':return admitted,effective
        value=packet(self.packet_sha256)
        if (Path(graph.root).resolve()!=Path('T:/').resolve() or Path(graph.scope).resolve()!=CONTROL.resolve() or self.runtime_root!=CONTROL.resolve() or graph.graph_id!='t_drive_repository_change' or graph.fingerprint!=value['graph_fingerprint'] or node is not graph.nodes.get('integrate') or node.get('kind')!='integration' or node.get('role')!='integrator' or node.get('access')!='write_scoped'):raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED','Wrong graph/root/node/publication binding')
        declared=validate_declarations(node.get('write_scope'),value['pack_id'])
        if declared!=value['git_scope']:raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED','Compiled scope differs from reviewed packet')
        return admitted,declared
    def claim(self,run_id,node_id,executor_id,capabilities=(),workspace=None):
        if (run_id,node_id,executor_id)!=(c.PUBLICATION_RUN,'integrate','/root') or workspace is None or Path(workspace).resolve()!=c.F/'.git' or self.runtime_root!=CONTROL.resolve():raise TransitionDenied('EXACT_GIT_SCOPE_REQUIRED','Wrong run/node/executor/explicit workspace/runtime root')
        packet(self.packet_sha256)
        return super().claim(run_id,node_id,executor_id,capabilities,workspace)
