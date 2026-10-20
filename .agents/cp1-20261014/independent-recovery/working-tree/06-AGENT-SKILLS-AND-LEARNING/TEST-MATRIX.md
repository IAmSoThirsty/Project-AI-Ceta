# 06-AGENT-SKILLS-AND-LEARNING - test matrix

## Unit-level acceptance coverage

Every source specification defines ten concrete test obligations: required behavior, a domain-specific adverse case, schema compatibility, stale references, access, bounds and interruption, concurrency, recovery, real integration, and independent proof. These are planned tests, not runtime results.

| Unit | Acceptance IDs | Positive oracle | Negative oracle | Initial execution state |
| --- | --- | --- | --- | --- |
| [CETA-06.01.01 / skill-manifest-schema](06.01-SKILL-DEFINITIONS/skill-manifest-schema.file.README.md) | AT-CETA-06.01.01-01 through AT-CETA-06.01.01-10 | A manifest describes the full effect surface and validates against the canonical schema. | A skill declares itself read-only while requesting a write-capable tool. | NOT EXECUTED |
| [CETA-06.01.02 / skill-contract-registry](06.01-SKILL-DEFINITIONS/skill-contract-registry.file.README.md) | AT-CETA-06.01.02-01 through AT-CETA-06.01.02-10 | A running task keeps its pinned skill revision during a catalog update. | A manifest is replaced in place under the same version and digest. | NOT EXECUTED |
| [CETA-06.01.03 / skill-dependency-resolver](06.01-SKILL-DEFINITIONS/skill-dependency-resolver.file.README.md) | AT-CETA-06.01.03-01 through AT-CETA-06.01.03-10 | An invocable skill has a complete compatible dependency set. | A dependency cycle is hidden by recursively loading until resource exhaustion. | NOT EXECUTED |
| [CETA-06.02.01 / skill-catalog](06.02-SKILL-DISCOVERY/skill-catalog.file.README.md) | AT-CETA-06.02.01-01 through AT-CETA-06.02.01-10 | Discovery shows usable skills separately from candidates awaiting review. | A revoked skill remains selectable from a stale cached search result. | NOT EXECUTED |
| [CETA-06.02.02 / skill-matching-engine](06.02-SKILL-DISCOVERY/skill-matching-engine.file.README.md) | AT-CETA-06.02.02-01 through AT-CETA-06.02.02-10 | A read-only inspection task selects a skill with matching effects and output contract. | A faster destructive skill is selected because its title is similar. | NOT EXECUTED |
| [CETA-06.02.03 / skill-compatibility-checker](06.02-SKILL-DISCOVERY/skill-compatibility-checker.file.README.md) | AT-CETA-06.02.03-01 through AT-CETA-06.02.03-10 | A compatible skill can be admitted on the qualified local environment. | Missing required isolation support is treated as a harmless warning. | NOT EXECUTED |
| [CETA-06.03.01 / skill-invocation-controller](06.03-SKILL-EXECUTION/skill-invocation-controller.file.README.md) | AT-CETA-06.03.01-01 through AT-CETA-06.03.01-10 | A skill run produces a traceable task and tool receipt sequence. | A retry creates a second external effect under a new hidden operation identifier. | NOT EXECUTED |
| [CETA-06.03.02 / skill-input-validator](06.03-SKILL-EXECUTION/skill-input-validator.file.README.md) | AT-CETA-06.03.02-01 through AT-CETA-06.03.02-10 | A valid input is normalized and bound to the approved task digest. | A malformed attachment path changes the operation target after validation. | NOT EXECUTED |
| [CETA-06.03.03 / skill-result-validator](06.03-SKILL-EXECUTION/skill-result-validator.file.README.md) | AT-CETA-06.03.03-01 through AT-CETA-06.03.03-10 | Every claimed output is present and verified against the skill contract. | A fluent final message substitutes for a missing output artifact. | NOT EXECUTED |
| [CETA-06.04.01 / skill-candidate-generator](06.04-SKILL-LEARNING/skill-candidate-generator.file.README.md) | AT-CETA-06.04.01-01 through AT-CETA-06.04.01-10 | A candidate captures the reusable method while excluding private run-specific values. | A successful one-off privileged action is generalized into unrestricted authority. | NOT EXECUTED |
| [CETA-06.04.02 / skill-learning-evaluator](06.04-SKILL-LEARNING/skill-learning-evaluator.file.README.md) | AT-CETA-06.04.02-01 through AT-CETA-06.04.02-10 | A candidate passes unseen inputs and all declared denial cases. | Training examples are reused as the only evidence of general usefulness. | NOT EXECUTED |
| [CETA-06.04.03 / skill-approval-workflow](06.04-SKILL-LEARNING/skill-approval-workflow.file.README.md) | AT-CETA-06.04.03-01 through AT-CETA-06.04.03-10 | Approval activates exactly the reviewed candidate digest. | The candidate changes after review but retains the earlier approval. | NOT EXECUTED |
| [CETA-06.05.01 / skill-version-manager](06.05-SKILL-LIFECYCLE/skill-version-manager.file.README.md) | AT-CETA-06.05.01-01 through AT-CETA-06.05.01-10 | A rollback selects a previously qualified revision without altering its content. | A rollback reactivates a revision that has a current security revocation. | NOT EXECUTED |
| [CETA-06.05.02 / skill-revocation-controller](06.05-SKILL-LIFECYCLE/skill-revocation-controller.file.README.md) | AT-CETA-06.05.02-01 through AT-CETA-06.05.02-10 | A queued invocation cannot start after its skill revision is revoked. | A cached invocation bypasses the updated revocation generation. | NOT EXECUTED |
| [CETA-06.05.03 / skill-audit-recorder](06.05-SKILL-LIFECYCLE/skill-audit-recorder.file.README.md) | AT-CETA-06.05.03-01 through AT-CETA-06.05.03-10 | An auditor reconstructs who approved and invoked a particular skill revision. | An invocation log includes raw credential material from the skill input. | NOT EXECUTED |


