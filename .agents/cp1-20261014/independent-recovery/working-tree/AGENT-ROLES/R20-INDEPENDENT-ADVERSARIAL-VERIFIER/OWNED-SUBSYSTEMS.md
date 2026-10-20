# R20 subsystem scope

Independent review scope; this role does not take default write ownership of every subsystem.

| Subsystem | Purpose |
| --- | --- |
| [00-MASTER-ARCHITECTURE](../../00-MASTER-ARCHITECTURE/README.md) | Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules. |
| [01-CONSTITUTIONAL-GOVERNANCE](../../01-CONSTITUTIONAL-GOVERNANCE/README.md) | Interpret owner-approved constitutional rules and produce explainable, version-bound governance decisions. |
| [02-IDENTITY-AND-AUTHORITY](../../02-IDENTITY-AND-AUTHORITY/README.md) | Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities. |
| [03-COMPANION-INTELLIGENCE](../../03-COMPANION-INTELLIGENCE/README.md) | Provide a continuous human-facing intelligence that deliberates, remembers, proposes work, and reports governed outcomes. |
| [04-PERSISTENT-MEMORY](../../04-PERSISTENT-MEMORY/README.md) | Preserve episodic, semantic, and procedural information with provenance, access control, correction, and portability. |
| [05-CONTEXT-INTELLIGENCE](../../05-CONTEXT-INTELLIGENCE/README.md) | Assemble bounded, attributable, task-relevant context while preserving instruction precedence and exact critical state. |
| [06-AGENT-SKILLS-AND-LEARNING](../../06-AGENT-SKILLS-AND-LEARNING/README.md) | Define, discover, qualify, invoke, revise, and revoke reusable native agent skills. |
| [07-AGENT-ORCHESTRATION](../../07-AGENT-ORCHESTRATION/README.md) | Coordinate specialized agents through bounded task contracts, explicit handoffs, concurrency control, and independent verification. |
| [08-TASK-AND-WORKFLOW-ENGINE](../../08-TASK-AND-WORKFLOW-ENGINE/README.md) | Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization. |
| [09-MODEL-RUNTIME](../../09-MODEL-RUNTIME/README.md) | Manage native model artifacts, qualified inference, optional owner-configured endpoints, routing, lifecycle, and controlled customization. |
| [10-TOOLS-AND-CAPABILITIES](../../10-TOOLS-AND-CAPABILITIES/README.md) | Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts. |
| [11-EXECUTION-AND-ISOLATION](../../11-EXECUTION-AND-ISOLATION/README.md) | Enforce the final action boundary, isolate workers, observe real effects, and coordinate stopping and uncertain outcomes. |
| [12-ENGINEERING-INTELLIGENCE](../../12-ENGINEERING-INTELLIGENCE/README.md) | Turn approved engineering requirements into inspected source changes, reproducible tests, independent review, and evidence-backed delivery. |
| [13-NATIVE-DEVELOPMENT-WORKSPACE](../../13-NATIVE-DEVELOPMENT-WORKSPACE/README.md) | Provide a local project explorer, source editor, diff review, terminal, revision management, previews, and recoverable workspace state. |
| [14-AUTOMATION-AND-SCHEDULING](../../14-AUTOMATION-AND-SCHEDULING/README.md) | Create durable time- and event-triggered tasks with explicit authority renewal, concurrency, missed-trigger handling, and observable outcomes. |
| [15-COMMUNICATION-AND-INTERACTION](../../15-COMMUNICATION-AND-INTERACTION/README.md) | Provide native conversation, voice, media, attachments, optional communication channels, notifications, and explicit human decisions. |
| [16-KNOWLEDGE-AND-RESEARCH](../../16-KNOWLEDGE-AND-RESEARCH/README.md) | Ingest and retrieve authorized sources, extract knowledge, compare evidence, and produce attributable research outputs. |
| [17-EVIDENCE-AND-PROVENANCE](../../17-EVIDENCE-AND-PROVENANCE/README.md) | Capture, seal, query, replay, and independently verify operation evidence and artifact lineage. |
| [18-SECURITY-AND-ENFORCEMENT](../../18-SECURITY-AND-ENFORCEMENT/README.md) | Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity. |
| [19-STATE-AND-RECOVERY](../../19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. |
| [20-RESOURCE-MANAGEMENT](../../20-RESOURCE-MANAGEMENT/README.md) | Profile hardware, reserve compute and memory, control workload admission, handle pressure, meter inference, and qualify offline behavior. |
| [21-EXTENSIONS-AND-INTEROPERABILITY](../../21-EXTENSIONS-AND-INTEROPERABILITY/README.md) | Enable optional native extensions and generic interoperability through versioned contracts, qualification, scoped authority, and isolated lifecycle management. |
| [22-DESKTOP-AND-USER-EXPERIENCE](../../22-DESKTOP-AND-USER-EXPERIENCE/README.md) | Provide an accessible native application shell, command center, owner controls, decision surfaces, evidence inspection, onboarding, and maintenance. |
| [23-TESTING-AND-QUALIFICATION](../../23-TESTING-AND-QUALIFICATION/README.md) | Define and execute layered tests, adversarial checks, recovery probes, usability checks, and evidence-bound product qualification. |
| [24-BUILD-AND-RELEASE](../../24-BUILD-AND-RELEASE/README.md) | Build, package, qualify, sign where configured, update, roll back, and deliver the complete native application with inspectable evidence. |

## Ownership coordination

Use [the assignment matrix](../ROLE-ASSIGNMENT-MATRIX.md) and the per-file specifications to identify builders and reviewers. One active writer owns each mapped source path. Shared schemas remain with the canonical schema owner even when this role contributes to their implementation. A conflict is resolved before either agent publishes changes.
