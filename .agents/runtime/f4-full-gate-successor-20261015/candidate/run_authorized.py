"""Pinned F4 engineering runner. --inspect is read-only; execution needs explicit args."""
import argparse
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import sys

import full_gate as gate

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parents[1]
Q = Path(__file__).resolve().parent
PARENT = F/'.agents/runtime/re-foundation4-20261015'
PARENT_Q = F/'.agents/re-foundation4-20261015'
PY = F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
SUPPORT_SHA = '787f858cb2007dc79253d3e6a3cf835ab11f19226c7601c0fd32a7546cc8c4eb'
ENVIRONMENT = F/'.agents/runtime/er1-20261014/independent-destination/environment-independent-after.json'


def support():
    gate.require(Path(sys.executable) == PY and os.name == 'nt' and not sys.flags.optimize, 'EXACT_E3_RUNTIME_REQUIRED')
    raw = (PARENT/'foundation_support.py').read_bytes()
    gate.require(gate.digest(raw) == SUPPORT_SHA, 'FROZEN_SUPPORT_REQUIRED')
    spec = importlib.util.spec_from_file_location('foundation_support', PARENT/'foundation_support.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    gate.require(module.sha(PARENT_Q/'TRANSFER-MANIFEST.json') == gate.PARENT_MANIFEST, 'FROZEN_F4_MANIFEST_REQUIRED')
    return module


def context(s, mode, nonce):
    gate.require(mode in ('targeted', 'destination') and type(mode) is str, 'RUN_MODE')
    gate.require(type(nonce) is str and gate.re.fullmatch('[0-9a-f]{32}', nonce) is not None, 'RUN_NONCE')
    manifest = s.read(PARENT_Q/'TRANSFER-MANIFEST.json')
    S = PARENT_Q if mode == 'targeted' else F
    try:
        current = {name:s.ordinary(S/name) for name in manifest['payloads']}
    except Exception as error:
        raise gate.GateError('EXACT_F4_336_RUNTIME_REQUIRED') from error
    gate.require(len(current) == 336 and all(row['sha256'] == manifest['payloads'][name]['candidate']['sha256']
        for name,row in current.items()), 'EXACT_F4_336_RUNTIME_REQUIRED')
    baseline = s.read(F/'.agents/runtime/ct4-20261014/ACCEPTED-SOURCE-BASELINE.json')['source_hashes']
    protected = {name:s.ordinary(F/name) for name in baseline} if mode == 'targeted' else None
    if protected is not None:
        gate.require(all(row['sha256'] == baseline[name] for name,row in protected.items()), 'CURRENT_SOURCE290_REQUIRED')
    expected_environment = s.read(ENVIRONMENT)
    environment = {}
    for row in expected_environment['members']:
        if row['kind'] == 'ordinary_file':
            name = row['relative_path']
            observed = s.ordinary(PY.parents[1]/name)
            gate.require(observed['sha256'] == row['sha256'] and observed['native_identity'] == row['native_identity'], 'E3_ENVIRONMENT_DRIFT')
            environment[name] = observed
    gate.require(len(environment) == 3601, 'EXACT_ENVIRONMENT_CENSUS_REQUIRED')
    runtime_paths = [PARENT/name for name in ('foundation_support.py','run_joined.py','complete_source.py','publish_source.py',
        'STAGED-JOIN.json','COHORT-INPUTS.json','REQUIRED-SOURCE-TESTS.json','AUXILIARY-TEST-TOOLS.json',
        'independent-review/review.json')]
    runtime_paths += [F/name for name in (
        '.agents/runtime/ac1-20261014/native_fixture_support.py',
        '.agents/runtime/ac1-20261014/build-r2/isolated_worker.exe',
        '.agents/runtime/na2-20261014/build-r1/build.json',
        '.agents/runtime/ob2-20261014/build-reuse/BUILD-REUSE.json',
        '.agents/runtime/wt1-20261014/independent-review/review_hostile.py',
        '.agents/runtime/wt2-20261014/independent-root-review/hostile_native.py',
        '.agents/runtime/wt3-20261014/independent-review/probe_known_exit.py',
        '.agents/runtime/nc3-20261015/parent-probe-primary-cleanup.py')]
    approval = s.read(F/'.agents/runtime/na2-20261014/build-r1/build.json')
    observer = s.read(F/'.agents/runtime/ob2-20261014/build-reuse/BUILD-REUSE.json')
    runtime_paths += [Path(approval['native_executable']['path']), Path(observer['native_image']['path'])]
    auxiliary = s.read(PARENT/'AUXILIARY-TEST-TOOLS.json')
    runtime_paths += [S/name for name in auxiliary['members']]
    runtime = {str(path.relative_to(F)):s.ordinary(path) for path in runtime_paths}
    tools = {name:s.ordinary(Q/name) for name in ('full_gate.py','run_authorized.py','complete_authorized.py')}
    return {'schema_version':1,'original_case_id':gate.CASE,'run_nonce':nonce,'mode':mode,
        'output_path':str(R/'runs'/nonce),'source_root':str(S),'F4_manifest_sha256':gate.PARENT_MANIFEST,
        'runtime_source_hashes_and_native_sha256':gate.digest(gate.canonical(current)),
        'protected_Source290_sha256':None if protected is None else gate.digest(gate.canonical(protected)),
        'E3_3601_ordinary_sha256':gate.digest(gate.canonical(environment)),
        'runtime_dependencies':runtime,'successor_tools':tools,'interpreter':s.ordinary(PY),
        'test_profile':'exact original denial method only; no profile create/delete; ordinary existing bounded regression fixtures',
        'authority_scope':'trusted operator engineering command; no CETA authority or activation',
        'metadata109':'unresolved and unwaived; this runner cannot accept Source'}


def capture_approval(s, stack, path, expected, *, limit=gate.MAX_RECORD_BYTES):
    path = Path(path)
    gate.require(path.is_absolute() and path.is_relative_to(F/'.agents/runtime'), 'OWNED_APPROVAL_PATH_REQUIRED')
    before = s.ordinary(path)
    gate.require(type(limit) is int and 0 < limit <= 16*1024*1024 and before['bytes'] <= limit and before['sha256'] == expected, 'APPROVAL_PIN')
    stream = stack.enter_context(s.fs.open_source(path, exclusive=True))
    descriptor = s.fs.file_identity(os.fstat(stream.fileno()))
    raw = stream.read(limit+1)
    gate.require(gate.digest(raw) == expected and s.ordinary(path) == before and
        s.fs.file_identity(os.fstat(stream.fileno())) == descriptor, 'APPROVAL_CAPTURE_DRIFT')
    # Retain this share-read-only handle for the entire invocation, denying
    # replacement/write/delete of the captured authorization on Windows.
    return gate.ApprovalCapture(raw, expected, before['native_identity'], str(path))


def write_new(s, path, value):
    path = Path(path)
    gate.require(path.is_relative_to(R), 'SUCCESSOR_OUTPUT_SCOPE')
    s.fs.safe_components(path.parent, allow_missing=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    s.fs.safe_components(path.parent)
    s.fs.write_new(path, gate.canonical(value)+b'\n')


def launch_compiled(amended, namespace):
    # No subprocess, retry, fallback or alternative interpreter. This is the
    # exact original runner executed in this already verified E3 process.
    exec(compile(amended, str(PARENT/'run_joined.py')+'#authorized-successor', 'exec'), namespace)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=('targeted','destination'))
    parser.add_argument('--run-nonce', required=True)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--partial', action='store_true')
    parser.add_argument('--approval-path', type=Path)
    parser.add_argument('--approval-sha256')
    args = parser.parse_args(argv)
    s = support()
    gate.require(R == F/'.agents/runtime/f4-full-gate-successor-20261015', 'EXACT_SUCCESSOR_ROOT')
    current = context(s, args.mode, args.run_nonce)
    raw_runner = s.fs.read_bytes(PARENT/'run_joined.py')
    amended = gate.amend_runner(raw_runner)
    supplied = args.approval_path is not None or args.approval_sha256 is not None
    gate.require(not supplied or (args.approval_path is not None and args.approval_sha256 is not None), 'COMPLETE_APPROVAL_ARGUMENTS')
    if args.inspect:
        gate.require(not supplied and not args.partial, 'INSPECT_TAKES_NO_APPROVAL')
        print(json.dumps({'subject':current,'approval_created':False,'executed':False,
            'amended_runner_sha256':gate.digest(amended.encode()),'legacy_regex_limitation':gate.LEGACY_LIMIT},indent=2))
        return 0
    gate.require(supplied != args.partial, 'EXPLICIT_FULL_AUTHORIZATION_OR_PARTIAL_REQUIRED')
    output = Path(current['output_path'])
    s.fs.safe_components(output.parent, allow_missing=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    gate.require(not output.exists(), 'FRESH_RUN_OUTPUT_REQUIRED')
    old_argv = sys.argv
    execution_gate = None
    with ExitStack() as stack:
        capture = capture_approval(s, stack, args.approval_path, args.approval_sha256) if supplied else None
        if capture is not None:
            execution_gate = gate.ExecutionGate(capture,current,snapshot=lambda:context(s,args.mode,args.run_nonce),
                write_new=lambda p,v:write_new(s,p,v),root=R)
            execution_gate.start()
        provenance = {'runner_sha256':s.sha(Path(__file__)),'gate_sha256':s.sha(Q/'full_gate.py'),
            'parent_runner_sha256':gate.PARENT_RUNNER,'amended_runner_sha256':gate.digest(amended.encode()),
            'F4_manifest_sha256':gate.PARENT_MANIFEST,'authorization_sha256':None if capture is None else capture.sha256,
            'approval_path':None if capture is None else capture.path,'approval_native_identity':None if capture is None else capture.native_identity,
            'run_nonce':args.run_nonce,'actual_argv':[str(PY),'-B','-X','utf8',str(Path(__file__)),*(argv if argv is not None else sys.argv[1:])],
            'subject':current,'legacy_regex_limitation':gate.LEGACY_LIMIT}
        namespace = {'__name__':'__main__','__file__':str(PARENT/'run_joined.py'),'__gate_output':output,
            '__gate_authorization_path':None if capture is None else Path(capture.path),
            '__gate_authorization':None if capture is None else execution_gate.record,
            '__execution_gate':execution_gate,'__gate_partial':args.partial,'__gate_select':gate.select_ids,
            '__gate_provenance':provenance}
        sys.argv = [str(PARENT/'run_joined.py'), args.mode, args.run_nonce]
        try:
            launch_compiled(amended, namespace)
        except BaseException as primary:
            # Keep the exact primary, including SystemExit(0); a reporting
            # failure may never replace it. Marker remains consumed on failure.
            if not isinstance(primary,SystemExit) or primary.code not in (None,0):
                try:
                    write_new(s,R/'attempt-failures'/(args.run_nonce+'.json'),
                        {'kind':'ENGINEERING_ATTEMPT_FAILED','authorization_sha256':provenance['authorization_sha256'],
                         'run_nonce':args.run_nonce,'primary_type':type(primary).__name__,'Source_accepted':False})
                except BaseException:
                    pass
            raise
        finally:
            sys.argv = old_argv
    return 0


if __name__ == '__main__':
    sys.exit(main())
