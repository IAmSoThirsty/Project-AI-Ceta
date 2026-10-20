"""Application calls over one captured kernel port.

This layer forwards untrusted requests and preserves kernel results and denials.
It neither authenticates a request nor exposes a concrete persistence adapter.
"""
from dataclasses import dataclass
from typing import Protocol

from ceta.contracts.evidence_admission import ConsumptionEvidence
from ceta.contracts.kernel_transactions import KernelResult
from ceta.contracts.wire import ParsedRecord


class KernelPort(Protocol):
    """Kernel-owned operations; Python protocol conformance grants no authority."""

    def prepare(self, proposal_wire: bytes, request_context: object) -> KernelResult: ...

    def consume(self, permit_wire: bytes, request_context: object) -> KernelResult: ...

    def revoke(
        self, grant_wire: bytes, request_context: object, reason_ref: str
    ) -> KernelResult: ...

    def resolve_consumption(self, permit: ParsedRecord) -> ConsumptionEvidence: ...

    def resolve_consumption_for_peer(self, permit_wire: bytes, request_context: object) -> ConsumptionEvidence: ...

    def recover_permit(self, permit_wire: bytes, request_context: object) -> ParsedRecord: ...

    def recover_preparation(self, proposal_wire: bytes, request_context: object) -> ParsedRecord: ...

    def require_runtime_admission(self) -> None: ...


@dataclass(frozen=True)
class KernelUseCases:
    """Delegate to the kernel captured by the composition owner.

    No request-supplied owner, trusted flag, fallback writer or effect adapter is
    selected here. Injected fixture ports do not establish OS authentication.
    """

    _kernel: KernelPort

    def prepare(self, proposal_wire: bytes, request_context: object) -> KernelResult:
        return self._kernel.prepare(proposal_wire, request_context)

    def consume(self, permit_wire: bytes, request_context: object) -> KernelResult:
        return self._kernel.consume(permit_wire, request_context)

    def revoke(
        self, grant_wire: bytes, request_context: object, reason_ref: str
    ) -> KernelResult:
        return self._kernel.revoke(grant_wire, request_context, reason_ref)

    def resolve_consumption(self, permit: ParsedRecord) -> ConsumptionEvidence:
        return self._kernel.resolve_consumption(permit)

    def resolve_consumption_for_peer(self, permit_wire: bytes, request_context: object) -> ConsumptionEvidence:
        """Forward authenticated public lookup; preserve the trusted internal callback."""
        return self._kernel.resolve_consumption_for_peer(permit_wire, request_context)

    def recover_permit(self, permit_wire: bytes, request_context: object) -> ParsedRecord:
        """Observe current bound state; never retry or redeem an uncertain command."""
        return self._kernel.recover_permit(permit_wire, request_context)

    def recover_preparation(self, proposal_wire: bytes, request_context: object) -> ParsedRecord:
        """Observe original issuance when its generated permit ID was not returned."""
        return self._kernel.recover_preparation(proposal_wire, request_context)

    def require_runtime_admission(self) -> None:
        """Preserve the kernel's typed denial; this call enables no effects."""
        return self._kernel.require_runtime_admission()
