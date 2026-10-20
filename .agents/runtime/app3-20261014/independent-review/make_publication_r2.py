from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
source = root / "verify_publication.py"
text = source.read_text(encoding="utf-8")
old = 'self.root = Path(tempfile.mkdtemp(prefix="application-owned-", dir=FIXTURES))'
new = 'self.root = Path(pub.fs.io_path(Path(tempfile.mkdtemp(prefix="application-owned-", dir=FIXTURES))))'
assert text.count(old) == 1
text = text.replace(old, new).replace("native-mechanism-r1", "native-mechanism-r2")
target = root / "verify_publication_r2.py"
with target.open("x", encoding="utf-8") as stream:
    stream.write(text)
print(json.dumps({"original_test_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "r2_test_source_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "change": "Deep synthetic application fixture root uses the already approved Windows extended-length I/O path; native/publication/source mechanism unchanged"}))
