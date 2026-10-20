"""Owned client executes native validation outside the operator/UI call stack."""
from pathlib import Path
import hashlib
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ceta.contracts.kernel_transactions import require
from ceta.contracts.wire import ContractError, MAX_WIRE_BYTES, RecordCodec, canonical_bytes, strict_loads
from ceta.identity.windows_pipe import WindowsServerBinding, send_pipe_request


def emit(value):
    wire = canonical_bytes(value)
    require(len(wire) <= 4096, "CONTROL_MESSAGE_TOO_LARGE")
    sys.stdout.buffer.write(wire + b"\n"); sys.stdout.buffer.flush()


def main():
    require(len(sys.argv) == 2, "CLIENT_SPOOL_REQUIRED")
    spool = Path(sys.argv[1])
    require(spool.is_absolute() and spool.resolve(strict=True).is_relative_to(ROOT / ".agents/fixtures"),
            "CLIENT_DEVELOPMENT_ROOT_REQUIRED")
    codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
    emit({"event": "ready", "pid": os.getpid()})
    while True:
        line = sys.stdin.buffer.readline(4097)
        if not line: return 0
        require(len(line) <= 4096 and line.endswith(b"\n"), "CONTROL_MESSAGE_TOO_LARGE")
        command = strict_loads(line[:-1])
        require(type(command) is dict and set(command) == {"profile", "attempt", "request_sha256",
            "pipe", "server_pid", "server_creation", "server_image", "timeout_ms"}
            and command["profile"] == "ceta-owned-call-v1"
            and type(command["attempt"]) is str and re.fullmatch(r"[0-9a-f]{32}", command["attempt"]),
            "CLIENT_CONTROL_INVALID")
        require(type(command["timeout_ms"]) is int and 1 <= command["timeout_ms"] <= 10000,
                "CLIENT_CONTROL_TIMEOUT_INVALID")
        attempt = command["attempt"]
        request_path, response_path = spool / (attempt + ".request.json"), spool / (attempt + ".response.json")
        # Paths remain in the validated private spool. Windows extended
        # spelling supports the current destination without changing guards.
        request_io_path, response_io_path = (
            Path("\\\\?\\" + str(path)) if sys.platform == "win32" else path
            for path in (request_path, response_path))
        binding = None
        try:
            require(not request_io_path.is_symlink() and not request_io_path.is_junction(), "CLIENT_REQUEST_LINK_REJECTED")
            with request_io_path.open("rb") as stream: wire = stream.read(MAX_WIRE_BYTES + 1)
            require(1 <= len(wire) <= MAX_WIRE_BYTES and hashlib.sha256(wire).hexdigest() == command["request_sha256"],
                    "CLIENT_REQUEST_BINDING")
            binding = WindowsServerBinding(command["server_pid"], expected_creation_time=command["server_creation"],
                                           expected_image_sha256=command["server_image"])
            response = send_pipe_request(command["pipe"], wire, codec, command["timeout_ms"] / 1000,
                                         expected_server=binding)
            with response_io_path.open("xb") as stream: stream.write(response.original_response)
            emit({"event": "call_result", "attempt": attempt,
                  "response_sha256": hashlib.sha256(response.original_response).hexdigest()})
        except (ContractError, OSError) as error:
            code = error.code if type(error) is ContractError else "CLIENT_IO_UNCERTAIN"
            safe = code if re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", code) else "TRANSPORT_UNCERTAIN"
            emit({"event": "call_uncertain", "attempt": attempt, "code": safe})
        finally:
            if binding is not None: binding.close()


if __name__ == "__main__":
    raise SystemExit(main())
