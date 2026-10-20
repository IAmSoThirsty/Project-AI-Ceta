"""Refuse compiler drift before a locked build of the canonical reference."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "release": "1.96.1",
    "host": "x86_64-pc-windows-gnu",
    "commit-hash": "31fca3adb283cc9dfd56b49cdee9a96eb9c96ffd",
}


def require_compiler_identity(version: str) -> None:
    fields = dict(line.split(": ", 1) for line in version.splitlines() if ": " in line)
    if any(fields.get(key) != value for key, value in EXPECTED.items()):
        raise ValueError("Native compiler identity differs; reopen ADR-017 before building")


def main() -> int:
    version = subprocess.run(["rustc", "+stable-x86_64-pc-windows-gnu", "--version", "--verbose"],
                             cwd=ROOT, capture_output=True, check=True, text=True).stdout
    require_compiler_identity(version)
    print(version, flush=True)
    manifest = ROOT / "native/canonical_reference/Cargo.toml"
    for command in ("test", "build"):
        result = subprocess.run(["cargo", "+stable-x86_64-pc-windows-gnu", command,
                                 "--locked", "--manifest-path", str(manifest)], cwd=ROOT)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
