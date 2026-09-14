# PeMark V8.5.1 Preview

English | [简体中文](RELEASE_V8_5_1_PREVIEW.zh-CN.md)

V8.5.1 establishes the first public V8.5 baseline while preserving the pure
Direct-PE build: Python emits the PE32+ image and AMD64 instructions without a
compiler, assembler or linker.

## Fixed

- Deterministic clean shutdown after the main window is destroyed.
- Correct SOURCE/PREVIEW visibility through one ViewState writer.
- Unified Preview, style, position-map and Outline scan.
- Lossless indentation and spacing in fenced code.
- Safe word-wrap EDIT recreation after raising the text limit.
- Viewport-bounded formatting for large Markdown spans.
- Shared cached scrollbar geometry for paint, hit-test and drag.

## Validation

- 12/12 emitted-machine-code behavior groups passed.
- 210/210 scrollbar boundary combinations passed.
- 17/17 Windows GUI smoke checks passed.
- 5/5 ordinary WM_CLOSE runs returned exit code 0.
- Consecutive builds produced identical binaries.

Release asset:
`pemark_x64_v8_5_1.exe`

SHA-256:
`b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`

## Preview limitations

Atomic saving, short-write recovery, unsaved-change protection, legacy encoding
fallback, all capacity boundaries, code signing, ASLR and separated PE section
permissions are not yet certified. Keep backups of important documents.
