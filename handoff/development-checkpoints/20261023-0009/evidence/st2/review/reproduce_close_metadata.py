"""Independent pure-expression check; never execute a Root closure or canonical effect."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import ast,hashlib,json
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';R=S/'review'
path=S/'control/ROOT-CLOSE.py';raw=path.read_bytes();expected='8174315abc34152ce883f9fd380735bd0688b45f2e9810895aa5ff5107a6778a'
assert hashlib.sha256(raw).hexdigest()==expected
module=ast.parse(raw);calls=[node for node in ast.walk(module) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='dict' and any(item.arg is None and isinstance(item.value,ast.Name) and item.value.id=='post' for item in node.keywords)]
assert len(calls)==1
post=dict(recorded_at='INDEPENDENT_OBSERVATION_TIMESTAMP',recorded_by='/root',reviewer='/root/status_packet_review',decision='PASS_EXACT_RECORD_APPLICATION',process_sha256='a'*64,result_sha256='b'*64)
error=None
try:eval(compile(ast.Expression(calls[0]),str(path)+':pure-metadata-expression','eval'),dict(datetime=datetime,timezone=timezone,C=S/'control',r=SimpleNamespace(s=SimpleNamespace(sha=lambda path:'c'*64)),post=post))
except TypeError as fault:error=dict(type=type(fault).__name__,message=str(fault))
assert error is not None and 'recorded_at' in error['message']
report=dict(status='REPRODUCED_BLOCKER',finding_id='ST2-CLOSE-METADATA-01',source_path=str(path),source_sha256=expected,line=calls[0].lineno,normal_independent_report_keys=list(post),failure=error,evaluated_only_one_pure_metadata_expression=True,Root_tool_executed=False,canonical_test_bodies_executed=0,canonical_or_fixture_or_Git_writes=False,repair='Use an explicit non-colliding metadata wrapper or reviewed deterministic merge preserving the original report; bind a fresh exact candidate and review it independently.',full_product_acceptance=False)
with (R/'CLOSE-METADATA-REPRODUCTION.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
