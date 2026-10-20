from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/er1-20261014", F / ".agents/runtime/er1-20261014"
V = R / "independent-review"
mode = sys.argv[1]
assert hashlib.sha256((Q / "TRANSFER-MANIFEST.json").read_bytes()).hexdigest() == "7325582b9fa18972dc2e6337e66e55fa3c7ae1ee5db600824aedeca58bb73f83"
assert hashlib.sha256((R / "implement.json").read_bytes()).hexdigest() == "34b94f4d8919f2e691bfde4f6df99f090e579a9201eb38bac4a97b9403e8db8f"
if mode == "claim":
    args = ["node", "claim", "er1-20261014", "review", "--executor", "/root/pressure_writer", "--workspace", str(Q)]
elif mode == "complete":
    args = ["node", "complete", "er1-20261014", "review", str(V / "review.json")]
else: raise ValueError(mode)
command = ["powershell.exe", "-NoProfile", "-File", r"T:\02-Config\agents\taar-orchestrate.ps1", *args, "--runtime-root", str(R)]
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(command, cwd=r"T:\00-Active", capture_output=True)
for suffix, value in (("stdout.txt", result.stdout), ("stderr.txt", result.stderr)):
    (V / (mode + "." + suffix)).open("xb").write(value)
payload = json.loads(result.stdout.decode("utf-8-sig"))
(V / (mode + ".json")).open("x", encoding="utf-8").write(json.dumps({"command": command,
    "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
    "exit_status": result.returncode, "response": payload}, indent=2) + "\n")
assert result.returncode == 0 and payload.get("allowed", False), payload
if mode == "claim": print(json.dumps(payload))
else: print(json.dumps({"sequence": payload["sequence"], "states": payload["states"], "allowed": payload["allowed"]}))
