"""Relocate exact AC1 fault/fixture helpers into one fresh AC2 run child."""
from ac2_support import *
R = D = Path(os.environ['CETA_AC2_PROBE_ROOT']).resolve(strict=True)
assert R.is_relative_to(F / '.agents/runtime/ac2-20261014')

def candidate_cut():
    inputs = json.loads((F / '.agents/runtime/ac2-20261014/source-inputs.json').read_text())
    names = set(inputs['source_payloads']) | set(inputs['scope'])
    return {name: ordinary(Q / name) for name in sorted(names)}

def source_cut():
    inputs = json.loads((F / '.agents/runtime/ac2-20261014/source-inputs.json').read_text())
    return {name: ordinary(F / name) for name in inputs['source_payloads']}
