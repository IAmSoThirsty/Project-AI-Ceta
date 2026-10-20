"""Exact authenticated ingress routes into the existing captured kernel port."""
from ceta.contracts.kernel_transactions import require
from ceta.contracts.local_ipc import LocalMessage
from ceta.contracts.task_drafts import TASK_OPERATIONS


class KernelIngress:
    def __init__(self, kernel, identity_owner, task_drafts=None):
        self._kernel, self._identity = kernel, identity_owner
        self._task_drafts = task_drafts

    def __call__(self, message, context):
        require(type(message) is LocalMessage, "IPC_MESSAGE_REQUIRED")
        # Public lookup must retain the same context through the kernel's durable
        # subject checks. The native receiver already checked route/scope.
        self._identity.require_message(context, message)
        self._identity.authenticate(context)
        if message.operation in TASK_OPERATIONS:
            require(self._task_drafts is not None, "TASK_OWNER_UNAVAILABLE")
            return self._task_drafts(message, context)
        wire = message.record.original_wire
        if message.operation == "kernel.prepare":
            return self._kernel.prepare(wire, context)
        if message.operation == "kernel.consume":
            return self._kernel.consume(wire, context)
        if message.operation == "kernel.revoke":
            return self._kernel.revoke(wire, context, message.reason_ref)
        if message.operation == "kernel.resolve_consumption":
            return self._kernel.resolve_consumption_for_peer(wire, context)
        if message.operation == "kernel.recover_permit":
            return self._kernel.recover_permit(wire, context)
        if message.operation == "kernel.recover_preparation":
            return self._kernel.recover_preparation(wire, context)
        require(False, "IPC_OPERATION_UNAVAILABLE")
