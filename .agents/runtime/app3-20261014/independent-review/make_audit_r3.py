from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
source = R / "audit_joined_cut_r2.py"
text = source.read_text(encoding="utf-8")
old = 'producer["value"]["result"]["manifest_sha256"]'
new = 'producer["value"]["result"]["transfer_manifest_sha256"]'
assert text.count(old) == 1
text = text.replace(old, new)
target = R / "audit_joined_cut_r3.py"
with target.open("x", encoding="utf-8") as stream:
    stream.write(text)
print(json.dumps({"r2_audit_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "r3_audit_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "change": "Use exact inspected transfer_manifest_sha256 producer field for both RS3 and RD2; reviewer field remains manifest_sha256"}))
