# PeMark V8.6.5 release results

[简体中文](V8_6_5_RELEASE_RESULTS.zh-CN.md) | English

- Date: 2026-09-19
- Tag: `v8.6.5`
- Channel: stable
- Scope: window frame separation in both themes

## Artifacts

| Item | Value |
|---|---|
| Generator | `src/current/generate_markdown_editor_v8_6_5.py` |
| Generator SHA-256 | `2d18f4d1a1987d69b668252fdbd9450e1a33293919f62976746e4d7daadffbff` |
| Binary | `bin/current/pemark_x64_v8_6_5.exe` |
| Binary SHA-256 | `a038974bcd61c6a2720af5fb40ef7ad0c5c12c3745d801b8ef06e119b3b679e9` |
| Binary size | 190976 bytes |
| `.text` | 59658 of the 61440-byte budget (headroom 1782) |
| Raw data | 189952 bytes, six sections, image size 196608 |
| Virtual BSS | 102400 bytes |

## Gates run on this build

1. **Deterministic build.** Two consecutive generator runs produced the
   identical SHA-256 `a038974b…`; `tools/build_current.py` now pins V8.6.5 and
   the same digest, so a third run is checked by the standard helper.
2. **Machine-code regression.** `python tools/test_v8_5_1.py
   src/current/generate_markdown_editor_v8_6_5.py` reports `"failures": []`.
   Coverage includes the 210 scrollbar capacity/height/top combinations,
   viewport formatting and clip invariants, drag clamping at both extremes,
   queued mouse handlers consuming message position, and the destroyed-window
   exit path.
3. **PE inspection.** `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_6_5.exe` reports PE32+ AMD64 (`0x8664`,
   optional header `0x020B`), six sections with protections
   RX / R / RW / RW / R / R and no W+X page, and the expected import surface
   (KERNEL32, USER32, GDI32, DWMAPI, UXTHEME).
4. **GUI smoke on an interactive desktop.**
   `python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_6_5.exe` →
   17/17 PASS, including the single-visible-document-surface invariant
   (SOURCE), 20 consecutive mode switches, theme and newline round-trips, and a
   clean `WM_CLOSE` exit with code 0.
5. **Frame pixel measurement on the running window.** All four edges carry the
   theme frame colour: `#B0B0B0` in light mode and `#3C3C3C` in dark mode, two
   physical pixels wide at 150% display scaling, updating within one frame on a
   live Light/Dark switch.

## Baseline repairs included

- `tools/build_current.py` still pinned the V8.6.3 generator and V8.6.3 digest;
  it now pins V8.6.5.
- `tools/smoke_test_v8_5_1.py` was invoked with an explicit executable path.
  Its default argument still points at `bin/current/pemark_x64_v8_5_1.exe`, and
  `CODEX_START_HERE.md` previously told agents to run it *without* arguments —
  which would have validated a V8.5.1 binary while claiming to check the
  current build. The first-session command now passes the path explicitly.
- `.github/workflows/direct-pe.yml` hard-coded the V8.6.3 generator path, binary
  path and expected digest. Neither the V8.6.4 nor the V8.6.5 release updated
  them, so the "Verify release hash" step threw `SHA-256 mismatch` on every
  published push while the build itself was correct. The workflow now reads the
  generator, binary and expected digest from `manifest.json`, which every
  release updates by definition.
- The V8.6 behaviour suites in CI ran against `src/candidate/`, an old V8.6
  snapshot that predates the `Ctrl+J` right-sidebar reservation (1315), so
  `test_v8_6_keymap.py` failed with `accelerator 09/004A must map to 1315, got
  None` on every push since V8.6.4 while the release build was correct. Those
  suites now take `PEMARK_GENERATOR` / `PEMARK_EXE` / `PEMARK_TREE_EXE` from the
  current channel named in `manifest.json`, and `test_v8_6_caption.py` reads its
  expected version label from `current_snapshot` instead of a hard-coded V8.6.3
  string. The `Direct-PE validation` workflow is green on this release — the
  first successful run of that workflow since V8.6.3.
- The published `README.md` still advertised V8.6.3 after the first push of this
  release: download link, expected hash, build and verify commands, validation
  link and the repository-layout version line. It is updated together with
  `README.zh-CN.md`, `docs/README.md`, `docs/README.zh-CN.md` and
  `docs/WIN32_API_SURFACE.md`, and the publishing checklist now names the public
  entry points as a required release step.

## Not covered by this build

- No independent second-machine verification pack for V8.6.5 (V8.5.4 had one).
- The V8.6 GUI suites that need real pointer input were not part of this gate.
  `tools/test_v8_6_mouse_activate.py` also fails on the frozen V8.6.4 baseline,
  so that failure is pre-existing and unrelated to this release.
- The executable remains unsigned.
