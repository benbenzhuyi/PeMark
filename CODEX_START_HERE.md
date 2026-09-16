# Codex start here

This is a pure Direct-PE Windows x64 project. The Python generator directly
emits the PE32+ image and AMD64 machine code. The production build must not use
a compiler, assembler, linker, managed runtime or interpreter packager.

## Current baseline

- Version: V8.5.3 Preview.
- Generator: `src/current/generate_markdown_editor_v8_5_3.py`.
- Binary: `bin/current/pemark_x64_v8_5_3.exe`.
- Expected EXE SHA-256:
  `6ad87c6dcb3b9d3a35041d1bc37e5792f3cfd16cb79046088a3426200d0bb7d0`.
- Validation record: `docs/V8_5_3_RELEASE_RESULTS.md`.

V8.5.1 remains available in `src/current/` and `bin/current/` as the previous
release; V8.4.23 stays frozen under `archive/`. Documents describing earlier
handoffs are historical evidence unless a newer document adopts the same issue
as active work.

## First-session sequence

1. Read `AGENTS.md`.
2. Read `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`.
3. Read `docs/MILESTONE_PLAN.md`.
4. Read `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`.
5. Read `docs/V8_5_3_RELEASE_RESULTS.md`.
6. Read `docs/WIN64_ABI_RULES.md` and `docs/FAILED_APPROACHES.md`.
7. Run `python tools/build_current.py`.
8. Run
   `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_3.py`.
9. Inspect the PE with `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_5_3.exe`.

Run `tools/smoke_test_v8_5_1.py` in an interactive Windows desktop session
after any GUI, message-loop, theme, layout, control recreation or shutdown
change.

## Current priorities

V8.5.3 (document safety) is released. Dynamic capacity continues as V8.5.3: the
document, render, position-map and encoded-output buffers still have fixed sizes,
and each migration is one bounded change with its own failure evidence. PE
hardening follows as V8.5.4.

Work on one ownership boundary at a time and add a deterministic regression for
every fix. Before adding any new mechanism, answer "what is the minimum
sufficient engineering for this step" and gate verification by level (see
`docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md` 5.1).
