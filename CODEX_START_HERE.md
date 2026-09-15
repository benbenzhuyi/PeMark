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
2. Read `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`.
3. Read `docs/MILESTONE_PLAN.md`.
4. Read `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`.
5. Read `docs/V8_5_1_MERGE_RESULTS.md`.
6. Read `docs/WIN64_ABI_RULES.md` and `docs/FAILED_APPROACHES.md`.
7. Run `python tools/build_current.py`.
8. Run
   `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_1.py`.
9. Inspect the PE with `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_5_1.exe`.

Run `tools/smoke_test_v8_5_1.py` in an interactive Windows desktop session
after any GUI, message-loop, theme, layout, control recreation or shutdown
change.

## Current priorities

V8.5.2 (document safety) already implements atomic Save/Save As, short-write
recovery, unsaved-document protection and strict encoding. What remains for that
release is evidence, not new mechanism: rerun the commit and milestone gates on
the release commit and record the known limits.

Dynamic capacity continues as V8.5.3 (one arena slice at a time), then PE
hardening as V8.5.4. Work on one ownership boundary at a time and add a
deterministic regression for every fix.
