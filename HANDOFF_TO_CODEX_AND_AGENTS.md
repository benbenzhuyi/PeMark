# Handoff to Codex and Other Agents

> Historical V8.4.23 handoff context. For the current V8.5.2 Preview baseline,
> start with `CODEX_START_HERE.md` and `docs/V8_5_2_RELEASE_RESULTS.md`.

## Executive summary

The project began as a demonstration that useful Windows software could be generated as a PE32+ x64 executable without a traditional compilation toolchain. It grew from a tiny Notepad into a Markdown editor with file I/O, menus, shortcuts, find/replace, zoom, word-wrap, status bar, Source/Preview modes, Outline, Light/Dark themes, Markdown formatting, large-document support and position mapping.

The experiment succeeded technically, but the V8.4.x line exposed the limits of patch-driven development in a single large byte-emitter script. The handoff goal is therefore **not merely to fix two bugs**. It is to preserve the Direct-PE achievement while moving state, parsing, layout, theme, navigation and rendering behind explicit ownership boundaries.

## What is known to work reasonably well in the current lineage

- Direct PE32+ generation and loader compatibility.
- Native Win32 window/menu/edit control creation.
- UTF-8/ANSI/UTF-16LE loading paths and CR/LF normalization.
- Save as UTF-8.
- Standard editing/menu operations and accelerators.
- Source-mode editing and Markdown insertion commands.
- Large-file opening after x64 stack-alignment fixes.
- RichEdit Preview and semantic style application.
- Source↔Preview render-source map concept.
- Viewport-lazy semantic formatting concept for large Preview documents.
- Outline parsing and source-position storage concept.
- Dark/Light palette and status/menu custom painting, though UI theming remains fragile.

## Historical handoff snapshot

`archive/generators/generate_markdown_editor_v8_4_23.py` / matching
`archive/binaries/direct_pe_markdown_editor_x64_v8_4_23.exe`.

This snapshot is an **active development state, not a stable release**. Use the archive to compare regressions.

## Immediate P0 defects

See `docs/CURRENT_CODE_AUDIT.md`. In short:

- Preview Outline navigation uses a clobbered `RAX` after `IsWindowVisible`, producing invalid source offset lookups and often mapping to end-of-document.
- Custom Outline scrollbar is architecturally distributed and currently does not reliably present a draggable thumb in field testing.

## Why the archive matters

Some older versions are useful behavior references:

- V8.4.17: viewport-lazy Preview formatting transition.
- V8.4.19: independent native scrollbar gutter solved ListBox item/scrollbar overlap but had classic visual style.
- V8.4.20–23: custom scrollbar experiments; useful as negative/partial references, not as unquestioned foundations.

Diff the generators to understand exactly which machine-code sequence changed.

## Recommended takeover sequence

1. Tag the package exactly as received.
2. Reproduce the V8.4.23 binary hash.
3. Run static inspection.
4. On Windows, reproduce P0 issues.
5. Add debug instrumentation build capability (recommended: import `OutputDebugStringW` only in a debug variant) so state can be logged without disturbing release semantics.
6. Build V8.4.24-stabilization with only ViewController + OutlineController ownership refactors.
7. Run the full regression matrix.
8. Only after stabilization, begin V8.5 parser/layout/theme modularization.

## What not to do

- Do not keep stacking `InvalidateRect/RedrawWindow/ShowWindow/SetWindowTheme` calls until a screenshot looks right.
- Do not preserve values in volatile registers across Win32 calls.
- Do not maintain source position and preview position as two independent canonical arrays.
- Do not tie view mode to both a flag and actual HWND visibility without one controller enforcing the invariant.
- Do not add new features before stabilizing state ownership.
