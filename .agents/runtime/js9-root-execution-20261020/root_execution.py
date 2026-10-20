"""Use the installed coordinator for this exact engineering execution phase."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
D = F / '.agents/runtime/js9-runtime-20261020/successor-r2'
EMPTY = R / 'read-only-workspace'
RUN = 'js9-root-execution-20261020'
PACKET_PIN = 'eb5f4c993a74f7b378db9b2dd10e039fadc64ebff3c31887c78393ce58157055'
TOOL = 'T:/02-Config/agents/taar-orchestrate.ps1'


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        assert stream.write(raw) == len(raw)


def invoke(label, arguments):
    argv = ['powershell', '-NoProfile', '-File', TOOL, *arguments, '--runtime-root', str(R)]
    result = subprocess.run(argv, cwd=F, capture_output=True)
    for suffix, raw in (('stdout', result.stdout), ('stderr', result.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream:
            assert stream.write(raw) == len(raw)
    response = json.loads(result.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), dict(argv=argv, exit_status=result.returncode, response=response))
    assert result.returncode == 0 and response['allowed'] is True, response
    return response


def complete(node, result, *, validations, commands=(), executor='/root'):
    current = json.loads((R / RUN / 'claims.json').read_bytes())[node]
    assert current['executor_id'] == executor
    graph = json.loads((R / RUN / 'graph.json').read_bytes())
    sys.path.insert(0, 'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
    from taar.orchestration_runtime import _snapshot_workspace, _changed_files
    changed = _changed_files(current['baseline_snapshot'],
        _snapshot_workspace(Path(current['workspace']), Path(graph['root'])))
    receipt = dict(schema_version=1, run_id=RUN, node_id=node, executor_id=executor,
        started_at=current['claimed_at'], finished_at=now(), input_hash=current['input_hash'],
        changed_files=changed, result=result, commands=list(commands),
        validations=[dict(name=name, passed=passed) for name, passed in validations], exit_status=0)
    path = R / (node + '-receipt.json')
    save(path, receipt)
    return invoke(node + '-complete', ['node', 'complete', RUN, node, str(path)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('init', 'claim-execution'))
    args = parser.parse_args()
    raw = (D / 'PACKET.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PACKET_PIN
    packet = json.loads(raw)
    assert len(packet['application_paths']) == 31
    if args.operation == 'init':
        EMPTY.mkdir(exist_ok=False)
        evidence_scope = D.relative_to(F).as_posix() + '/**'
        graph = dict(version=1, graph=dict(id='ceta_js9_root_execution',
            policy=dict(fail_closed=True, max_parallel=4, prohibit_scope_overlap=True,
                prohibit_self_review=True, require_receipts=True),
            nodes=dict(
                discover=dict(kind='agent', role='explorer', access='read_only'),
                plan=dict(kind='agent', role='architect', access='read_only'),
                implement=dict(kind='agent', role='worker', access='write_scoped', write_scope=[evidence_scope]),
                review=dict(kind='agent', role='reviewer', access='read_only'),
                validate=dict(kind='gate', access='read_only', commands=['git -C "{workspace}" diff --check']),
                integrate=dict(kind='integration', role='integrator', access='write_scoped',
                    write_scope=packet['application_paths'] + [evidence_scope])),
            edges=[dict(id=a+'_'+b, **{'from':a,'to':b,'type':kind}) for a,b,kind in (
                ('discover','plan','depends_on'), ('plan','implement','delegates_to'),
                ('implement','review','requires_review'), ('review','validate','authorizes'),
                ('validate','integrate','gates'))]))
        text = ('# Exact JS9 engineering execution lease\n\n'
                'Reuse the established r6 work and reviewed frozen tool/candidate cuts. '
                'No profile creation, retry, publication or acceptance follows from this graph alone.\n\n'
                '```agents-graph\n' + json.dumps(graph, indent=2) + '\n```\n')
        with (R / 'AGENTS.md').open('x', encoding='utf-8') as stream:
            stream.write(text)
        invoke('run-init', ['run', 'init', '--root', str(F), '--scope', str(R), '--run-id', RUN])
        for node in ('discover', 'plan'):
            invoke(node+'-ready', ['run', 'ready', RUN])
            invoke(node+'-claim', ['node', 'claim', RUN, node, '--executor', '/root', '--workspace', str(EMPTY)])
            complete(node, dict(reused_existing_plan=True, packet_sha256=PACKET_PIN,
                candidate_manifest=packet['candidate_manifest'], source_mutated=False,
                native_execution=False, phase='BOUND_EXECUTION_PREPARATION'),
                validations=[('exact_frozen_packet_and_existing_critical_path', True)])
    else:
        invoke('execution-ready', ['run', 'ready', RUN])
        result = invoke('execution-claim', ['node', 'claim', RUN, 'implement',
            '--executor', '/root', '--workspace', str(D)])
        assert result['claim']['effective_write_scope'] == [D.relative_to(F).as_posix()+'/**']
    print(json.dumps(dict(operation=args.operation, run_id=RUN, native_execution=False, source_mutated=False)))


if __name__ == '__main__':
    main()
