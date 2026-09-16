# PeMark V8.5.4

English | [简体中文](RELEASE_V8_5_4.zh-CN.md)

V8.5.4 is the first stable release of PeMark. The Python generator still emits
the PE32+ image and AMD64 machine code directly, without a compiler, assembler or
linker, and the release is the point where the properties a user depends on are
backed by measurements instead of intentions.

## What stable means here

- Your work is protected: saving is transactional through a sibling staging file
  with atomic replacement, unsaved changes are derived from document revisions
  and guarded by one shared Save / Discard / Cancel controller, and every tested
  failure path keeps the previous file and the in-memory document intact.
- Nothing silently truncates: the fixed document, render, style, Outline, decode
  and file-byte buffers are gone, replaced by arenas sized from the actual
  document. A failed allocation leaves the active document untouched.
- Memory is audited: virtual BSS fell from 119.5 MB to 8 KB, and repeated
  open/parse/close cycles reach a stable memory and handle plateau.
- The image is hardened: six sections with separated permissions (no page is
  writable and executable at the same time), base relocations and ASLR enabled,
  and unwind metadata emitted for every non-leaf routine.

## Changes since V8.5.1 Preview

| Area | V8.5.1 Preview | V8.5.4 |
|---|---|---|
| Saving | single `CREATE_ALWAYS` write, short writes accepted | staging file, complete-write loop, atomic replace, recovery policy |
| Unsaved work | no protection | revision-derived dirty state, shared Save/Discard/Cancel |
| Encoding | UTF-8 with silent ANSI fallback | strict UTF-8 / UTF-8 BOM / UTF-16LE BOM, EOL preserved |
| Capacity | 2048 Outline, 131072 styles, fixed 8.5M-unit buffers | dynamic arenas, no silent truncation |
| Memory | 119.5 MB virtual BSS | 8 KB virtual BSS, stable plateau |
| PE | one read/write/execute section, fixed base | six sections, W^X enforced, ASLR, `.pdata` |

## Validation

- 13/13 emitted-machine-code behavior groups, including 210/210 scrollbar
  boundary combinations.
- 17/17 Windows GUI smoke checks and 5/5 clean exits.
- Open/encoding transaction matrix and eight atomic-save fault modes.
- Destructive-transition and revision-ownership matrices.
- Allocation-failure injection for the Outline, style, render, document, decode
  and file-byte arenas.
- 2600-heading, 140,000-span and 1.2 MB capacity cases.
- Memory plateau over 12 Open + Preview + New cycles with zero handle growth.
- Section permissions and ASLR verified against the loaded image, not only the
  file.
- Deterministic consecutive builds; an independent machine can reproduce the
  same coverage with `tools/verify_release_v8_5_4.py`.

Release asset:
`pemark_x64_v8_5_4.exe`

SHA-256:
`aa8de9cda9ed90a2cf66a3a93e021dc91cc192073078a90c53fa9669f478c5cc`

## Known limitations

- The executable is unsigned. Windows SmartScreen may warn on first run; verify
  the SHA-256 above before executing.
- The 4 MiB input policy is still a compile-time bound. Oversized files are
  rejected with an explicit message rather than truncated; the buffers behind
  the policy are dynamic.
- Legacy code pages are not accepted as a fallback, so non-UTF-8 documents must
  be converted first.
- Full cross-frame stack unwinding is not demonstrated. `.pdata` is structured
  correctly, the system resolves entries for our addresses and a stack walk
  reaches the module, but a debugger does not continue past the first of our
  frames. The code raises no exceptions, so behaviour is unaffected.
- Verification was performed on the maintainer's Windows machine plus one
  independent machine using the verification pack; broader environment coverage
  is a work in progress.
- Workspace, advanced editing and AI features are not part of this release.
