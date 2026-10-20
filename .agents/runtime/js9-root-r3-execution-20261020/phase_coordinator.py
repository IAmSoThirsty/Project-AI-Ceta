"""Use the installed coordinator with distinct evidence, fixture and Source scopes."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
D = F / '.agents/runtime/js9-runtime-20261020/successor-r3'
Q = F / '.agents/js9-runtime-r5-20261020'
EMPTY = R / 'read-only-workspace'
RUN = 'js9-root-r3-execution-20261020'
TOOL = 'T:/02-Config/agents/taar-orchestrate.ps1'


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def invoke(label, arguments):
    argv = ['powershell', '-NoProfile', '-File', TOOL, *arguments, '--runtime-root', str(R)]
    completed = subprocess.run(argv, cwd=F, capture_output=True)
    for name, raw in (('stdout', completed.stdout), ('stderr', completed.stderr)):
        with (R / (label + '.' + name)).open('xb') as stream:
            assert stream.write(raw) == len(raw)
    response = json.loads(completed.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), dict(argv=argv, exit_status=completed.returncode, response=response))
    assert completed.returncode == 0 and response['allowed'] is True, response
    return response


def claim(node, executor, workspace):
    assert workspace.is_dir()
    invoke(node + '-ready', ['run', 'ready', RUN])
    return invoke(node + '-claim', ['node', 'claim', RUN, node, '--executor', executor,
        '--workspace', str(workspace)])


def complete(node, result, *, commands=(), validations=(), decision=None, executor='/root', exit_status=0):
    current = json.loads((R / RUN / 'claims.json').read_bytes())[node]
    assert current['executor_id'] == executor
    graph = json.loads((R / RUN / 'graph.json').read_bytes())
    sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_runtime import _snapshot_workspace, _changed_files
    changed = _changed_files(current['baseline_snapshot'],
        _snapshot_workspace(Path(current['workspace']), Path(graph['root'])))
    receipt = dict(schema_version=1, run_id=RUN, node_id=node, executor_id=executor,
        started_at=current['claimed_at'], finished_at=datetime.now(timezone.utc).isoformat(),
        input_hash=current['input_hash'], changed_files=changed, result=result,
        commands=list(commands), validations=list(validations), exit_status=exit_status)
    if decision is not None:
        receipt['decision'] = decision
    path = R / (node + '-receipt.json')
    save(path, receipt)
    return invoke(node + '-complete', ['node', 'complete', RUN, node, str(path)])


def bound_packet():
    binding = json.loads((R / 'EXECUTION-BINDING.json').read_bytes())
    raw = (D / 'PACKET.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == binding['packet_sha256']
    packet = json.loads(raw)
    assert len(packet['application_paths']) == 31 and packet['candidate_payload_count'] == 541
    return packet


def initialize(pin):
    raw = (D / 'PACKET.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pin
    save(R / 'EXECUTION-BINDING.json', dict(packet_sha256=pin, candidate=str(Q), tools=str(D),
        runtime_outside_workspaces=True, operator_permission_inherited_only_with_exact_effect_comparison=True))
    packet = bound_packet()
    EMPTY.mkdir(exist_ok=False)
    rel = lambda path: path.relative_to(F).as_posix() + '/**'
    nodes = dict(
        discover=dict(kind='agent', role='explorer', access='read_only'),
        plan=dict(kind='agent', role='architect', access='read_only'),
        implement=dict(kind='agent', role='worker', access='write_scoped', write_scope=[rel(D)]),
        candidate_fixtures=dict(kind='agent', role='worker', access='write_scoped',
            write_scope=[rel(Q / '.agents/fixtures')]),
        candidate_cache=dict(kind='agent', role='worker', access='write_scoped',
            write_scope=[rel(Q / '.local-test-output')]),
        review=dict(kind='agent', role='reviewer', access='read_only'),
        validate=dict(kind='gate', access='read_only', commands=['git -C "{workspace}" diff --check']),
        integrate=dict(kind='integration', role='integrator', access='write_scoped',
            write_scope=packet['application_paths'] + ['.local-test-output/**']),
        destination_evidence=dict(kind='agent', role='worker', access='write_scoped', write_scope=[rel(D)]),
        destination_fixtures=dict(kind='agent', role='worker', access='write_scoped',
            write_scope=['.agents/fixtures/**']))
    dependencies = [('discover', 'plan', 'depends_on')]
    dependencies += [('plan', name, 'delegates_to') for name in
        ('implement', 'candidate_fixtures', 'candidate_cache')]
    dependencies += [(name, 'review', 'requires_review') for name in
        ('implement', 'candidate_fixtures', 'candidate_cache')]
    dependencies += [('review', 'validate', 'authorizes'), ('validate', 'integrate', 'gates'),
        ('validate', 'destination_evidence', 'depends_on'),
        ('validate', 'destination_fixtures', 'depends_on')]
    graph = dict(version=1, graph=dict(id='ceta_js9_r3_execution', policy=dict(fail_closed=True,
        max_parallel=4, prohibit_scope_overlap=True, prohibit_self_review=True, require_receipts=True),
        nodes=nodes, edges=[dict(id=a + '_' + b, **{'from':a, 'to':b, 'type':kind})
            for a, b, kind in dependencies]))
    text = ('# Exact reviewed JS9 R3 execution scopes\n\n'
        'Reuse the existing product plan. Candidate and destination evidence remain separate. '
        'Fixture leases record the paths excluded from a parent workspace snapshot. '
        'Only a separate exact release admits an engineering operation.\n\n```agents-graph\n'
        + json.dumps(graph, indent=2) + '\n```\n')
    with (R / 'AGENTS.md').open('x', encoding='utf-8') as stream:
        stream.write(text)
    invoke('run-init', ['run', 'init', '--root', str(F), '--scope', str(R), '--run-id', RUN])
    for node in ('discover', 'plan'):
        claim(node, '/root', EMPTY)
        complete(node, dict(reused_established_plan=True, packet_sha256=pin,
            candidate_payload_count=541, Source_mutation=False, native_operation=False),
            validations=[dict(name='exact_successor_binding_and_dependency_scopes', passed=True)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('init', 'claim-candidate', 'claim-destination'))
    parser.add_argument('--packet-sha256')
    args = parser.parse_args()
    if args.operation == 'init':
        assert args.packet_sha256 is not None
        initialize(args.packet_sha256)
    else:
        bound_packet()
        selected = [('implement', D), ('candidate_fixtures', Q / '.agents/fixtures'),
            ('candidate_cache', Q / '.local-test-output')] if args.operation == 'claim-candidate' else [
                ('integrate', F), ('destination_fixtures', F / '.agents/fixtures')]
        if args.operation == 'claim-destination':
            selected.insert(1, ('destination_evidence', D))
        for node, workspace in selected:
            claim(node, '/root', workspace)
    print(json.dumps(dict(operation=args.operation, run_id=RUN, Source_publication=False,
        product_acceptance=False)), flush=True)


if __name__ == '__main__':
    main()
