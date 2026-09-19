# Codex start here

[简体中文](CODEX_START_HERE.zh-CN.md) | English

This is a pure Direct-PE Windows x64 project. The Python generator directly
emits the PE32+ image and AMD64 machine code. The production build must not use
a compiler, assembler, linker, managed runtime or interpreter packager.

## Current baseline

- Version: V8.6.5 (stable, released 2026-09-19).
- Generator: `src/current/generate_markdown_editor_v8_6_5.py`.
- Binary: `bin/current/pemark_x64_v8_6_5.exe`.
- Expected EXE SHA-256:
  `a038974bcd61c6a2720af5fb40ef7ad0c5c12c3745d801b8ef06e119b3b679e9`.
- Validation record: `docs/V8_6_5_RELEASE_RESULTS.md`.

V8.6.3 and V8.6.4 remain available in `src/current/` and `bin/current/` as
earlier stable releases; V8.5.4 and V8.6.1 also remain, and V8.4.23 stays frozen
under `archive/`. Documents describing earlier handoffs are historical evidence
unless a newer document adopts the same issue as active work.

## First-session sequence

1. Read `AGENTS.md`.
2. Read `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`.
3. Read `docs/MILESTONE_PLAN.md`.
4. Read `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`.
5. Read `docs/V8_6_5_RELEASE_RESULTS.md`.
6. Read `docs/WIN64_ABI_RULES.md` and `docs/FAILED_APPROACHES.md`.
7. Run `python tools/build_current.py`.
8. Run
   `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_6_5.py`.
9. Inspect the PE with `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_6_5.exe`.

Run `python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_6_5.exe` in an
interactive Windows desktop session after any GUI, message-loop, theme, layout,
control recreation or shutdown change. Always pass the executable path: the
script's default argument is still `bin/current/pemark_x64_v8_5_1.exe`, so an
argument-less run would silently validate the old V8.5.1 binary instead.

## Current priorities

V8.6.3 completed the V8.6 desktop workspace (custom title row, Fluent glyphs,
expandable file tree, file operations, high-DPI sharpness) and V8.6.4 completed
the workspace close-out (recent-file list, panel visibility switches). V8.6.5
adds a visible window frame in both themes and freezes the line.

The next milestone named by the maintainer is the **AI right sidebar**.
`View → Right Sidebar` (`Ctrl+J`) already reserves `right_sidebar_visible` and
the V8.6 layout does not consume it yet; see `docs/MILESTONE_PLAN.md` for the
milestone ordering before starting it.

Work on one ownership boundary at a time and add a deterministic regression for
every fix. Before adding any new mechanism, answer "what is the minimum
sufficient engineering for this step" and gate verification by level (see
`docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md` 5.1).
