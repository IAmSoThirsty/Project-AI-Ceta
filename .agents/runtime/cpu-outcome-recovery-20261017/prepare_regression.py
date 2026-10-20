from pathlib import Path
F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
value = (F/'.agents/runtime/cpu-capacity-connection-20261017/run_regression.py').read_text(encoding='utf8')
value = value.replace('cpu-capacity-connection-20261017', 'cpu-outcome-recovery-20261017')
value = value.replace('import test_native_owner_execution as execution',
    'import test_cpu_capacity_connection as connection\nimport test_native_owner_execution as execution')
value = value.replace('outcomes.OutcomeTransactionsTests, admission.CpuExecutionAdmissionTests):',
    'outcomes.OutcomeTransactionsTests, admission.CpuExecutionAdmissionTests, connection.CapacityConnectionTests):')
value = value.replace('before = inputs()', "before = inputs()\nmanifest = json.loads((R/'cut-r2/MANIFEST.json').read_bytes())\nassert all(manifest['payload_hashes'][name] == pin for name,pin in before.items())")
value = value.replace('record = dict(at=', "record = dict(frozen_manifest=str(R/'cut-r2/MANIFEST.json'), frozen_manifest_sha256=sha(R/'cut-r2/MANIFEST.json'), at=")
with (R/'run_regression.py').open('x', encoding='utf8') as stream: stream.write(value)
print('Prepared unchanged 169-case controlled regression cohort.')
