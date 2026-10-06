# Change control and amendment procedure

**Document ID:** GOV-04  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Trigger

Open a change record for altered constitutional meaning, interfaces, persistent schemas, protocol signatures, trust assumptions, model/prompt configuration, qualification thresholds or supported capabilities. Ordinary implementation fixes remain reviewable diffs, linked to requirements and tests. Preserve the exact problem and observed evidence rather than replacing it with a cleaner narrative.

## Procedure

Classify the change, identify its controlling source and affected consumers, write the before/after semantics, define compatibility and invalidation, and add an executable rejection/acceptance test. Obtain the required authority before broadening privileges, touching live data, spending funds or using production keys. Implement in the designated workspace without deleting unrelated changes. Run the affected gate closure and preserve the first failed result.

## Activation

Pin a new contract/policy/config identity. Existing active work either stays on its pinned version or migrates through explicit revalidation. A compiled policy cannot self-authorize its own amendment. Cutover requires quiesced writers and a tested rollback/data-compatibility plan. Update documentation, requirement references and source manifests as part of the same reviewed change.

## Unresolved conflicts

Record both sources, competing meanings, affected behaviours and the precise decision needed. Continue independent work. Do not make uncertainty disappear by selecting the option that is easier to implement or by downgrading a mandatory test.
