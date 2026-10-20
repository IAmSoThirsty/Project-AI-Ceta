"""Create-only FN6 preparation from the exact Root-reviewed KA5 helpers."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import uuid

N = Path(__file__).resolve().parent
R = N.parent
F = R.parents[2]
OLD = F / '.agents/runtime/ka5-20261015/native-readiness'
MANIFEST = '6bd87db98906075971ecde1bd07444d28b3a957ba017cef2836cde097737eb24'
PINS = {
    'readiness_support.py': '1c941e0692c6cc8d48cc588ddf287ef8e546eb232cfdc85233c0f67a0580dbd5',
    'resource_witness.py': '071b1402c309021fbbdf510f3755dc0b8571de7b37446ef40ba46a32926ec399',
    'run_native.py': '8056f7c3f02d276a52afb7e9b6c76866b7f2ed451a59446e4cc2de1427f87de4',
    'supervise_native.py': '0ff7afa77437a38bae396b41cdce5529e66b688a7ad55d6162a1c13706cff03e',
    'bounded_custody.py': '715b88ab286a524f5815ec3c47b987ba82cc50709272fdc467b7ddc76eeba1b4',
    'prepare_inputs.py': '960ae83516b7f40003fc3b8076b653baaee3d444e8f12f81b0be4012d7380515',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, raw):
    if isinstance(raw, str):
        raw = raw.encode('utf8')
    with (N / name).open('xb') as stream:
        stream.write(raw)


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    review_raw = (OLD / 'ROOT-REVIEW.json').read_bytes()
    reviewed = json.loads(review_raw)
    assert reviewed['decision'] == 'approved' and reviewed['exit_status'] == 0
    assert reviewed['reviewer'] == '/root' and reviewed['scripts_sha256'] == PINS
    originals = {}
    for name, pin in PINS.items():
        raw = (OLD / name).read_bytes()
        assert sha(raw) == pin, name
        originals[name] = raw
    for name in ('test_readiness_controls.py', 'test_timing_reader_controls.py'):
        originals[name] = (OLD / name).read_bytes()
    (N / 'reviewed-ka5-beforeimages').mkdir(exist_ok=False)
    for name, raw in originals.items():
        write('reviewed-ka5-beforeimages/' + name, raw)

    text = originals['readiness_support.py'].decode('utf8')
    text = text.replace('KA5', 'FN6').replace('ka5', 'fn6').replace('342', '352')
    text = text.replace('d96cae1fbddd213a2ab3d49309a5021c018db8bca57404c41712a502bcd9c3fd', MANIFEST)
    text = once(text, "REVIEW_PIN = 'ca6a2d83f5ea8ced6a10f92eaeb0c1146673d6be793b25eb5f3f24eaacbd7dfe'",
                'REVIEW_PIN = None  # Pending actual distinct FN6 approval; input freeze fails closed.')
    text = once(text, "review.get('author') == '/root/wt1_reviewer'", "review.get('author') == '/root/pressure_writer'")
    write('readiness_support.py', text)
    for name in ('resource_witness.py', 'bounded_custody.py'):
        write(name, originals[name])
    write('supervise_native.py', originals['supervise_native.py'].decode('utf8').replace('candidate342', 'candidate352'))
    text = originals['run_native.py'].decode('utf8').replace('candidate342', 'candidate352').replace('ka5-native-', 'fn6-native-')
    text = once(text, '    fixture_root.mkdir(parents=True, exist_ok=False)',
                '    fs.safe_components(fixture_root, allow_missing=True)\n    fixture_root.mkdir(parents=True, exist_ok=False)')
    write('run_native.py', text)

    text = originals['prepare_inputs.py'].decode('utf8').replace('KA5', 'FN6').replace('ka5', 'fn6').replace('342', '352')
    text = once(text, "prepared_by='/root/wt1_reviewer'", "prepared_by='/root/pressure_writer'")
    text = once(text,
        'I independently reviewed FN6 controlled code and now author this readiness adaptation; Root must independently review/release these tools. Prior WT4 authorship relies on prior distinct Root acceptance.',
        'I authored FN6 and this readiness adaptation; the distinct FN6 component review is a prerequisite, and Root must independently review/release these tools. Controlled providers are not genuine authority.')
    text = once(text, "'E3_NATIVE_DRIFT_FROM_FN6')", "'E3_NATIVE_DRIFT_FROM_FN6')\n    current_members = {p.relative_to(E3).as_posix() for p in E3.rglob('*') if p.is_file()}\n    require(current_members == set(e3_before), 'E3_ORDINARY_MEMBERSHIP_DRIFT')")
    text = once(text, "        'KA4_consumed_native_findings':", """        'FN5_rejected_manifest': F / '.agents/fn5-20261015/TRANSFER-MANIFEST.json',
        'FN5_rejected_review': F / '.agents/runtime/fn5-20261015/independent-review/review.json',
        'FN5_rejected_report': F / '.agents/runtime/fn5-20261015/independent-review/REPORT.json',
        'FN5_rejected_readback': F / '.agents/runtime/fn5-20261015/independent-review/REVIEW-READBACK.json',
        'FN5_rejected_seal': F / '.agents/runtime/fn5-20261015/independent-review/REVIEW-SEAL.json',
        'FN6_parent_failure_readback': R / 'FAILED-PARENT-READBACK.json',
        'KA5_parent_manifest': F / '.agents/ka5-20261015/TRANSFER-MANIFEST.json',
        'KA5_controlled_component_review': F / '.agents/runtime/ka5-20261015/independent-review/review.json',
        'KA5_prior_native_findings_HISTORY_ONLY': F / '.agents/runtime/ka5-20261015/native-readiness/ROOT-NATIVE-FINDINGS.json',
        'KA5_prior_native_readiness_review_HISTORY_ONLY': F / '.agents/runtime/ka5-20261015/native-readiness/ROOT-REVIEW.json',
        'KA5_prior_native_inputs_HISTORY_ONLY': F / '.agents/runtime/ka5-20261015/native-readiness/PREPARED-INPUTS.json',
        'KA4_consumed_native_findings':""")
    text = text.replace('No KA2 native pass or Source acceptance transferred to FN6.', 'No KA2 or KA5 native pass or Source acceptance transferred to FN6.')
    text = once(text, "            and not fixture.exists(), 'FUTURE_PRIVATE_FIXTURE_NOT_FRESH')",
                "            and not fixture.exists(), 'FUTURE_PRIVATE_FIXTURE_NOT_FRESH')\n    fs.safe_components(fixture, allow_missing=True)")
    write('prepare_inputs.py', text)
    text = originals['test_readiness_controls.py'].decode('utf8')
    text = text.replace('KA5_SEVEN_NATIVE_ENGINEERING', 'FN6_SEVEN_NATIVE_ENGINEERING')
    text = once(text, "author='/root/wt1_reviewer'", "author='/root/pressure_writer'")
    write('test_readiness_controls.py', text)
    write('test_timing_reader_controls.py', originals['test_timing_reader_controls.py'])
    task = dict(at=datetime.now(timezone.utc).isoformat(), author='/root/pressure_writer',
        job='FN6 original seven native qualification engineering preparation only', writable_root=str(N),
        candidate_root=str(F / '.agents/fn6-20261015'), manifest_sha256=MANIFEST,
        future_fixture_root=str(F / '.agents/fn6-20261015/.agents/fixtures' / ('fn6-native-' + uuid.uuid4().hex)),
        future_fixture_state='ABSENT; no candidate fixture directory created during preparation',
        native_execution='NOT_RUN', Source_pin=False, Source_publication=False,
        Root_instruction='Actual successful distinct FN6 review before input freeze; exact Root tool review and fresh one-attempt release before any native execution',
        independence='FN6 and preparation author /root/pressure_writer; component reviewer /root/wt1_reviewer; independent engineering reviewer and release owner /root',
        previous_native_attempts='KA4 FAILED consumed; KA5 PASSED on its different cut. Both history only; neither qualifies FN6.',
        preparation_read_errors=[], reviewed_origin=dict(path=str(OLD), review_sha256=sha(review_raw), scripts_sha256=PINS),
        copied_product_LOC_credit=0, original_controls=21, unchanged_timing_reader_controls=3)
    write('TASK-BINDING.json', json.dumps(task, indent=2) + '\n')
    for path in N.glob('*.py'):
        ast.parse(path.read_bytes())
    print(json.dumps(dict(created_scripts=len(list(N.glob('*.py'))), native_execution='NOT_RUN', review_pin='PENDING', future_fixture_root=task['future_fixture_root'])))


if __name__ == '__main__':
    main()
