# Large-File Design and Performance Guide

## Current limits

- input bytes: 4 MiB
- document text: reserved arena, policy bound 8.5M units, committed in 512 KiB blocks
- decode/serialize scratch and file bytes: arenas committed in 64 KiB blocks,
  sized per operation (no fixed cap)
- render->source map + render text: dynamic arena, `max(4096, normalized_length + 1)` units
- style spans: dynamic arena, `max(4096, normalized_length/2 + 16)` entries
- Outline entries: dynamic arena, `max(4096, normalized_length/4 + 1)` entries
- total virtual BSS: 8 KiB; PE virtual size 86 KB

The frozen V8.5.2 pre-arena baseline registered exactly 2048 of 2600 headings.
The first Phase E migration replaces the three fixed Outline arrays with one
contiguous `VirtualAlloc` block. Capacity is derived from canonical document
length with a 4096-entry minimum and retained for reuse. The 2600-heading fixture
now registers all entries and passes first/middle/last Source navigation.

The second Phase E migration does the same for the three style-span columns,
retiring the 131072-entry table. Both arenas are reserved before the Open commit
point, publish their pointers only after a successful allocation, and keep the
previous arena intact when growth fails. A 140,000-span fixture confirms that
formatting metadata is no longer truncated.

The third migration covers the render side: the position map and the render text
share one arena sized from the canonical document length, and the scanner's
overflow guard reads the published capacity instead of a constant. The document,
decode and encoded-output buffers are still fixed.

The fourth migration moves the document text itself: the policy bound is
reserved once as address space, pages are committed in 512 KiB unit blocks as
content grows, and the editor text limit keeps using the same policy bound so no
user-visible behaviour changes.

The fifth migration removes the last two fixed buffers: decode/serialize scratch
and file bytes are now committed in 64 KiB blocks sized by the operation, and the
encoding APIs read their limits from the published capacity. No fixed document,
render, style, Outline, decode or file-byte array remains, so the image no longer
declares a large virtual region.

## Lessons from V8.4.x

- Large-file crashes were not simply 'buffer too small'; one major issue was x64 stack misalignment in Outline rebuilding.
- RichEdit per-style full-document formatting caused ~10-second Preview transitions on ~0.9MB Markdown.
- Zoom should use `EM_SETZOOM`; reparsing on every zoom is unacceptable.
- Theme changes must not reflow/reparse the whole document.
- UI updates during load should suppress redraw until state is coherent.

## Target strategy

- parse only on document revision changes
- cache RenderModel/Outline/PositionMap by revision
- format Preview by viewport
- preserve caret and top-visible anchor in source coordinates
- debounce maintenance after wheel activity
- consider VirtualAlloc-backed arenas instead of giant fixed BSS in V8.5.x

## Performance measurements to capture on Windows

For 1KB / 500KB / 887KB / 1.2MB:

- open-to-source-visible ms
- source->preview ms
- preview->source ms
- Outline build ms
- first Outline jump ms
- wheel FPS/latency feel
- theme switch ms
- zoom latency
- memory working set / commit

Codex should add a diagnostic timing build rather than relying on subjective screenshots.
