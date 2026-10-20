"""Truthful input-token observation from the existing prepared-request contract.

There is no observed response-usage producer or canonical usage ledger in this
namespace.  This module therefore measures only exact input tokenizations and
does not charge, reserve, or persist inference usage.
"""
from dataclasses import dataclass

from ceta.contracts.request_compiler import PreparedRequest
from ceta.contracts.resource_management import digest, identifier, require


@dataclass(frozen=True, slots=True)
class InputTokenMeasurement:
    request_id: str
    prepared_commitment: str
    payload_commitment: str
    runtime_digest: str
    reserved_output_tokens: int
    input_tokens: int | None
    state: str
    reason_code: str | None

    def __post_init__(self) -> None:
        identifier(self.request_id, "RESOURCE_INFERENCE_REQUEST_IDENTIFIER_INVALID")
        digest(self.prepared_commitment, "RESOURCE_INFERENCE_PREPARED_COMMITMENT_INVALID")
        digest(self.payload_commitment, "RESOURCE_INFERENCE_PAYLOAD_COMMITMENT_INVALID")
        digest(self.runtime_digest, "RESOURCE_INFERENCE_RUNTIME_DIGEST_INVALID")
        require(type(self.reserved_output_tokens) is int and self.reserved_output_tokens >= 1,
                "RESOURCE_INFERENCE_RESERVED_OUTPUT_INVALID")
        require(self.state in {"MEASURED", "UNRESOLVED"}, "RESOURCE_INFERENCE_MEASUREMENT_STATE_INVALID")
        if self.state == "MEASURED":
            require(type(self.input_tokens) is int and self.input_tokens >= 0 and self.reason_code is None,
                    "RESOURCE_INFERENCE_MEASUREMENT_INVALID")
        else:
            require(self.input_tokens is None and self.reason_code == "TOKENIZATION_NOT_EXACT",
                    "RESOURCE_INFERENCE_MEASUREMENT_INVALID")


@dataclass(frozen=True, slots=True)
class InputTokenAssessment:
    state: str
    request_id: str
    input_tokens: int | None
    reserved_output_tokens: int
    context_tokens: int
    reason_codes: tuple[str, ...]


def measure_input_tokens(prepared: PreparedRequest) -> InputTokenMeasurement:
    """Measure an exact prepared preview, pinned to its owner-selected state."""
    require(type(prepared) is PreparedRequest, "RESOURCE_INFERENCE_PREPARED_REQUEST_REQUIRED")
    state, tokenization = prepared.selection.state, prepared.tokenization
    require(tokenization.runtime == state.runtime, "RESOURCE_INFERENCE_PREPARED_RUNTIME_MISMATCH")
    bindings = (state.request_id, prepared.commitment, tokenization.payload_commitment,
                state.runtime.runtime_commitment, state.reserved_output_tokens)
    if not tokenization.exact:
        return InputTokenMeasurement(*bindings, None, "UNRESOLVED", "TOKENIZATION_NOT_EXACT")
    return InputTokenMeasurement(*bindings, len(tokenization.token_ids), "MEASURED", None)


def assess_input_context(measurement: InputTokenMeasurement, prepared: PreparedRequest) -> InputTokenAssessment:
    """Pure preview advice bound to the observed prepared record, never a charge."""
    require(type(measurement) is InputTokenMeasurement and type(prepared) is PreparedRequest,
            "RESOURCE_INFERENCE_ASSESSMENT_INPUT_INVALID")
    state, tokenization = prepared.selection.state, prepared.tokenization
    reserved_output_tokens, context_tokens = state.reserved_output_tokens, state.runtime.context_tokens
    expected = (state.request_id, prepared.commitment, tokenization.payload_commitment,
                state.runtime.runtime_commitment, reserved_output_tokens)
    actual = (measurement.request_id, measurement.prepared_commitment, measurement.payload_commitment,
              measurement.runtime_digest, measurement.reserved_output_tokens)
    if tokenization.runtime != state.runtime or actual != expected:
        return InputTokenAssessment("BLOCKED", state.request_id, None, reserved_output_tokens, context_tokens,
                                    ("PREPARED_RECORD_STALE_OR_MISMATCHED",))
    if not tokenization.exact:
        return InputTokenAssessment("BLOCKED", state.request_id, None, reserved_output_tokens, context_tokens,
                                    ("PREPARED_TOKENIZATION_NOT_EXACT",))
    if measurement.state == "MEASURED" and measurement.input_tokens != len(tokenization.token_ids):
        return InputTokenAssessment("BLOCKED", state.request_id, None, reserved_output_tokens, context_tokens,
                                    ("PREPARED_TOKEN_COUNT_MISMATCH",))
    if measurement.state != "MEASURED":
        return InputTokenAssessment("BLOCKED", state.request_id, None, reserved_output_tokens,
                                    context_tokens, ("INPUT_USAGE_UNRESOLVED",))
    if measurement.input_tokens + reserved_output_tokens > context_tokens:
        return InputTokenAssessment("REJECTED", state.request_id, measurement.input_tokens,
                                    reserved_output_tokens, context_tokens,
                                    ("INPUT_OUTPUT_CONTEXT_EXCEEDED",))
    return InputTokenAssessment("ADVISORY", state.request_id, measurement.input_tokens,
                                reserved_output_tokens, context_tokens,
                                ("EXACT_INPUT_TOKEN_MEASUREMENT",))
