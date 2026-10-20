# R05 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S02 Requirements Decomposition](../../AGENT-SKILLS/S02-REQUIREMENTS-DECOMPOSITION/SKILL.md) | Approved product goals, exact user requirements, constraints, and existing acceptance obligations. | A requirement-to-unit map with measurable outputs, dependency edges, and acceptance oracles. |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S07 Authority Boundary Implementation](../../AGENT-SKILLS/S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/SKILL.md) | Principal and capability contracts, trust policy, target resource model, and scoped effect requirements. | Use-time authorization checks with bounded delegation, replay protection, and revocation evidence. |
| [S11 Memory And Retrieval Engineering](../../AGENT-SKILLS/S11-MEMORY-AND-RETRIEVAL-ENGINEERING/SKILL.md) | Memory and source contracts, access scope, provenance rules, and retrieval or deletion fixtures. | Attributed canonical memory, rebuildable indexes, conflict-aware retrieval, and validated context inputs. |
| [S12 Agent Workflow Engineering](../../AGENT-SKILLS/S12-AGENT-WORKFLOW-ENGINEERING/SKILL.md) | Task graph, agent roles, skill manifests, resource limits, authority scope, and handoff contracts. | Bounded multi-agent execution with fenced ownership, durable handoffs, and separate review. |
| [S16 Test Generation And Execution](../../AGENT-SKILLS/S16-TEST-GENERATION-AND-EXECUTION/SKILL.md) | Requirements, unit specifications, canonical contracts, inspected test tooling, and controlled fixtures. | Executed source-bound tests with independent oracles and explicit pass, fail, blocked, skipped, or not-executed states. |
| [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md) | A proposed completion statement, artifact references, execution records, tests, and known evidence gaps. | A claim ledger classifying each statement as supported, contradicted, incomplete, or not-executed. |
