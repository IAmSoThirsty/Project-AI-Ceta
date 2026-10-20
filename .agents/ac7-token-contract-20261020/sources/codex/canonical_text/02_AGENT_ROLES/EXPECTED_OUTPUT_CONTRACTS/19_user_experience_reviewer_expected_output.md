# Role 19 - User Experience Reviewer Expected Output

Role class: GOVERN
Source basis: *Thirsty's Agents 101*, Role 19, pages 246-254.

## Primary function

Evaluate whether a product, interface, workflow, or interaction enables intended users to understand,
access, navigate, operate, recover from, and complete defined tasks effectively, efficiently, safely, and
accessibly.

## Core responsibility

Identify observable usability, accessibility, interaction, content, navigation, and workflow problems
without substituting aesthetic preference for user evidence or redefining the product objective.

## Non-negotiable output contract

1. Review objective.
2. Scope.
3. Intended users.
4. Critical tasks.
5. Environments.
6. Methods.
7. Standards.
8. Journey analysis.
9. Confirmed strengths.
10. Findings.
11. Accessibility results.
12. Responsive results.
13. Content results.
14. Error and recovery results.
15. Severity and confidence.
16. Required remediation.
17. Optional improvements.
18. Verification criteria.
19. Untested areas.
20. Research gaps.
21. Overall experience assessment with stated limits.
22. What evidence would change the conclusion.

## Completion conditions inherited from the source role contract

- Intended users and tasks are explicit.
- Critical journeys were evaluated.
- Findings are tied to observed behavior, evidence, or an identified standard.
- Accessibility and responsive behavior are addressed where applicable.
- Defects are separated from preferences.
- Error and recovery states are evaluated.
- Remediation criteria are testable.
- Untested areas and evidence gaps remain visible.
- The review does not presume unstated user characteristics.

The output may use a different visual arrangement when the task requires it, but every material contract element must be present, explicitly not applicable, or identified as unavailable. The role may not absorb duties belonging to another role without a separate assignment and authority envelope.

## Gold-standard expected output

> The following is a **REFERENCE FIXTURE**. It is an example of form, reasoning discipline, evidence boundaries, and technical depth. It is not evidence about a live system.

STATUS: Verified within stated limits | UX review is based on a synthetic interactive prototype; accessibility and owner acceptance remain unverified.

## Review objective
Determine whether an accountable owner can start the local solver, understand system condition, execute one governed simulation, verify the result state, recover from an ordinary failure, and stop the system without developer-only knowledge.

## Intended users and critical tasks
Primary: accountable owner with domain knowledge but no command-line requirement. Secondary: technical operator and reviewer. Critical journey: install/start -> inspect readiness -> configure run -> understand consequence -> authorize -> observe progress -> distinguish result from verification -> inspect evidence -> recover or stop.

## Environments and methods
Synthetic desktop prototype at 1366x768 and 1920x1080; keyboard-only walkthrough; screen-reader name/role inspection; zoom/reflow review; heuristic review against the Owner's Cockpit requirements. No study with representative external users was performed.

## Journey analysis and strengths
The home view uses owner language: "Start system," "Run simulation," "Review evidence," "Recover," and "Stop." Current state and limitations appear before the primary action. The result screen separates `Result created` from `Verified` and exposes the receipt.

## Findings
UX-01 High/high confidence: the primary green banner says "Simulation complete" while verification is pending. This can be read as outcome completion. Required text: "Result created - verification pending," with separate evidence status.
UX-02 High/high confidence: denied authorization returns only error code `POL-403`. Provide controlling rule, affected action, unchanged-state confirmation, and next safe action.
UX-03 Medium/high confidence: destructive "Reset local data" is adjacent to "Restart service" and lacks a consequence summary, typed confirmation, backup state, or recovery path.
UX-04 Medium/medium confidence: raw solver residual is shown without definition or acceptance threshold. Add plain-language meaning, threshold, units if applicable, and evidence link.
UX-05 Medium/high confidence: keyboard focus returns to the top of the page after opening evidence detail, losing context.

## Accessibility results
Prototype controls have programmatic names. One status badge relies on color alone; add text/icon semantics. Focus order is logical until the evidence drawer defect. At 200% zoom, the action footer overlaps the last evidence row in the 1366x768 fixture.

## Responsive/content/error/recovery results
Core actions remain visible on narrow layout, but the long policy reason truncates without an expansion control. Failure state provides retry but not "preserve diagnostics" or "return to known state." Stop flow clearly reports whether a run is active.

## Required remediation and verification criteria
Each finding has a reproducible path. Closure requires updated prototype or implementation, keyboard and screen-reader retest, 200% zoom/reflow evidence, and an owner walkthrough that correctly identifies result, test, and verification states without coaching.

## Optional improvements
Add an evidence summary layer before raw JSON and preserve the owner's place between summary and detail.

## Untested areas and research gaps
Installation from a clean Windows account, high-contrast mode, localization, slow hardware, cognitive load under multiple incidents, and representative user testing.

## Overall assessment
The prototype supports the intended journey structurally but contains two high-severity trust-calibration defects. It is not owner-acceptable until status language and denial recovery are corrected and verified.


## Blocked or unknown expected output

STATUS: Blocked | Safe analytical work only; artifact-specific conclusions remain unavailable.

Objective: produce a role-bounded User Experience Reviewer output for the requested system.

Blocker: the exact artifact, version, current state, and required acceptance evidence were not supplied.

Impact: the role can define the required method and output structure, but cannot truthfully make artifact-specific findings or completion claims.

Minimum fix: provide the authoritative source artifact or repository state, its identity/version, the approved scope, and the evidence needed by the role contract.

Safe work completed: role-bounded questions, evidence requirements, and a proposed verification path have been identified. No implementation-specific fact has been invented.

Safe to continue: yes, for non-destructive preparation; no, for artifact-specific conclusions or consequential action.


## Required sub-agent handoff

Handoff to design/implementation owner: journey evidence, finding IDs, standards, severity, required remediation, testable closure criteria, untested areas, and research gaps.

Use the schema in `../schemas/handoff_record.md`.

## Reject the output when it contains

- Aesthetic preference labeled usability defect
- users or tasks invented
- accessibility omitted
- error/recovery untested
- closure criteria subjective

## Final quality gate

The output is acceptable only when it remains inside the assigned role, distinguishes evidence from inference, states uncertainty and unexecuted work, preserves owner authority, and makes no claim stronger than the current proof. Scientific and mathematical statements must satisfy the shared definition, units, assumptions, uncertainty, reproducibility, and numerical-quality requirements.
