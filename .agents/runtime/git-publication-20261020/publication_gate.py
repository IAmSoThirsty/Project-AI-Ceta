"""Use the installed TAAR runtime for the remaining Git publication transitions."""
from pathlib import Path
import importlib.util
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
CONTROL = R / 'control'
spec = importlib.util.spec_from_file_location('existing_phase_coordinator',
    F / '.agents/runtime/js9-root-r3-execution-20261020/phase_coordinator.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.R = CONTROL
c.RUN = 'ceta-git-publication-20261020'
c.EMPTY = CONTROL / 'read-only-workspace'


def initialize():
    CONTROL.mkdir(exist_ok=True)
    assert not (CONTROL / c.RUN).exists(), 'Existing run must not be reinitialized'
    c.EMPTY.mkdir(exist_ok=True)
    graph = dict(version=1, graph=dict(id='t_drive_repository_change',
        nodes=dict(verify_polyglot27=dict(kind='agent', role='reviewer', access='read_only')),
        override_nodes=dict(
            implement=dict(kind='agent', role='worker', access='write_scoped',
                write_scope=['00-Active/Project-AI-CETA', '00-Active/Project-AI-CETA/**']),
            integrate=dict(kind='integration', role='integrator', access='write_scoped',
                write_scope=['00-Active/Project-AI-CETA', '00-Active/Project-AI-CETA/**']),
            validate=dict(kind='gate', access='read_only', commands=[
                'git -C "{workspace}" diff --check',
                'git -C "{workspace}" diff --cached --check -- .gitattributes .gitignore'])),
        edges=[
            dict(id='git_implement_byte_review', **{'from':'implement','to':'verify_polyglot27','type':'requires_review'}),
            dict(id='git_byte_review_validate', **{'from':'verify_polyglot27','to':'validate','type':'authorizes'})]))
    text = ('# Prospective Git publication gates\n\n'
        'Scope: finalize the existing staged checkpoint, independently inspect it, validate, '
        'then commit and push the exact tree under the current user instruction. '
        'No product integration or live qualification is authorized here. '
        'The inherited T: root graph and its distinct review remain in force.\n\n'
        'Initial skill checks, read-only delegation and staging began before this run was '
        'initialized. Their preserved command evidence is not retroactive TAAR authorization. '
        'This run records the remaining prospective transitions only.\n\n```agents-graph\n'
        + json.dumps(graph, indent=2) + '\n```\n')
    path = CONTROL / 'AGENTS.md'
    if path.exists():
        assert path.read_text(encoding='utf-8') == text
    else:
        path.write_text(text, encoding='utf-8')
    argv = ['powershell','-NoProfile','-File',c.TOOL,'graph','validate','--root','T:/','--scope',str(CONTROL)]
    validation = subprocess.run(argv, cwd=F, capture_output=True)
    (CONTROL / 'graph-validate-r2.stdout').write_bytes(validation.stdout)
    (CONTROL / 'graph-validate-r2.stderr').write_bytes(validation.stderr)
    response = json.loads(validation.stdout.decode('utf-8-sig'))
    c.save(CONTROL / 'graph-validate-r2.json', dict(argv=argv,exit_status=validation.returncode,response=response))
    assert validation.returncode == 0 and response['allowed'] is True
    c.invoke('run-init', ['run','init','--root','T:/','--scope',str(CONTROL),'--run-id',c.RUN])
    for node in ('discover','plan'):
        c.claim(node, '/root', c.EMPTY)
        c.complete(node, dict(scope='Explicit user-authorized Git checkpoint publication',
            source_root=str(F), remote='git@github.com:IAmSoThirsty/Project-AI-Ceta.git',
            current_source_or_product_qualification=False, reused_existing_user_scope=True,
            prerequisites='122 skills verified; branch/HEAD/remote and existing staged tree inspected',
            prior_unregistered_operations_preserved=True),
            validations=[dict(name='exact_user_scope_and_prospective_gate_graph', passed=True)])
    c.claim('implement', '/root', F)
    print(json.dumps(dict(run_id=c.RUN, remaining_gate='finalize_stage_then_independent_reviews')))


if __name__ == '__main__':
    initialize()
