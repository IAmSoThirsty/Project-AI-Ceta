# Native code and environment bindings

`NativeCodeBinding(tuple[CodePin, ...])` measures the finite reviewed manifest
provided by trusted local composition. Each entry names its source/environment
group, a unique bounded logical name, an ordinary absolute file path and the
expected SHA-256. Group names require exact built-in strings; subclasses and
custom equality objects are denied before file pinning. Both groups are required. Duplicate paths/names, missing files,
links, reparse objects, wrong hashes and file/count/byte bounds are denied.

The implementation retains read-only noninheritable file handles with read-only
sharing, and read-attribute ancestor handles without delete sharing. Windows
normally excludes writes, file replacement and ancestor renames for that retained
lifetime. Initial hashing checks exact native metadata before/after reading.
Full 64-bit volume serials, 128-bit file IDs and native volume paths are measured.
Framed group commitments bind each logical name, digest, size, path and native
identity; copied identical bytes on a different object produce a different
commitment. Directory content changes remain permitted and do not change the
meaning of pinned named files. The manifest must enumerate the complete admitted
source/runtime dependency surface; this library does not discover missing files
or decide which code is authorized.

`require_current()` checks retained identities/metadata. `snapshot()` returns
immutable measured data. `retained()` supplies one exact same-thread private lease
while the owner lock and native pins remain held. Its `require_current()` is a
pure final fence with no I/O, clock callbacks or authority issuance. A forged,
expired, foreign-thread or canceled lease is denied. Canonical enrollment,
authority, clock/deadline, policy and Stop/revocation checks remain separate
mandatory composition responsibilities.

`close()` first invalidates leases, then attempts bounded lock acquisition.
Active/foreign-thread leases keep native custody and require explicit retry after
retirement. Handle retirement reuses the reviewed duplicate-object cleanup fence.
Uncertain cleanup remains attached through nonoverridable exception storage;
diagnostic attributes cannot replace a primary control exception. No ACL,
configuration, service, account or AppContainer profile changes occur.

Actual tests use disposable Windows files, held native handles, real denied
writes/replacements/renames and concurrent retirement. These observations do not
issue grants or establish genuine owner approval, OS isolation, public runtime
admission or governed effect acceptance. Same-process privileged mutation,
administrator/kernel tampering and unenumerated dependencies remain trust limits.
