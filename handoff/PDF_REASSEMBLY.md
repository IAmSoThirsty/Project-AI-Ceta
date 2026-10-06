# Preserved Codex reference PDF

The GitHub account rejected Git LFS with: "This repository exceeded its LFS budget."
The owner's authorized alternative stores this one reference PDF as two ordinary
Git files in `assets/reference-parts/`. Both parts are below 100 MiB. The complete
original PDF remains unchanged in the author's local repository.

After cloning, run from the repository root with Python 3.10 or later:

```powershell
python tools/reassemble_codex_pdf.py
```

This creates `sources/codex/Thirstys_Codex_Standards_Edition_Volume_01_Foundations_and_Governance.pdf` using Python's standard library and the ordered part manifest.
Each part and the complete output are checked with SHA256. An existing identical
PDF is verified without rewriting it; different existing content is preserved and
the command fails. Publication uses an atomic no-overwrite hard link in the output
directory; the destination filesystem must support hard links. NTFS is supported.
The reconstructed PDF is ignored by Git because the two parts preserve its bytes.

Expected output: **143878071 bytes**, SHA256 **072721b27af19ffa909eae0b4e564e7c56db81269fb121102bc82cb9d293edb8**.

For a disposable verification output, use:

```powershell
python tools/reassemble_codex_pdf.py --output <new-existing-directory>/reference.pdf
```

The exact commit mappings, local backup identities, and LFS rejection are recorded
in `handoff/GIT_PDF_SPLIT_PUBLICATION_20261020.json`. Earlier LFS migration records
describe the completed local attempt; this ordinary Git split supersedes it for
publication. Existing source text extractions, source digests, implementation,
tests, acceptance evidence and product status remain preserved. This transport
change establishes source publication and reference recovery, not product acceptance.
