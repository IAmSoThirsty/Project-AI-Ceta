"""Real pipe peer authentication, with unfinished authority owners closed."""
from ceta.contracts.wire import ContractError


class WindowsIdentityOwners:
    def __init__(self, registry):
        self._registry = registry

    def authenticate(self, request_context):
        return self._registry.authenticate(request_context)

    def require_message(self, request_context, message):
        self._registry.require_message(request_context, message)

    def task_owner_binding(self, request_context):
        return self._registry.task_owner_binding(request_context)

    def require_prepared_basis(self, proposal, basis_wire, peer):
        raise ContractError("TRUSTED_PREPARATION_OWNER_UNAVAILABLE")

    def require_admission(self, permit, basis_wire, peer):
        raise ContractError("PROTECTED_RESOURCE_OWNER_UNAVAILABLE")

    def require_revocation(self, grant, peer, reason_ref):
        raise ContractError("TRUSTED_REVOCATION_OWNER_UNAVAILABLE")

    def clock(self):
        raise ContractError("TRUSTED_CLOCK_OWNER_UNAVAILABLE")
