# Codex start here

[简体中文](CODEX_START_HERE.zh-CN.md) | English

This is a pure Direct-PE Windows x64 project. The Python generator directly
emits the PE32+ image and AMD64 machine code. The production build must not use
a compiler, assembler, linker, managed runtime or interpreter packager.

## Current baseline

- Version: V8.6.3 (stable, released 2026-09-18).
- Generator: `src/current/generate_markdown_editor_v8_6_3.py`.
- Binary: `bin/current/pemark_x64_v8_6_3.exe`.
- Expected EXE SHA-256:
  `5fe17a495f691747e33d3372a78f202b442ae67cf55af2414ecba4a769186b21`.
- Validation record: `docs/V8_6_3_RELEASE_RESULTS.md`.

V8.5.4 and V8.6.1 remain available in `src/current/` and `bin/current/` as
earlier stable releases; V8.4.23 stays frozen under `archive/`. Documents
describing earlier handoffs are historical evidence unless a newer document
adopts the same issue as active work.

## First-session sequence

1. Read `AGENTS.md`.
2. Read `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`.
3. Read `docs/MILESTONE_PLAN.md`.
4. Read `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`.
5. Read `docs/V8_6_3_RELEASE_RESULTS.md`.
6. Read `docs/WIN64_ABI_RULES.md` and `docs/FAILED_APPROACHES.md`.
7. Run `python tools/build_current.py`.
8. Run
   `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_6_3.py`.
9. Inspect the PE with `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_6_3.exe`.

Run `tools/smoke_test_v8_5_1.py` in an interactive Windows desktop session
after any GUI, message-loop, theme, layout, control recreation or shutdown
change.

## Current priorities

V8.6.3 completed the V8.6 desktop workspace (custom title row, Fluent glyphs,
expandable file tree, file operations, high-DPI sharpness). The remaining V8.6
work is the in-memory recent-file list at the bottom of the File menu and
turning `View → Files/Outline Panel` into visibility switches; after that,
V8.7 advanced editing per `docs/MILESTONE_PLAN.md` §7.

Work on one ownership boundary at a time and add a deterministic regression for
every fix. Before adding any new mechanism, answer "what is the minimum
sufficient engineering for this step" and gate verification by level (see
`docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md` 5.1).
