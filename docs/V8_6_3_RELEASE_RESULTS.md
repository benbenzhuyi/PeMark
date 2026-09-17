# V8.6.3 Stable Release Validation Results

Scope: formal V8.6 desktop-workspace release. The commands below were executed
against `src/current/generate_markdown_editor_v8_6_3.py` and
`bin/current/pemark_x64_v8_6_3.exe` in an interactive Windows desktop session.

## Release identity

| Item | Value |
|---|---|
| Version | V8.6.3 (Stable) |
| Release date | 2026-09-18 |
| Generator | `src/current/generate_markdown_editor_v8_6_3.py` |
| Generator SHA-256 | `4667c02a0ae4d50e0fbf80fff8cb915cb55b56569c6c4c2497dee95d1a1875f9` |
| Binary | `bin/current/pemark_x64_v8_6_3.exe` |
| Binary size | 182,784 bytes |
| Binary SHA-256 | `5fe17a495f691747e33d3372a78f202b442ae67cf55af2414ecba4a769186b21` |
| Emitted text | 58,316 bytes (61,440-byte budget) |
| Virtual BSS | 94,208 bytes |
| PE virtual size | 188,416 bytes |

The formal window caption is `PeMark x64 V8.6.3 — Direct-PE Markdown Editor`.

## V8.6 user-visible changes

- A 32px custom title row combines the application identity, accelerator-aware
  menus, six consistently styled tool buttons and Windows window controls.
- The left sidebar is an expandable workspace tree with Fluent folder/document
  glyphs, single-click activation, keyboard navigation and persistent selection.
- New File, New Folder, inline/context-menu Rename, Recycle Bin Delete, Copy
  Path, Refresh and Collapse All are connected to the shared workspace model.
- The file and Outline panels retain independent scrolling and panel switching.
- Preview wheel, thumb drag and Outline jumps settle back to rendered output
  after large-document movement instead of remaining in transient source text.
- `DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED` removes the whole-window bitmap
  stretching that made RichEdit, sidebar and caption text look soft on scaled
  displays. Sidebar rows use opaque ClearType backgrounds, 13px Microsoft YaHei
  UI text and level-aware Outline weights/colours.

## Release gates

| Check | Result |
|---|---|
| Deterministic build | Two consecutive formal builds, identical SHA-256 |
| Machine-code regression | 13/13 groups; 210/210 scrollbar geometry cases |
| PE inspection | PE32+ AMD64 GUI, six sections, `SizeOfImage` 0x2E000 |
| Section separation / ASLR | RX/R/RW/RW/R/R; no W+X; loaded protection verified |
| Unwind metadata | 87 valid, ordered and resolvable `RUNTIME_FUNCTION` entries |
| GUI smoke | 17/17 checks; 5/5 clean exits |
| DPI and title row | PASS: GDI-scaled awareness, caption geometry/icons/commands |
| Workspace model and projection | PASS: filtering, expansion, item data and activation; 20/20 repeated 130-entry rebuilds preserve revision state |
| File operations | PASS: rename, create, Recycle Bin delete and copy path |
| Keyboard navigation | PASS: focus, Enter activation and Backspace parent navigation |
| Document safety | Open/encoding, 8/8 save faults, destructive transitions, revisions |
| Capacity and allocation failure | 2600 headings, 140,000 spans and every dynamic arena |
| Memory plateau | 12 open/parse/close cycles; handles +0; bounded private memory |

The real-pointer mouse suites could not drive `GetCursorPos`/`SetCursorPos` from
the release host's Codex shell. Their message-level coverage passed, and the
maintainer completed the corresponding single-click, splitter, title-button and
large-document interactions manually before approving this release.

## Publication

| Item | Value |
|---|---|
| Release commit | `7fb4443ea868268d650f27c8533e1e2144069f63` |
| Annotated tag | `v8.6.3` |
| GitHub release | https://github.com/benbenzhuyi/PeMark/releases/tag/v8.6.3 |
| Attached asset | `pemark_x64_v8_6_3.exe` (182,784 bytes) |
| Asset SHA-256 (upload record) | `5fe17a495f691747e33d3372a78f202b442ae67cf55af2414ecba4a769186b21` |
| Asset SHA-256 (re-downloaded) | `5fe17a495f691747e33d3372a78f202b442ae67cf55af2414ecba4a769186b21` |
| CI, `main` push run [35283788365](https://github.com/benbenzhuyi/PeMark/actions/runs/35283788365) | success |
| CI, `v8.6.3` tag push run [35284010496](https://github.com/benbenzhuyi/PeMark/actions/runs/35284010496) | success |

The `v8.6.3` tag was first cut at `f197b21`, before the file-tree path
ownership fix recorded above existed. Because no GitHub release had been
published against it, the tag was moved to the validated `7fb4443` commit and
force pushed before the release was created.

## Reproducing the core record

```powershell
python tools/build_current.py
python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_6_3.py
python tools/inspect_pe.py bin/current/pemark_x64_v8_6_3.exe
$env:PEMARK_GENERATOR = "$PWD/src/current/generate_markdown_editor_v8_6_3.py"
$env:PEMARK_EXE = "$PWD/bin/current/pemark_x64_v8_6_3.exe"
$env:PEMARK_TREE_EXE = $env:PEMARK_EXE
python tools/test_v8_5_4_sections.py
python tools/test_v8_5_4_unwind.py
python tools/test_v8_6_dpi.py
python tools/test_v8_6_caption.py
python tools/test_v8_6_tree_model.py
python tools/test_v8_6_tree_ui.py
python tools/test_v8_6_navigation.py
python tools/test_v8_6_rename.py
python tools/test_v8_6_file_ops.py
python tools/test_v8_6_keyboard.py
python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_6_3.exe
```

## Known limitations

The executable is unsigned. The Settings gear and right-sidebar switch are
visual placeholders. Full stack walking beyond the first PeMark frame is not
demonstrated, although the unwind entries are valid and the application does
not use exceptions. AI integration and advanced editing beyond the present
workspace are outside this release.
