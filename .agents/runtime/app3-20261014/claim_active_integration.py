"""Advance the exact reviewed cut through real gate and active-source claims."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
S = R.parents[2]
Q = S / ".agents/app3-20261014"
RUN = "app3-20261014"
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
review_path = R / "independent-review/review.json"
assert sha(review_path) == "be523c8e5b765756948b4dacba5a73cea4e8738a5c838183abca7c79123b9491"
assert sha(Q / "TRANSFER-MANIFEST.json") == "491955891bd35135579fd525b312c3f7b54e727ee2be55d189eb76293606ed0b"
assert sha(S / ".agents/runtime/rs2-20261014/apply_joined_source.py") == "4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77"
state = read(R / RUN / "state.json")
assert state["nodes"]["review"]["state"] == "SUCCEEDED" and state["nodes"]["validate"]["state"] == "READY"
assert not read(R / RUN / "claims.json")
def step(label, *args):
    argv = ["powershell", "-NoProfile", "-File", r"T:\02-Config\agents\taar-orchestrate.ps1", *args,
            "--runtime-root", str(R)]
    started = datetime.now(timezone.utc).isoformat()
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (("stdout", done.stdout), ("stderr", done.stderr)):
        with (R / (label + "." + suffix)).open("xb") as stream:
            stream.write(data)
    response = json.loads(done.stdout)
    with (R / (label + ".json")).open("x", encoding="utf-8") as stream:
        json.dump({"started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
                   "argv": argv, "exit_status": done.returncode, "response": response}, stream, indent=2)
        stream.write("\n")
    assert done.returncode == 0 and response.get("allowed") is True, (label, response.get("code"), response.get("message"))
    print(json.dumps({"step": label, "allowed": True, "code": response.get("code")}), flush=True)
step("active-validate-claim", "node", "claim", RUN, "validate", "--executor", "/root", "--workspace", str(Q))
step("active-validate-gate", "node", "run-gate", RUN, "validate")
step("active-integrate-claim", "node", "claim", RUN, "integrate", "--executor", "/root", "--workspace", str(S))
claim = read(R / RUN / "claims.json")["integrate"]
assert claim["workspace"] == str(S) and claim["executor_id"] == "/root"
print(json.dumps({"state": "RUNNING", "source_root": str(S), "claimed_at": claim["claimed_at"],
                  "input_hash": claim["input_hash"], "sequence": read(R / RUN / "state.json")["sequence"]}), flush=True)
