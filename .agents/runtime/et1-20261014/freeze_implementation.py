"""Freeze only the reviewed four-path author candidate; no Source publication."""
from et_support import *
inputs = json.loads((R / 'SOURCE-INPUTS.json').read_text()); scope = inputs['eligible_paths']
cohort = json.loads((R / 'connected-r1.json').read_text())
assert cohort['tests_run'] == cohort['unique_methods'] == 385 and cohort['exit_status'] == 0
assert not cohort['failures'] and not cohort['errors'] and not cohort['skips']
assert cohort['expected_ids'] == cohort['executed_ids'] == cohort['stopped_ids']
assert cohort['candidate_before'] == cohort['candidate_after'] and len(cohort['candidate_after']) == 316
rows = {name: ordinary(Q / name) for name in sorted(cohort['candidate_after'])}
assert rows == cohort['candidate_after']
source = {name: ordinary(F / name) for name in inputs['Source290']}
assert source == inputs['Source290']
conservation = json.loads((R / 'input-conservation.json').read_text())
assert conservation['Source290_bytes_native_identities_exact'] and conservation['E3_ordinary_files_exact'] == 3601
self_review = json.loads((R / 'SELF-REVIEW.json').read_text())
measures = json.loads((R / 'implementation-measures.json').read_text())
assert measures['new_source_LOC'] == 315 and measures['new_test_LOC'] == 355 and measures['source_removed'] == 0
assert json.loads((R / 'all-source-imports.json').read_text())['count'] == 82
actions = {}
for name in scope:
    if name in source:
        preserved = R / 'Source-before-images' / name; preserved.parent.mkdir(parents=True, exist_ok=True)
        fs.write_new(preserved, fs.read_bytes(F / name)); assert sha(preserved) == source[name]['sha256']
        actions[name] = {'action': 'EXTEND', 'before': source[name], 'before_image': ordinary(preserved),
            'candidate': rows[name], 'KA1_dependency_before_image': ordinary(R / 'before-images' / name)}
    else:
        try: fs.lstat(F / name)
        except FileNotFoundError: pass
        else: raise AssertionError('Occupied Source CREATE: ' + name)
        actions[name] = {'action': 'CREATE', 'before': None, 'absence_observed_by_lstat': True, 'candidate': rows[name]}
assert sum(row['action'] == 'EXTEND' for row in actions.values()) == 1
write_new(R / 'publication-before-images.json', {'recorded_at': utc(), 'actions': actions,
    'Source290': source, 'rule': 'Only four eligible paths. transactions.py contains separately reviewed KA1 content plus the measured ET1 additive delta; Root must join that dependency explicitly, not borrow ET1 LOC for KA1.',
    'Source_application': False})
prior = [reference(R / (label + '.json')) for label in ('targeted-r1', 'targeted-r2', 'targeted-r3')]
write_new(R / 'PRIOR-FAILURES.json', {'recorded_at': utc(), 'attempts': prior,
    'classifications': {
        'targeted-r1': '4 failures/21 errors from strict8192-capacity overflow preventing the intended later seams. A separate evidence reader incorrectly used _connection is None for closure; the actual journal retains a closed connection object. Both failures preserved.',
        'targeted-r2': 'The duplicated raw native observation was removed but an exact observed8339-byte complete transaction still exceeded8192. Further redundant reference/limitation text removed without dropping native bytes or weakening bounds. All fixture stores were actually closed.',
        'targeted-r3': '33methods, one incorrect test assertion expecting an exact already-settled historical attempt retry on a read-only store to raise. Root-authorized idempotent reconciliation returns exact prior evidence with no write; corrected test requires equal result and unchanged store position.',
        'final_connected': '385unique cases passed, including unchanged4KiB overflow/8KiB positive cases, exact atomicity and real two-process crash seams.'},
    'before_images': {name: ordinary(R / 'capacity-r1-before-images' / name) for name in (
        'effect_transactions.py', 'effect_transactions_r2.py', 'run_tests.py', 'run_tests_r3.py',
        'test_owned_cpu_outcome_transactions.py', 'test_outcome_before_readonly_oracle_fix.py')},
    'first_bounded_diagnostic': reference(R / 'probe-first-failure.txt'),
    'actual_capacity_probes': [reference(path) for path in sorted(R.glob('capacity-probe-*/failure.json'))],
    'source_reader_attempt': 'One inspected nonexistent src/ceta/contracts/schemas/records.schema.json path was corrected to actual contracts/schemas/records.schema.json; no file mutation or schema-corruption claim.'})
fixture_root = Q / '.agents/fixtures'
fixtures = {}
if fixture_root.exists():
    for path in sorted(fixture_root.rglob('*')):
        if path.is_file(): fixtures[path.relative_to(Q).as_posix()] = ordinary(path)
write_new(R / 'owned-fixture-inventory.json', {'recorded_at': utc(), 'candidate_fixture_members': fixtures,
    'qualification': 'Generated disposable SQLite/recovery fixtures under this author-owned candidate only. All393 observed journals closed; actual crash children exited71/72. These artifacts are excluded from product payloads, Source publication and LOC credit.'})
