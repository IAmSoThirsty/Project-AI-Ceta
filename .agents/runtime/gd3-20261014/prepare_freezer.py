"""Reuse the exact GD2 validation machinery with explicit immediate-parent facts."""
import hashlib
from pathlib import Path

R = Path(__file__).resolve().parent
F = R.parents[2]
prior = F / '.agents/runtime/gd2-20261014/freeze_candidate.py'
text = prior.read_text().replace("F, RUN = R.parents[2], 'gd2-20261014'", "F, RUN = R.parents[2], 'gd3-20261014'")
text = text.replace("00-Active/Project-AI-CETA/.agents/gd2-20261014/", "00-Active/Project-AI-CETA/.agents/gd3-20261014/")
insert = '''LAST = F / '.agents/gd2-20261014'
LASTR = F / '.agents/runtime/gd2-20261014'
assert sha(LAST / 'TRANSFER-MANIFEST.json') == 'cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a'
last_manifest = read(LAST / 'TRANSFER-MANIFEST.json')
last_rows = {row['relative_path']: row for row in last_manifest['payloads']}
assert len(last_rows) == 281
last_state = read(LASTR / 'gd2-20261014/state.json')
assert last_state['nodes']['review']['state'] == 'FAILED' and last_state['sequence'] == 9
assert read(LASTR / 'gd2-20261014/claims.json') == {}
last_review = read(LASTR / 'independent-review/review.json')
assert last_review['decision'] == 'rejected' and last_review['exit_status'] == 1
'''
marker = "assert sha(BASE / 'TRANSFER-MANIFEST.json')"
assert marker in text
text = text.replace(marker, insert + '\n' + marker, 1)
text = text.replace("assert sha(R / 'originals' / relative) == row['candidate_sha256'] == sha(BASE / relative)",
                    "assert sha(BASE / relative) == row['candidate_sha256']\n    assert sha(R / 'originals' / relative) == last_rows[relative]['candidate_sha256'] == sha(LAST / relative)")
text = text.replace("read(R / 'hostile-baseline-r1.json')", "read(LASTR / 'hostile-baseline-r1.json')")
text = text.replace("ref(R / 'hostile-baseline-r1.json')", "ref(LASTR / 'hostile-baseline-r1.json')")
text = text.replace("'minimal_successor_source_LOC': root_delta, 'new_test_meaningful_LOC': new_test_lines,", "'minimal_successor_source_LOC': {'added': 0, 'removed': 0, 'net': 0}, 'nested_validation_repair_LOC_from_GD1': root_delta, 'new_test_meaningful_LOC': new_test_lines, 'newly_authored_source_and_tests_this_successor': 0,")
text = text.replace("'test_edit_correction': ref(R / 'validation-test-correction.json'),", "'test_edit_correction': ref(R / 'validation-test-correction.json'), 'immediate_parent_rejection': ref(LASTR / 'independent-review/review.json'), 'immediate_parent_manifest': ref(LAST / 'TRANSFER-MANIFEST.json'),")
text = text.replace("job='GD2 process timing plus nested observation rejection and recovery'", "job='GD3 corrected process timing and nested validation delivery'")
text = text.replace("'new_source_LOC_this_successor': root_delta, 'new_test_LOC_this_successor': new_test_lines,", "'new_source_LOC_this_successor': {'added': 0, 'removed': 0, 'net': 0}, 'new_test_LOC_this_successor': 0, 'first_integration_root_nested_test_LOC': new_test_lines,")
text = text.replace("successor_new_test_LOC=new_test_lines,", "successor_new_test_LOC=0, first_integration_root_nested_test_LOC=new_test_lines,")
text = text.replace("'classification': 'ROOT_TEST_CLASS_PATCH_PLACEMENT_CORRECTED_BEFORE_RUN'", "'classification': 'ROOT_TWO_REUSED_MISPLACED_OBSERVATION_LINES_REMOVED_WITHOUT_FUNCTIONAL_CHANGE'")
text = text.replace("tofile='GD2/'", "tofile='GD3/'")
assert 'assert len(snapshot) == len(changed) == 282' in text
target = R / 'freeze_candidate.py'
compile(text, str(target), 'exec')
with target.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
print(hashlib.sha256(target.read_bytes()).hexdigest())
