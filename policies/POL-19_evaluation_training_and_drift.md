# Evaluation, training and drift attribution

**Document ID:** POL-19  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Scope and controlling responsibilities

Enforcement owner: evaluation service + promotion gate. This policy derives from the ground-up master prompt sections 24, 36. It is a complete written implementation rule; source adoption, exact compiled policy bytes and runtime enforcement require the build gates.

## Rules

Evaluation MUST separate development fixtures, candidate-selection data, final held-out evidence and operational monitoring. Preserve family/source-lineage split rules and all failed runs. Revealing an answer or iteratively optimizing against a held-out item changes its evidentiary status.

Measure the full pipeline using repeated samples and declared rubrics. Wording differences are observable data; causal attribution to a training technique or motive requires additional evidence. Counterexamples and improvements remain in reports. Agreement rate and bluntness are not substitutes for correctness.

Training requires explicit asset, compute, budget and publication permission. Pin data, transforms, model, optimizer settings and checkpoints. Promotion changes only the tested capability profile under current policy. A historically promoted structured transition head does not confer general Companion reasoning competence.

## Enforcement and evidence

Implement predicates at the stated control boundary and add rejection fixtures for each forbidden path. Record the exact policy version, inputs, evaluated rule IDs and result. The policy's text is not itself an executable guard. Preserve both a legal case and a boundary-violation case in the source-bound verification bundle.

## Change and exception handling

A conflict with current adopted source law blocks the affected activation and is entered in the decision register. Do not invent an exception to obtain a passing test. Proposed changes must preserve the audit trail, identify impacted requirements and re-run dependent tests. Emergency responses may only exercise pre-existing, narrower authority.

Requirement groups: REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04.
