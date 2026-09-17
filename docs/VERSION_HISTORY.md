# Version History / Engineering Timeline

Intermediate builds are preserved for diffing and regression archaeology; many were experimental and not release-stable.

## V8.6.3

Generator: `src/current/generate_markdown_editor_v8_6_3.py`

V8.6.3 completes the V8.6 desktop workspace: a custom title/menu row, Fluent
tool and file-tree glyphs, an expandable workspace tree, keyboard and mouse
activation, inline/context-menu file operations, large-document Preview
settling fixes, and GDI-scaled DPI awareness for sharp text on scaled displays.
It retains the V8.5.4 transactional document, dynamic-capacity and six-section
W^X/ASLR baseline. Validation record: `docs/V8_6_3_RELEASE_RESULTS.md`.

## V8.6.1

Generator: `src/current/generate_markdown_editor_v8_6_1.py`

V8.6.1 promoted the merged custom title row, Codex-style left/right sidebar
switches, literal `</>` Source icon and the Fluent/MDL2 tool/window icons into
`src/current/` and `bin/current/`. It inherits the V8.5.4 document-safety,
dynamic-capacity and PE-hardening baseline. The file-panel tree and file
operations were completed later in V8.6.3. Validation record:
`docs/V8_6_1_RELEASE_RESULTS.md`.

## V7

Generator: `generate_markdown_editor_v7.py`

V7 adds Markdown-aware editing commands, keyboard accelerators, .md file filters, and a lightweight side-by-side Markdown preview.

## V8

Generator: `generate_markdown_editor_v8.py`

V8 adds full-window rich Markdown rendering, a clickable Markdown outline, and Light / Dark display modes.

## V8.1

Generator: `generate_markdown_editor_v8_1.py`

V8.1 fixes Markdown render range alignment, rebuilds the outline parser, and improves native Dark Mode integration.

## V8.2

Generator: `generate_markdown_editor_v8_2.py`

V8.2 fixes initial outline loading, hardens Markdown inline rendering, and repairs Ctrl+K link insertion.

## V8.3

Generator: `generate_markdown_editor_v8_3.py`

V8.3 repairs the machine-code UTF-16 scanner, Markdown rendering, dark menu chrome, themed preview colors, and the outline presentation.

## V8.4

Generator: `generate_markdown_editor_v8_4.py`

V8.4 fixes inactive-window dark repainting, resolves the status-bar shortcut conflict, and adds Heading 1 through Heading 6 editing commands.

## V8.4.1

Generator: `generate_markdown_editor_v8_4_1.py`

V8.4.1 introduces a canonical Document Model: source editing uses CRLF, Preview renders from an independent buffer, and Outline parses the Document Model. Preview never writes back to Source.

## V8.4.2

Generator: `generate_markdown_editor_v8_4_2.py`

V8.4.2 hardens the Document Model for large Markdown files, raises the supported file limit, configures Rich Edit with EM_EXLIMITTEXT, adds render bounds checks, and completes dark menu/status-corner painting.

## V8.4.3

Generator: `generate_markdown_editor_v8_4_3.py`

V8.4.3 fixes a verified x64 stack-alignment defect in large-document outline rebuilding, caps outline rows before native listbox insertion, and explicitly repaints the non-client menu gap/border for dark mode.

## V8.4.4

Generator: `generate_markdown_editor_v8_4_4.py`

V8.4.4 keeps the large-document fixes and adds three rendering stability fixes: status updates are no longer triggered by every mouse-move message, owner-drawn outline/status text explicitly selects the ClearType UI font into the paint DC, the native status-bar sizing grip is masked by a clipping-aware themed sibling cover, and the lower-right frame is repainted after Windows draws it.

## V8.4.5

Generator: `generate_markdown_editor_v8_4_5.py`

V8.4.5 fixes the V8.4.4 outline owner-draw crash caused by using volatile R9 after SelectObject, separates fixed ClearType fonts for Outline and Status Bar from document zoom, and makes the lower-right status-corner cover owner-drawn and explicitly topmost among child windows.

## V8.4.6

Generator: `generate_markdown_editor_v8_4_6.py`

V8.4.6 refines the pane/status visuals, adds source/preview text margins, makes Preview zoom display-only via EM_SETZOOM, avoids reparsing the whole Markdown document on every zoom step, and preserves the document position across zoom and Source/Preview switching.

## V8.4.7

Generator: `generate_markdown_editor_v8_4_7.py`

V8.4.7 removes the bulky Outline scrollbar, fixes Source margins after font changes, suppresses progressive redraw while loading large documents/outlines, and adds an exact render-to-source position map for Source/Preview caret preservation.

## V8.4.8

Generator: `generate_markdown_editor_v8_4_8.py`

V8.4.8 restores wheel scrolling to the borderless Outline, unifies Source/Preview insets at 10px, avoids full Markdown reparsing on theme/Outline toggles, suppresses visible large-document load churn, and preserves both caret and viewport anchors across Source/Preview transitions.

## V8.4.9

