# PeMark V8.5.2 Preview

English | [简体中文](RELEASE_V8_5_2_PREVIEW.zh-CN.md)

V8.5.2 is the document-safety release. It keeps the pure Direct-PE build:
Python emits the PE32+ image and AMD64 instructions without a compiler,
assembler or linker. No behavior was traded for the safety guarantees below.

## Added

- 64-bit `document_revision` and `saved_revision`. Unsaved state is derived from
  revision equality only; there is no independent dirty flag.
- One unsaved-change controller shared by New, Open, Exit and window close, with
  Save / Discard / Cancel. A failed save cancels the destructive transition and
  keeps the document.
- Transactional Save As: the chosen path is a candidate until the write
  succeeds and its handle closes.

## Fixed

- Save now writes a sibling `.pemark.tmp` staging file, loops until the whole
  snapshot is written, flushes, checks the close result and commits with
  `MoveFileExW(REPLACE_EXISTING | WRITE_THROUGH)`. The previous target survives
  every tested pre-commit failure; a preexisting staging artifact is preserved
  and reported instead of being truncated.
- A one-shot `WriteFile` call could silently accept short writes. Partial
  progress now advances the buffer, and zero progress, API failure or an
  oversized count fail the save.
- Open previously disturbed view, path and model state before the new document
  was known to be readable. Read, decode and both arena reservations now finish
  before one commit point; failure leaves text, path, revisions, encoding, EOL
  and view mode untouched.
- Open read once and accepted whatever arrived. It now loops until the file-size
  snapshot is fully read and rejects zero progress.
- Malformed UTF-8 silently fell back to the ANSI code page. UTF-8, UTF-8 BOM and
  UTF-16LE BOM are now explicit, strict paths; malformed UTF-8, embedded NUL and
  odd-length UTF-16 are rejected.
- Encoding and preferred line ending are committed with the document, so saving
  preserves UTF-8, UTF-8 BOM or UTF-16LE BOM and CRLF, LF or CR output.

## Capacity

- The 2048-entry Outline limit and the 131072-entry Markdown style limit are
  retired. Both tables now live in `VirtualAlloc` arenas sized from the
  normalized document length and reserved before the Open commit point.
- A 140,000-span document records every span; the previous build truncated at
  131,072.

Full dynamic-capacity work, including the remaining fixed document, render,
position-map and encoded-output buffers, continues as V8.5.3.

## Validation

- 13/13 emitted-machine-code behavior groups, including 210/210 scrollbar
  boundary combinations.
- 17/17 Windows GUI smoke checks.
- 5/5 ordinary WM_CLOSE runs returned exit code 0.
- Open transaction and strict-encoding matrix: UTF-8, UTF-8 BOM, UTF-16LE BOM,
  LF, CRLF and CR round trips, including empty BOM files; malformed input keeps
  the previous document.
- Atomic-save fault injection: short write completion, zero-progress rejection,
  first-call failure, partial-then-failure, flush failure, replace failure,
  staging-create failure and close failure with cleanup retry.
- Destructive-transition matrix: clean close; Cancel/Discard/Save for dirty close
  and New; Open decision cancel and picker cancel; failed save during close.
- Arena allocation-failure injection for both Outline and style tables.
- Two consecutive builds produced the same binary.

Release asset:
`pemark_x64_v8_5_2.exe`

SHA-256:
`2c105660dbac96b7de18614f43753073b3b5613e22bba160ceb8058646040e30`

## Preview limitations

The document, render, position-map and encoded-output buffers are still fixed
sizes; oversized input is rejected explicitly rather than truncated. Legacy code
pages are no longer accepted as a fallback, so non-UTF-8 documents must be
converted first. Code signing, ASLR and separated PE section permissions are not
implemented yet, long-running memory-plateau measurements are outstanding, and
the workspace and AI features are not part of this release. Keep backups of
important documents.
