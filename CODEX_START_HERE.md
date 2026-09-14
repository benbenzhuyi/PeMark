# Codex start here

This is a pure Direct-PE Windows x64 project. The Python generator directly
emits the PE32+ image and AMD64 machine code. The production build must not use
a compiler, assembler, linker, managed runtime or interpreter packager.

## Current baseline

- Version: V8.5.1 Preview.
- Generator: `src/current/generate_markdown_editor_v8_5_1.py`.
- Binary: `bin/current/pemark_x64_v8_5_1.exe`.
- Expected EXE SHA-256:
  `b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`.
- Validation record: `docs/V8_5_1_MERGE_RESULTS.md`.

V8.4.23 remains frozen under `archive/`. Documents explicitly describing the
V8.4.23 handoff or audit are historical evidence unless a newer document adopts
the same issue as active work.

## First-session sequence

1. Read `AGENTS.md`.
2. Read `docs/V8_5_1_MERGE_RESULTS.md`.
3. Read `docs/WIN64_ABI_RULES.md`.
4. Read `docs/ARCHITECTURE_V8_5_TARGET.md`.
5. Read `docs/FAILED_APPROACHES.md`.
6. Run `python tools/build_current.py`.
7. Run
   `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_1.py`.
8. Inspect the PE with `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_5_1.exe`.

Run `tools/smoke_test_v8_5_1.py` in an interactive Windows desktop session
after any GUI, message-loop, theme, layout, control recreation or shutdown
change.

## Current priorities

The next release gates are atomic Save/Save As, short-write recovery,
unsaved-document protection, encoding fallback, capacity boundaries and PE
section/security hardening. Work on one ownership boundary at a time and add a
deterministic regression for every fix.
