"""Compose native development ingress without profiles, keys or effects."""
from ceta.application.ipc_service import KernelIngress
from ceta.composition.kernel_service import compose_kernel
from ceta.identity.owners import WindowsIdentityOwners
from ceta.kernel.task_drafts import TaskDrafts
from ceta.identity.windows_pipe import WindowsPipeServer


def compose_local_kernel_service(store, codec, installation_scope_id, registry, pipe_name):
    owners = WindowsIdentityOwners(registry)
    kernel = compose_kernel(store, codec, installation_scope_id, owners=owners)
    return WindowsPipeServer(pipe_name, registry, KernelIngress(kernel, owners), codec)


def compose_duplex_kernel_service(store, codec, installation_scope_id, registry, pipe_name):
    """The same kernel/store owner, with authenticated correlated result bytes."""
    from ceta.contracts.local_results import encode_response
    owners = WindowsIdentityOwners(registry)
    kernel = compose_kernel(store, codec, installation_scope_id, owners=owners)
    tasks = TaskDrafts(store, codec, owners)
    return WindowsPipeServer(pipe_name, registry, KernelIngress(kernel, owners, tasks), codec,
                             response_encoder=encode_response)
