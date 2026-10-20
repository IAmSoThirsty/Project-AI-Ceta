# R14 required construction skills

Load only the skills relevant to the current task and their directly linked procedures. These instructions guide future engineering work; their presence does not establish that the work has been performed.

| Skill | Required input | Expected output |
| --- | --- | --- |
| [S03 Contract First Design](../../AGENT-SKILLS/S03-CONTRACT-FIRST-DESIGN/SKILL.md) | Canonical contract references, producer and consumer owners, local language conventions, and compatibility constraints. | A versioned interface decision with fields, invariants, errors, state semantics, and shared test fixtures. |
| [S09 Durable Storage Engineering](../../AGENT-SKILLS/S09-DURABLE-STORAGE-ENGINEERING/SKILL.md) | Reconciled storage engine, data schemas, transaction boundaries, retention rules, and fault fixtures. | Durable local records, atomic publication intent, integrity checks, and tested restoration. |
| [S10 Cryptographic Integrity Engineering](../../AGENT-SKILLS/S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/SKILL.md) | Approved trust model, established local cryptographic facilities, canonicalization rules, and key lifecycle policy. | Domain-bound digests and signatures with protected keys, rotation, and precise verification outcomes. |
| [S19 Evidence Chain Validation](../../AGENT-SKILLS/S19-EVIDENCE-CHAIN-VALIDATION/SKILL.md) | Operation records, artifacts, signatures, lineage, required evidence profile, and trust context. | A verification result separating integrity, attribution, completeness, observed behavior, and unresolved gaps. |
| [S22 Documentation And Traceability](../../AGENT-SKILLS/S22-DOCUMENTATION-AND-TRACEABILITY/SKILL.md) | Accepted implementation behavior, requirements, test results, source and artifact identities, and existing documentation. | Current file, contract, operation, migration, and release guidance with validated links. |
| [S24 Independent Reproduction](../../AGENT-SKILLS/S24-INDEPENDENT-REPRODUCTION/SKILL.md) | Producer deliverables, exact source and environment references, acceptance criteria, and raw evidence. | A separately produced verification report with reproduced results and explicit discrepancies. |
| [S25 No Proof No Claim Verification](../../AGENT-SKILLS/S25-NO-PROOF-NO-CLAIM-VERIFICATION/SKILL.md) | A proposed completion statement, artifact references, execution records, tests, and known evidence gaps. | A claim ledger classifying each statement as supported, contradicted, incomplete, or not-executed. |
