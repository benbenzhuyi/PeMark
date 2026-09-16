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

## Stack-walking metadata (.pdata)

- Emitted `RUNTIME_FUNCTION` entries for every non-leaf routine: 42 entries taken
  from the called-routine set, with each prologue read back from the generated
  machine code (push sequence plus `sub rsp, imm`). Leaf routines get no entry,
  which matches the x64 rule that an address without a table entry is unwound as
  a leaf.
- `UNWIND_INFO` blobs live in `.rdata` and the exception directory size covers
  only the entry array, which is how linkers lay this out (notepad.exe keeps
  every unwind blob in `.rdata` and its directory size is exactly the array).
- Verified: 42 well-formed version-1 entries with ordered, non-overlapping
  ranges; dbghelp resolves entries for our addresses; a real stack walk reaches
  our module; the windowed process still starts, works and exits cleanly under
  ASLR.
- Known limitation, recorded rather than claimed as working: the dbghelp walk
  reaches our frame but does not continue past it, so full unwinding is not yet
  demonstrated. Program behaviour is unaffected — the code raises no exceptions
  — and `tools/test_v8_5_4_unwind.py` prints this state explicitly instead of
  asserting success.

## CFG / CET conclusion

- Wrote `docs/V8_5_4_CFG_CET_FEASIBILITY.md` from measured facts: 480 IAT call
  sites, 11 register call sites (three UxTheme exports resolved through
  `GetProcAddress`), no exports, no runtime-replaceable function pointers, no
  LOAD_CONFIG directory and `GUARD_CF` not set.
- CFG is **not implemented**: it would need instrumentation at 491 indirect call
  sites plus a LOAD_CONFIG table, while the only indirect targets are loader-filled
  IAT slots and three system DLL exports — there is nothing an attacker could
  redirect today. The document records the three implementation steps and the
  trigger that should reopen the decision (plugin-style callbacks or model
  providers in V9).
- CET is **not declared**: the emitted code already satisfies the behavioural
  requirement (no SEH, no `ret` to a computed address, no return address written
  as data), so a declaration would add load-time risk without changing behaviour.
  The document records what a future declaration would touch.
- Also fixed a real defect found while testing the unwind table: the prologue
  parser mapped REX-prefixed `41 54..57` (R12–R15) onto register numbers 4–7
  (RSP/RBP/RSI/RDI), so unwind codes named the wrong registers.

V8.5.4's milestone deliverables are complete. One release-gate deviation is
recorded below rather than hidden.
