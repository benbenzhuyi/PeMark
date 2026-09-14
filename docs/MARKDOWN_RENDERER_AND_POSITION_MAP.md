# Markdown Renderer, Outline and Position Mapping

## Current model

V8.4.23 maintains:

- `document_model`: canonical UTF-16/CRLF text
- `previewbuf`: rendered text representation
- style arrays: start/end/type
- `render_srcmap`: render code-unit -> source code-unit
- Outline arrays: source position, render position, level

Preview formatting became viewport-lazy in V8.4.17 to avoid tens of thousands of RichEdit format operations on large documents.

## Desired parser contract

The parser should operate on `DocumentModel revision N` and produce all of:

- Render text
- semantic style spans
- Outline entries (source offsets)
- monotonic render->source map

This avoids parsing headings/code fences differently in Outline and Preview.

## Position mapping

Render->source is direct via `render_srcmap`.

Source->render should binary-search the monotonic map. End-of-document is a legitimate mapping only when the source target is at/after source end — not as a generic error fallback.

Add assertions/diagnostics:

```text
0 <= sourceOffset <= document_len
0 <= renderOffset <= render_len
render_srcmap[i] <= render_srcmap[i+1]
```

## Lazy formatting

Keep text generation separate from RichEdit semantic styling.

Entering Preview:

1. Ensure render buffer/map/style table current for Document revision.
2. Set RichEdit default/base formatting.
3. Load render text once.
4. Restore mapped viewport/caret.
5. Apply semantic style spans only for viewport + safety margin.

On scroll/page/jump: apply styles for newly visible ranges. Avoid full-document style loops.

## Current cap issue history

The style span array was 4096 and failed after roughly 4095 lines in stress content. V8.4.16 raised it to 131072. The architectural fix is eventually dynamic/arena allocation, not ever-larger fixed arrays.

## Outline cap

Current Outline arrays cap at 2048 entries. The supplied `outline_2600_headings.md` intentionally exposes this boundary.
