# Current Code Audit — V8.4.23

> Historical audit of the frozen V8.4.23 handoff. The current public baseline is
> V8.5.1 Preview; see `V8_5_1_MERGE_RESULTS.md` and
> `../CHANGELOG_UNRELEASED.md` for resolved findings and active release gates.

## Snapshot facts

- Generator: `generate_markdown_editor_v8_4_23.py`
- Generated EXE: `45056` bytes
- EXE SHA-256: `50fdb51c28a90f9457d61761c923cd54f668de040e81941d99030fc42f2f2f4f`
- Generator SHA-256: `579ac6165d62b39ebe2a0019f9d9b817d9a9874911f491b8f92ed8e370733992`
- PE32+ AMD64, GUI subsystem.
- Fixed image base `0x140000000`.
- One RWX section; no relocations/ASLR.
- Text RVA `0x1000`, RDATA `0x8000`, IDATA `0xB000`, BSS `0xC000`.
- Emitted text length: 27426 bytes; text budget before RDATA: 28672; remaining headroom: **1246 bytes**.
- Virtual BSS: 121106432 bytes (115.50 MiB).
- Fixed file input cap: 4 MiB.
- Wide buffers: 8,500,000 UTF-16 code units.
- Markdown style span cap: 131,072.
- Outline entry cap: 2,048.
- Emitted labels: 443.

## P0-001 — Preview Outline navigation targets EOF / invalid location

**Status:** root cause confirmed in source.

Current `navigate_outline` sequence near source lines 2106–2121:

1. `LB_GETCURSEL` returns item index in `RAX`.
2. Code converts it to byte offset (`index*4`) in `RAX`.
3. If `preview_flag != 0`, it calls `IsWindowVisible(hwnd_preview)`.
4. `IsWindowVisible` returns 0/1 in `RAX` and is allowed to clobber volatile registers.
5. Code then uses **that new RAX** as the byte offset into `outline_srcpos`.

This violates Win64 register lifetime rules. A true return usually makes offset=1 (misaligned byte access), producing a garbage source offset; `map_source_to_render` often resolves it to render end, matching field behavior where every Outline item jumps to document EOF.

**Required fix/refactor:** Do not patch by moving one instruction only. In the stabilization refactor, capture the selected Outline entry's canonical source offset into a nonvolatile register/BSS/stack local before any API call. Better: `navigate_outline` obtains `sourceOffset` first, then asks ViewController which surface is active.

## P0-002 — Custom Outline scrollbar has no usable thumb / cannot drag

**Status:** field symptom confirmed; exact root cause not yet proven. Current code has excessive ownership dispersion.

Scrollbar state is spread across:

- thread message pump (`WM_MOUSEMOVE`, button events, wheel)
- `update_outline_hover`
- `sync_outline_scrollbar`
- `outline_scroll_drag_move`
- `resize_children`
- custom `scrollproc` paint window
- palette/theme code

The current design computes/consumes thumb geometry in several places and physically hides/shows the custom child HWND. Field testing reports surface/gutter appearance without a draggable thumb.

**Do not continue local repaint patches.** Refactor to a single `OutlineScrollState`; one `scroll_layout()` calculates and stores track/thumb rectangles. `scroll_paint`, hit-test, page click and drag must use the same cached rect.

## P1 — multiple view-state authorities

V8.4.x accumulated `preview_flag`, actual HWND visibility and `view_hwnd`. V8.4.23 attempts reconciliation using `IsWindowVisible`, but that introduces both complexity and the P0-001 register bug. Replace with one ViewController state and enforce visibility from it.

## P1 — independent parser paths

Outline building and Preview rendering still scan Markdown separately. This can cause parser-state divergence (especially around fenced code, headings, inline constructs). V8.5 should share one parse stream/model.

## P1 — hard caps

- Outline: 2048 entries. `tests/outline_2600_headings.md` intentionally exceeds this.
- Style spans: 131072.
- Input: 4 MiB.
- Work buffers: large fixed BSS arenas.

Document all expected failure modes rather than silently truncating.

## P1 — PE text region is almost full

Only **1246 bytes** remain before fixed `RDATA_RVA=0x8000`. This is a critical engineering constraint. Major code changes can trigger `text overlaps rdata`. Before V8.5 growth, change the PE layout strategy.

## P2 — experimental PE security/hardening debt

- one RWX section
- no ASLR/relocations
- no x64 unwind `.pdata`
- no CFG metadata
- large static virtual BSS

These are acceptable for the experimental handoff but should be explicitly tracked.

## Recommended stabilization scope

V8.4.24 should change only:

- ViewController / Outline navigation
- Outline scrollbar controller/state
- optional diagnostics build support

Do not touch parser/render/theme/file I/O unless a test proves necessity.
