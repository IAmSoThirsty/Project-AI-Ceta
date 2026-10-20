"""Read-only staged-blob inspection; never prints matching content."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(r"T:\00-Active\Project-AI-CETA")
parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
parser.add_argument("--expected-tree")
args = parser.parse_args()
raw = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT)
rows = []
by_blob = collections.defaultdict(list)
for item in raw.split(b"\0"):
    if not item:
        continue
    meta, path = item.split(b"\t", 1)
    mode, oid, stage = meta.decode("ascii").split()
    rel = path.decode("utf-8")
    row = {"mode": mode, "blob": oid, "stage": int(stage), "path": rel}
    rows.append(row)
    by_blob[oid].append(rel)
expected_tree_matches = None
if args.expected_tree:
    tree_raw = subprocess.check_output(["git", "ls-tree", "-r", "-z", args.expected_tree], cwd=ROOT)
    tree_map = {}
    for item in tree_raw.split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, oid = meta.decode("ascii").split()
        tree_map[path.decode("utf-8")] = (mode, oid)
    expected_tree_matches = tree_map == {row["path"]: (row["mode"], row["blob"]) for row in rows} and all(row["stage"] == 0 for row in rows)
patterns = {
    "private_key_header": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{32,255}|github_pat_[A-Za-z0-9_]{50,255})"),
    "aws_access_key": re.compile(rb"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    "slack_token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,255}"),
    "openai_token": re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{36,255}"),
    "assigned_sensitive_literal": re.compile(rb'''(?i)(?:api[_-]?key|private[_-]?key|secret[_-]?key|password|access[_-]?token)\s*[:=]\s*["']([^"'\r\n]{10,255})["']'''),
}
hits = []
over_limit = []
binary = []
sizes = {}
digests = {}
blocked_paths = []
bad_parts = {".tmp", ".venv", "venv", "site-packages", "node_modules", "target", "__pycache__", ".private", ".local-runtime", ".local-credentials", ".local-profiles", ".local-test-output", ".local-build-cache"}
for row in rows:
    path = Path(row["path"])
    if any(part in bad_parts for part in path.parts) or path.suffix.lower() in {".key", ".pem", ".p12", ".pfx", ".db", ".sqlite", ".sqlite3"}:
        blocked_paths.append(row["path"])
with subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
    for oid, paths in by_blob.items():
        child.stdin.write(oid.encode("ascii") + b"\n")
        child.stdin.flush()
        header = child.stdout.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            raise RuntimeError("Unexpected git cat-file response")
        size = int(header[2])
        data = child.stdout.read(size)
        if len(data) != size or child.stdout.read(1) != b"\n":
            raise RuntimeError("Incomplete staged blob read")
        sizes[oid] = size
        digests[oid] = hashlib.sha256(data).hexdigest()
        if size > 100 * 1024 * 1024:
            over_limit.extend(paths)
        if b"\0" in data:
            binary.extend({"path": p, "bytes": size, "sha256": digests[oid]} for p in paths)
            continue
        for line_number, line in enumerate(data.splitlines(), 1):
            for name, pattern in patterns.items():
                if pattern.search(line):
                    hits.append({"paths": paths, "line": line_number, "pattern": name, "line_sha256": hashlib.sha256(line).hexdigest()})
    child.stdin.close()
    if child.wait() != 0:
        raise RuntimeError("git cat-file failed")
index = {row["path"]: row for row in rows}
required = {}
entry_manifest = json.loads((ROOT / ".agents/runtime/real-effect-entrypoint-20261020/MANIFEST.json").read_text("utf-8"))
for rel, expected in entry_manifest["payload_hashes"].items():
    required[".agents/real-effect-entrypoint-20261020/" + rel] = expected
loader_receipt = json.loads((ROOT / ".agents/runtime/ac7-loader-capture-20261020/HALT-RECEIPT.json").read_text("utf-8"))
for rel, facts in loader_receipt["candidate_files"].items():
    required[".agents/ac7-loader-capture-20261020/" + rel] = facts["sha256"]
q5_manifest = json.loads((ROOT / ".agents/runtime/js9-runtime-20261020/successor-r3/MANIFEST-Q5.json").read_text("utf-8"))
q5 = q5_manifest["payload_hashes"]
packet = json.loads((ROOT / ".agents/runtime/js9-runtime-20261020/successor-r3/PACKET.json").read_text("utf-8"))
for rel, expected in q5.items():
    required[".agents/js9-runtime-r5-20261020/" + rel] = expected
accepted_baseline = json.loads((ROOT / ".agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json").read_text("utf-8"))
for rel, expected in accepted_baseline["effective_payload_hashes"].items():
    required[rel] = expected
required_checks = []
for rel, expected in required.items():
    row = index.get(rel)
    actual = None if row is None else digests[row["blob"]]
    required_checks.append({"path": rel, "expected_sha256": expected, "staged_sha256": actual, "matches": actual == expected})
result = {
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "index_listing_sha256": hashlib.sha256(raw).hexdigest(), "staged_path_count": len(rows),
    "expected_tree": args.expected_tree, "expected_tree_matches": expected_tree_matches,
    "index_stable_through_blob_scan": raw == subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT),
    "unique_blob_count": len(by_blob), "total_path_bytes": sum(sizes[row["blob"]] for row in rows),
    "unique_blob_bytes": sum(sizes.values()), "forbidden_path_candidates": blocked_paths,
    "over_100_MiB": over_limit, "binary_blobs": binary, "potential_secret_matches": hits,
    "required_private_candidate_checks": required_checks,
    "scope": "All stage-zero blobs in this exact Git index. Pattern scan cannot prove absence of all secrets; matches require context review. No runtime tests executed.",
}
destination = Path(args.output)
with destination.open("x", encoding="utf-8") as output:
    json.dump(result, output, indent=2)
print(json.dumps({k: v for k, v in result.items() if k not in {"potential_secret_matches", "binary_blobs", "required_private_candidate_checks"}}, indent=2))
print(json.dumps({"potential_secret_match_count": len(hits), "binary_blob_count": len(binary), "receipt": str(destination)}, indent=2))
