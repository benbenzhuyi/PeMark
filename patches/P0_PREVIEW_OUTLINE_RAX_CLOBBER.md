# P0: Preview Outline navigation uses clobbered RAX

## Confirmed defect

In `navigate_outline`, V8.4.23 computes `index*4` in RAX, then calls `IsWindowVisible`. The call overwrites RAX with BOOL 0/1, and the code later adds RAX to `outline_srcpos`.

## Minimal mechanical correction (not the preferred final architecture)

Store the byte offset or, better, the actual `sourceOffset` in a nonvolatile register/stack/BSS before the API call; use that saved value after `IsWindowVisible`.

## Preferred stabilization refactor

1. `LB_GETCURSEL` -> index.
2. Bounds check.
3. Load `sourceOffset = outline_srcpos[index]` immediately.
4. Query ViewController active mode/surface.
5. SOURCE: target=sourceOffset.
6. PREVIEW: target=PositionMap.source_to_render(sourceOffset).
7. Send selection/scroll to the chosen HWND.

Never use an array byte offset across an API call.
