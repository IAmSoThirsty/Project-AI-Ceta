# Architecture registry

components.json assigns 25 functional owners. Production dependency direction and IPC are specified in docs/architecture/DEPENDENCIES_AND_IPC.md. A component is a responsibility, not automatically a process or trust domain. The application/composition and native folders join or enforce these responsibilities without becoming rival authorities. Gate A resolves the actual process roster, platform mechanisms and toolchain before implementation crosses those boundaries.

Implementation proceeds under the root AGENTS.md and build/work_packages.json. Preserve runtime evidence statuses and the original handoff manifest.
