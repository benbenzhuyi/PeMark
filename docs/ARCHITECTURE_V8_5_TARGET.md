# V8.5 Target Architecture — Detailed Design

## 1. Goals

Preserve the project's defining property — **a native Windows x64 EXE generated directly from Python without compiler/assembler/linker** — while replacing patch-driven global state with explicit domains and controllers.

The target is not an object-oriented rewrite for its own sake. The generated runtime may remain compact hand-emitted machine code, but the **generator must express architecture explicitly** and each emitted routine must have one owner and contract.

## 2. High-level dependency graph

```text
User Input / Win32 Messages
            |
            v
       Event Router
            |
    +-------+--------+
    |                |
    v                v
Command Controller  View Controller
    |                |
    v                v
Document Model <---- View State
    |
    v
Markdown Parser
    |
 +--+----------------------+------------------+
 |                         |                  |
 v                         v                  v
Render Model          Outline Model      Position Map
 |                         |                  |
 +------------+------------+------------------+
              |
              v
          UI Surfaces
 Source/Edit | Preview/RichEdit | Outline/ListBox
              |
              v
       Layout + Theme/Palette
```

## 3. Architectural invariants

### 3.1 Document text

`DocumentModel.text` is the sole canonical Markdown. Internally normalize to UTF-16 + CRLF. Source Edit is an editable projection; after EN_CHANGE it synchronizes into the model. Preview never writes back.

### 3.2 View mode

Exactly one enum/state:

```text
ViewMode = SOURCE | PREVIEW
```

Only `set_view_mode(mode)` may show/hide the document surfaces. Every command and Outline navigation asks ViewController for the active surface; no direct independent `preview_flag` logic in event handlers.

Invariant:

```text
SOURCE  <=> Source HWND visible && Preview HWND hidden
PREVIEW <=> Preview HWND visible && Source HWND hidden
```

### 3.3 Outline model

Each entry:

```text
OutlineEntry {
    source_offset_u16;
    level;       // 1..6
    title span / text reference;
}
```

Do not keep a canonical `outline_renderpos`. Preview target is derived from `PositionMap.source_to_render(source_offset)` at navigation time.

### 3.4 Parser unification

Current generator has independent Outline and Preview parsing paths. V8.5 should have one block/inline parser that emits events/nodes used by both OutlineModel and RenderModel. This prevents code-fence/heading disagreement.

Suggested streaming event model:

```text
Heading(level, source_start, source_end, text_span)
Paragraph(...)
Quote(...)
Bullet(...)
CodeFenceOpen(marker, len)
CodeFenceClose(...)
InlineBold(start,end)
InlineItalic(start,end)
InlineCode(start,end)
Link(text_start,text_end,url_start,url_end)
```

### 3.5 Position map

Maintain monotonic mapping from render UTF-16 offset -> source UTF-16 offset. Source→render uses binary search over the monotonic map. Mapping is derived from the current parser/render pass and tagged with `document_revision`.

Never use stale maps across document revisions.

### 3.6 Layout manager

One routine computes all rectangles from `client_w/client_h/status_h/outline_width/metrics`:

```text
content_rect
outline_rect
scroll_gutter_rect
scroll_thumb_rect
visual_divider_rect
resize_hit_rect
document_rect
status_rect
```

No command handler should call `MoveWindow` with independently calculated geometry.

### 3.7 Theme system

`ThemePalette` contains colors/brushes. Theme switch changes palette + invalidates surfaces; it does not parse Markdown or rebuild DocumentModel.

### 3.8 Scrollbar state

One state structure:

```text
OutlineScrollState {
    item_count;
    visible_rows;
    top_index;
    max_top;
    track_rect;
    thumb_rect;
    visible;
    hot;
    dragging;
    drag_offset;
}
```

`scroll_layout()` is the only geometry producer. Paint, hit-test and drag consume the cached rects. This directly addresses the V8.4.20–23 failure mode where geometry/state was distributed across message-pump and paint paths.

## 4. Module boundaries in the generator

Refactor the Python generator itself into logical emitter modules even if kept in one file initially:

```text
PEBuilder
ImportBuilder
X64Emitter
Win64CallHelpers
AppStateLayout
DocumentEmitter
ParserEmitter
RenderEmitter
OutlineEmitter
ViewControllerEmitter
LayoutEmitter
ThemeEmitter
CommandEmitter
WndProcEmitter
DiagnosticsEmitter
```

Each emitted runtime routine should have a contract comment: inputs, outputs, clobbers, state read/written, nested calls.

## 5. Runtime update flow

### Open file

```text
Read bytes
 -> decode
 -> normalize EOL into DocumentModel
 -> revision++
 -> Source set from model (redraw suppressed)
 -> parse once
 -> OutlineModel + RenderModel + PositionMap
 -> ViewMode = SOURCE
 -> layout
 -> repaint
```

### Edit source

```text
EN_CHANGE
 -> debounce/sync DocumentModel
 -> revision++
 -> mark parser/render/outline dirty
 -> rebuild at controlled boundary
```

### Source -> Preview

```text
capture source caret + viewport in source coordinates
 -> ensure RenderModel/PositionMap revision matches DocumentModel
 -> set ViewMode(PREVIEW)
 -> restore mapped caret/viewport
 -> format visible viewport only
```

### Outline click

```text
entry.source_offset
 -> if SOURCE: target source offset
 -> if PREVIEW: PositionMap.source_to_render
 -> select/caret
 -> restore viewport
 -> if Preview: format visible semantic ranges
```

## 6. Large document strategy

Current V8.4.23 fixed caps: 4 MiB input, 8.5M UTF-16 work buffers, 131072 style spans, 2048 Outline entries. V8.5 should gradually replace fixed global arrays with bounded arenas/chunks encoded in BSS or VirtualAlloc-backed memory (still pure Win32 native at runtime). Consider importing `VirtualAlloc/VirtualFree` in a later phase.

Preview optimization priorities:

1. Parse linear once per document revision.
2. Avoid per-span RichEdit formatting for offscreen regions.
3. Cache style ranges; apply only viewport + margin.
4. Theme change only updates visible semantic colors and base default format without reflow.
5. Keep zoom display-only with `EM_SETZOOM`.

## 7. Direct-PE hardening path

Current one-section RWX layout is acceptable for experimentation but should be treated as technical debt. Later V8.5 phases should consider separate `.text`, `.rdata`, `.idata`, `.data/.bss`, relocation support/ASLR, and optional x64 `.pdata` unwind metadata — all still generated directly by Python.

**Urgent:** current machine-code text is 27426 bytes against a fixed budget of 28672; only 1246 bytes remain before `RDATA_RVA`. Re-layout before major code growth.

## 8. Migration phases

- **V8.4.24 stabilization:** ViewController + OutlineController only; no feature additions.
- **V8.5.0 architecture baseline:** generator modularization + layout/theme ownership.
- **V8.5.1 parser unification:** one parser feeds Outline/Render/PositionMap.
- **V8.5.2 large-doc arenas/virtual allocation.**
- **V8.5.3 PE layout hardening / optional ASLR & unwind.**

Each phase must preserve the regression suite.
