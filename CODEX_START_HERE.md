# Codex start here

This is a pure Direct-PE Windows x64 project. The Python generator directly
emits the PE32+ image and AMD64 machine code. The production build must not use
a compiler, assembler, linker, managed runtime or interpreter packager.

## Current baseline

- Version: V8.6.1.
- Generator: `src/current/generate_markdown_editor_v8_6_1.py`.
- Binary: `bin/current/pemark_x64_v8_6_1.exe`.
- Expected EXE SHA-256:
  `abd79de90999a70f3b5328c63cb73109ea0a38cac85c5ed59f197cab397ac4bc`.
- Validation record: `docs/V8_6_1_RELEASE_RESULTS.md`.

V8.5.4 remains available in `src/current/` and `bin/current/` as the previous
stable release; V8.4.23 stays frozen under `archive/`. Documents describing earlier
handoffs are historical evidence unless a newer document adopts the same issue
as active work.

## First-session sequence

1. Read `AGENTS.md`.
2. Read `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`.
3. Read `docs/MILESTONE_PLAN.md`.
4. Read `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`.
5. Read `docs/V8_6_1_RELEASE_RESULTS.md`.
6. Read `docs/WIN64_ABI_RULES.md` and `docs/FAILED_APPROACHES.md`.
7. Run `python tools/build_current.py`.
8. Run
   `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_6_1.py`.
9. Inspect the PE with `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_6_1.exe`.

Run `tools/smoke_test_v8_5_1.py` in an interactive Windows desktop session
after any GUI, message-loop, theme, layout, control recreation or shutdown
change.

## Current priorities

V8.6.1 promotes the candidate title row, Fluent/MDL2 icon set and the current
sidebar panel frame into `src/current/`. The remaining V8.6 work is the file
panel redesign (tree model and file operations); each slice keeps its own
deterministic regression and release evidence.

Work on one ownership boundary at a time and add a deterministic regression for
every fix. Before adding any new mechanism, answer "what is the minimum
sufficient engineering for this step" and gate verification by level (see
`docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md` 5.1).
