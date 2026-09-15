# V8.5.2 Release Validation Results

Scope: document-safety release of the pure Direct-PE Markdown editor.
Every command below was executed on the release commit in an interactive
Windows desktop session.

## Release identity

| Item | Value |
|---|---|
| Version | V8.5.2 (Preview) |
| Generator | `src/current/generate_markdown_editor_v8_5_2.py` |
| Generator SHA-256 | `2b93aa79143b33c249826d003dbf6837058e876b27aac6cd7b2e4b19786023b1` |
| Binary | `bin/current/pemark_x64_v8_5_2.exe` |
| Binary size | 78,336 bytes |
| Binary SHA-256 | `2c105660dbac96b7de18614f43753073b3b5613e22bba160ceb8058646040e30` |
| Emitted text | 29,466 bytes (budget 61,440) |
| Virtual BSS | 119,508,992 bytes |

The candidate channel (`src/candidate/generate_markdown_editor_v8_5_2.py`)
produces the same machine code and differs only in the window title, About text
and output file name.

## Commit gate

| Check | Command | Result |
|---|---|---|
| Deterministic build | `python tools/build_current.py` | two builds, identical SHA-256 |
| Machine-code regressions | `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_2.py` | 13/13 groups, 0 failures |
| PE inspection | `python tools/inspect_pe.py bin/current/pemark_x64_v8_5_2.exe` | PE32+ AMD64, GUI, expected imports |

## Milestone gate

| Check | Command | Result |
|---|---|---|
| Revision ownership | `python tools/test_v8_5_2_revision.py` | `(0,0) -> (1,0) -> (2,2) -> (3,2) -> (4,2) -> (4,4) -> (5,5)`, exit 0 |
| Open transaction and strict encoding | `python tools/test_v8_5_2_open_encoding.py` | UTF-8 / BOM / UTF-16LE / LF / CRLF / CR round trips; malformed input rejected transactionally |
| Atomic save fault injection | `python tools/test_v8_5_2_write_injection.py` | 8/8 modes preserve the target and clean staging files |
| Destructive transition matrix | `python tools/test_v8_5_2_destructive.py` | Cancel/Discard/Save for close and New, picker cancel, failed save |
| Outline capacity baseline | `python tools/test_v8_5_2_capacity_baseline.py` | 2600 headings registered, first/middle/last navigation |
| Outline arena allocation failure | `python tools/test_v8_5_2_outline_alloc_injection.py` | prior document and arena preserved |
| Style arena allocation failure | `python tools/test_v8_5_2_style_alloc_injection.py` | growth failure preserves state; first failure publishes no arena |
| Style span capacity | `python tools/test_v8_5_2_style_capacity.py` | 140,000 spans recorded, geometry and payloads verified |
| Windows GUI smoke | `python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_5_2.exe` | 17/17 |
| Ordinary close | 5 runs, `WM_CLOSE` then wait | exit codes `[0, 0, 0, 0, 0]` |

The V8.5.2 test entrypoints accept `PEMARK_GENERATOR` and `PEMARK_EXE` to point a
run at the release channel instead of the development channel.

## Known limitations carried into this release

- The document, render, position-map and encoded-output buffers are still fixed
  sizes. Oversized input is rejected explicitly and the previous document is
  preserved; it is never silently truncated.
- Legacy code pages are not a fallback. Non-UTF-8 and non-UTF-16 documents are
  rejected with an actionable error.
- Memory and handle plateau over long editing sessions has not been measured.
- The image is still a single read/write/execute section, unsigned, and without
  ASLR or unwind metadata. This is the V8.5.4 scope.
- Workspace, advanced editing and AI features are not part of this release.

## Reproducing this record

```powershell
python tools/build_current.py
python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_2.py
python tools/inspect_pe.py bin/current/pemark_x64_v8_5_2.exe
$env:PEMARK_GENERATOR = "$PWD/src/current/generate_markdown_editor_v8_5_2.py"
$env:PEMARK_EXE = "$PWD/bin/current/pemark_x64_v8_5_2.exe"
python tools/test_v8_5_2_revision.py
python tools/test_v8_5_2_open_encoding.py
python tools/test_v8_5_2_write_injection.py
python tools/test_v8_5_2_destructive.py
python tools/test_v8_5_2_capacity_baseline.py
python tools/test_v8_5_2_outline_alloc_injection.py
python tools/test_v8_5_2_style_alloc_injection.py
python tools/test_v8_5_2_style_capacity.py
python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_5_2.exe
```
