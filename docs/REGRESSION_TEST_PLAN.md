# Regression Test Plan

## Release gate philosophy

A Direct-PE binary is not accepted because it parses statically or because the EXE launches once. Windows interactive regressions must pass on a real machine.

## Tier 0 — build/static

- Python generator syntax passes.
- Generator produces EXE without overlap error.
- SHA recorded.
- `inspect_pe.py` reports AMD64 PE32+, GUI, expected section/imports.
- emitted code stays within layout budget.

## Tier 1 — smoke

Use `tests/smoke_small.md`.

- open/save/reopen
- source edit
- all H1-H6 commands
- bold/italic/inline code/code block/quote/bullet/link
- find/replace
- word wrap
- status bar fields
- zoom
- theme switch
- Source/Preview
- Outline navigation

## Tier 2 — mode/state invariant

Cold start -> open file -> must be SOURCE.

1. Immediately click first/middle/last Outline items: Source jumps correctly.
2. Press Ctrl+Shift+P exactly once: must visibly enter PREVIEW.
3. Click first/middle/last Outline items: Preview jumps to corresponding sections, never all to EOF.
4. Toggle 20 times; odd/even state must remain correct.
5. After every toggle, menu check, logical mode and visible HWND must agree.

## Tier 3 — custom scrollbar

With long Outline:

- hover reveal
- thumb visible
- thumb height proportional and >= minimum
- drag top->middle->bottom
- drag bottom->top
- click track above/below
- wheel over Outline
- move mouse out during drag
- resize Outline width
- switch Light/Dark 20 times
- Source/Preview 20 times

At all times paint/hit-test must use the same `thumbRect`.

## Tier 4 — large documents

Use `large_regression_1_2mb.md` and `position_map_300_chapters.md`.

- first load no crash
- first Outline jump before any mode toggle works
- Source->Preview latency measured
- Preview Outline jump correct on first frame
- scroll/wheel smooth enough; no full-document twitch
- zoom without full reparse
- theme switch without full reparse
- positions preserved across modes

## Tier 5 — capacity boundaries

Use `outline_2600_headings.md`.

Current 2048 Outline cap should be explicitly observed/documented. Future dynamic model must show all 2600.

Test file >4MiB should produce a clean 'too large' error, not crash.

## Tier 6 — newline/encoding

Open `newline_lf.md`, `newline_crlf.md`, `newline_cr.md`; Source internal behavior should normalize correctly and preserve visible paragraphs.

Test UTF-8 Chinese and UTF-16LE samples.

## Regression evidence

For each candidate build record:

- version/hash
- Windows build/DPI/theme
- test file
- pass/fail
- latency metrics
- screenshots only for visual failures
- crash address/registers if applicable
