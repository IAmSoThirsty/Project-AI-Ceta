"""Explicit disposable development service; never a normal-profile entrypoint."""
from pathlib import Path
import base64
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ceta.composition.ipc_service import compose_duplex_kernel_service
from ceta.contracts.kernel_transactions import require
from ceta.contracts.local_ipc import OPERATIONS
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.identity.windows_pipe import WindowsPeerRegistry
from ceta.store.journal import SqliteJournal


def emit(value):
    wire = canonical_bytes(value)
    require(len(wire) <= 4096, "CONTROL_MESSAGE_TOO_LARGE")
    sys.stdout.buffer.write(wire + b"\n"); sys.stdout.buffer.flush()


def main():
    require(len(sys.argv) == 2 and len(sys.argv[1]) <= 32768, "SERVICE_CONFIGURATION_REQUIRED")
    config = strict_loads(base64.b64decode(sys.argv[1], validate=True))
    require(type(config) is dict and set(config) == {"profile", "root", "installation",
        "scopes", "create", "pipe", "client_pid", "client_creation", "client_image",
        "principal", "session"} and config["profile"] == "ceta-owned-service-v1",
        "SERVICE_CONFIGURATION_INVALID")
    root = Path(config["root"])
    require(root.is_absolute() and root.resolve(strict=True).is_relative_to(ROOT / ".agents/fixtures"),
            "SERVICE_DEVELOPMENT_ROOT_REQUIRED")
    require(type(config["create"]) is bool and type(config["scopes"]) is list and 1 <= len(config["scopes"]) <= 8
            and config["installation"] in config["scopes"], "SERVICE_CONFIGURATION_INVALID")
    codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
    registry, store, receiver = None, None, None
    try:
        # Existing journal startup validates preserved state before writer access.
        # No identity/key replacement or failure-reset path exists here.
        store = SqliteJournal(root, codec, tuple(config["scopes"]), create=config["create"], profile=STORE_PROFILE)
        registry = WindowsPeerRegistry()
        registry.register(config["client_pid"], config["principal"], config["session"],
            allowed_operations=tuple(OPERATIONS), allowed_scopes=tuple(config["scopes"]),
            expected_creation_time=config["client_creation"], expected_image_sha256=config["client_image"])
        receiver = compose_duplex_kernel_service(store, codec, config["installation"], registry, config["pipe"])
        positions = [{"scope_id": scope, "next_sequence": store.position(scope).next_sequence,
                      "head": store.position(scope).head} for scope in config["scopes"]]
        emit({"event": "ready", "pid": os.getpid(), "generation": receiver.receiver_generation,
              "positions": positions, "authority": "CLOSED"})
        while True:
            try:
                receiver.receive_once(5.0)
            except ContractError as error:
                # Transport denials are not kernel results. No unsafe exception
                # message/path is returned and no authority fallback is invoked.
                code = error.code.split(":", 1)[0]
                if code == "WINDOWS_PIPE_TIMEOUT": continue
                emit({"event": "transport_denied", "code": code if code.isidentifier() else "TRANSPORT_DENIED"})
    except ContractError as error:
        emit({"event": "startup_denied", "code": error.code.split(":", 1)[0]})
        return 2
    finally:
        if receiver is not None: receiver.close()
        if registry is not None: registry.close()
        if store is not None: store.close()


if __name__ == "__main__":
    raise SystemExit(main())
