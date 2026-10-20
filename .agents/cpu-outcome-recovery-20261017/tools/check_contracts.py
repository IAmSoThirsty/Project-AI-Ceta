"""Exercise actual supplied record examples through the pure contract codec."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ceta.contracts import ContractError, RecordCodec, canonical_bytes, strict_loads


def main() -> int:
    codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
    results = []
    for path in sorted((ROOT / "contracts/examples").glob("*.json")):
        example = strict_loads(path.read_bytes())
        try:
            codec.decode(canonical_bytes(example["instance"]))
            actual = "ACCEPT"
        except ContractError:
            actual = "REJECT"
        results.append({"example": path.name, "expected": example["expected_shape"],
                        "actual": actual, "result": "PASS" if actual == example["expected_shape"] else "FAIL"})
    try:
        strict_loads((ROOT / "contracts/examples/duplicate_keys.wire.txt").read_bytes())
        duplicate_result = "FAIL"
    except ContractError as exc:
        duplicate_result = "PASS" if exc.code == "DUPLICATE_KEY" else "FAIL"
    passed = all(r["result"] == "PASS" for r in results) and duplicate_result == "PASS"
    print(json.dumps({"scope": "RECORD_SHAPES_ONLY", "result": "PASS" if passed else "FAIL",
                      "examples": results, "duplicate_key_rejection": duplicate_result,
                      "authority_qualification": "NOT_RUN", "system_runtime": "NOT_RUN"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
