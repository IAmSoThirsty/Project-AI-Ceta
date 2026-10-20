"""Bind a narrow pure-wire performance repair to the existing reviewed chain."""
from pathlib import Path
import json
import shutil
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/er1-20261015'
P = F / '.agents/js2-20261015'
PR = F / '.agents/runtime/js2-20261015'
sys.dont_write_bytecode = True
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'


def main():
    assert len(sys.argv) == 1 and not Q.exists() and not (R / s.RUN).exists()
    assert s.sha(P / 'TRANSFER-MANIFEST.json') == 'b411c8e228199884d068d827095dfb00f33d6d3f5b4e495c9138e8925c1dee4a'
    assert s.sha(PR / 'independent-root-review/review.json') == '770b21893844e3e9bd142eff01860c3229f5f4d5a36932ee18ffa547424388db'
    joined = json.loads((PR / 'direct-integration/JOINED-SOURCE.json').read_bytes())
    assert len(joined['Source290']) == 290 and len(joined['candidate292']) == 292
    source = {name: s.ordinary(F / name) for name in joined['Source290']}
    parent = {name: s.ordinary(P / name) for name in joined['candidate292']}
    assert source == joined['Source290'] and parent == joined['candidate292']
    s.write_new(R / 'SOURCE-INPUTS.json', {'at': s.utc(), 'Source290': source,
        'parent292': parent, 'parent_manifest': s.reference(P / 'TRANSFER-MANIFEST.json'),
        'component_review': s.reference(PR / 'independent-root-review/review.json'),
        'failed_full_gate': s.reference(PR / 'direct-integration/FAILED-VALIDATION-READBACK.json'),
        'measured_codec': s.reference(R / 'CODEC-PROFILE-R1.json'),
        'authority': 'Current project engineering; Source remains290. Parent component is reviewed; complete full gate FAILED and no integration is adopted.'})
    Q.mkdir(exist_ok=False)
    s.invoke(['run', 'init', '--root', 'T:/', '--scope', str(Q), '--run-id', s.RUN], 'run-init')
    s.claim('discover')
    s.complete('discover', {'inputs': s.reference(R / 'SOURCE-INPUTS.json')},
        [{'command': 'ER1 finite Source290 and reviewed-parent292 native and byte inspection', 'exit_status': 0}],
        [('all finite inputs exact', True)])
    s.claim('plan')
    paths = ['src/ceta/contracts/wire.py', 'src/ceta/contracts/editor_recovery.py',
             'src/ceta/contracts/task_drafts.py', 'tests/contract/test_wire_scanning.py',
             'contracts/EDITOR_RECOVERY_V1.md']
    s.write_new(R / 'TASK-BINDING.json', {'at': s.utc(), 'author': '/root', 'eligible_paths': paths,
        'scope': 'Replace per-character Python scans with bounded compiled character searches; preserve exact strict JSON, depth, canonical Unicode, lowercase hex, byte limits and public interfaces.',
        'acceptance': ['Original relevant wire/editor/task tests unchanged',
            'Deterministic old/new rejection and value equivalence on escaped quotes, backslashes, structural depth and invalid text',
            'Lowercase hex type/length/alphabet rejection unchanged',
            'Same retained532455B request yields exact original/canonical bytes and commitments',
            'Separate profile measurement discloses overhead and makes no historical timeout cause claim',
            'Correct editor contract text to describe existing bounded reference/chunk route'],
        'exclusions': ['Source publication', 'authority or deadline changes', 'native workers or profiles',
                       'canonical state-store/owner changes', 'adopting failed JS2 full qualification']})
    s.complete('plan', {'binding': s.reference(R / 'TASK-BINDING.json'), 'eligible_paths': paths},
        [{'command': 'ER1 exact call sites, canonical profile and measured scan inspection', 'exit_status': 0}],
        [('narrow five-path scope and unchanged acceptance semantics', True)])
    s.claim('implement')
    for name, row in parent.items():
        target = Q / name
        s.fs.safe_components(target, missing_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(P / name, target)
        assert s.ordinary(target)['sha256'] == row['sha256']
        assert s.ordinary(P / name) == row
    s.write_new(R / 'COPIED-INPUTS.json', {'at': s.utc(), 'candidate292': {
        name: s.ordinary(Q / name) for name in parent}, 'copied_code_credit': 0,
        'Source_publication': False})
    print(json.dumps({'implement': 'RUNNING', 'candidate': str(Q), 'paths': paths,
                      'copied_payloads': 292, 'copied_code_credit': 0}))


if __name__ == '__main__':
    main()
