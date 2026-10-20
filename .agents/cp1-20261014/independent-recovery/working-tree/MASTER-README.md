# CETA Native Architecture Construction Pack

Version: **1.0.0**. Prepared: **2026-10-11**. Package purpose: **construct the complete approved native architecture in the actual local CETA application**.

## Start here

This archive contains populated subsystem construction instructions, not runtime implementation code. It preserves the approved deep structure: **25 subsystems, 144 component folders, 432 planned implementation-file specifications, 21 construction roles, 25 reusable construction skills, 43 canonical contracts, and 20 end-to-end qualification scenarios**.

Each planned source file has an individual `.file.README.md` describing responsibility, domain records, public operations, end-to-end build steps, interfaces, ownership, concurrency, cancellation, failure, recovery, security, evidence, agents, skills, and ten acceptance cases. Every directory has a README. The skill entry points and role definitions guide future engineering work and are separate from deployed runtime agents and learned skills.

## First construction pass

1. Read [the engineering rules](GLOBAL-ENGINEERING-RULES.md) and [the product completion standard](PRODUCT-COMPLETION-STANDARD.md).
2. Inspect the owner-selected local CETA application using [the reconciliation rules](EXISTING-CETA-RECONCILIATION.md) and [the integration plan](INTEGRATION-PLAN/README.md). No remote repository or remembered source layout is assumed.
3. Map every logical unit in [the source registry](MANIFESTS-AND-TRACEABILITY/PLANNED-SOURCE-FILE-REGISTRY.md) to actual local paths and decide reuse, extend, or create from evidence. Preserve existing canonical owners, user data, and acceptance gates.
4. Approve [canonical contracts](INTERFACE-CONTRACTS/README.md) and follow [the validated construction waves](DEPENDENCY-MAPS/BUILD-ORDER-GRAPH.md) with [the phase plan](IMPLEMENTATION-SEQUENCE/README.md).
5. Assign bounded builders and independent reviewers using [the role library](AGENT-ROLES/README.md) and load the relevant [construction skills](AGENT-SKILLS/README.md).
6. Implement each mapped unit end to end, run its actual tests, integrate real native paths, and preserve exact evidence through [the traceability registers](MANIFESTS-AND-TRACEABILITY/README.md).
7. Qualify complete owner workflows using [the layered gates](ACCEPTANCE-CRITERIA/README.md) and [the end-to-end scenarios](ACCEPTANCE-CRITERIA/END-TO-END-SCENARIOS/README.md) before delivering the actual installed product.

## Subsystem navigation

