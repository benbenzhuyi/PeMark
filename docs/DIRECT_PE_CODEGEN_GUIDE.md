# Direct PE Code Generation Guide

## Build philosophy

The Python script is not the application runtime. It is a **binary image generator**. It writes a complete Windows PE32+ image containing AMD64 machine code and manually constructed imports/data.

## Current PE layout (V8.4.23)

```text
ImageBase       0x140000000
FileAlignment   0x200
SectionAlignment 0x1000

TEXT_RVA        0x1000
RDATA_RVA       0x8000
IDATA_RVA       0xB000
BSS_RVA         0xC000
```

The file currently uses one loader-simple RWX section whose raw area contains code + rdata + idata and whose virtual-only tail supplies BSS.

```text
.text section characteristics = 0xE00000E0
CODE | INIT_DATA | UNINIT_DATA | EXECUTE | READ | WRITE
```

This is deliberate experimental simplicity, not a production-hardening recommendation.

## Critical current capacity

- Code budget from 0x1000 to 0x8000: 28672 bytes.
- Current emitted code: 27426 bytes.
- Remaining: **1246 bytes**.

Do not add significant emitted code before changing layout. Preferred next step: move RDATA farther out or introduce a section/RVA allocator. Longer term, generate separate `.text`, `.rdata`, `.idata`, `.data/.bss` sections.

## PE headers

- DOS `MZ`, `e_lfanew=0x80`
- PE signature `PE\0\0`
- Machine AMD64 `0x8664`
- Optional header magic PE32+ `0x20B`
- GUI subsystem
- Image base 0x140000000
- no base-relocation directory; ASLR is therefore not enabled in current builds
- import and IAT directories point into manually built IDATA

## Import table construction

`build_idata()` creates:

1. IMAGE_IMPORT_DESCRIPTOR array
2. ILT arrays
3. IAT arrays
4. DLL names
5. hint/name entries
6. descriptor RVAs

`call_iat(fn)` emits RIP-relative indirect `FF 15 rel32` to the IAT slot.

See `docs/WIN32_API_SURFACE.md` for current DLL/function set.

## RDATA

The generator writes UTF-16/ASCII strings, accelerator table, status part boundaries, filters, Markdown syntax strings and other constants into a manually aligned bytearray.

## BSS

`bss_alloc()` assigns virtual RVAs sequentially. The file does not store the zero bytes; the section's virtual size extends through BSS and Windows zero-initializes it.

Current BSS is about 115.50 MiB because of large document/work buffers and render-source map.

## Machine-code emitter

`class E` provides minimal instructions and fixup handling:

- labels/rel32 branches/calls
- RIP-relative LEA/load/store
- register moves/arithmetic
- simple indexed UTF-16 access
- IAT calls

It is intentionally incomplete. Add instruction encoders carefully and test byte encodings independently.

## Branch fixups

Internal labels store offsets in the TEXT bytearray. `patch()` resolves relative displacements. Any PE layout change must preserve distinction between file offset, section offset, RVA and VA.

## Reproducible build

Use:

```powershell
python .\src\current\generate_markdown_editor_v8_4_23.py
python .\tools\inspect_pe.py .\bin\current\direct_pe_markdown_editor_x64_v8_4_23.exe
```

The captured generator currently hardcodes `/mnt/data` output. One early refactor should add a command-line/project-relative output path while producing identical bytes otherwise.

## Recommended codegen refactor

Before V8.5 grows:

- central `PELayout` object allocating RVAs
- typed symbols (code/rdata/bss/import)
- structured function frames for stack/ABI
- helper to spill volatile values
- section builder
- deterministic symbol/map dump
- optional debug symbol text map (`label -> RVA`)

Keep final output pure PE; these are build-time generator improvements only.
