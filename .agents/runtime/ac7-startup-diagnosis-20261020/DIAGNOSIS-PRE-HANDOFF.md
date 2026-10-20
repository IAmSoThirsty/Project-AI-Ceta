The recorded AC7 attempt failed with `0xC0000142` (`STATUS_DLL_INIT_FAILED`). The exact failing DLL, initialization phase and causal launch difference remain **UNKNOWN**. This diagnosis supports the observed failure and several source-level differences; it does not support a speculative binary, ACL, capability, token or policy repair. The failure blocks positive native qualification of this attempt. The bounded read-only diagnosis is complete.

The sole project is `T:\00-Active\Project-AI-CETA`, branch `candidate/societal-reasoning-v1`, HEAD `83fc9432b4a37ee7f91d6c5b0d358a015548aed4`. Existing dirty work was preserved. All new outputs are in `T:\00-Active\Project-AI-CETA\.agents\runtime\ac7-startup-diagnosis-20261020`. No worker, test image, profile, listener, application, DLL or debugger was launched or attached during this diagnosis. No source, candidate, build, configuration, ACL or policy was changed.

The exact historical cut is attempt `q-6be3c32cb832461093c6d15dc9c538f8`, under `T:\00-Active\Project-AI-CETA\.agents\runtime\ac7-token-contract-20261020`. The parent qualification terminal ran from 2026-10-20 09:34:55.079562 UTC to 09:34:59.351255 UTC and exited 1, with no automatic retry. Its captured child tool hash matches the current qualification tool. The probe receipt records worker PID 26536, creation time 134369624986270138; ordinary PID 21160, creation time 134369624980284103. These are historical identities and were not used to select live processes.

| Exact input | SHA-256 |
| --- | --- |
| Worker: original build-r2, attempt build-r2 copy, fixture asset copy | `3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc` (4,872,606 bytes each) |
| Rust source | `592d7e3630d2dae1f8df6c6e3b686eff7f9c4d31aa889bd03cd66cab9782676d` |
| build-r2/BUILD.json | `545db529a078d1a1b46a00968823ce8dfb39efeb94a78b451860823c36ddfd97` |
| native-profile-r2.json | `ab1c95b6940c4a94d588221cfe9622e44cc706e06d75287baf04280f59d0a78c` |
| Transformed driver actually executed | `251d0d93ef2e261d257c6622d2d18034d71ec329a345c536f69283a15458d6df` |
| Captured qualification tool | `79da07922e6a7f56cca0ae9d90a2498c3d6f28a58dcb6bd3144ab56a87b5bd84` |

The build receipt records rustc 1.96.1, commit `31fca3adb283cc9dfd56b49cdee9a96eb9c96ffd`, host `x86_64-pc-windows-gnu`, and `--edition=2024 -C target-feature=+crt-static -O`. The prior independent artifact review remains scoped to its images; this diagnosis additionally verifies all three image copies and the receipt identity. Fourteen recorded qualification/build stdout and stderr digests match their files. Five pure Rust tests are a historical passing receipt; none was rerun. `crt-static` is a recorded compiler option, while the PE still contains Windows DLL imports.

The source comparison uses the attempt's candidate snapshot, not the live canonical `src/ceta` tree. Current `windows_jobs.py`, `isolated_worker.py`, `isolated_worker.rs` and `service.py` match their attempt snapshot pins. The qualification tool matches its separate child terminal pin. Driver/support hashes match `PROBE-BINDING.json`. The tool constructs an in-memory `ac_support` shim, executes captured driver/support bytes, and sets their candidate root to the AC7 candidate. A missing physical `qdir/ac_support.py` is therefore not a missing dependency finding. Full receipt snapshots, hashes and bindings are retained in [INPUT-RECEIPTS.json](T:/00-Active/Project-AI-CETA/.agents/runtime/ac7-startup-diagnosis-20261020/INPUT-RECEIPTS.json), [RECEIPT-STREAM-BINDINGS.json](T:/00-Active/Project-AI-CETA/.agents/runtime/ac7-startup-diagnosis-20261020/RECEIPT-STREAM-BINDINGS.json), and the two source excerpt files.

