# V8.5.4 Stable Release Validation Results

Scope: first stable release of PeMark. Every command below was executed against
the release channel (`src/current/generate_markdown_editor_v8_5_4.py` and
`bin/current/pemark_x64_v8_5_4.exe`) in an interactive Windows desktop session.

## Release identity

| Item | Value |
|---|---|
| Version | V8.5.4 (Stable) |
| Generator | `src/current/generate_markdown_editor_v8_5_4.py` |
| Generator SHA-256 | `6f49756166ad985a89d3ba4a9c3c1eec5337f8cac1d8bfaec02869bf5b020c90` |
| Binary | `bin/current/pemark_x64_v8_5_4.exe` |
| Binary size | 91,648 bytes |
| Binary SHA-256 | `aa8de9cda9ed90a2cf66a3a93e021dc91cc192073078a90c53fa9669f478c5cc` |
| Emitted text | 30,672 bytes (budget 61,440) |
| Virtual BSS | 8,192 bytes |
| PE virtual size | 98,304 bytes |

## Commit gate

| Check | Result |
|---|---|
| Deterministic build | two consecutive builds, identical SHA-256 |
| Machine-code regressions | 13/13 groups, 0 failures |
| PE inspection | PE32+ AMD64, GUI, 6 sections, `imageSize` 0x18000 |

## Milestone gate

| Check | Result |
|---|---|
| Section separation and ASLR (`test_v8_5_4_sections.py`) | 6 sections RX/R/RW/RW/R/R, no W+X; loaded image reports `PAGE_EXECUTE_READ` / `PAGE_READONLY` / `PAGE_READWRITE`; base relocated from `0x140000000` |
| Unwind metadata (`test_v8_5_4_unwind.py`) | 42 `RUNTIME_FUNCTION` entries, version-1 unwind info, dbghelp resolves entries, walk reaches our module. Full cross-frame unwinding is **not** demonstrated; the test prints that state. |
| Open and strict encoding (`test_v8_5_2_open_encoding.py`) | UTF-8 / BOM / UTF-16LE / LF / CRLF / CR round trips; malformed input rejected transactionally |
| Atomic save fault injection (`test_v8_5_2_write_injection.py`) | 8/8 modes preserve the target and clean staging files |
| Destructive transitions (`test_v8_5_2_destructive.py`) | Cancel/Discard/Save for close and New, picker cancel, failed save |
| Revision ownership (`test_v8_5_2_revision.py`) | `(0,0) → (1,0) → (2,2) → (3,2) → (4,2) → (4,4) → (5,5)`, exit 0, relocated base reported |
| Capacity gates | 2600 headings, 140,000 spans, Outline/style/render/document/scratch arena failure cases |
| Memory plateau (`test_v8_5_3_memory_plateau.py`) | 12 cycles × 3 fixtures, handle growth 0 |
| Windows GUI smoke | 17/17 |
| Ordinary close | 5/5 exit code 0 |

## Stability rationale

PeMark is a personal open-source experiment whose primary research goal is
AI-native software engineering. This release is labelled stable because the
properties that a user depends on are now backed by measurements rather than
intentions:

- documents cannot be lost by a failed save, a short write, an interrupted
  replacement or an unsaved destructive transition;
- no fixed document-sized buffer silently truncates content any more, and a
  failed allocation leaves the active document untouched;
- writable memory is not executable, code pages are read-only, and the image is
  relocated by ASLR on every run;
- repeated open/parse/close cycles reach a stable memory and handle plateau.

What stable does **not** claim is recorded in the release notes: the binary is
unsigned, verification was done on the maintainer's machine plus one independent
machine, the 4 MiB input policy is still a compile-time bound, and full
cross-frame stack unwinding is unproven.

## Reproducing this record

```powershell
python tools/build_current.py
python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_4.py
python tools/inspect_pe.py bin/current/pemark_x64_v8_5_4.exe
$env:PEMARK_GENERATOR = "$PWD/src/current/generate_markdown_editor_v8_5_4.py"
$env:PEMARK_EXE = "$PWD/bin/current/pemark_x64_v8_5_4.exe"
python tools/test_v8_5_4_sections.py
python tools/test_v8_5_4_unwind.py
python tools/test_v8_5_2_revision.py
python tools/test_v8_5_2_open_encoding.py
python tools/test_v8_5_2_write_injection.py
python tools/test_v8_5_2_destructive.py
python tools/test_v8_5_2_capacity_baseline.py
python tools/test_v8_5_2_outline_alloc_injection.py
python tools/test_v8_5_2_style_alloc_injection.py
python tools/test_v8_5_2_style_capacity.py
python tools/test_v8_5_3_render_arena.py
python tools/test_v8_5_3_document_arena.py
python tools/test_v8_5_3_scratch_arenas.py
python tools/test_v8_5_3_memory_plateau.py
python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_5_4.exe
```

An independent machine can run the same coverage through
`python tools/verify_release_v8_5_4.py` and report the JSON summary.
