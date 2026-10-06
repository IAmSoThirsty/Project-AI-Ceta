# Primary engineering reference register

Checked during package authoring on 2026-10-06. These are dependency-design references, not a declaration that any proposed CETA binary is qualified. Pin the actual selected toolchain/library versions and recheck current advisories during implementation.

## SQLite

https://sqlite.org/wal.html
https://sqlite.org/backup.html
https://sqlite.org/releaselog/3_51_3.html

WAL requires a same-host shared-memory design and explicit checkpoint/backup handling. The upstream WAL-reset advisory identifies fixes in 3.51.3 and listed backports. Require a supported fixed build or documented equivalent and verify the library actually loaded by the frozen application. A Python version does not determine that evidence.

## Windows resource boundaries

https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation

Job Objects manage process groups and resource/lifetime behaviour; Microsoft documents process security as a separate responsibility. AppContainer provides a resource-isolation mechanism whose actual capability and broker configuration must be tested. No security guarantee is inherited merely from naming either API.

## Local inference

https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

Use the exact chosen revision's model-loading, template, tokenization, device, endpoint and cancellation contract. Master documentation is a lookup lead rather than qualification of an arbitrary historical binary. CETA owns the qualified runtime lifecycle.

## Schemas

https://json-schema.org/draft/2020-12

Contract schemas in this package declare JSON Schema Draft 2020-12. Shape validation is separate from duplicate-key rejection, canonical byte rules, cryptographic proof and authority. Runtime validators must implement those additional semantic controls.

## Secret memory

https://doc.libsodium.org/memory_management

Reviewed memory-wiping and locking facilities are inputs to a bounded native secret-lifetime design. Callers must handle locking failures and copied material. A call to a wipe function is not evidence of global zero-residue across every consumer and operating-system facility.

## Linux enforcement

https://docs.kernel.org/bpf/prog_lsm.html

The OctoReflex Linux enforcement lane must be qualified where that kernel mechanism actually runs. It does not certify Windows-host effects or an entire WSL host boundary.
