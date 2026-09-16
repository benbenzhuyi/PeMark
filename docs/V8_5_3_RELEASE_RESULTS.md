# V8.5.3 Release Validation Results

Scope: dynamic-capacity release of the pure Direct-PE Markdown editor. Every
command below was executed against the release channel
(`src/current/generate_markdown_editor_v8_5_3.py` and
`bin/current/pemark_x64_v8_5_3.exe`) in an interactive Windows desktop session.

## Release identity

| Item | Value |
|---|---|
| Version | V8.5.3 (Preview) |
| Generator | `src/current/generate_markdown_editor_v8_5_3.py` |
| Generator SHA-256 | `7926f34ed8ef5312a469ff8200fd559070921587aebc7f0dedacbaa5dd37f2b8` |
| Binary | `bin/current/pemark_x64_v8_5_3.exe` |
| Binary size | 78,336 bytes |
| Binary SHA-256 | `6ad87c6dcb3b9d3a35041d1bc37e5792f3cfd16cb79046088a3426200d0bb7d0` |
| Emitted text | 30,672 bytes (budget 61,440) |
| Virtual BSS | 8,192 bytes |
| PE virtual size | 86,016 bytes |

## Commit gate

| Check | Command | Result |
|---|---|---|
| Deterministic build | `python tools/build_current.py` | two builds, identical SHA-256 |
| Machine-code regressions | `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_3.py` | 13/13 groups, 0 failures |
| PE inspection | `python tools/inspect_pe.py bin/current/pemark_x64_v8_5_3.exe` | PE32+ AMD64, GUI, image size 0x16000 |

## Milestone gate

The V8.5.2 suites run unchanged on the V8.5.3 release channel through
`PEMARK_GENERATOR` / `PEMARK_EXE`:

| Check | Result |
|---|---|
| Revision ownership (`test_v8_5_2_revision.py`) | `(0,0) -> (1,0) -> (2,2) -> (3,2) -> (4,2) -> (4,4) -> (5,5)`, exit 0 |
| Open transaction and strict encoding (`test_v8_5_2_open_encoding.py`) | UTF-8 / BOM / UTF-16LE / LF / CRLF / CR round trips; malformed input rejected transactionally |
| Atomic save fault injection (`test_v8_5_2_write_injection.py`) | 8/8 modes preserve the target and clean staging files |
| Destructive transition matrix (`test_v8_5_2_destructive.py`) | Cancel/Discard/Save for close and New, picker cancel, failed save |
| Outline capacity and arena failure | 2600 headings registered; growth failure preserves state |
| Style arena failure and capacity | 140,000 spans recorded; both injection modes safe |
| Render arena (`test_v8_5_3_render_arena.py`) | geometry, mapping range/monotonicity, preview load, growth failure preserved |
| Document arena (`test_v8_5_3_document_arena.py`) | reservation reuse, aligned block growth, editor-driven growth, failure safety |
| Scratch arenas (`test_v8_5_3_scratch_arenas.py`) | empty start, aligned growth, reuse, Save round trip, byte/wide failure safety |
| Memory plateau (`test_v8_5_3_memory_plateau.py`) | 12 cycles x 3 fixtures: handle growth 0, private usage +1.8 MB, working set +1.3 MB |
| Windows GUI smoke (`smoke_test_v8_5_1.py`) | 17/17 |
| Ordinary close | 5/5 runs returned exit code 0 |

## Capacity outcome

| Buffer | V8.5.2 | V8.5.3 |
|---|---|---|
| Document text | fixed 8.5M units | reserved policy bound, 512 KiB blocks |
| Render map + render text | fixed 8.5M units | dynamic arena from normalized length |
| Style spans | fixed 131,072 | dynamic arena |
| Outline entries | fixed 2048 | dynamic arena |
| Decode/serialize scratch | fixed 8.5M units | arena, 64 KiB blocks |
| File bytes and encoded output | fixed 34.5 MB | arena, 64 KiB blocks |
| Virtual BSS | 119,508,992 bytes | 8,192 bytes |
| PE virtual size | 121,159,680 bytes | 86,016 bytes |

The 4 MiB input policy, the editor text limit and every safety guarantee from
V8.5.2 are unchanged.

## Known limitations carried into this release

- The 4 MiB input policy is still a compile-time bound; the buffers behind it are
  no longer fixed, so raising the policy is now a separate, testable change.
- Legacy code pages are still not a fallback.
- The image remains a single read/write/execute section, unsigned, without ASLR
  or unwind metadata. That is the V8.5.4 scope; the huge virtual region that
  blocked section separation is gone.
- Workspace, advanced editing and AI features are not part of this release.

## Reproducing this record

```powershell
python tools/build_current.py
python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_5_3.py
python tools/inspect_pe.py bin/current/pemark_x64_v8_5_3.exe
$env:PEMARK_GENERATOR = "$PWD/src/current/generate_markdown_editor_v8_5_3.py"
$env:PEMARK_EXE = "$PWD/bin/current/pemark_x64_v8_5_3.exe"
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
python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_5_3.exe
```
