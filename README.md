# CETA Intelligence Operating System

## Ground-up build package / 1.0 / 2026-10-06

**Start with [START_HERE.md](START_HERE.md). Give Codex [CODEX_BOOTSTRAP_PROMPT.md](CODEX_BOOTSTRAP_PROMPT.md).**

The objective is a persistent, governed intelligence system that shares an authorized operational environment with its human counterpart. It preserves continuity, reasons from evidence, proposes bounded actions, crosses explicit authority before effects, verifies consequences and carries an accurate state forward. CETA remains the product identity; Project-AI is the architectural purpose and lineage.

This package provides the prewritten project materials and folder structure. It is organized for actual implementation rather than a patchwork upgrade. Original source, requirement groups, policies, contracts, component ownership, work packages, acceptance cases and runbooks are linked by stable IDs. Runtime implementation and evidence remain Codex's assignment.

Read the [system contract](docs/architecture/SYSTEM_CONTRACT.md), [definition of done](docs/governance/DEFINITION_OF_DONE.md) and [package index](PACKAGE_INDEX.md). The [tree](PACKAGE_TREE.txt) provides exact file locations. The [requirements register](requirements/requirements.json), [component register](architecture/components.json), [build work](build/work_packages.json), and [acceptance register](acceptance/scenarios.json) are machine-readable as well as human-inspectable.

The original master prompt and the supplied architecture and standards corpus are retained under sources/. The full twenty-volume Codex source set and all 406 original lifecycle text sections are included; their actual applicability, adoption and implementation statuses are distinct. Current local repository state must be inspected before code changes, and legacy data must be migrated through a tested preservation process.

The only implementation delivered here is a read-only package-consistency validator. Run `python tools/validate_package.py` from this folder. It checks the documents and manifest, not the intended operating system. See [package validation evidence](evidence/package/README.md) and [status semantics](docs/governance/AUTHORITY_AND_STATUS.md).
