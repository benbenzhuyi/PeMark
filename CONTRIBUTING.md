# Contributing

English | [简体中文](CONTRIBUTING.zh-CN.md)

Thank you for helping with this Direct-PE experiment.

Read `AGENTS.md`, `docs/WIN64_ABI_RULES.md`,
`docs/ARCHITECTURE_V8_5_TARGET.md` and `docs/FAILED_APPROACHES.md` before
editing the generator.

Production executables must be emitted directly by the Python generator. Do not
introduce a compiler, assembler, linker, managed runtime or interpreter
packager into the production path.

For each change:

1. Keep one owner for document, view, layout and scrollbar state.
2. Treat all Win64 volatile registers as clobbered across every API call.
3. Add or update a deterministic emitted-machine-code regression.
4. Run `python tools/build_current.py`.
5. Run `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_4.py`.
6. For GUI changes, run `python tools/smoke_test_v8_5_1.py` on Windows.
7. Update `CHANGELOG_UNRELEASED.md` and affected architecture documents.

Keep pull requests focused. Explain the machine-code invariant being changed,
the failure that motivated it, and the exact validation performed.
