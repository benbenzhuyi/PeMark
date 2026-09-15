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
