import hashlib
import json
from pathlib import Path
import shutil

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/gd1-20261014", F / ".agents/runtime/gd1-20261014"
claim = json.loads((R / "gd1-20261014/claims.json").read_text())["implement"]
assert claim["workspace"] == str(Q) and claim["executor_id"] == "/root/pressure_writer"
assert not any(Q.iterdir())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = json.loads((R / "plan.json").read_text())["result"]["payloads"]
for item in inputs:
    relative = item["relative_path"]
    source, target, before = F / relative, Q / relative, R / "before-images" / relative
    assert sha(source) == item["sha256"], relative
    target.parent.mkdir(parents=True, exist_ok=True)
    before.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    shutil.copyfile(source, before)
    assert sha(target) == sha(before) == item["sha256"]
(R / "input-copy.json").open("x", encoding="utf-8").write(json.dumps({"payloads": inputs,
    "claim": claim, "excluded": ["virtual environments", "__pycache__", "historical ledgers", "generated runtime fixtures"]}, indent=2) + "\n")
print(json.dumps({"payload_count": len(inputs), "source": str(F), "candidate": str(Q)}))

