"""Compose one kernel service without opening storage or activating a profile."""
from ceta.application.use_cases import KernelUseCases
from ceta.contracts.kernel_transactions import AuthorityOwners, KernelStorePort
from ceta.contracts.wire import RecordCodec
from ceta.kernel.transactions import KernelTransactions


def compose_kernel(
    store: KernelStorePort,
    codec: RecordCodec,
    installation_scope_id: str,
    owners: AuthorityOwners | None = None,
) -> KernelUseCases:
    """Capture one explicitly supplied store and owner set in one kernel.

    Missing owners remain unavailable; fixture owners confer no native identity
    or effect authority. Resource opening and lifecycle activation are not part
    of this composition function.
    """
    kernel = KernelTransactions(store, codec, installation_scope_id, owners=owners)
    return KernelUseCases(kernel)