The historical probe records `is_appcontainer=true`, capability count 0, integrity RID 4096, `IsTokenRestricted=false`, raw result 0, last error 0, and measured restricted SID count 0 before resume. The ordinary control records medium integrity `S-1-16-8192` and liveness both before and after the worker. The worker later exited 3221225794; facts are null and stderr is empty. Cleanup records ordinary exit 125 after owned termination. Profile create/delete HRESULT 0 is recorded, but independent cleanup acceptance belongs to the parent result review. None of those facts identifies the failed DLL.

Microsoft maps `0xC0000142` to DLL initialization failure. `CreateProcessW` may return before initialization completes, so successful creation, parent token measurement and resume are compatible with subsequent DLL initialization failure. A load-time DLL entry point returning FALSE is one documented way initialization can fail and terminate a process. The status has no DLL name in this receipt. These documents establish the status meaning and a possible mechanism, not the actual failing component. [MS-ERREF NTSTATUS values](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55), [CreateProcessW return value](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw), [DLL entry point return value](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-entry-point-function).

The following is derived from the pinned driver and launch functions, cross-checked with the recorded identities, arguments and native path receipt. It is not a raw `CreateProcessW` trace. Exact source ranges are preserved in [SOURCE-EXCERPTS.json](T:/00-Active/Project-AI-CETA/.agents/runtime/ac7-startup-diagnosis-20261020/SOURCE-EXCERPTS.json) and [SUPPLEMENTAL-SOURCE-EXCERPTS.json](T:/00-Active/Project-AI-CETA/.agents/runtime/ac7-startup-diagnosis-20261020/SUPPLEMENTAL-SOURCE-EXCERPTS.json); the complete comparison and both argument vectors are in [LAUNCH-COMPARISON.json](T:/00-Active/Project-AI-CETA/.agents/runtime/ac7-startup-diagnosis-20261020/LAUNCH-COMPARISON.json).

| Startup surface | Ordinary control | Isolated worker |
| --- | --- | --- |
| Image bytes | Same pinned image | Same pinned image |
| Mode/arguments | `hold 30000` | `probe` plus asset, scratch, protected paths, PID 21160, port 49671 and excluded event marker 888 |
| Application and argv[0] spelling | Resolved `T:\...\assets\isolated_worker.exe` | `\\?\Volume{e4bb1102-0000-0000-0000-100000000000}\...\assets\isolated_worker.exe` |
| Current directory | Drive-letter fixture path | Same fixture identity through volume GUID path |
| Base creation flags | `0x08080404` | `0x08080404` |
| Base flag meaning | Suspended, Unicode environment, extended startup, no window | Same |
| Job limits set by this launch | Kill on job close | Kill on job close and active process limit 1 |
| Attribute list | JOB_LIST | JOB_LIST, SECURITY_CAPABILITIES (SID, zero capabilities), CHILD_PROCESS_POLICY=1, HANDLE_LIST |
| Selected inherited handles | None; `bInheritHandles=false` | Three pipe ends; `bInheritHandles=true` |
| STARTF_USESTDHANDLES | Unset | Set (`0x100`); stdin reads, stdout/stderr write |
| Desktop pointer | NULL from zeroed structure | NULL from zeroed structure |
| Environment producer | `_IsolationAPI.environment(same scratch)` | Same method, called separately |

Both environment calls produce six keys: SystemRoot, WINDIR, PATH, TEMP, TMP and LOCALAPPDATA. The first three derive from `GetWindowsDirectoryW`; PATH contains only System32. TEMP/TMP select the same scratch directory. LOCALAPPDATA comes from the current user's known folder through `SHGetKnownFolderPath`, not an observed AppContainer-specific value. Both serialize with the same sorted Unicode helper. Exact historical environment values/bytes were not serialized, so byte equality is **UNKNOWN**. No environment change is justified from this gap alone.

