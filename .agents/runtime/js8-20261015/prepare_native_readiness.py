"""Bind the existing seven-case harness to the reviewed JS8 source subject."""
from foundation_support import *
import ast
import difflib
import uuid

N = R / 'native-readiness'
PARENT_R = F / '.agents/runtime/fn6-20261015'
PARENT_Q = F / '.agents/fn6-20261015'
ORIGIN = PARENT_R / 'native-readiness'
PARENT_MANIFEST_PIN = '6bd87db98906075971ecde1bd07444d28b3a957ba017cef2836cde097737eb24'
STOP_REVIEW = F / '.agents/runtime/js8-20261015-stop-review'
STOP_REVIEW_PIN = 'f693fd85bf46465d41bfa40ad073adc5cfb87eda896b663f2428fcca738bce0e'
STOP_SEAL_PIN = '8d3c7cb5d8c69abbc02a77237166fb6faf50466428d0c0769bdb9da38a28ddb0'
READY_PIN = '33f3ec54c2aa2d29af54c1708b8d0212045eab9f4842f18ffc51dadd6f27dc77'
SIX = ('readiness_support.py', 'resource_witness.py', 'run_native.py',
       'supervise_native.py', 'bounded_custody.py', 'prepare_inputs.py')
EXPECTED_ORIGIN = {
 'readiness_support.py':'cffa80fd1d600444ebb6ebf22de7eb47005fba84d64d65a873d0fd42c8b346c6',
 'resource_witness.py':'071b1402c309021fbbdf510f3755dc0b8571de7b37446ef40ba46a32926ec399',
 'run_native.py':'32b54b6eed4ff88fee55b6d1e7e76e49d19a327150d41950ba8904d1df594081',
 'supervise_native.py':'859559379fb858518d442ae77627bc244d3e1d02c81ce0806e3949a472e78829',
 'bounded_custody.py':'715b88ab286a524f5815ec3c47b987ba82cc50709272fdc467b7ddc76eeba1b4',
 'prepare_inputs.py':'9b178a4e528fc53fccbe8c3328d24d690251d80c3866b205177cf760bd57ca51'}


def replace_once(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old), count)
    return text.replace(old, new)


