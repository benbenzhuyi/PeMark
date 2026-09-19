# PeMark V8.6.5

[简体中文](RELEASE_V8_6_5_GITHUB.zh-CN.md) | English

Stable release of the pure Direct-PE Markdown editor. No compiler, assembler,
linker, managed runtime or interpreter packager is involved: the Python
generator emits the PE32+ image and the AMD64 machine code directly.

## Highlights

**The window now has a visible frame in both themes.** Two independent causes
were measured on the live window and both are fixed:

1. `WM_NCCALCSIZE` made the client area cover the entire window, so DWM had no
   frame strip to paint at all;
2. `DWMWA_BORDER_COLOR` was set to the window background itself (`#1A1A1A` on a
   `#202020` surface in dark mode, pure white on the light backdrop), so even a
   painted frame would have been invisible.

The frame colour is now taken from a pixel measurement of the Windows Explorer
frame: `#3C3C3C` in dark mode and `#B0B0B0` in light mode, two physical pixels
at 150% display scaling — the same brightness and thickness Explorer uses.

## What changed

- `wp_nccalcsize` insets the returned client rectangle by 1px on all four sides,
  restoring the 1px non-client strip DWM requires before it draws the frame.
  Child controls are positioned relative to the client area, so they move inward
  by one pixel automatically and no layout code changed.
- `DWMWA_BORDER_COLOR` follows the theme and never matches the window
  background.
- `wp_ncpaint` no longer paints the four edges with GDI. Measurement showed DWM
  composites its frame above any GDI drawing placed in those pixels, so keeping
  both produced four differently coloured edges.

## Verification

- two consecutive builds reproduce the identical binary digest;
- machine-code regression: `failures: []` (includes 210 scrollbar geometry
  combinations, clip and formatting invariants, drag clamping, exit path);
- PE inspection: six sections, RX/R/RW/RW/R/R, no W+X page;
- GUI smoke on an interactive desktop: 17/17 PASS, clean exit code 0;
- frame pixel measurement: uniform `#B0B0B0` light / `#3C3C3C` dark on all four
  edges, updating within one frame on a theme switch.

## Asset

Attach `bin/current/pemark_x64_v8_6_5.exe` only.

- SHA-256:
  `a038974bcd61c6a2720af5fb40ef7ad0c5c12c3745d801b8ef06e119b3b679e9`
- Size: 190976 bytes

## Notes

- The executable is unsigned; expect a SmartScreen prompt.
- The explicit frame colour uses `DWMWA_BORDER_COLOR`, a Windows 11 attribute.
  On older systems the frame keeps whatever the system draws.
- The AI right sidebar is reserved (`View → Right Sidebar`, `Ctrl+J`) but not
  implemented in this release; it is the next milestone.
