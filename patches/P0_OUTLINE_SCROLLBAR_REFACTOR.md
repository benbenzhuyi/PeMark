# P0: Outline custom scrollbar state/geometry refactor

The field symptom in V8.4.23 is a hover gutter/surface without a reliably visible/draggable thumb.

Do not patch paint timing in isolation. Replace distributed fields/logic with one `OutlineScrollState` and one layout routine.

## State

```text
item_count
visible_rows
top_index
max_top
track_rect
thumb_rect
visible
hot
dragging
drag_offset
```

## Rules

- `scroll_layout()` calculates all geometry and stores it.
- WM_PAINT draws exactly `state.thumb_rect`.
- hit-test tests exactly `state.thumb_rect`.
- drag maps pointer to `top_index` using exactly the stored track/thumb travel.
- wheel updates top index -> layout -> repaint.
- theme changes paint colors only.
- Outline width/layout changes -> layout -> repaint.
- no independent duplicate calculation in message pump and paint routine.

Add debug logging of every state field until Windows regression passes.
