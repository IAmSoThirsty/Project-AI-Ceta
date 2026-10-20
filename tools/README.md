# Package tooling

validate_package.py is the implemented read-only package checker. Run `python tools/validate_package.py` from this package root, or provide `--root` pointing at an extracted package. Its JSON output covers document structure, IDs, traceability, source presence, work-package acyclicity, declared status, local links and payload hashes. It does not execute CETA, touch an existing profile, download dependencies or qualify models/security.

Add `--with-jsonschema` to require the already-installed optional jsonschema library and validate the compound schema plus synthetic shape examples. A missing optional dependency fails that requested check rather than silently skipping it. `--skip-manifest` is only for authoring structural checks before sealing; the output explicitly marks hashes unverified and is not sufficient for final delivery. `--report /path/outside/package.json` writes a result only to a new file outside the package; the default writes JSON to stdout.

The package checker belongs to specification tooling. Application verification commands, actual runtime test implementations and product build tools are assigned to Codex under build/work_packages.json. Never use this checker's result as a replacement for those deliverables.


`python tools/selftest_package_validator.py` reproduces the 15 structural-checker tests using an isolated temporary copy. It deliberately mutates only that copy, leaves the original package unchanged and prints its results. The tests concern document integrity and false-status detection, not application safety. The optional jsonschema library must already be installed for this self-test.

`py -3 -B tools/verify_allocations.py` checks current declared requirement,
component, work-package, case and gate relationships against the preserved
manifest-bound identifier sets. It detects missing allocations, unknown or
duplicate links, mismatched owner/section assignments, missing forward case
bindings and cycles in the declared component/work-package dependency graphs.
Inputs are hashed before and after the read. It writes JSON to stdout and never
changes a requirement, case, gate or runtime status. Contract rejections report
stable error codes.

The allocation checker is specification tooling. Its PASS means the checked
registry relationships are consistent within that scope. It does not verify
interface implementations, actual imports/processes, assigned human reviewers,
source semantics, test adequacy, runtime behavior or Gate A completion. The
preserved identifier universe is the current handoff baseline; a deliberate
baseline amendment requires updating the corresponding baseline evidence,
rather than silently dropping a requirement or case from the checker.

The source checker command, py -3 -B tools/verify_source_coverage.py, verifies
supplied immutable source bytes and detailed applicability references. Its
coverage summary must agree with the detailed rows. The original pending-only
description is accepted only when every row is unresolved; a stale counted
summary is rejected. Parsed metadata bytes must match the first input snapshot,
and all watched inputs must remain unchanged through verification. These checks
add no source adoption, conformance, runtime qualification or Gate A acceptance.
The existing --require-reconciliation flag also requires zero unresolved rows.
The report binds the actual parsed metadata hashes and checker hash. A completed
unchanged-input check is reported explicitly; failure before that check leaves
its field unknown rather than claiming unchanged bytes.

Run its targeted integrity and mutation tests with
py -3 -B -m unittest discover -s tests/contract -p test_source_coverage.py -v.

Run its targeted fault-injection tests with
`py -3 -B -m unittest discover -s tests/contract -p test_allocations.py -v`.
