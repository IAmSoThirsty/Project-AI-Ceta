"""Use the actual installed review transitions, preserving every command result."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys

V = Path(__file__).resolve().parent
R, F = V.parent, V.parents[3]
Q, RUN = F / ".agents/gd2-20261014", "gd2-20261014"
mode = sys.argv[1]
assert hashlib.sha256((Q / "TRANSFER-MANIFEST.json").read_bytes()).hexdigest() == "cd51569eedb171f822defce05a21b53ad79ca2005e51a9c0ac253564b3088d8a"
assert hashlib.sha256((R / "implement.json").read_bytes()).hexdigest() == "7f76cf5e45dd8726bbf66bbfb398651205a277bf7aa52141a3cbd688027ce98a"
if mode == "claim":
    args = ["node", "claim", RUN, "review", "--executor", "/root/pressure_writer", "--workspace", str(Q)]
elif mode == "complete":
    args = ["node", "complete", RUN, "review", str(V / "review.json")]
else:
    raise ValueError(mode)
command = ["powershell.exe", "-NoProfile", "-File", r"T:\02-Config\agents\taar-orchestrate.ps1", *args, "--runtime-root", str(R)]
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(command, cwd=r"T:\00-Active", capture_output=True)
for suffix, value in (("stdout.txt", result.stdout), ("stderr.txt", result.stderr)):
    (V / (mode + "." + suffix)).open("xb").write(value)
payload = json.loads(result.stdout.decode("utf-8-sig"))
(V / (mode + ".json")).open("x", encoding="utf-8").write(json.dumps({"command": command,
    "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
    "exit_status": result.returncode, "response": payload}, indent=2) + "\n")
if mode == "claim":
    assert result.returncode == 0 and payload.get("allowed", False), payload
else:
    decision = json.loads((V / "review.json").read_text())["decision"]
    if decision == "approved":
        assert result.returncode == 0 and payload.get("allowed", False), payload
    else:
        assert payload.get("code") == "EXECUTION_FAILED" and not payload.get("allowed", False), payload
print(json.dumps({key: payload.get(key) for key in ("allowed", "code", "sequence", "states")}), flush=True)
