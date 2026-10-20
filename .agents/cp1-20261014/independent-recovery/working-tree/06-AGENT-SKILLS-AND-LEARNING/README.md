# 06-AGENT-SKILLS-AND-LEARNING

## Mission

Define, discover, qualify, invoke, revise, and revoke reusable native agent skills.

**Invariant:** A learned procedure is a candidate until independently qualified and approved. Skills request capabilities; they do not contain their own authority.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [06.01 Skill Definitions](06.01-SKILL-DEFINITIONS/README.md) | Define a versioned skill contract; declare dependencies and effects; validate its structure; bind approved instructions and qualification evidence. | 3 |
| [06.02 Skill Discovery](06.02-SKILL-DISCOVERY/README.md) | Search approved skills; match task intent and declared requirements; filter unavailable or unauthorized choices; return explainable candidates. | 3 |
| [06.03 Skill Execution](06.03-SKILL-EXECUTION/README.md) | Pin a qualified skill; validate inputs; obtain scoped task admission; execute through governed tools; validate outputs and evidence; finalize explicitly. | 3 |
| [06.04 Skill Learning](06.04-SKILL-LEARNING/README.md) | Extract a candidate from successful work; remove incidental secrets and authority; define applicability; test unseen cases; request approval; publish a new revision. | 3 |
| [06.05 Skill Lifecycle](06.05-SKILL-LIFECYCLE/README.md) | Publish versioned revisions; pin active runs; revoke unsafe versions; invalidate pending invocations; retain auditable history and rollback evidence. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
