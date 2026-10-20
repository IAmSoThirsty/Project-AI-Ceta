from ac_support import *

claim('discover')
current = source_inventory()
units = P / '.agents/cp1-20261014/independent-recovery/working-tree'
documents = [units / ('11-EXECUTION-AND-ISOLATION/11.02-EXECUTION-SANDBOX/' + name)
             for name in ('README.md', 'execution-environment-builder.file.README.md',
                          'execution-boundary-enforcer.file.README.md', 'sandbox-cleanup-controller.file.README.md')]
documents += [units / 'INTERFACE-CONTRACTS/EXECUTION/isolation-context.contract.md',
              P / 'docs/specification/21_windows_process_and_resource_enforcement.md',
              P / 'policies/POL-13_windows_containment.md',
              P / '.agents/runtime/authoritative-inputs-20261014/CETA-UNIFIED-CODE-IMPLEMENTATION-PLAN-r6.txt',
              P / '.agents/runtime/real-effect-20261014/plan-review/IMPLEMENTATION-AND-ACCEPTANCE-PLAN.md']
inputs = {'observed_at': utc(), 'source_root': str(P), 'payloads': current,
          'source_count': len(current), 'HEAD': fs.text_git(P, 'rev-parse', 'HEAD'),
          'branch': fs.text_git(P, 'branch', '--show-current'),
          'dirty_tracked': fs.text_git(P, 'status', '--porcelain=v1', '-uno'),
          'documents': [ordinary(path) for path in documents],
          'base_windows_jobs': current['src/ceta/supervisor/windows_jobs.py'],
          'source_rule': 'Endpoint cut; separately authorized ordered Root RB/PERF publications are forward cuts, never silent overlay.',
          'authority': 'Root explicit AC1 engineering/native-disposable-resource assignment; no live enrollment/approval/effect admission.',
          'effects': {'READ': 'Exact own native assets and disposable sentinel metadata/probe data only; no protected owner/other-project data',
                     'WRITE': 'New Q/R files; restrictive ACLs/mandatory labels only fresh owned native fixtures; bounded scratch writes',
                     'HOST': 'Own supervised Windows jobs/processes/pipes and disposable local network listener probes; no profiles/install/elevation/configuration'},
          'source_publication': False}
write_new(R / 'source-inputs.json', inputs)
command = subprocess.list2cmdline([sys.executable, '-B', '-X', 'utf8', str(Path(__file__))])
complete('discover', {'source_inputs': reference(R / 'source-inputs.json'), 'source_count': len(current),
                     'mapped_units': ['CETA-11.02.01', 'CETA-11.02.02', 'CETA-11.02.03']},
         [{'command': command, 'exit_status': 0}], [('Current Source/native owner and applicable inputs pinned', True)])
claim('plan')
scope = ['src/ceta/supervisor/isolated_worker.py', 'native/windows_broker/isolated_worker.rs',
         'tests/contract/test_isolated_worker.py', 'contracts/ISOLATED_WORKER_V1.md']
binding = {'run_id': RUN, 'actor': ACTOR, 'writer_role': 'R10 Tool and Execution Engineer',
           'coordinator': '/root', 'reviewer': 'Root assigns distinct actor after frozen implement release',
           'candidate': str(Q), 'runtime': str(R), 'eligible_paths': scope,
           'reuse': 'Byte-exact Source dependencies; canonical WindowsOwnedProcess/API/custody methods',
           'create': 'Explicit no-capabilities AppContainer launch, typed native token facts and fixed native probe/tests/contract',
           'requirements': ['RE-S3', 'RE-T09', 'RE-T10', 'RE-03', 'RE-04', 'RE-05', 'RE-06', 'RE-07', 'RE-08'],
           'native_fixtures': str(R / 'native-fixtures'),
           'excluded': ['Existing windows_jobs.py edits', 'Active Source/E3', 'Other repositories', 'Persistent host configuration',
                        'AppContainer profile install', 'Loopback exemption/firewall/account/elevation', 'Authority/enrollment/clock/UI'],
           'qualification': 'Actual token/SID/no capabilities/low integrity/job; allowed asset/scratch; denied sentinels/process mutation/network/listen; observed retirement.',
           'unqualified_runtime': 'Canonical positive authority and real-effect activation remain closed; this is a native library dependency.',
           'source_application': False}
write_new(R / 'TASK-BINDING.json', binding)
complete('plan', {'task_binding': reference(R / 'TASK-BINDING.json'), 'scope': scope},
         [{'command': command, 'exit_status': 0}], [('Exact CREATE/reuse/native scopes and closed activation boundary bound', True)])
owned = claim('implement')
assert owned['baseline_snapshot'] == {}
for name, row in sorted(current.items()):
    raw = fs.read_bytes(P / name); assert digest(raw) == row['sha256']
    target = Q / name; target.parent.mkdir(parents=True, exist_ok=True); fs.write_new(target, raw)
write_new(R / 'implementation-started.json', {'observed_at': utc(), 'claim': owned,
          'base_count': len(current), 'source_inputs': reference(R / 'source-inputs.json'),
          'eligible_paths': scope, 'all_staged_existing_files': 'REUSE; not eligible Source application'})
print(json.dumps({'implement_claimed': True, 'source_count': len(current), 'input_hash': owned['input_hash']}, indent=2))