The pipe producer requests inheritable handles and clears inheritance only on parent ends. The isolated launcher checks selected handle inheritance, supplies a handle list, and installs the three standard handles. That source evidence does not independently prove child-side standard handle usability. Microsoft states that these fields are copied without validation; it does not identify stdio as this failure's cause. The two inspected launch bodies do not set additional UI restrictions or a mitigation-policy attribute. Inherited/OS state outside them is not established. [CreateProcessW standard handle responsibilities](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).

The actual path receipt reports native image length 233 and directory length 206, both below its exclusive bound 258. This rules out a failure of that particular preflight bound, not every loader or CRT path assumption. The ordinary control uses a different mode and stdio arrangement; liveness is not evidence that it completed the probe or that all initialization/API paths were equivalent. Rust `probe` begins at line 207, prints its JSON only at line 241, and `main` begins at line 245. With no entry marker, empty stdout does not establish whether Rust `main` was reached. Runtime API ordering and the last completed operation remain **UNKNOWN**.

The supplemental file parser confirms PE32+ AMD64, 19 sections and 191 normal imported symbols across these eight descriptors:

| Direct import descriptor | Imported symbol count | Selected observation |
| --- | ---: | --- |
| api-ms-win-core-synch-l1-2-0.dll | 3 | WaitOnAddress, WakeByAddressAll, WakeByAddressSingle |
| bcryptprimitives.dll | 1 | ProcessPrng |
| ADVAPI32.dll | 4 | ConvertSidToStringSidW, GetTokenInformation, IsTokenRestricted, OpenProcessToken |
| KERNEL32.dll | 122 | Includes GetLastError and SetLastError |
| msvcrt.dll | 28 | Statically declared imports despite recorded crt-static compiler option |
| ntdll.dll | 6 | NtCreateFile, NtCreateNamedPipeFile, NtOpenFile, NtReadFile, NtWriteFile, RtlNtStatusToDosError |
| USERENV.dll | 1 | GetUserProfileDirectoryW |
| WS2_32.dll | 26 | Socket API imports |

The worker declares no delay-import directory. Its optional header at file offset 152 declares required OS 4.0, subsystem version 5.2 and Windows character subsystem 3. These raw header fields do not establish compiler target defaults, the supported minimum Rust platform, or a Windows XP-related cause. DllCharacteristics `0x0160` declares high entropy VA, dynamic base and NX; the AppContainer header bit is clear. The parent nevertheless recorded an AppContainer token. Static declarations do not prove runtime enforcement, successful initialization or native isolation. [Microsoft PE format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).

Seven direct DLL names have readable current System32 candidate files. The parser preserves each candidate's SHA-256, sections, normal/delay imports and selected exported forwarders. This is a one-level file graph, not the failed process's module list. Selected concrete next edges are:

| Current System32 candidate | Normal concrete edges (API-set names omitted here) | Delay concrete edges (API-set names omitted here) |
| --- | --- | --- |
| bcryptprimitives | ntdll | none declared |
| ADVAPI32 | msvcrt, ntdll, KERNELBASE, SECHOST, KERNEL32, RPCRT4 | CRYPTSP, WINTRUST, CRYPTBASE, SspiCli, USER32, CRYPT32, bcrypt |
| KERNEL32 | ntdll, KERNELBASE | RPCRT4 |
| msvcrt | ntdll, KERNELBASE | none declared |
| ntdll | none declared | none declared |
| USERENV | RPCRT4, ntdll | SspiCli, IPHLPAPI, DNSAPI, netutils, logoncli, profapi, cldapi |
| WS2_32 | ntdll, RPCRT4 | NSI |

