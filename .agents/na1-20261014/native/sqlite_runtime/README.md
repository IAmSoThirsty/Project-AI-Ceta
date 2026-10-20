# Project-local SQLite runtime

The Windows x64 library is SQLite 3.53.4 from the official archive at
https://sqlite.org/2026/sqlite-dll-win-x64-3530400.zip. The official download
page supplies archive SHA3-256
`deddee963c810d1eeac3ce5e15c7c41da21a1c54d7a39cf54fbf577d2f50de3a`.
The DLL SHA-256 is
`ab57d0437795ecc757cb693f32ea224173fa9856594d95cfa6b5033e645cd1ec`.
`contracts/SQLITE_RUNTIME_V1.json` records both members, their sizes, CRCs,
digests and the official page identities. The acquisition receipt and original
ZIP are preserved in the adjacent specification increment-20 cache.

SQLite is public-domain software; see https://sqlite.org/copyright.html.
Its upstream implementation is used as the declared persistence dependency.
No source program from the Codex attachment corpus was executed.

`ceta.store.sqlite_runtime` loads this exact DLL before CPython imports SQLite.
It rejects a different already loaded library, verifies the actual module path
and runtime version, and retains the installed CPython wrapper. It changes no
installed interpreter, environment PATH, global trust or application profile.
The source-test snapshot includes the native runtime directory explicitly.
The actual loaded identity is measured by `tools/probe_sqlite_runtime.py`.

The initial archive descriptor establishes dependency bytes. Later probe/test
receipts establish loaded compatibility at their exact cuts. Installed packaging,
power-loss, hardware trust and authenticated operating qualification remain open.
