# Agents And Tasks contracts

Canonical shared records for agents and tasks. Read the common contract rules, preserve exact schema ownership, and implement producer-consumer conformance tests before relying on the interface.

| Contract | Owner | Mandatory semantics |
| --- | --- | --- |
| [agent-manifest](agent-manifest.contract.md) | [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md) | Reusable role and runtime agent identity are distinct. A role declaration cannot grant capabilities or establish independent review. |
| [agent-message](agent-message.contract.md) | [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md) | Messages are authenticated task-scoped claims. Delivery is deduplicated and does not create authority or establish factual truth. |
| [agent-handoff](agent-handoff.contract.md) | [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md) | The receiver validates exact artifacts, remaining work, authority, and uncertainty before accepting ownership. Handoff does not revive expired authority. |
| [task-definition](task-definition.contract.md) | [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md) | A task has measurable acceptance and explicit effect scope. A goal does not authorize every possible means or permit silent scope reduction. |
| [workflow-transition](workflow-transition.contract.md) | [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md) | Only declared transitions with satisfied guards commit. Expected-version checks prevent stale workers from overwriting newer state. |
| [skill-manifest](skill-manifest.contract.md) | [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md) | Candidate, qualified, approved, active, deprecated, and revoked states are distinct. Learned content never contains an implicit authority grant. |
| [scheduled-task](scheduled-task.contract.md) | [14-AUTOMATION-AND-SCHEDULING](../../14-AUTOMATION-AND-SCHEDULING/README.md) | Occurrence identity is stable across restart and clock changes. Current authority is checked when each occurrence is admitted. |

Common rules: [types, versions, authority, errors, and provenance](../CONTRACT-COMMON-RULES.md).
