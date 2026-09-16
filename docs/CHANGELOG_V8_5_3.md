# PeMark V8.5.3 (unreleased)

V8.5.2 shipped; its full record is `docs/CHANGELOG_V8_5_2.md`.

## Render arena (position map + render text)

- Moved `render_srcmap` and `previewbuf` from fixed 8.5M-unit BSS arrays into one
  contiguous `VirtualAlloc` arena holding `[map: 4 bytes/unit][text: 2
  bytes/unit]`. Capacity is `max(4096, normalized_length + 1)` units, reserved
  before the Open commit point and never shrunk during a process lifetime.
- The render scanner now bounds its output index by the published arena capacity
  instead of a compile-time constant, and the RichEdit load path and both
  source-mapping readers use the published pointers.
- Added `ARENA_ALLOC_INJECTION_MODE` render modes (`render_fail_first`,
  `render_fail_second`) and `tools/test_v8_5_3_render_arena.py`. The test checks
  arena geometry, mapping range and monotonicity, preview loading, and that both
  a failed first allocation and a failed growth allocation leave the document,
  path, revisions and the previous arena intact.
- Virtual BSS drops from 119,508,992 to 68,509,696 bytes; emitted text grows from
  29,466 to 29,757 bytes.
- Verified with the existing V8.5.2 suites on the V8.5.3 channel: 13/13
  machine-code groups, Open/encoding transaction matrix, atomic save fault
  injection, destructive transition matrix, revision ownership, Outline and
  style arena failure, 140000-span capacity and the 17/17 GUI smoke suite.

## Document arena (reserved policy bound + block commit)

- Replaced the fixed `WIDE_CHARS`-unit `document_model` array with a reserved
  arena: the policy bound stays `WIDE_CHARS` units (17 MB of address space) and
  physical pages are committed in 512 KiB unit blocks only as content grows.
  The editor text limit and the normalization bound keep using `WIDE_CHARS`, so
  visible behaviour is unchanged.
- Open reserves the document arena before its commit point in all four decode
  branches. Editor sync reserves the length it is about to read and, when the
  commit fails, restores the editor from the unchanged model instead of leaving
  the control and the model out of step. New requires the same reservation and
  leaves the current document alone if it fails.
- Fixed a defect introduced during this migration: the normalization loop's new
  capacity guard reused `rax`, which held the current source character, so every
  character was written as the low half of `capacity - 3`. The guard now uses
  `rdx`, and the block-size mask uses `~(CHUNK - 1)`.
- Added `document_fail_first` / `document_fail_second` injection modes and
  `tools/test_v8_5_3_document_arena.py`: reservation is reused across Open, the
  commit grows in aligned blocks for a 1.2 MB document, editor edits commit
  further blocks, a failed commit preserves text, path, revisions and prior
  contents, and a failed first commit leaves the reservation unpublished.
- Virtual BSS drops from 68,509,696 to 51,511,296 bytes. The remaining fixed
  buffers are `widebuf` (decode/serialize scratch) and `bytebuf` (file bytes).
- Re-verified on the V8.5.3 channel: 13/13 machine-code groups, Open/encoding
  transaction matrix, atomic save fault injection, destructive transition
  matrix, revision ownership, Outline/style/render arena failure, 140000-span
  capacity and the 17/17 GUI smoke suite.

## Scratch arenas (decode/serialize + file bytes) and memory plateau

- Replaced the last two fixed buffers. `widebuf` (decode/serialize scratch) and
  `bytebuf` (file bytes and encoded output) are now arenas committed in 64 KiB
  blocks and sized by the operation: Open reserves `file_bytes + 2` bytes and
  `file_bytes + 1` units before reading, Save reserves `document_len + 1` units
  and `4 * document_len + 3` bytes before encoding, and both search helpers
  reserve the editor snapshot length. Encoding API limits now come from the
  published capacities instead of compile-time constants.
- Virtual BSS falls from 51,511,296 to 8,192 bytes and the PE virtual size from
  51,589,120 to 86,016 bytes: no fixed document, render, style, Outline, decode
  or file-byte array remains.
- Added `wide_fail_first/second` and `byte_fail_first/second` injection modes and
  `tools/test_v8_5_3_scratch_arenas.py`: arenas start empty, grow in aligned
  blocks with the document, are reused and never shrunk, Save encodes through
  them, and an injected failure preserves text, path, revisions and the previous
  arena. Arena capacity that was already committed stays reusable, which is
  cache rather than document state.
- Added `tools/test_v8_5_3_memory_plateau.py`, the V8.5.3 exit gate: 12 cycles of
  Open(parse-only) + Preview(parse) + New over small/medium/large fixtures show
  zero handle growth and about 1.6 MB of private-memory growth between the first
  and last quarter of the run, i.e. a stable plateau rather than unbounded
  growth.
