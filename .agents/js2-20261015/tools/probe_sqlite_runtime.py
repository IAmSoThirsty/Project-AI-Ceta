"""Observe the pinned engine actually loaded by this interpreter."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ceta.store.sqlite_runtime import load_sqlite, runtime_identity

sqlite3 = load_sqlite()
connection = sqlite3.connect(":memory:")
connection.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
connection.setconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False)
report = {"result": "PASS_LOADED_PINNED_SQLITE", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
          "command": [sys.executable, "-B", "-X", "utf8", str(Path(__file__)), *sys.argv[1:]],
          "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "runtime": runtime_identity(), "source_id": connection.execute("select sqlite_source_id()").fetchone()[0],
          "defensive": connection.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE),
          "trusted_schema": connection.getconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA),
          "compile_options": [row[0] for row in connection.execute("pragma compile_options")],
          "installed_qualification": "NOT_RUN", "power_loss": "NOT_TESTED"}
connection.close()
if len(sys.argv) == 2:
    with Path(sys.argv[1]).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
print(json.dumps(report))
