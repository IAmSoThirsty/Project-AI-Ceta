# Collaborative publication review: preliminary findings

Reviewer: `/root/publication_review`. Scope: current Project-AI: CETA Git checkpoint and upload request. This review does not resume product implementation or execute product/native tests.

## Verified observations

- Git root is `T:/00-Active/Project-AI-CETA`; branch is `candidate/societal-reasoning-v1`; pre-publication HEAD is `83fc9432b4a37ee7f91d6c5b0d358a015548aed4`.
- Nineteen tracked files were modified at initial inspection. The initial Git index was empty. Local branches include `build/standalone` and `candidate/societal-reasoning-v1`.
- `.git/info/exclude:9` ignores the entire `.agents/` tree, including authored private candidates. Ordinary `git add -A` would omit that work. It requires deliberate selection without activating its code in canonical `src/ceta`.
- `.tmp/` contains 316 untracked transient executors/duplicate extracted material. Inspected `.tmp/neo_exec_3361c3d4.bat` targets the separate `T:/00-Active/CETA-NATIVE-ARCHITECTURE` repository. Preserve locally and exclude from this publication snapshot.
- `.github/instructions/codacy.instructions.md` is IDE agent configuration. The attempted backslash ignore does not currently exclude it. It is not a product dependency.
- `native/sqlite_runtime/win-x64/sqlite3.dll` is a 3,285,504-byte declared product dependency. Its adjacent README and `contracts/SQLITE_RUNTIME_V1.json` preserve official SQLite provenance and pinned digest. It must not be lost under blanket binary exclusions.
- The latest private AC7 loader candidate contains four authored Python files, with exact identities in `.agents/runtime/ac7-loader-capture-20261020/HALT-RECEIPT.json`. It remains incomplete and unqualified for native execution.
- Private real-effect entrypoint changes and joined JS9 source remain candidates. Publication under their original `.agents/` paths does not establish canonical integration or product acceptance.
- The root halt checkpoint preserves 2,622 start/stop events with one test failure; final report construction also failed with `KeyError: native_after_fixture_cleanup`. Source publication and product acceptance remain false. Preserve the raw logs, case events and both failures.

## Review checks and limitations

- Installed `codex-repo-preservation` and `codex-secret-exposure-auditor` self-tests each passed their four bundled source-hash checks.
- The exact latest user prompt was retained in `USER-PROMPT.txt`; prompt-check reported SHA-256 `8148359f0824e28a2183207acb249de2b25aad9f2bbc1d3b9e82566c0929a879`, no unverified critical terms, and incomplete dictionary coverage. No full dictionary verification is claimed.
- The installed secret audit sampled 5,000 text files, found no configured secret patterns, and retained `skill-secret-scan.json`. The sample mostly covers early archived cuts; it is not a final staged-tree audit.
- Its 5,000 POSIX-mode access warnings do not establish actual Windows ACL exposure. No Windows ACL remediation is warranted from that heuristic alone.
- A broad metadata inventory stopped with WinError 3 on a long physical-target snapshot path. No inventory-completeness claim is made. The exception is preserved in the tool record; no files were removed or modified by that inventory.
- Include authored `.diff`, `.patch`, `.stdout`, `.stderr`, `.log`, `.jsonl`, `.lock`, and `.def` material as applicable, alongside ordinary source/docs/config, to preserve meaningful evidence and build inputs.
- Exclude environments, caches, disposable/native fixtures, local credentials, private keys, databases and unrelated temporary executor payloads. Preserve all such files locally. Exact final exclusions must be recorded rather than silently discarded.

## Disposition

Preliminary review only. Awaiting Root's exact staged tree, path inventory and exclusions for final independent publication review. This is not product acceptance, an installed-runtime qualification or authorization for additional native effects.
