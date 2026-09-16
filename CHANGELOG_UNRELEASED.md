# PeMark V8.5.4 (unreleased)

V8.5.3 shipped; its full record is `docs/CHANGELOG_V8_5_3.md`.

V8.5.4 is the Direct-PE hardening milestone: declare sections and region
permissions, add base relocations and ASLR, emit unwind metadata where it
applies, and verify the result with the existing loader and regression
evidence. The huge single writable region is gone, so this work can now be
measured instead of argued about.

## Section separation (W^X)

- The single RWX section is gone. The image now declares four sections in RVA
  order: `.text` (RX, code), `.rdata` (R, strings and read-only tables),
  `.idata` (RW, import directory and IAT) and `.bss` (RW, zero-initialized
  state). No section is both writable and executable.
- Each section's `VirtualSize` and `SizeOfRawData` span the whole gap to the next
  RVA, and the raw buffer stays one-to-one with the RVA plan. A compact layout
  made Windows reject the image with `ERROR_BAD_EXE_FORMAT`; the rejected and
  accepted variants are recorded in `docs/FAILED_APPROACHES.md`.
- The header area grew to 0x400 so the four section headers fit inside
  `SizeOfHeaders`. File size is 78,848 bytes; `SizeOfImage` is 90,112 bytes.
- Added `tools/test_v8_5_4_sections.py`: it parses the section table (names,
  order, RVAs, raw ranges, characteristics, no W+X) and then queries the loaded
  image with `VirtualQueryEx` to require `PAGE_EXECUTE_READ` for `.text`,
  `PAGE_READONLY` for `.rdata` and `PAGE_READWRITE` for `.idata`/`.bss`, followed
  by a real windowed launch and clean exit.
- Re-verified on this channel: 13/13 machine-code groups, Open/encoding
  transaction matrix, atomic save fault injection, destructive transition
  matrix, revision ownership, Outline/style/render/document/scratch arena
  failure, 140000-span capacity, memory plateau and the 17/17 GUI smoke suite.

## Base relocations and ASLR

- Added a `.reloc` section: one block per image page, each block declaring only
  `IMAGE_REL_BASED_ABSOLUTE` entries. That is the correct statement for this
  image because every data reference is RIP-relative and every imported call goes
  through the IAT, so no location needs a fixup.
- `DllCharacteristics` now sets `DYNAMIC_BASE` next to `NX_COMPAT`, so the loader
  chooses the base address. Verified by reading the module base at runtime: runs
  land at e.g. `0x7FF73D810000` instead of the preferred `0x140000000`, and
  windowed launch, symbol access and clean shutdown all still work.
- Build assertions require whole relocation blocks, page-aligned `PageRVA`,
  ABSOLUTE-only entries, one block per image page and `DYNAMIC_BASE` enabled.
- `tools/test_v8_5_4_sections.py` now also checks the relocation directory, the
  block structure and that the loaded base differs from the preferred base.
- File size is 87,552 bytes and `SizeOfImage` 94,208 bytes: `.reloc` adds 0x200
  bytes of raw data and the raw buffer extends to the relocation RVA.
- Test entrypoints no longer require the preferred base. `test_v8_5_2_revision.py`
  reports the actual (relocated) base, and the V8.5.2/V8.5.3 suites derive their
  output names from the generator under test so one suite can cover both channels.

`.pdata` unwind metadata and the CFG/CET feasibility conclusion remain for later
slices.
