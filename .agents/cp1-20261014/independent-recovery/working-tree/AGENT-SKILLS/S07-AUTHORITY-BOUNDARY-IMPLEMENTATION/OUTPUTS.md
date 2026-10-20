# S07 output contract

## Domain deliverable

Use-time authorization checks with bounded delegation, replay protection, and revocation evidence.

## Required evidence envelope

Return task and unit identities, exact source and artifact references, contract revisions, transformation or implementation decisions, executed procedures, raw observations, accepted results, failed or not-executed obligations, recovery implications, and reviewer status. Include before and after digests for changed content and preserve the original input lineage.

## Status discipline

Use specified for design, implemented for actual source behavior, executed for a real test run, and verified only for evidence that satisfies its oracle. Distinguish self-check and independent reproduction. The required observable result is: A stale or revoked capability cannot authorize effects through any supported entry path.

The output must not contain invented files, fabricated execution logs, unsupported citations, hidden scope changes, or claims that a plan itself completed the application.
