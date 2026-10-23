"""Release only the reviewed preparation gate; canonical writes require later claims."""
from pathlib import Path
import os,sys,json
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work';RUN='ceta-st23-r2'
os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',PYTHONDONTWRITEBYTECODE='1');sys.path[:0]=[str(W),'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce']
import run_status as r
from taar.orchestration_runtime import OrchestrationRuntime
assert len(sys.argv)==3;pin,review_pin=sys.argv[1:];b,q=r.load_prepared(pin)
assert r.s.sha(S/'review/MANIFEST.json')==review_pin
review=json.loads((S/'review/REVIEW.json').read_bytes());assert review['decision']=='approved' and review['manifest_sha256']==pin
rt=OrchestrationRuntime(C);v=rt.verify(RUN);assert v['allowed'] and v['receipts_valid'] and v['states']['validate']=='READY'
a=rt.claim(RUN,'validate','/root',workspace=S/'packet');assert a['allowed'];r.s.save(C/'ROOT-validate-claim-api.json',dict(api='OrchestrationRuntime.claim',response=a))
a=rt.run_gate(RUN,'validate');r.s.save(C/'ROOT-validate-gate-api.json',dict(api='OrchestrationRuntime.run_gate',response=a));assert a['allowed'] and a['states']['validate']=='SUCCEEDED'
print(json.dumps(dict(gate='SUCCEEDED',manifest_sha256=pin,canonical_writes=False)))
