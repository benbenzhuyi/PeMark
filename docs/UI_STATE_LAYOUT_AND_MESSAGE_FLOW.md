# UI State, Message Flow and Layout Ownership

## Current V8.4.23 state (legacy/transition)

Global BSS contains many independent fields: `preview_flag`, `outline_flag`, `status_flag`, `theme_dark`, `view_hwnd`, scrollbar flags/geometry, caret/viewport anchors and HWNDs. This evolved incrementally and is the main reason fixes interact.

## Target ViewController

```text
ViewState
- mode: SOURCE | PREVIEW
- active_hwnd
- caret_source_offset
- viewport_source_anchor
- zoom_pct
```

Only ViewController may change Source/Preview visibility.

## Current message routing

The generator uses two layers:

- top-level `wndproc` for synchronous WM_COMMAND/WM_SIZE/owner-draw/colors/etc.
- thread message pump interception for child-targeted WM_MOUSEMOVE/LBUTTON/MOUSEWHEEL and private posted events.

This is workable but dangerous if ownership is unclear. Document every private WM_APP event and prevent the pump from becoming a second controller layer.

## Layout target

One `layout_compute()` should derive:

```text
content_h = client_h - status_h
outline_total_width
outline_content_rect
outline_scroll_gutter_rect
outline_divider_rect (1px)
outline_resize_hit_rect (8px logical)
document_rect
status_rect
```

Show/hide should not change unrelated widths unexpectedly. A hidden scrollbar may hide its visuals, but its reserved gutter geometry should remain if that is the chosen design.

## Paint ownership

- Source EDIT: control paints text/background; parent handles control color.
- Preview RichEdit: control paints content; semantic spans applied separately.
- Outline ListBox: owner-draw item content only.
- Scrollbar: dedicated surface/module; must not share geometry responsibility with ListBox.
- Divider: visual only.
- Resize hit zone: logical only; does not need to be a visible window.
- Status bar: no bright cell borders; palette-consistent.

## Theme ownership

Palette is global state; surfaces consume it. No theme code should toggle document mode or rebuild parsing.
