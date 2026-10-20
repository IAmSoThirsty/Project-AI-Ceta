"""Bounded record framing; no peer identity, permission or dispatch is implied."""
from __future__ import annotations

from .wire import ContractError, MAX_WIRE_BYTES, ParsedRecord, RecordCodec

FRAME_PROFILE = "ceta-record-framing-v1"
HEADER_BYTES = 4


def decode_frame_length(header: bytes) -> int:
    """Validate a complete header before the transport reads/allocates its body."""
    if type(header) is not bytes:
        raise ContractError("IPC_HEADER_MUST_BE_BYTES")
    if len(header) != HEADER_BYTES:
        raise ContractError("IPC_HEADER_SIZE")
    size = int.from_bytes(header, byteorder="big", signed=False)
    if not 1 <= size <= MAX_WIRE_BYTES:
        raise ContractError("IPC_BODY_SIZE_LIMIT")
    return size


def frame_record(wire: bytes, codec: RecordCodec) -> bytes:
    """Frame validated original bytes without rewriting their evidence identity."""
    if type(wire) is not bytes:
        raise ContractError("WIRE_MUST_BE_BYTES")
    if not 1 <= len(wire) <= MAX_WIRE_BYTES:
        raise ContractError("IPC_BODY_SIZE_LIMIT")
    codec.decode(wire)
    return len(wire).to_bytes(HEADER_BYTES, byteorder="big", signed=False) + wire


def decode_record_frame(frame: bytes, codec: RecordCodec) -> ParsedRecord:
    """Decode exactly one complete frame; trailing or missing bytes are errors."""
    if type(frame) is not bytes:
        raise ContractError("IPC_FRAME_MUST_BE_BYTES")
    # Check before slicing or parsing. A caller-supplied complete buffer already
    # exists; the transport must use decode_frame_length before receiving it.
    if len(frame) > HEADER_BYTES + MAX_WIRE_BYTES:
        raise ContractError("IPC_FRAME_SIZE_LIMIT")
    size = decode_frame_length(frame[:HEADER_BYTES])
    if len(frame) - HEADER_BYTES != size:
        raise ContractError("IPC_FRAME_LENGTH")
    return codec.decode(frame[HEADER_BYTES:])
