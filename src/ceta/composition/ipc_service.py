"""Compose native development ingress without profiles, keys or effects."""
from ceta.application.ipc_service import KernelIngress
from ceta.composition.kernel_service import compose_kernel
from ceta.identity.owners import WindowsIdentityOwners
from ceta.kernel.task_drafts import TaskDrafts
from ceta.identity.windows_pipe import WindowsPipeServer


def _selected_kernel(store, codec, installation_scope_id, registry, native_runtime):
    if native_runtime is None:
        owners = WindowsIdentityOwners(registry)
        return compose_kernel(store, codec, installation_scope_id, owners=owners), owners
    from ceta.composition.native_cpu_runtime import NativeCpuRuntime
    from ceta.contracts.kernel_transactions import require
    require(type(native_runtime) is NativeCpuRuntime, 'NATIVE_CPU_RUNTIME_REQUIRED')
    return native_runtime.select(store, codec, installation_scope_id, registry)


def compose_local_kernel_service(store, codec, installation_scope_id, registry, pipe_name,
                                 *, native_runtime=None):
    kernel, owners = _selected_kernel(store, codec, installation_scope_id, registry, native_runtime)
    return WindowsPipeServer(pipe_name, registry, KernelIngress(kernel, owners), codec)


def compose_duplex_kernel_service(store, codec, installation_scope_id, registry, pipe_name,
                                  *, native_runtime=None):
    """The same kernel/store owner, with authenticated correlated result bytes."""
    from ceta.contracts.local_results import encode_response
    kernel, owners = _selected_kernel(store, codec, installation_scope_id, registry, native_runtime)
    tasks = TaskDrafts(store, codec, owners)
    return WindowsPipeServer(pipe_name, registry, KernelIngress(kernel, owners, tasks), codec,
                             response_encoder=encode_response)
