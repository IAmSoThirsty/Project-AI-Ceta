from pathlib import Path
F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
original = (F/'.agents/runtime/cpu-capacity-connection-20261017/run_controlled.py').read_text(encoding='utf8')
value = original.replace('cpu-capacity-connection-20261017', 'cpu-outcome-recovery-20261017')
value = value.replace('import test_cpu_capacity_connection as tests', 'import test_cpu_outcome_recovery as tests')
value = value.replace('tests.preparation.FIXTURES', 'tests.base.preparation.FIXTURES')
value = value.replace('tests.admission.authority.ROOT', 'tests.base.admission.authority.ROOT')
value = value.replace('tests.CapacityConnectionTests', 'tests.CpuOutcomeRecoveryTests')
value = value.replace('before = inputs()', "before = inputs()\nmanifest = json.loads((R/sys.argv[2]/'MANIFEST.json').read_bytes())\nassert all(manifest['payload_hashes'][name] == pin for name,pin in before.items())")
value = value.replace("record = dict(at=", "record = dict(frozen_manifest=str(R/sys.argv[2]/'MANIFEST.json'), frozen_manifest_sha256=sha(R/sys.argv[2]/'MANIFEST.json'), at=")
with (R/'run_controlled.py').open('x', encoding='utf8') as stream: stream.write(value)
print('Prepared controlled-only runner; native processes and effects blocked.')
