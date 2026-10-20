# Owned-child loader capture R5 — dormant qualification tooling

This successor retains the seven-member and NTDLL/PDB repairs and fixes the
independently reproduced LOADER-R3-02 default-validation bypass. The actual canonical
helper adds CreateEventW to the six _ControlApi members. R4 admits exactly those
seven members and the helper's precise [c_void_p, W.BOOL, W.BOOL, W.LPCWSTR] ->
HANDLE declaration. Unknown extras, missing members and changed ABIs remain
refused. Before this R5 freeze the author personally read both complete terminal
predecessor reviews. R3 was rejected for LOADER-R3-01 and LOADER-R3-02. R4's
seven-member repair was independently verified, but its overall review failed
for the inherited defaults blocker. R4's actual runtime failure code was
EXECUTION_FAILED; R3's was REVIEW_REJECTED. Their original bytes, dispositions,
receipts and ledger states are pinned in PREDECESSOR-REVIEWS.json. This changes no canonical CETA source and
authorizes no native action. The recorded native failure remains 0xC0000142;
its failed DLL and initialization phase remain UNKNOWN until actual evidence
supports attribution. A passing controlled case is not a native qualification.

`caller_boundary.py` admits already imported AC7 modules only from the pinned
357-file source cut. It checks source bytes, import specifications/loaders,
package locations, current code, function defaults, declared aliases/constants,
class/method and ctypes layouts. It does not unload or replace those modules.
Positional and keyword defaults are normalized using only exact builtin
tuple/list/dict/primitive data, or identity for explicitly source-referenced
trusted objects. Supplied equality, boolean, hashing and iterator hooks are
never called. Dictionary keys are normalized without lookup or hashing of
caller-provided keys. Cycles, unsupported objects/subclasses, nonfinite numbers
and excessive scalar/container/depth/node sizes are refused. The bounds are
depth16, total2048nodes,256items/container,65536bytes/scalar and4096integerbits.
Captured fixture/support/shim modules must match their existing declared byte
transform, filesystem-reader code, paths and aliases. The qualification driver's
two constructor custody wrappers are admitted only with their exact code,
original constructors, closure owner and custody collections.

The actual adapter validates the prepared context, creator thread, exact handle
collection, close callback and release binding before consuming an attempt or
loading a native provider. Existing native control members additionally need
their exact pointer identities and ABI. Later protected handle queries require
pipe type, inheritable child ends and noninheritable parent ends. The adapter
checks the live bindings again before its temporary debug hook. Child-pipe
closure preserves the canonical close-then-remove order. An interrupted close
retains its collection and explicit uncertainty; it is never automatically
replayed. Parent handles remain borrowed. Original AppContainer/job/environment,
path and launch construction remain in the pinned canonical launcher.

`loader_snaps.py` reads MSF7 information stream 1 and modern AMD64 DBI stream 3
as bounded bytes. `match_codeview` requires an exact GUID, information age at
least the image age, and a nonzero DBI age exactly equal to the image age. The
three ages remain separate observations. DBI signature -1, version 19990903,
AMD64 machine and stream/substream bounds are mandatory. The vendor's legacy
age-zero fallback is deliberately unsupported. The consumer now requires
`CETA_OWNED_LOADER_SYMBOL_INPUTS_V2`; the historically blocked V1 is still denied.

The rule and header were checked against Microsoft's observed `master` source:
[PDB1::OpenValidate4](https://raw.githubusercontent.com/microsoft/microsoft-pdb/master/PDB/dbi/pdb.cpp)
lines 762–815, and
[NewDBIHdr](https://raw.githubusercontent.com/microsoft/microsoft-pdb/master/PDB/dbi/dbi.h)
lines 107–182. No immutable Microsoft revision was verified. The retained local
NTDLL/PDB byte pins are exact. Their observed image/information/DBI ages are
1/4/1, with GUID bytes `5bd431c0a10d6e8a74d06ed6ab2dd9e1`.

Run the controlled suite with the pinned e3 interpreter and a new attempt name:

```
python.exe -B -X utf8 run_data_controls.py tests --attempt review-unique
```

The runner guards DLL/native/process/network constructors and confines writes
to its own work directory. The new contexts import actual pinned CETA source,
execute only the dormant captured helper/support definitions, and compile the
driver definitions without its module-scope native reader preflights. They do
not invoke prepare_probe, run_native_probe, inspect, effect or qualify. The
positive caller control exercises the actual owned-caller and adapter functions
and stops at the guarded native-member boundary. Its synthetic handles and
unconstructed control object are explicitly refused by production native-member
validation. No native pipe, child, profile, listener, debugger or target-memory
operation was executed. This is bounded in-process binding validation, not a
security claim against an interpreter whose entire trusted runtime is replaced.

All 88 R4 case identifiers and method ASTs, including 83 R3 cases, 60 R2 case
identifiers and all 28 original test method ASTs, are retained. Eight focused R5
cases include full validate_prepared mutations on the real pinned canonical
WindowsOwnedProcess._cpu_window positional default and apply_cpu_rate_limit
keyword default. Hostile hook counts remain zero. Nested data, trusted-object
identity, mapping order, wrong types, subclasses, cycles and bounds are covered.
The retained five R4 cases exercise
the actual seven-member guard using noncalled typed pointer wrappers around
inert integer addresses. Those wrappers are data controls with no DLL/native
provenance; no function pointer is invoked and no production integration is
claimed. The adapter control passes the real guard and stops before consuming
an attempt or loading providers. Missing/extra/wrong ABI cases are rejected.
Two historical R2 symbol test methods intentionally changed in R3: matching accepts
a newer information age with an exact DBI age, and the corruption case targets
the stream-page field in the expanded fixture layout. `pdb_fixture` now contains
a real 64-byte DBI header. The original release helper also includes the two
new required caller-binding dictionaries. No original 28 test assertion changed.

`ACTION-PACKET.json` describes a dormant action, not an executable release.
Pending work includes independent review, Root's distinct reviewed V2 symbol
input derivation, a fresh exact in-process canonical caller binding/bridge and
action-specific owner approval. Existing historical fixture handles are never
adopted. No target DLL was loaded. Actual DbgHelp type resolution, private PEB
offsets, debugger events, own-child instrumentation and cleanup remain unverified.
`verify_frozen.py` only reads hashes, pinned inputs and controlled receipts.
