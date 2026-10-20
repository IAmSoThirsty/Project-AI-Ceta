import json
from pathlib import Path
import subprocess
import sys

F = Path(r"T:\00-Active\Project-AI-CETA")
Q, R = F / ".agents/gd1-20261014", F / ".agents/runtime/gd1-20261014"
run = "gd1-20261014"
mode, node = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None
if mode == "init":
    args = ["run", "init", "--root", "T:\\", "--scope", str(Q), "--runtime-root", str(R), "--run-id", run]
elif mode == "claim":
    args = ["node", "claim", run, node, "--executor", "/root/pressure_writer", "--workspace", str(Q), "--runtime-root", str(R)]
elif mode == "complete":
    args = ["node", "complete", run, node, str(R / (node + ".json")), "--runtime-root", str(R)]
else:
    raise ValueError(mode)
command = ["powershell.exe", "-NoProfile", "-File", r"T:\02-Config\agents\taar-orchestrate.ps1", *args]
result = subprocess.run(command, cwd=r"T:\00-Active", capture_output=True, text=True, encoding="utf-8")
stem = (node + "-" if node else "") + mode + "-output"
original_stem, attempt = stem, 1
while (R / (stem + ".txt")).exists() or (R / (stem + ".json")).exists():
    attempt += 1
    stem = original_stem + "-r" + str(attempt)
(R / (stem + ".txt")).open("x", encoding="utf-8").write(result.stdout + result.stderr)
payload = json.loads(result.stdout)
(R / (stem + ".json")).open("x", encoding="utf-8").write(json.dumps(payload, indent=2) + "\n")
assert result.returncode == 0 and payload.get("allowed", True), (result.returncode, payload)
print(json.dumps(payload))

