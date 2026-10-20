# Native CPU runtime composition

This composition joins the existing RE-T23/RE-T24 producer and observer,
RE-T27 physical outcome capacity, native approval owner, recovery coordinator
and canonical journal. It supplies no new authority issuer or durable writer.

`NativeCpuConfiguration` is an explicit trusted-process input containing the
existing concrete native clock, retained code manifest, observer, capacity
runtime and bounded capacity budget. It binds the observer image and actual
imported observer source to their retained native file entries. It binds the
capacity helper path/digest to its retained entry. Native owners still perform
their actual platform, file, consent and request checks. A configuration is
not an approval, grant, attestation or independently verified trust domain.

`open_service_journal` supplies this exact capacity runtime when opening the
one `SqliteJournal`. It preserves the original constructor path when native
configuration is absent. It rejects a native scope absent from the journal's
scope registry before opening the writer. Unknown stores and existing files
retain the journal's original preservation and validation requirements.

`NativeCpuRuntime` requires that journal, its codec, scope registry and selected
capacity VFS. It creates `NativeStoreBinding` and `NativeOwnerView`, supplying
the budget and original observer before constructing `NativeCpuOwnerSession`.
The session therefore captures the actual view-bound capacity and provenance
methods. The existing kernel constructor binds preparation to that same owner
and journal. The existing IPC factories accept an additive keyword-only runtime
and select only its exact kernel/identity pair. Original positional calls retain
their closed identity-only composition.

`execute` requires the original kernel's retained execution lease and delegates
to the existing `NativeCpuOutcomeAdapter`. The original kernel still performs
consumption, attempt commit, Stop precedence and dispatch fencing. `reconcile`
delegates observation and outcome recording under the original active or
explicitly reopened recovery custody. It creates no new dispatch. A pending
shutdown denies new ingress/execution while preserving this bookkeeping path.
The recovery owner remains responsible for authenticating the original context
and retaining the exact capacity and producer facts.

The runtime owns its store-file pins and native approval session. The caller
retains the journal, registry, clock, code binding and observer. Runtime close
requests owner Stop, then requires execution and capacity custody to retire.
It retires the observer's existing operation custody before closing the owner
and file pins. An unresolved execution, observer or file close retains the
runtime and dependencies. Constructor interruptions preserve the initiating
`BaseException`, exact partial owner and ordered cleanup failures. Explicit
retry is available through the retained runtime. Service cleanup stops in
dependency order, preserves its primary exception and does not automatically
repeat an already failed constructor cleanup.

The service control-message shape is unchanged. Native dependencies cannot be
selected by wire fields, environment discovery or a claimed qualified Boolean.
`service_process.main(native_configuration=...)` is an additive trusted-process
composition entry; its existing command-line invocation retains the original
development configuration. All fixture-root restrictions remain effective.

Controlled composition tests use the real SQLite journal, native session
initializer, view and kernel with explicitly controlled clock, code/file and
observer facts. They invoke no native VFS registration, process, listener,
approval ceremony or CPU Set. These results establish construction, identity
binding, denial and cleanup behavior within that declared scope.

Genuine owner ceremony, qualified restricted workers, native joined execution,
the production request compiler and public operation routing remain required
integration work. The kernel's existing general runtime-admission method stays
closed. Positive native/full/destination verification requires the exact joined
source and case pins plus the coordinator's separate execution release.
