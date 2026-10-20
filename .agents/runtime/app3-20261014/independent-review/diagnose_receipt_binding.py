from pathlib import Path
import json

R = Path(__file__).resolve().parent
S = R.parents[3]
runtime = S / ".agents/runtime/rs3-20261014"
raw = json.loads((runtime / "independent-review/review.json").read_text())
stored = json.loads((runtime / "rs3-20261014/receipts/review.json").read_text())
stored.pop("receipt_hash", None)
differences = {key: {"raw": raw.get(key), "stored": stored.get(key)} for key in set(raw) | set(stored)
               if raw.get(key) != stored.get(key)}
with (R / "receipt-normalization-diagnosis.json").open("x", encoding="utf-8") as stream:
    json.dump(differences, stream, indent=2)
    stream.write("\n")
print(json.dumps(differences, indent=2))
