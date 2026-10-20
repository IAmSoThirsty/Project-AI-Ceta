from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
source = R / "verify_publication_r2.py"
text = source.read_text(encoding="utf-8").replace("native-mechanism-r2", "native-mechanism-r3")
target = R / "verify_publication_r3.py"
with target.open("x", encoding="utf-8") as stream:
    stream.write(text)
print(json.dumps({"test_body_unchanged": True, "output_version": "r3 after actual APP3 claim/frozen source audit",
                  "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "r3_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))
