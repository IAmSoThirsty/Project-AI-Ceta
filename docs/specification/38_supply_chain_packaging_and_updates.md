# Supply chain, packaging, and updates

**Document ID:** SPEC-38  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

### REQ-38-01

Build from recorded source and pinned dependencies/toolchain with manifests, licenses, and SBOM. Keep training dependencies outside the desktop closure when unnecessary for runtime. Recheck actual advisories and retain findings rather than suppressing them. Inspect libraries loaded by the frozen executable.

### REQ-38-02

Produce installer, offline asset route, required dependency/source companion, verification bundle, and reproducible recipe. Distinguish reproducible instructions from demonstrated bit-for-bit builds. Bind source, executable, installer, assets, and evidence separately. Matching version labels cannot prove that an installer contains newer source.

### REQ-38-03

Preserve the documented personal publisher-verification choice unless superseded by an explicit owner decision. Publisher keys remain separate from runtime, custody, and audit identities. Generic build permission does not authorize using/exporting/rotating private production keys. Validate channel, bytes, compatibility, freshness, rollback, and migration before updating. Do not alter trust stores or suppress OS warnings to imply trust.

### REQ-38-04

Updates are governed maintenance with quiescence, backup, verified activation, health checks, and rollback. Failure preserves user data and a recoverable previous state. Public release, website edits, distribution, uploads, paid services, and production signing require applicable current authorization. Implementation authorization is not automatic publication authorization.

### REQ-38-05

Give the rebuild an unambiguous development version distinct from the installed legacy release. Preserve separate source, package, application, schema, policy, and model versions where their meanings differ. Do not reuse an old release tag or rename an old installer to suggest it contains the rebuild. Resolve the production release number at the authorized release gate and verify source-to-binary-to-installer correspondence.

## Build obligation

Implement these requirement groups through the owning component contract. Preserve the full original requirement; decompose compound groups into atomic implementation tickets without deleting clauses. Record actual file paths and evidence only after implementation. The package's requirement numbers do not replace original Codex clause identifiers.

## Verification binding

Mandatory related scenarios: B122, B123, B124, B112. Exact applicability and additional source-derived cases must be reconciled at Gate A. A passing package checker establishes document consistency only.
