# Governance kernel and Thirsty-Lang semantics

**Document ID:** SPEC-16  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-16-01

Implement deterministic policy and transition evaluation under one kernel contract. Preserve carried-forward CETA semantics, including the 23-operation reference instruction set, through differential tests against retained fixtures. A cleaner representation is allowed; changed meaning requires an explicit version, rationale, migration mapping, and assurance. Never silently reinterpret a trained transition policy's outputs under a different operation set.

### REQ-16-02

Compile Thirsty-Lang or other policy sources to bounded typed IR. Pin source, compiler, effective policy, and rule identifiers in each run. Reject unknown operations, ambiguous resolution, contradictory mandatory constraints, invalid references, excessive recursion, and nondeterministic authority predicates. Model interpretation may propose a policy mapping but cannot compile binding law by itself.

### REQ-16-03

Record evaluated inputs, relevant revisions, rules, outcome, obligations, denial conditions, and revalidation triggers. Distinguish permission, obligation, availability, epistemic support, and consent. True or useful proposals may be unauthorized; authorized operations may fail. The owner's authority to choose an action is not authority to make a factual proposition true.

### REQ-16-04

Apply scope and least authority to reads, inference over private material, memory changes, notifications, file modifications, commands, network access, protected-object release, and publication. Maintenance is not a superuser exemption. Policy amendments follow an independently authorized process; the constrained model cannot approve its own restrictions away.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B005, B048, B051, B057, B059, B061. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
