# Start here

This is the complete prewritten build-specification workspace for the ground-up CETA Intelligence Operating System. The application implementation is assigned to Codex. The package contains original source material, a unified engineering contract, concrete component assignments, policies, record schemas, dependency-ordered work, acceptance specifications and operational procedures.

## Using this folder

Extract the ZIP into a new directory that will not overwrite your existing repository or application data. Open this folder in Codex as a reference workspace and provide CODEX_BOOTSTRAP_PROMPT.md. Give Codex access to the actual authorized CETA worktree when it begins implementation. The historical local path in the prompt is a discovery lead; Codex must confirm the current one. Do not merge this root AGENTS.md over existing repository instructions without reconciliation.

From the extracted folder, `python tools/validate_package.py` checks package structure, identifiers, traceability and every manifest-covered file hash. It needs only Python's standard library. `python tools/validate_package.py --with-jsonschema` also exercises the supplied JSON Schema examples if the optional jsonschema package is already installed. Neither command installs dependencies or runs the future application. An optional `--report` destination must be outside this immutable handoff folder.

## Reading route

AGENTS.md establishes engineering conduct. CODEX_BOOTSTRAP_PROMPT.md is the complete kickoff assignment. The governance charter and system contract explain the coherent system to build. architecture/components.json maps its 25 responsibilities to src/ceta folders. Each component README tells Codex what to implement and how its real boundary is verified.

requirements/requirements.json preserves every paragraph-level requirement group from the original 43-section master prompt. The groups are deliberately not claimed to be atomic; Codex decomposes them into implementation tickets without losing the original obligations. policies/ contains 24 prewritten policies. contracts/ contains 20 strict record-shape contracts, examples and semantic obligations. build/ provides 28 ordered work packages and eight acceptance gates. acceptance/ provides all 128 original scenario definitions with fixture, method and evidence instructions.

The complete twenty-volume Codex PDFs are in sources/codex. The selected original embedded text corpus includes all 406 lifecycle sections, front matter, shared governance, roles and references. Searchable text is supplementary and retains original source status. Seven additional original architecture/behaviour papers and page-labelled text derivatives are in sources/architecture and sources/extracted_text. The former master prompt is preserved byte-for-byte in sources/ground_up_master_prompt.original.md.

## What is ready, and what Codex builds

The folder architecture, written contracts, policies, requirements, source bundle, work orders, case specifications and package-validation tool are supplied. Runtime code, native helpers, real test implementations, model configuration qualification, installer and operating evidence are implementation deliverables. Their initial states are explicitly NOT_STARTED or NOT_RUN. A folder named kernel does not pretend a kernel was already implemented.

Build the complete governance cycle first inside a narrow environment, then expand qualified capability through the same contracts. Ground-up means coherent responsibility and authority, not discarding sound algorithms or the user's history. Preserve one CETA identity, one authoritative worktree and one final live interpretation of permissions and state.
