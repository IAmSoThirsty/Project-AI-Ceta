# Native Windows broker assignment

Implement the narrow helper necessary for authenticated IPC, actual OS principals, process/handle ownership, resource access, bounded cancellation and secret lifetimes. Select and record the native language/toolchain at Gate A against the existing application and real Windows requirements. Do not elevate the full desktop/model or substitute Job Objects for resource isolation. Read SPEC-21, CMP-14 effects, POL-13, and cases B063-B072 before implementation. Keep request schemas strict and expose no arbitrary shell, SQL, signing-byte or dynamic import service.

Implementation proceeds under the root AGENTS.md and build/work_packages.json. Preserve runtime evidence statuses and the original handoff manifest.
