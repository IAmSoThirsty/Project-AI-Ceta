# Tools And Resources contracts

Canonical shared records for tools and resources. Read the common contract rules, preserve exact schema ownership, and implement producer-consumer conformance tests before relying on the interface.

| Contract | Owner | Mandatory semantics |
| --- | --- | --- |
| [tool-manifest](tool-manifest.contract.md) | [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md) | The manifest binds exact implementation and effects, including transitive actions. Discovery exposes availability, not permission. |
| [tool-invocation](tool-invocation.contract.md) | [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md) | Invocation arguments are normalized before approval and immutable afterward. Every invocation goes through the common execution gate. |
| [tool-result](tool-result.contract.md) | [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md) | Schema-valid success still requires declared outputs and observed effects. Preserve raw evidence and unknown outcomes. |
| [resource-budget](resource-budget.contract.md) | [20-RESOURCE-MANAGEMENT](../../20-RESOURCE-MANAGEMENT/README.md) | Child budgets share the parent envelope. Measured use, estimates, and reservations are distinct and control-plane reserve remains available. |
| [workload-admission](workload-admission.contract.md) | [20-RESOURCE-MANAGEMENT](../../20-RESOURCE-MANAGEMENT/README.md) | Admission atomically reserves resources and is fenced by generation. Capacity checks alone do not authorize launch. |

Common rules: [types, versions, authority, errors, and provenance](../CONTRACT-COMMON-RULES.md).
