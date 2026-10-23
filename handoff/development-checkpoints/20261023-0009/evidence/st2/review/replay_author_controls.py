"""Independent execution of exact authored disposable controls, rebound only into review scope."""
from pathlib import Path
import ast,hashlib,json,sys
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';W=S/'work';R=S/'review'
source=W/'controls.py';raw=source.read_bytes();manifest=json.loads((W/'MANIFEST.json').read_bytes());assert hashlib.sha256(raw).hexdigest()==manifest['work_hashes']['controls.py']
tree=ast.parse(raw);assignments=[node for node in tree.body if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='ROOT'];assert len(assignments)==1
original=ast.dump(assignments[0].value,include_attributes=False);assignments[0].value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(value=str(R/'author-controls-replay-r1'))],keywords=[]);ast.fix_missing_locations(tree)
with (R/'AUTHOR-CONTROLS-REPLAY-BINDING.json').open('x',encoding='utf8') as stream:json.dump(dict(source_sha256=hashlib.sha256(raw).hexdigest(),source_path=str(source),only_AST_change='ROOT output assignment rebound to own review scope',original_assignment_AST=original,output=str(R/'author-controls-replay-r1'),independently_authored_tests=False,independent_execution=True,canonical_test_bodies_executed=0,canonical_or_fixture_or_Git_writes=False),stream,indent=2)
sys.path.insert(0,str(W));exec(compile(tree,str(source)+':review-output-rebind','exec'),dict(__name__='__main__',__file__=str(source)))
