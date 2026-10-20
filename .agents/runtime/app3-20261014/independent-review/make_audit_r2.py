"""Preserve r1 and apply the inspected installed-runtime receipt augmentation."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
source = R / "audit_joined_cut.py"
text = source.read_text(encoding="utf-8")
old = '    assert raw == stored, (run, node, "accepted and selected receipt content differs")'
new = '''    expected_stored = dict(raw)
    # Installed orchestration_runtime.py:521-523 appends precisely these actual
    # corroborating observations before computing the accepted receipt hash.
    expected_stored["observed_git"] = stored["observed_git"]
    expected_stored["git_baseline"] = stored["git_baseline"]
    assert expected_stored == stored, (run, node, "accepted and selected receipt content differs beyond the exact runtime augmentation")'''
assert text.count(old) == 1
text = text.replace(old, new)
text = text.replace('manifest = read(manifest_path)',
                    'assert sha(manifest_path) == "491955891bd35135579fd525b312c3f7b54e727ee2be55d189eb76293606ed0b"\nmanifest = read(manifest_path)')
target = R / "audit_joined_cut_r2.py"
with target.open("x", encoding="utf-8") as stream:
    stream.write(text)
print(json.dumps({"r1_audit_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "r2_audit_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "change": "Model the two verified runtime-generated git observation fields exactly; all raw receipt content, accepted normalized hash and frozen APP3 manifest remain checked"}))