Generator: `generate_markdown_editor_v8_4_9.py`

V8.4.9 adds a draggable Outline splitter with a hover-revealed fast scrollbar, eliminates separator paint residue, and makes Preview theme changes viewport-scoped instead of synchronously restyling the full document.

## V8.4.10

Generator: `generate_markdown_editor_v8_4_10.py`

V8.4.10 replaces the broken floating Outline scrollbar with the ListBox native themed scrollbar shown only near the splitter, removes the remaining separator artifacts, and makes Preview theme refresh color-only so navigation no longer triggers expensive whole-document reformatting.

## V8.4.11

Generator: `generate_markdown_editor_v8_4_11.py`

V8.4.11 makes the splitter owner-drawn to eliminate stale text fragments, and debounces Preview theme maintenance so mouse-wheel scrolling never performs synchronous RichEdit restyling.

## V8.4.12

Generator: `generate_markdown_editor_v8_4_12.py`

V8.4.12 isolates Source/Preview painting from the splitter with sibling clipping, keeps the splitter topmost in child Z-order, and preserves the debounced Preview scrolling path.

## V8.4.13

Generator: `generate_markdown_editor_v8_4_13.py`

V8.4.13 separates the 1px visual divider from an 8px logical drag hit-zone, unifies all content heights through one layout metric, and visually trims the Outline native scrollbar to match the document scrollbar while preserving native drag behavior.

## V8.4.14

Generator: `generate_markdown_editor_v8_4_14.py`

V8.4.14 keeps the Outline scrollbar fully native and unobstructed, removes the visual trim overlay, and preserves the 1px divider plus independent 8px resize hit-zone. Native scrollbar dragging is protected from hover auto-hide while the left mouse button is held.

## V8.4.15

Generator: `generate_markdown_editor_v8_4_15.py`

V8.4.15 stabilizes native Outline scrollbar theming when it is dynamically revealed and makes Preview formatting deterministic by cancelling stale lazy-theme timers before every full render. The native scrollbar remains unobstructed, with the 1px divider and independent 8px resize hit-zone preserved.

## V8.4.16

Generator: `generate_markdown_editor_v8_4_16.py`

V8.4.16 fixes the 4096-style-span ceiling for very large Markdown documents, hardens first-frame Outline scrollbar theming after Light/Dark switches, and reserves a scrollbar-safe text inset so owner-drawn Outline rows can never paint under the native scrollbar.

## V8.4.17

Generator: `generate_markdown_editor_v8_4_17.py`

V8.4.17 makes Preview semantic formatting viewport-lazy: entering a huge Markdown document no longer sends tens of thousands of RichEdit formatting operations for the whole file, and outline/page jumps immediately format the newly visible viewport instead of waiting for a scroll.

## V8.4.18

Generator: `generate_markdown_editor_v8_4_18.py`

V8.4.18 hard-isolates the Outline owner-draw content from the native scrollbar gutter: every row is clipped at the HDC level before any background or text is painted, so outline items cannot overwrite or visually cut through the themed scrollbar in either Source or Preview mode.

## V8.4.19

Generator: `generate_markdown_editor_v8_4_19.py`

V8.4.19 replaces the unstable ListBox non-client scrollbar with a permanently reserved scrollbar gutter and an independent themed SCROLLBAR child. Outline content, scrollbar, 1px visual divider, and the logical resize hit-zone now have separate geometry, eliminating redraw races between owner-drawn rows and scrollbar chrome.

## V8.4.20

Generator: `generate_markdown_editor_v8_4_20.py`

V8.4.20 is an architecture-preview build. It keeps the permanent Outline gutter and centralized layout geometry, but replaces the native SCROLLBAR skin with a palette-driven owner-drawn overlay thumb. Scrollbar visual width, hit area, divider, theme colors, and drag state are now separated instead of relying on Windows non-client/theme behavior.

## V8.4.21

Generator: `generate_markdown_editor_v8_4_21.py`

V8.4.21 is an architecture-preview stabilization build. The permanent Outline gutter remains, but the scrollbar surface is now a dedicated custom child window with its own WM_PAINT lifecycle. This fixes the V8.4.20 invisible thumb and stale opposite-theme gutter while preserving separated visual width, hit area, divider, palette colors and drag state.

## V8.4.22

Generator: `generate_markdown_editor_v8_4_22.py`

V8.4.22 stabilizes the custom Outline scrollbar and first-load navigation. The custom scrollbar surface is now synchronously repainted with current palette colors, its thumb geometry no longer depends on volatile register state across Win32 calls, and Preview outline navigation maps the canonical source heading position through the current Source-to-Render map instead of relying on a separately populated render-position table.

## V8.4.23

Generator: `generate_markdown_editor_v8_4_23.py`

V8.4.23 hardens view-mode state and the custom Outline scrollbar. Opening a document now explicitly re-enters Source mode, Preview commands reconcile logical state with the actually visible surface, Outline navigation uses the visible surface as the routing authority, and the custom scrollbar window is physically hidden when idle so only the thumb appears on hover.
