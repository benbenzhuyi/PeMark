# Development Manual — Pure Binary Native Windows Development

## Purpose

This manual is the practical day-to-day guide for continuing PeMark, the
Direct-PE Markdown Editor, with Codex or another coding agent. The project is
deliberately not a normal Python GUI application: Python is only the build-time
emitter; the output is a native Windows AMD64 PE executable.

## 1. Golden workflow

For every change:

1. Read the relevant architecture/issue docs.
2. Reproduce the current baseline and hash it.
3. Create a branch/copy for one bounded subsystem change.
4. Add or identify a deterministic regression test first.
5. Modify the generator.
6. Run Python syntax + PE static inspection.
7. On Windows, run the exact regression sequence.
8. Capture timings/state/logs, not just screenshots.
9. Update changelog, known issues, and hashes.
10. Only then move to the next subsystem.

## 2. Build model

```text
Python source generator
    -> bytearrays for code/rdata/imports
    -> x86-64 opcodes + rel32/RIP fixups
    -> PE headers/section
    -> final .exe
```

No compiler/assembler/linker may be inserted into the production path. Disassemblers/debuggers are allowed for analysis.

## 3. Current source organization

The current generator retains the V8.4 lineage's monolithic emitter shape with
these conceptual areas:

- constants/RDATA strings
- BSS symbol allocation
- import table builder
- x64 emitter class
- startup/window creation
- message pump
- command handling
- file I/O and decoding
- Source/Preview toggling
- Outline and scrollbar handling
- Markdown parser/render buffer/style map
- theme/layout/status logic
- custom WndProcs
- PE writer

V8.5 should preserve behavior while splitting these into explicit build-time emitter modules or clearly separated sections.

## 4. Safe emitted-function template

Before writing machine-code bytes, document:

```text
routine name:
inputs:
returns:
BSS reads:
BSS writes:
nonvolatile regs saved:
volatile values that must survive calls:
Win32/internal calls made:
stack frame size/alignment:
```

Then emit prologue/body/epilogue. Treat every call as destroying volatile registers.

## 5. State ownership

Never solve a UI problem by adding another independent flag.

Target ownership:

- Document text -> DocumentModel
- SOURCE/PREVIEW -> ViewController
- Outline entries/navigation -> OutlineController
- scrollbar geometry/drag -> OutlineScrollState
- all pane rectangles -> LayoutManager
- colors/brushes -> ThemePalette
- parsed Markdown semantics -> Parser/RenderModel

## 6. Debug builds

Strongly recommended: add a generator option such as `DEBUG_DIAGNOSTICS=True` that conditionally imports/uses `OutputDebugStringW` and emits state traces. Do not rely on visual inference for complex message ordering.

Useful diagnostics:

```text
DOC revision len
VIEW mode, visible HWNDs
OUTLINE selected index/source offset
MAP source->render result/render_len
SCROLL count/rows/top/max/track/thumb rect/drag
LAYOUT rectangles
THEME palette id
```

## 7. Windows test loop

Use a clean cold start when testing first-load defects. Tests that begin after several mode toggles may hide initialization bugs.

Always test:

- Source immediately after Open
- first Outline click
- first Ctrl+Shift+P
- first Preview Outline click
- beginning/middle/end navigation
- long Outline thumb drag
- Light/Dark immediately before hover reveal
- large document after cold start

## 8. Binary size/layout discipline

V8.5.3 uses the expanded layout documented in
`docs/PE_MEMORY_MAP_V8_5_3.md`. A code-overlap exception remains a
build-layout failure and must never be bypassed.

Long-term prefer a PE layout allocator and multiple sections while remaining direct-generated.

## 9. Versioning

- V8.4.23: frozen handoff snapshot.
- V8.4.24: stabilization only.
- V8.5.1: previous public Preview baseline.
- V8.5.3: current public Preview baseline (document safety).
- V8.5.3: dynamic capacity. V8.5.4: PE hardening.

Do not label a build 'stable' unless the regression matrix has actually passed on Windows.

## 10. Documentation maintenance

When behavior changes, update at least one of:

- `docs/CURRENT_CODE_AUDIT.md`
- `docs/FEATURE_AND_SHORTCUT_SPEC.md`
- `docs/WIN32_API_SURFACE.md`
- `docs/REGRESSION_TEST_PLAN.md`
- `docs/VERSION_HISTORY.md`
- `docs/DECISION_LOG.md`

The handoff package is intended to replace reliance on the original ChatGPT conversation.
