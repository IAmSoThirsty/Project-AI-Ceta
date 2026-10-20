"""Preserve the owner's exact supplied plan inside its selected repository."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os

R = Path(__file__).resolve().parent
S = R.parents[2]
source = Path(r"C:\Users\Quencher\Downloads\CETA-UNIFIED-CODE-IMPLEMENTATION-PLAN-r6.txt")
tool_path = S / ".agents/pr4-20261014/preserve_ceta_complete.py"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(tool_path) == "2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618"
spec = importlib.util.spec_from_file_location("ceta_supplied_plan_io", tool_path)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)
with fs.open_source(fs.safe_components(source), exclusive=True) as stream:
    data = stream.read()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == "e22b88a57c608a9b5711ee956a1e8909ea6efc002b39a578ea88692ddd0edf73"
    target = R / source.name
    with target.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
assert sha(target) == digest
record = {"recorded_at": datetime.now(timezone.utc).isoformat(), "source": str(source), "destination": str(target),
          "sha256": digest, "bytes": len(data), "status": "EXACT_USER_SUPPLIED_DOCUMENT_BYTES_PRESERVED",
          "authorization": "User supplied r6 and required exact implementation; subsequently required every involved source in the selected T repository",
          "source_access": "Exclusive read-only Windows handle; source is unchanged",
          "prior_failed_attempt": {"exit_status": 1, "type": "AttributeError",
          "error": "'_GeneratorContextManager' object has no attribute 'read'",
          "effects": "Only this new empty runtime directory was created; plan bytes were neither read nor copied"}}
with (R / "SOURCE.json").open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps(record))
