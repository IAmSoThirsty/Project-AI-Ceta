"""Native filenames for actual disposable fixture observations on Windows."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def native_fixture_path(path):
    """Preserve logical fixture bounds and observe the exact physical file."""
    logical = Path(path)
    if not logical.is_absolute() or not logical.resolve(strict=False).is_relative_to(ROOT / ".agents/fixtures"):
        raise AssertionError("Native test I/O must stay inside this candidate's disposable fixtures")
    return Path("\\\\?\\" + str(logical)) if sys.platform == "win32" else logical
