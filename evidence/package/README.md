# Package authoring validation

Package checks validate supplied files, IDs, links, original byte commitments, acceptance coverage, build order and example record shapes. Their reports explicitly describe document/package scope and state that runtime qualification was not performed. The final immutable manifest covers these reports like other payload files. The manifest cannot authenticate itself; the ZIP digest is supplied separately.

Implementation proceeds under the root AGENTS.md and build/work_packages.json. Preserve runtime evidence statuses and the original handoff manifest.