def main():
    assert not N.exists(), 'READINESS_SCOPE_ALREADY_EXISTS'
    assert sha(PARENT_Q / 'TRANSFER-MANIFEST.json') == PARENT_MANIFEST_PIN
    assert sha(STOP_REVIEW / 'review.json') == STOP_REVIEW_PIN
    assert sha(STOP_REVIEW / 'REVIEW-SEAL.json') == STOP_SEAL_PIN
    assert sha(R / 'STOP-TIMING-READY.json') == READY_PIN
    review = read(STOP_REVIEW / 'review.json')
    assert review['reviewer'] == '/root/history_preservation' and review['author'] == AUTHOR
    assert review['decision'] == 'approved' and type(review['exit_status']) is int and review['exit_status'] == 0
    assert review['whole_JS8_approved'] is False and review['lifecycle_transition'] is False
    parent = read(PARENT_Q / 'TRANSFER-MANIFEST.json')
    assert len(parent['payloads']) == 352
    payloads = {name: ordinary(Q / name) for name in sorted(parent['payloads'])}
    parent_facts = {name: ordinary(PARENT_Q / name) for name in sorted(parent['payloads'])}
    assert all(parent_facts[name] == row['candidate'] for name, row in parent['payloads'].items())
    differences = {name for name in payloads if payloads[name]['sha256'] != parent_facts[name]['sha256']}
    fixture = 'tests/contract/test_launcher_custody_paths.py'
    expected_changes = set(review['reviewed_payload_hashes']) | {fixture}
    assert differences == expected_changes and len(differences) == 4
    assert all(payloads[name]['sha256'] == pin for name, pin in review['reviewed_payload_hashes'].items())
    assert all(payloads[name] == row['reviewed'] for name, row in review['reviewed_files'].items())
    assert payloads[fixture]['sha256'] == '35af2c33a76b8ac44e368c9df4a36842b0f5a04fff00bc8ccb553a9e68fd5dd1'
    baseline = F / '.agents/runtime/js7-20261015/amendment-fixture1/ACCEPTED-SOURCE-BASELINE.json'
    assert sha(baseline) == 'bd7af13da30e54aa916696cb9c4dbcd32539e2600e0fdc02f8af56f63d47fbbf'
    admission = 'tests/contract/test_cpu_execution_admission.py'
    assert payloads[admission]['sha256'] == parent_facts[admission]['sha256']
    N.mkdir()
    subject = dict(schema_version=1, kind='JS8_NATIVE_SEVEN_SOURCE_SUBJECT', at=utc(),
        candidate_root=str(Q), payloads={name: dict(candidate=row) for name, row in payloads.items()},
        parent_manifest=reference(PARENT_Q / 'TRANSFER-MANIFEST.json'),
        parent_distinct_review=reference(PARENT_R / 'independent-review/review.json'),
        Stop_component_review=reference(STOP_REVIEW / 'review.json'), Stop_component_seal=reference(STOP_REVIEW / 'REVIEW-SEAL.json'),
        Stop_ready=reference(R / 'STOP-TIMING-READY.json'), accepted_Source295_baseline=reference(baseline),
        Source_baseline_binding=reference(R / 'SOURCE-BASELINE-BINDING.json'),
        parent_differences={name:dict(parent=parent_facts[name],candidate=payloads[name]) for name in sorted(differences)},
        original_seven_file=payloads[admission], product_modules=88,
        scope='Frozen source subject for independent seven-case engineering qualification; not a whole-JS8 manifest or review.',
        no_whole_JS8_approval=True, native_execution='NOT_RUN', Source_publication=False)
    write_new(N / 'SOURCE-SUBJECT.json', subject)
    subject_pin = sha(N / 'SOURCE-SUBJECT.json')
    future = Q / '.agents/fixtures' / ('js8-native-' + uuid.uuid4().hex)
    assert not future.exists()
    fs.safe_components(future, allow_missing=True)
    write_new(N / 'TASK-BINDING.json', dict(at=utc(), author=AUTHOR,
        job='Original seven native CPU qualification preparation for frozen JS8 source subject',
        writable_root=str(N), candidate_root=str(Q), manifest_sha256=subject_pin,
        manifest_semantics='SOURCE-SUBJECT.json is the separately frozen352 source map; no uncompleted JS8 author receipt is asserted.',
        future_fixture_root=str(future), future_fixture_state='ABSENT; preparation creates no candidate fixture',
        preparation_read_errors=[], native_execution='NOT_RUN', Source_publication=False,
        parent_prepared_inputs=reference(ORIGIN / 'PREPARED-INPUTS.json'),
        parent_controls=reference(ORIGIN / 'STATIC-CHECK-r1.json'),
        parent_controls_count=24, parent_controls_rerun=False,
        historical_failure_findings=reference(ORIGIN / 'ROOT-NATIVE-FINDINGS.json'),
        historical_failure_seal=reference(ORIGIN / 'FAILED-ATTEMPT-SEAL.json'),
        copied_product_LOC_credit=0,
        Root_instruction='Prepare only; exact distinct Root tool review and a fresh one-attempt release are required before native import/launch.'))
    maps = {}
    for name in SIX:
        origin = ORIGIN / name
        assert sha(origin) == EXPECTED_ORIGIN[name]
        before = origin.read_bytes()
        text = before.decode('utf8')
        if name == 'readiness_support.py':
            text = replace_once(text, 'FN6 seven-case engineering qualification inputs', 'JS8 seven-case engineering qualification inputs')
            text = replace_once(text, "Q = F / '.agents/fn6-20261015'", "Q = F / '.agents/js8-20261015'")
            text = replace_once(text, "MANIFEST_PIN = '" + PARENT_MANIFEST_PIN + "'", "MANIFEST_PIN = '" + subject_pin + "'  # Frozen native-only source subject, not whole-JS8 acceptance.")
            text = replace_once(text, 'fn6_readiness_native_reader', 'js8_readiness_native_reader')
            text = replace_once(text, "Q / 'TRANSFER-MANIFEST.json'", "N / 'SOURCE-SUBJECT.json'")
            text = text.replace('WRONG_FN6_CUT', 'WRONG_JS8_SOURCE_SUBJECT').replace('FN6_PAYLOAD_NATIVE_DRIFT', 'JS8_PAYLOAD_NATIVE_DRIFT')
            text = replace_once(text, 'FN6_SEVEN_NATIVE_ENGINEERING', 'JS8_SEVEN_NATIVE_ENGINEERING')
        elif name == 'run_native.py':
            text = replace_once(text, "startswith('fn6-native-')", "startswith('js8-native-')")
        elif name == 'prepare_inputs.py':
            text = replace_once(text, 'already-approved FN6 inputs', 'reviewed FN6 lineage and JS8 Stop repair inputs')
            text = replace_once(text, 'import struct', "import struct\nPARENT_R = F / '.agents/runtime/fn6-20261015'\nPARENT_Q = F / '.agents/fn6-20261015'\nPARENT_MANIFEST_PIN = '" + PARENT_MANIFEST_PIN + "'")
            start = text.index('def verify_actual_review():')
            end = text.index('\ndef literal_worker', start)
            original_function = text[start:end]
            adapted_function = original_function.replace('R / ', 'PARENT_R / ').replace("== MANIFEST_PIN", "== PARENT_MANIFEST_PIN")
            text = text[:start] + adapted_function + text[end:]
            text = replace_once(text, "pinned_json(Q / 'TRANSFER-MANIFEST.json', MANIFEST_PIN)", "pinned_json(N / 'SOURCE-SUBJECT.json', MANIFEST_PIN)")
            text = replace_once(text, "lineage = decode((R / 'INPUTS.json').read_bytes())", "lineage = decode((PARENT_R / 'INPUTS.json').read_bytes())")
            start = text.index('    proof_paths = {')
            end = text.index('\n    foundation = ', start)
            block = text[start:end].replace("Q / 'TRANSFER-MANIFEST.json'", "PARENT_Q / 'TRANSFER-MANIFEST.json'").replace('R / ', 'PARENT_R / ')
            block = block.replace('PARENT_PARENT_R', 'PARENT_R')
            block = block[:-5] + "        'JS8_source_subject': N / 'SOURCE-SUBJECT.json',\n        'JS8_Stop_ready': R / 'STOP-TIMING-READY.json',\n        'JS8_Stop_distinct_review': F / '.agents/runtime/js8-20261015-stop-review/review.json',\n        'JS8_Stop_distinct_seal': F / '.agents/runtime/js8-20261015-stop-review/REVIEW-SEAL.json',\n        'JS8_Source_baseline_binding': R / 'SOURCE-BASELINE-BINDING.json',\n        'JS8_parent_FN6_failed_native_findings': PARENT_R / 'native-readiness/ROOT-NATIVE-FINDINGS.json',\n        'JS8_parent_FN6_failed_native_seal': PARENT_R / 'native-readiness/FAILED-ATTEMPT-SEAL.json',\n    }"
            text = text[:start] + block + text[end:]
            text = replace_once(text, 'I authored FN6 and this readiness adaptation; the distinct FN6 component review is a prerequisite',
                'I authored FN6, the JS8 Stop repair and this adaptation; distinct FN6 and HP Stop reviews are prerequisites')
            text = replace_once(text, 'no KA2 native pass or Source acceptance transferred to FN6.', 'no parent native pass or whole-JS8/Source acceptance transferred to this cut.')
            text = replace_once(text, "startswith('fn6-native-')", "startswith('js8-native-')")
        raw = text.encode('utf8') if text != before.decode('utf8') else before
        ast.parse(raw)
        fs.write_new(N / name, raw)
        delta = ''.join(difflib.unified_diff(before.decode('utf8').splitlines(True), raw.decode('utf8').splitlines(True), fromfile=str(origin), tofile=str(N/name)))
        fs.write_new(N / (name + '.diff'), delta.encode('utf8'))
        maps[name] = dict(origin=ordinary(origin), adapted=ordinary(N / name), byte_exact=raw == before)
    write_new(N / 'MECHANICAL-ADAPTATION.json', dict(at=utc(), source_subject=reference(N / 'SOURCE-SUBJECT.json'),
        scripts=maps, changed_source_paths=sorted(differences),
        unchanged_native_methods=True, unchanged_runtime_witness_and_supervisor=True,
        controls='Parent24 retained; no repeated control campaign; compile/AST and input preparation only.',
        native_or_CETA_execution=False, product_LOC_credit=0))
    print(canonical(dict(source_subject_sha256=subject_pin, scripts=6, payloads=352, native_execution='NOT_RUN')))


if __name__ == '__main__':
    main()