API-set edges, including the worker's synchronization contract, are left unresolved. Delay edges do not prove those DLLs were loaded or initialized. Names such as USER32 or profapi in this graph are not culprit evidence. The fixture assets directory currently contains only the worker and allowed.txt, with no app-local DLL observed in that directory. Actual API-set hosts, KnownDLL resolution, SxS/redirection, dynamic loads and deeper dependencies were not recovered. Windows' loader may resolve dependencies by module name even when a parent module used a full path. [DLL search order](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order). Complete bounded records are [PE-DEPENDENCIES.json](T:/00-Active/Project-AI-CETA/.agents/runtime/ac7-startup-diagnosis-20261020/PE-DEPENDENCIES.json) and [DEPENDENCY-SUMMARY.json](T:/00-Active/Project-AI-CETA/.agents/runtime/ac7-startup-diagnosis-20261020/DEPENDENCY-SUMMARY.json).

Installed REA 6.7.0, matching workflow version 42, used the target-free Rust dependency reader. Evidence ID `ev_ebaab34d447134bcdee04332fd57bcbf01e9d6805c174ba3eac615af8a66f3ab` binds the exact attempt copy and observes no `.dep-v0` metadata. That means cargo-auditable package metadata is unavailable, not that dependencies are absent. The embedded rustc commit path at offset 668350 is explicitly an inference. REA did not recover functions, call ordering, loader phases or runtime behavior. Full inline Evidence and the exported bundle are preserved; `close_binary` returned null. No native engine was opened, so no RAM-dependent Ghidra work was required. Earlier Java/Ghidra/objdump failures were not retried.

The parent's existing 09:34:50–09:35:10 UTC Application, System, CodeIntegrity, AppLocker and Defender queries each have exact error ID `NoMatchingEventsFound,Microsoft.PowerShell.Commands.GetWinEventCommand`, zero examined events and empty matching arrays. The generic wrapper label `NO_RESULT_OR_INACCESSIBLE` is broader than these actual errors; no access-denied error is recorded. This finite query returned no matching events. It does not refute DLL initialization failure or prove an event was never recorded elsewhere/later.

| Unresolved explanation | Current support | What prevents a causal finding |
| --- | --- | --- |
| Principal/capability-sensitive DLL, CRT or TLS initialization | AppContainer worker fails; ordinary image remains alive; status denotes DLL initialization failure | No failing module, phase trace, matched mode/path/stdio control or entry marker |
| Volume GUID executable/current-directory path sensitivity | Exact path spellings differ | Length preflight passed; no component-specific failure evidence |
| Mode/stdio/environment-dependent initialization or later dynamic loading | `probe` differs from `hold`; handles differ; environment bytes not retained | No isolated hold result, child-side stdio observation, exact environment capture or last-operation marker |

All three remain hypotheses. A missing DLL name, a GNU target defect, a profile defect, blocked registry access, Defender intervention, an invalid pipe, or a particular dependency failure is not established. No containment weakening or toolchain change follows from this evidence.

One concrete next measurement is a separately reviewed, single startup-only attempt of the **same image** with `hold 250`, preserving the failed worker's AppContainer SID/zero capabilities, job/child policy, volume GUID executable/cwd, exact captured six-key environment, and three redirected standard handles. Capture exact launch inputs and raw stdout/stderr, token measurement and terminal status through the existing owned retirement path. This is a proposed measurement only: it was not implemented, launched or released here. A successful completion would show that this isolated configuration can reach the hold branch and narrow the difference to probe-specific paths; the same failure would retain the common startup path as a candidate without naming a DLL. A changed image or relaxed policy would weaken that comparison. The parent must retain its normal review/release boundary before any such attempt.

Collection finished with zero drift across 33 primary inputs, including all three worker copies; supplemental service source also matches its attempt snapshot and stayed unchanged. The first collector invocation failed because its review script incorrectly expected the qualification tool in the candidate-only snapshot; its failure is preserved and the collector now checks the separate actual tool receipt. The successful collection and supplemental receipt checks are file-only controls, not additional native or application acceptance. Remaining startup cause is classified **requires separate follow-up measurement; blocking positive AC7 qualification**, while evidence collection and this diagnosis are complete.
