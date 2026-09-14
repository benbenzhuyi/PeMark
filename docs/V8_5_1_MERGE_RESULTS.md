# V8.5.1 independent merge candidate

Date: 2026-09-14

This candidate combines the useful V8.5 architectural work with fixes that
were independently reproduced at emitted-machine-code and Win32-process level.
It remains a pure Python Direct-PE build: no compiler, assembler or linker was
introduced.

## Independent findings

The explicit jump from the dispatch tail to `exit` is required. Without it,
destroying the main window inside `DispatchMessageW` makes `IsWindow` return
zero and execution falls into the following helper routine. Its unmatched
`ret` uses unrelated stack data as a return address and terminates with
`0xC0000005`.

The external V8.5.0 reference also contained issues outside that shutdown fix:

- `set_view_mode_commit(PREVIEW)` branched to the Source display path.
- The wrapped EDIT style branch lost its unconditional jump because the jump
  text was inside a Python comment.
- EDIT recreation passed the full document at `CreateWindowExW`, before
  `EM_SETLIMITTEXT`, and reused an unrelated register as `HINSTANCE`.
- The unified scanner consumed up to three leading spaces before copying a
  fenced-code line.
- Viewport theme formatting still used a fixed 40,000-character window and did
  not clip an intersecting large span.
- Scrollbar painting and dragging still derived parts of their geometry
  independently.

The reported zero-entry Outline smoke failure was a test defect. Multiline EDIT
`WM_SETTEXT` does not emit `EN_CHANGE`. The corrected test explicitly sends
the child notification after injecting text and observes 31 expected Outline
entries, excluding the fenced-code pseudo-heading.

## Validation

- Generator build-time structure and parity assertions: passed.
- Unicorn emitted-x64 tests: 12/12 groups passed.
- Scrollbar combinations: 210/210 passed.
- Windows injected smoke suite: 17/17 passed.
- No-debugger launch, idle, WM_CLOSE and process-exit sequence: 5/5 returned 0.
- Determinism: two consecutive builds produced
  `b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`.

## Artifacts

- Generator: `src/stabilization/generate_markdown_editor_v8_5_1.py`
- Test harness: `tools/test_v8_5_1.py`
- Corrected Windows smoke test: `tools/smoke_test_v8_5_1.py`
- Binary: `bin/stabilization/pemark_x64_v8_5_1.exe`
- Memory map: `docs/PE_MEMORY_MAP_V8_5_1.md`

This establishes a reviewable merge baseline. It does not yet certify the
remaining file-safety work: atomic Save/Save As, short-write handling,
unsaved-change protection, encoding fallbacks and capacity-boundary behavior
remain separate release gates.
