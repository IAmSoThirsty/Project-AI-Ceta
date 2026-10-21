# Explicit operator process diagnostics

The existing development operator supports one finite, local observation:

```powershell
python tools/ceta_operator.py --diagnostics --diagnostics-envelope 250 2000 1073741824
```

These example envelope numbers are caller-declared limits, not qualified product targets.
`--diagnostics` requires all three nonnegative limits (latency milliseconds, CPU
milli-cores, memory bytes). It excludes `--inspector`. The diagnostics branch has
no GUI dependency. Existing explicit development-profile selection applies.
No production profile, background sampler, network export or arbitrary PID is selected.

The command uses the existing retained client and service process owners. It
collects two frames per process, retains at most two safe telemetry projections
per process, and discards the observations after returning the numeric report.
It reads the existing canonical SQLite Journal through its read-only interface;
installation stream and global store positions are checked before and after
collection. Lifecycle generation, identity, physical lifetime, clock and sample
freshness are rechecked. Changed or unavailable owners, state movement,
cancellation and missing required counters prevent a complete process-usage result.

Output separates startup from operation outcome and cleanup. A successful
startup does not establish measured process usage. The final JSON appears only
after owned shutdown and launcher custody closure complete. Exit0 accompanies
`COMPLETE_PROCESS_USAGE`; unavailable startup or measurement returns exit2.
Interruption and unresolved Journal/process cleanup preserve their actual
exceptions and retained custody rather than publishing success.

The public application method is `OperatorSession.resource_diagnostics(envelope)`.
It captures the current service generation and preserves drafts and request state.
This is an explicit trusted-controller observation, not a worker authority grant.

Results describe installation runtime aggregates. Task/project attribution,
workload latency, causal bottlenecks and qualification remain explicitly unavailable
or unestablished. The envelope is labeled `CALLER_DECLARED_UNQUALIFIED`. These
separately checked boundaries are not an atomic snapshot of live native and
SQLite state. Deadline/cancellation checks occur between synchronous calls;
existing SQLite validation and its busy timeout cannot be interrupted internally
by this collector, and strict wall-time/cancellation qualification remains open.

Requirement contributions: CETA-20.05.01/02, REQ-35-01/03 and bounded observation
under REQ-34-03. Controlled process-port tests plus real disposable SQLite prove
the declared domain/application seam. They do not qualify native process effects,
authentication, installed operation or full original acceptance.
