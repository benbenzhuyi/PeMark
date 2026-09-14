# Roadmap from V8.4.23 to V8.5+

## V8.4.24 — Stabilization / Handoff Candidate

No new user features.

- rewrite ViewController ownership
- rewrite OutlineController navigation
- consolidate custom scrollbar state/geometry or temporarily choose a stable reference behavior
- add debug instrumentation option
- pass full regression suite

Acceptance: no known P0 bug in agreed test matrix. It may still have documented technical debt.

## V8.5.0 — Generator architecture baseline

- split logical emitter modules
- add PE layout allocator / increase code region
- symbol map output
- structured Win64 function frames
- central AppState/Layout/Palette

## V8.5.1 — Unified Markdown parser

- one parse feeds Render/Outline/PositionMap
- explicit fenced-code state
- parser test corpus

## V8.5.2 — Dynamic/arena document structures

- reduce giant fixed BSS
- remove 2048 Outline hard cap
- consider VirtualAlloc arenas

## V8.5.3 — PE hardening

Still no external compiler/linker, but generate cleaner PE:

- separate sections
- optional relocations + ASLR
- optional `.pdata` unwind metadata
- read-only data where possible
- eliminate RWX section if feasible

## Later product features

Only after architecture stability: tabs, file browser, richer Markdown, autosave/session, AI integrations, plugin/API integration, etc.
