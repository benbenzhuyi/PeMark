# Feature and Shortcut Specification — Current Expected Behavior

## File

- New — Ctrl+N
- Open — Ctrl+O
- Open Folder — Ctrl+Shift+O
- Refresh Tree — (menu only)
- Collapse All — (menu only)
- Save — Ctrl+S
- Save As — Ctrl+Alt+S
- Close — Ctrl+W
- Recent Files (up to 10, in-memory) — (menu only, commands 1316–1325)
- Exit — Alt+F4

## Edit

- Undo — Ctrl+Z
- Cut — Ctrl+X
- Copy — Ctrl+C
- Paste — Ctrl+V
- Find — Ctrl+F
- Find Next — F3
- Replace — Ctrl+H
- Select All — Ctrl+A

## Markdown commands

- H1..H6 — Ctrl+1 .. Ctrl+6
- Bold — Ctrl+Alt+B (Ctrl+B reserved for Outline)
- Italic — Ctrl+I
- Inline Code — Ctrl+`
- Code Block — Ctrl+Shift+K
- Quote — Ctrl+Q
- Bullet List — Ctrl+Shift+8
- Link — Ctrl+K

## View

- Zoom In — Ctrl++ / Ctrl+mouse-wheel up
- Zoom Out — Ctrl+- / Ctrl+mouse-wheel down
- Reset Zoom — Ctrl+0
- Word Wrap — Ctrl+Shift+W
- Status Bar — Ctrl+Alt+S
- Source/Preview toggle — Ctrl+Shift+P
- Left Sidebar — Ctrl+B
- Right Sidebar (reserved for V9 AI sidebar) — Ctrl+J
- Files Panel (exclusive maximize toggle) — (menu only)
- Outline Panel (exclusive maximize toggle) — (menu only)
- Light/Dark toggle — Ctrl+Alt+T

## Status bar

Expected fields:

- line / column
- total characters
- selected characters
- zoom percent
- line endings (Windows CRLF)
- encoding

## Current file formats

Open filters: `.md`, `.markdown`, `.txt`, all files. Input paths include UTF-8, UTF-16LE and ANSI decoding logic; internal text is UTF-16 CRLF; save path writes UTF-8.

## Current capacity

- file input maximum: 4 MiB
- Outline entries: 2048
- style spans: 131072
- wide work buffers: 8.5M UTF-16 units

Capacity boundaries must be surfaced/tested; do not silently assume unlimited documents.
