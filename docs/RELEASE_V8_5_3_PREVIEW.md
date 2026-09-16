# PeMark V8.5.3 Preview

English | [简体中文](RELEASE_V8_5_3_PREVIEW.zh-CN.md)

V8.5.3 is the dynamic-capacity release. It keeps the pure Direct-PE build and
every V8.5.2 document-safety guarantee, and it removes the last fixed
document-sized buffers. No visible behaviour was traded away: the 4 MiB input
policy, the editor text limit and the unsaved-change rules are unchanged.

## What changed

- The document text, the position map with its render text, the style spans and
  the Outline tables now live in arenas sized from the actual document instead
  of fixed arrays. The 2048-entry Outline and 131072-entry style caps are gone.
- Decode/serialize scratch and the file-byte buffer are committed in 64 KiB
  blocks sized by the operation, and the encoding APIs take their limits from
  the published capacity. A small document no longer reserves tens of megabytes
  that only a large one needs.
- Every arena publishes its pointer only after a successful allocation, so a
  failed growth leaves the active document, path, revisions, encoding and EOL
  metadata untouched. Capacity that was already committed stays owned as
  reusable cache.

## Capacity result

| Buffer | V8.5.2 | V8.5.3 |
|---|---|---|
| Virtual BSS | 119,508,992 bytes | 8,192 bytes |
| PE virtual size | 121,159,680 bytes | 86,016 bytes |
| Outline entries | fixed 2048 | dynamic |
| Style spans | fixed 131,072 | dynamic |
| Document, render, decode and file buffers | fixed | dynamic |

The enormous writable region that made section separation impractical is gone;
PE hardening continues as V8.5.4.

## Validation

- 13/13 emitted-machine-code behavior groups.
- 17/17 Windows GUI smoke checks.
- 5/5 ordinary WM_CLOSE runs returned exit code 0.
- Open/encoding transaction matrix and eight atomic-save fault modes.
- Destructive-transition and revision-ownership matrices.
- Allocation-failure injection for the Outline, style, render, document, decode
  and file-byte arenas.
- 2600-heading Outline, 140,000-span style and 1.2 MB document capacity cases.
- Memory plateau: 12 cycles of Open + Preview + New over small, medium and large
  fixtures with zero handle growth and about 1.8 MB of private-memory growth.
- Two consecutive builds produced the same binary.

Release asset:
`pemark_x64_v8_5_3.exe`

SHA-256:
`6ad87c6dcb3b9d3a35041d1bc37e5792f3cfd16cb79046088a3426200d0bb7d0`

## Preview limitations

The 4 MiB input policy is still a compile-time bound, although the buffers behind
it are now dynamic; raising it is a separate, testable change. Legacy code pages
are not accepted as a fallback. The image is still a single read/write/execute
section, unsigned, without ASLR or unwind metadata. Workspace, advanced editing
and AI features are not part of this release. Keep backups of important
documents.
