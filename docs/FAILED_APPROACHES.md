# Failed / Fragile Approaches — Do Not Repeat Blindly

This document is intentionally blunt. These designs were tested on real Windows and caused regressions.

## Dynamic ListBox non-client scrollbar + owner draw

Versions around V8.4.10–18. The native ListBox scrollbar was shown/hidden dynamically while Outline rows were owner-drawn. Theme/non-client/client geometry and queued paints raced, producing classic-style first frames and scrollbar segments apparently cut by item painting.

## Visual trim overlay on native scrollbar

V8.4.13 tried to visually shave 1–3 pixels from the Outline native scrollbar to match RichEdit. The extra overlay created Z-order/repaint artifacts. Abandoned in V8.4.14.

## Independent native SCROLLBAR child

V8.4.19 separated geometry and solved item-overlap races, but the standalone traditional `SCROLLBAR` did not consistently match Windows 11 RichEdit visual style and tended to look classic.

## STATIC + SS_OWNERDRAW custom scrollbar

V8.4.20 attempted a palette-driven thumb using owner-draw STATIC. Paint lifecycle depended on parent WM_DRAWITEM; field result: missing thumb and stale wide gutter. Do not reintroduce.

## Custom child scrollbar without consolidated state

V8.4.21–23 gave the scrollbar its own WM_PAINT, but state/geometry remained distributed across hover, sync, drag, layout and message-pump code. Field result still includes missing/undraggable thumb. The lesson: **custom drawing alone is not architecture**. One state object and one geometry function are required.

## Full-document RichEdit semantic formatting

Large documents took many seconds. Use viewport-lazy formatting.

## Multiple independent view-mode truths

`preview_flag` + HWND visibility + view HWND produced first-toggle anomalies and navigation routed to hidden surfaces. One controller must own mode.

## Keeping volatile registers live across Win32 calls

Repeated source of crashes/corruption. See ABI guide. Never assume RAX/R9/R10 survives an API call.

## Patching visual artifacts with more redraw calls

Repeated `InvalidateRect/RedrawWindow/SetWindowPos/FRAMECHANGED` may mask a race but increases state coupling. First determine geometry and ownership.

## Packing PE section raw data tightly (V8.5.4)

When the single section was first split into `.text/.rdata/.idata/.bss`, each
section's `SizeOfRawData` was set to the aligned size of its real payload and the
raw data was packed back to back. Windows rejected the image with
`ERROR_BAD_EXE_FORMAT` (WinError 193) before any code ran, while `pefile` parsed
the same file without warnings, so static checks alone did not catch it.

A second variant made every section span the whole gap to the next RVA
(`VirtualSize == SizeOfRawData == next_rva - rva`, raw data still laid out at
`headers_size + (rva - TEXT_RVA)`). That image loads, runs and closes normally.
Measured rule for this generator: **each section must cover the full RVA gap to
the next section, and the raw buffer must stay one-to-one with the RVA plan.**

Diagnosis note: the Windows Application log named the faulting module and
exception (0xC0000005) for the variants that loaded but crashed; the rejected
variants produced no event at all, which is what pointed at the section table
rather than at the code.
