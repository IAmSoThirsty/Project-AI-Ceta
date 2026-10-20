"""Controlled local serialization occupancy; no native resource/effect."""
from pathlib import Path
import json,sys,unittest
from unittest.mock import patch
P=Path('T:/00-Active/Project-AI-CETA');Q=P/'.agents/cpb1-20261014';R=P/'.agents/runtime/cpb1-20261014'
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract'),str(P/'.agents/runtime/ka1-20261014')]
import ka1_support as s
s.Q=Q;s.R=R
import test_native_cpu_binding as fixture
module=fixture.module
class ReturnOccupancy(unittest.TestCase):
    def test_post_measurement_serialization_time_cannot_outlive_duration(self):
        host=fixture.ControlledHost();binding=host.binding();self.addCleanup(binding.close)
        capture=binding.capture();request=fixture.request(capture,duration=5_000_000)
        canonical=module.canonical_bytes;calls=[]
        def delayed(value):
            calls.append(1);result=canonical(value)
            if len(calls)==2:host.advance(20_000_000)
            return result
        with patch.object(module,'canonical_bytes',delayed):
            with self.assertRaises(fixture.ContractError):binding.driver_arguments(capture,request)
label=sys.argv[1]
with (R/(label+'.txt')).open('x',encoding='utf-8') as raw:
    result=unittest.TextTestRunner(stream=raw,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReturnOccupancy))
s.write_new(R/(label+'.json'),dict(recorded_at=s.utc(),tests_run=result.testsRun,
    failures=[dict(test=t.id(),traceback=body) for t,body in result.failures],errors=[dict(test=t.id(),traceback=body) for t,body in result.errors],
    skips=result.skipped,source=s.ordinary(Q/'src/ceta/effects/native_cpu_binding.py'),raw=s.reference(R/(label+'.txt')),
    fixture='Controlled three-domain host;20ms serialization occupancy against5ms requested duration; no native resources.',
    exit_status=0 if result.wasSuccessful() else 1))
print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),exit_status=0 if result.wasSuccessful() else 1)),flush=True)
sys.exit(0 if result.wasSuccessful() else 1)