## Component and subsystem tests

| Component | Integrated behavior | Invariant |
| --- | --- | --- |
| [06.01](06.01-SKILL-DEFINITIONS/README.md) | Define a versioned skill contract; declare dependencies and effects; validate its structure; bind approved instructions and qualification evidence. | Skill instructions must disclose all potential effect classes before admission. |
| [06.02](06.02-SKILL-DISCOVERY/README.md) | Search approved skills; match task intent and declared requirements; filter unavailable or unauthorized choices; return explainable candidates. | A good semantic match does not establish permission or qualification. |
| [06.03](06.03-SKILL-EXECUTION/README.md) | Pin a qualified skill; validate inputs; obtain scoped task admission; execute through governed tools; validate outputs and evidence; finalize explicitly. | A skill may not call effectful adapters outside the common execution gate. |
| [06.04](06.04-SKILL-LEARNING/README.md) | Extract a candidate from successful work; remove incidental secrets and authority; define applicability; test unseen cases; request approval; publish a new revision. | Learning changes skill content, not the governing constitution or capability issuer. |
| [06.05](06.05-SKILL-LIFECYCLE/README.md) | Publish versioned revisions; pin active runs; revoke unsafe versions; invalidate pending invocations; retain auditable history and rollback evidence. | Rollback of skill content cannot restore previously revoked authority. |


Run these flows through actual local implementations after unit tests. Bind results to exact source, dependencies, configuration, environment, and artifact bytes. A mock-only test cannot qualify a native enforcement or installed-product claim. Preserve failed, blocked, skipped, and not-executed cases separately. Use [the cross-system scenarios](../ACCEPTANCE-CRITERIA/END-TO-END-SCENARIOS/README.md) for user-workflow qualification.