support = ('et_support.py', 'bootstrap.py', 'run_tests.py', 'conserve_inputs.py', 'self_review.py', 'freeze_implementation.py')
manifest = {'schema_version': 1, 'cut': RUN, 'frozen_at': utc(), 'author': ACTOR,
    'source_root': str(F), 'candidate_root': str(Q), 'runtime_root': str(R),
    'eligible_application_paths': scope, 'application_actions': actions,
    'payload_count': 316, 'payloads': rows, 'dependency_payloads_uncredited': 312,
    'Source290_before': reference(R / 'SOURCE-INPUTS.json'), 'before_images': reference(R / 'publication-before-images.json'),
    'KA1_manifest': inputs['KA1_manifest'], 'KA1_review': inputs['KA1_distinct_review'],
    'dependency_closure': inputs['dependency_closure'], 'NOV2_reconciliation': inputs['NOV2_reconciliation'],
    'qualification': reference(R / 'connected-r1.json'), 'qualification_raw': reference(R / 'connected-r1.txt'),
    'tests': {'new_methods': 33, 'reused_mandatory_methods': 352, 'unique_methods': 385,
        'failures': 0, 'errors': 0, 'skips': 0, 'actual_journals_closed': len(cohort['fixture_stores']),
        'real_crash_exits': [71, 72], 'new_threads_remaining': []},
    'self_review': reference(R / 'SELF-REVIEW.json'), 'measures': reference(R / 'implementation-measures.json'),
    'new_source_LOC': 315, 'new_test_LOC': 355, 'source_removed': 0,
    'reused_adapted_scaffolding_runtime_generated_LOC_credit': 0,
    'imports': reference(R / 'all-source-imports.json'), 'source_modules': 82,
    'input_conservation': reference(R / 'input-conservation.json'), 'prior_failures': reference(R / 'PRIOR-FAILURES.json'),
    'owned_fixture_inventory': reference(R / 'owned-fixture-inventory.json'),
    'plan_obligations': ['RE-S4', 'RE-T24', 'RE-T26', 'RE-T27', 'RE-T28', 'RE-T31'],
    'APIs': {
        'begin_owned_cpu_attempt': '(request_wire, permit_wire, native_proof, request_context) -> OwnedCpuOutcome',
        'record_owned_cpu_outcome': '(request_wire, permit_wire, receipt_wire, observation_wire_or_None, native_proof, request_context) -> OwnedCpuOutcome',
        'recover_owned_cpu_outcome': '(request_wire, permit_wire, request_context) -> OwnedCpuOutcome',
        'captured_owner_predicate': 'require_owned_cpu_outcome_current(phase, request, consumed_permit, receipt_or_None, native_observation_or_None, native_proof, peer, original_context) -> exactlyNone; phase ATTEMPT/OUTCOME'},
    'status': 'EXECUTABLE_LIBRARY_COMPLETE_AWAITING_DISTINCT_REVIEW_AND_NATIVE_PROVIDER_INTEGRATION',
    'Source_published': False, 'runtime_activation': False, 'genuine_native_effect_invocation': False,
    'positive_native_provider': 'CONTROLLED_TEST_FIXTURES_ONLY',
    'remaining': ['Root must compose and qualify the captured retained native producer/observer/currentness/evidence provider; absent/default capability remains closed.',
        'Actual independently observed native CPU cap/restore, protected native custody/store composition and genuine authentication remain unexecuted here.',
        'Serialized reservation bounds do not guarantee SQLite page/WAL overhead, filesystem capacity or physical power-loss behavior.',
        'Consumed attempt and returned historical DTOs never authorize another dispatch; durable liability is retained and restoration requires separate authority.'],
    'review_support': {name: ordinary(R / name) for name in support},
    'reviewer_guidance': 'Claim actual READY review before acceptance. Initialize the canonical SQLite loader before discovery. run_tests.py connected executes exact385 IDs and uses only fresh owned candidate/runtime fixtures; preserve frozen payloads and all existing fixture members. All native predicates in tests are controlled. No Source/E3 edits, native effects, Hello or profile actions. Review only the four eligible paths and exact Source/KA1 before-images; dependency and generated fixture bytes are not publication targets.'}
write_new(Q / 'TRANSFER-MANIFEST.json', manifest)
write_new(R / 'HANDOFF.json', {'recorded_at': utc(), 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
    'eligible_paths': scope, 'tests': manifest['tests'], 'APIs': manifest['APIs'],
    'new_source_LOC': 315, 'new_test_LOC': 355, 'source_removed': 0,
    'Source_application': False, 'genuine_native_effect_invocation': False, 'distinct_review_required': True})
def command(script, *args):
    return {'command': subprocess.list2cmdline([str(PY), '-B', '-X', 'utf8', str(R / script), *args]), 'exit_status': 0}
complete('implement', {'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'handoff': reference(R / 'HANDOFF.json'),
    'qualification': manifest['qualification'], 'prior_failures': manifest['prior_failures'],
    'new_source_LOC': 315, 'new_test_LOC': 355, 'source_removed': 0,
    'Source_application': False, 'genuine_native_effect_invocation': False,
    'native_outcome_provider': 'UNQUALIFIED_PENDING_ROOT_COMPOSITION'},
    [command('run_tests.py', 'connected-r1', 'connected'), command('conserve_inputs.py'), command('self_review.py')],
    [('385exact unique final methods pass with zero failures/errors/skips and393closed actual journals', True),
     ('Same journal atomic attempt/receipt/observation/settlement; exact consumed intent and charged liability preserved', True),
     ('Strict native-proof/default denial, capacity rollback, concurrency, two real crash exits and read-only recovery verified', True),
     ('Source290 and3601 E3 ordinary bytes/native identities/membership conserved; no native effect invoked', True),
     ('Only four application paths eligible; native integration and product activation remain explicitly unqualified', True)])
print(json.dumps({'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'implement': reference(R / 'implement.json'),
    'payloads': 316, 'tests': 385, 'new_source_LOC': 315, 'new_test_LOC': 355}))
