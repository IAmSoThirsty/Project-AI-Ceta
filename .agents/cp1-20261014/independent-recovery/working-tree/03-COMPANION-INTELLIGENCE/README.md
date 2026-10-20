# 03-COMPANION-INTELLIGENCE

## Mission

Provide a continuous human-facing intelligence that deliberates, remembers, proposes work, and reports governed outcomes.

**Invariant:** Continuity, preference, confidence, and personality cannot confer execution authority. Human decisions remain attributable and task consent remains scoped.

## Component map

| Component | End-to-end behavior | Planned files |
| --- | --- | --- |
| [03.01 Companion Identity](03.01-COMPANION-IDENTITY/README.md) | Create a persistent companion profile; bind it to approved identity and preferences; evolve it through recorded changes; expose only currently available capabilities. | 3 |
| [03.02 Dialogue Intelligence](03.02-DIALOGUE-INTELLIGENCE/README.md) | Accept a turn; preserve exact user wording; identify consequential ambiguity; assemble authorized context; generate a response plan; expose factual basis and proposed actions. | 3 |
| [03.03 Continuity And Adaptation](03.03-CONTINUITY-AND-ADAPTATION/README.md) | Load continuity records; apply explicit preferences; propose uncertain adaptations; reconcile interrupted sessions; restore task and dialogue references. | 3 |
| [03.04 Initiative And Deliberation](03.04-INITIATIVE-AND-DELIBERATION/README.md) | Identify a useful initiative; state rationale and alternatives; assess authority; ask for decisions where required; create a governed task only after valid approval. | 3 |
| [03.05 Companion Operations](03.05-COMPANION-OPERATIONS/README.md) | Translate approved plans into tasks; request tools through orchestration; observe progress; present results and interruptions with evidence links. | 3 |


## Read and build order

Read [architecture](ARCHITECTURE.md), [contracts](INTERFACE-CONTRACTS.md), [dependencies](DEPENDENCIES.md), and [build sequence](BUILD-SEQUENCE.md). Then load only the component and file specifications assigned to the current task. Use [the file index](FILE-INDEX.md) to find every planned source unit.

## Integration and qualification

Use [local integration instructions](INTEGRATION.md), [failure and recovery rules](FAILURE-AND-RECOVERY.md), [the test matrix](TEST-MATRIX.md), and [acceptance gate](ACCEPTANCE.md). [Agent assignments](AGENT-ASSIGNMENTS.md) defines construction responsibility and reviewer separation.

This subsystem contains 5 component folders and 15 planned implementation-file specifications. The package specifies their construction; it makes no claim about their presence in the uninspected local application. The initial reconciliation state for each logical path is LOCAL-INSPECTION-REQUIRED. Resolve that state through evidence before editing.
