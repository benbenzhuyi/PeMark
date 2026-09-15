# Large-File Design and Performance Guide

## Current limits

- input bytes: 4 MiB
- UTF-16 work buffers: 8.5M code units each
- byte output buffer: 34.5M bytes
- render->source map: 8.5M x 4 bytes
- style spans: 131072 x (start,end,type)
- Outline entries: 2048
- total virtual BSS: ~115.5 MiB

The frozen V8.5.2 pre-arena baseline registered exactly 2048 of 2600 headings.
The first Phase E migration replaces the three fixed Outline arrays with one
contiguous `VirtualAlloc` block. Capacity is derived from canonical document
length with a 4096-entry minimum and retained for reuse. The 2600-heading fixture
now registers all entries and passes first/middle/last Source navigation.

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
