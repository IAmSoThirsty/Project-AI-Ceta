# Package tooling

validate_package.py is the implemented read-only package checker. Run `python tools/validate_package.py` from this package root, or provide `--root` pointing at an extracted package. Its JSON output covers document structure, IDs, traceability, source presence, work-package acyclicity, declared status, local links and payload hashes. It does not execute CETA, touch an existing profile, download dependencies or qualify models/security.

Add `--with-jsonschema` to require the already-installed optional jsonschema library and validate the compound schema plus synthetic shape examples. A missing optional dependency fails that requested check rather than silently skipping it. `--skip-manifest` is only for authoring structural checks before sealing; the output explicitly marks hashes unverified and is not sufficient for final delivery. `--report /path/outside/package.json` writes a result only to a new file outside the package; the default writes JSON to stdout.

The package checker belongs to specification tooling. Application verification commands, actual runtime test implementations and product build tools are assigned to Codex under build/work_packages.json. Never use this checker's result as a replacement for those deliverables.


`python tools/selftest_package_validator.py` reproduces the 15 structural-checker tests using an isolated temporary copy. It deliberately mutates only that copy, leaves the original package unchanged and prints its results. The tests concern document integrity and false-status detection, not application safety. The optional jsonschema library must already be installed for this self-test.