| Subsystem | Purpose | Components | File specifications |
| --- | --- | --- | --- |
| [00-MASTER-ARCHITECTURE](00-MASTER-ARCHITECTURE/README.md) | Own the approved topology, component identities, lifecycle coordination, and local-source reconciliation rules. | 5 | 14 |
| [01-CONSTITUTIONAL-GOVERNANCE](01-CONSTITUTIONAL-GOVERNANCE/README.md) | Interpret owner-approved constitutional rules and produce explainable, version-bound governance decisions. | 5 | 15 |
| [02-IDENTITY-AND-AUTHORITY](02-IDENTITY-AND-AUTHORITY/README.md) | Establish principals, authenticated sessions, delegated authority, and revocable execution capabilities. | 5 | 15 |
| [03-COMPANION-INTELLIGENCE](03-COMPANION-INTELLIGENCE/README.md) | Provide a continuous human-facing intelligence that deliberates, remembers, proposes work, and reports governed outcomes. | 5 | 15 |
| [04-PERSISTENT-MEMORY](04-PERSISTENT-MEMORY/README.md) | Preserve episodic, semantic, and procedural information with provenance, access control, correction, and portability. | 6 | 18 |
| [05-CONTEXT-INTELLIGENCE](05-CONTEXT-INTELLIGENCE/README.md) | Assemble bounded, attributable, task-relevant context while preserving instruction precedence and exact critical state. | 5 | 15 |
| [06-AGENT-SKILLS-AND-LEARNING](06-AGENT-SKILLS-AND-LEARNING/README.md) | Define, discover, qualify, invoke, revise, and revoke reusable native agent skills. | 5 | 15 |
| [07-AGENT-ORCHESTRATION](07-AGENT-ORCHESTRATION/README.md) | Coordinate specialized agents through bounded task contracts, explicit handoffs, concurrency control, and independent verification. | 5 | 15 |
| [08-TASK-AND-WORKFLOW-ENGINE](08-TASK-AND-WORKFLOW-ENGINE/README.md) | Execute durable task graphs with exact state transitions, safe retries, checkpoints, cancellation, and evidence-backed finalization. | 5 | 15 |
| [09-MODEL-RUNTIME](09-MODEL-RUNTIME/README.md) | Manage native model artifacts, qualified inference, optional owner-configured endpoints, routing, lifecycle, and controlled customization. | 8 | 25 |
| [10-TOOLS-AND-CAPABILITIES](10-TOOLS-AND-CAPABILITIES/README.md) | Expose native tools through declared schemas, effect classifications, controlled dispatch, and verifiable receipts. | 5 | 15 |
| [11-EXECUTION-AND-ISOLATION](11-EXECUTION-AND-ISOLATION/README.md) | Enforce the final action boundary, isolate workers, observe real effects, and coordinate stopping and uncertain outcomes. | 6 | 18 |
| [12-ENGINEERING-INTELLIGENCE](12-ENGINEERING-INTELLIGENCE/README.md) | Turn approved engineering requirements into inspected source changes, reproducible tests, independent review, and evidence-backed delivery. | 6 | 18 |
| [13-NATIVE-DEVELOPMENT-WORKSPACE](13-NATIVE-DEVELOPMENT-WORKSPACE/README.md) | Provide a local project explorer, source editor, diff review, terminal, revision management, previews, and recoverable workspace state. | 6 | 18 |
| [14-AUTOMATION-AND-SCHEDULING](14-AUTOMATION-AND-SCHEDULING/README.md) | Create durable time- and event-triggered tasks with explicit authority renewal, concurrency, missed-trigger handling, and observable outcomes. | 5 | 15 |
| [15-COMMUNICATION-AND-INTERACTION](15-COMMUNICATION-AND-INTERACTION/README.md) | Provide native conversation, voice, media, attachments, optional communication channels, notifications, and explicit human decisions. | 6 | 18 |
| [16-KNOWLEDGE-AND-RESEARCH](16-KNOWLEDGE-AND-RESEARCH/README.md) | Ingest and retrieve authorized sources, extract knowledge, compare evidence, and produce attributable research outputs. | 5 | 15 |
| [17-EVIDENCE-AND-PROVENANCE](17-EVIDENCE-AND-PROVENANCE/README.md) | Capture, seal, query, replay, and independently verify operation evidence and artifact lineage. | 6 | 18 |
| [18-SECURITY-AND-ENFORCEMENT](18-SECURITY-AND-ENFORCEMENT/README.md) | Protect keys and secrets, define security boundaries, detect anomalies, contain incidents, and verify trust and dependency integrity. | 6 | 18 |
| [19-STATE-AND-RECOVERY](19-STATE-AND-RECOVERY/README.md) | Own canonical operational state, transactional persistence, snapshots, migrations, recovery, and historical reconstruction. | 6 | 18 |
| [20-RESOURCE-MANAGEMENT](20-RESOURCE-MANAGEMENT/README.md) | Profile hardware, reserve compute and memory, control workload admission, handle pressure, meter inference, and qualify offline behavior. | 6 | 18 |
| [21-EXTENSIONS-AND-INTEROPERABILITY](21-EXTENSIONS-AND-INTEROPERABILITY/README.md) | Enable optional native extensions and generic interoperability through versioned contracts, qualification, scoped authority, and isolated lifecycle management. | 6 | 18 |
| [22-DESKTOP-AND-USER-EXPERIENCE](22-DESKTOP-AND-USER-EXPERIENCE/README.md) | Provide an accessible native application shell, command center, owner controls, decision surfaces, evidence inspection, onboarding, and maintenance. | 9 | 27 |
| [23-TESTING-AND-QUALIFICATION](23-TESTING-AND-QUALIFICATION/README.md) | Define and execute layered tests, adversarial checks, recovery probes, usability checks, and evidence-bound product qualification. | 6 | 18 |
| [24-BUILD-AND-RELEASE](24-BUILD-AND-RELEASE/README.md) | Build, package, qualify, sign where configured, update, roll back, and deliver the complete native application with inspectable evidence. | 6 | 18 |


## Standard subsystem documents

Every subsystem contains README, FILE-INDEX, ARCHITECTURE, BUILD-SEQUENCE, DEPENDENCIES, INTERFACE-CONTRACTS, AGENT-ASSIGNMENTS, INTEGRATION, FAILURE-AND-RECOVERY, TEST-MATRIX, and ACCEPTANCE documents. Component folders add their own README and individual planned-file specifications. All content is populated; there are no empty source stubs or application implementation files in this archive.

## Logical paths and local reality

Logical source paths specify architecture ownership without choosing a new language or fabricating current local filenames. Actual paths, extensions, module conventions, policy grammar, storage and native backend bindings are established from the local application. The initial source-mapping state is LOCAL-INSPECTION-REQUIRED. The package does not claim any particular subsystem is already implemented or any application test has run. Existing local work is reused or extended wherever its observed behavior satisfies the specification.

## Evidence and completion

The file specifications define **4,320 planned file-level acceptance cases**, in addition to component, subsystem, contract, and product tests. Application test state starts NOT EXECUTED. The package's own structural, reference, coverage, skill-format, and integrity checks are recorded separately in [the package completeness report](MANIFESTS-AND-TRACEABILITY/PACKAGE-COMPLETENESS-REPORT.md). Those checks validate this construction archive, not the eventual running application.

## Full tree and integrity

Use [the complete directory tree](DIRECTORY-TREE.md), [the full file inventory](MANIFESTS-AND-TRACEABILITY/PACKAGE-FILE-INVENTORY.md), [the package manifest](PACKAGE-MANIFEST.md), and [the per-document integrity manifest](PACKAGE-INTEGRITY.md). [The decision register](INTEGRATION-PLAN/DESIGN-DECISION-REGISTER.md) distinguishes approved architecture choices from local bindings that require inspection.

The package uses native CETA terminology throughout. Optional interfaces are generic and owner-controlled; no named external agent product is required or integrated by this design.
