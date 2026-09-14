# PeMark V8.5.1 Preview

## V8.5.2 preparation

- Established normative file-operation contracts and a verified current I/O and
  fixed-capacity map.
- Defined build-time-only failure injection for file I/O and arena allocation.
- Added deterministic UTF-8, BOM, UTF-16LE, malformed-input, embedded-NUL and
  boundary fixtures with SHA-256 records.
- Added a 30-run Windows launch/resource/clean-exit baseline harness.
- No production generator or executable behavior changed in this preparation step.

## V8.5.2 document revision candidate

- Added a candidate-channel implementation of 64-bit `document_revision` and
  `saved_revision` with single-writer build assertions. The fields are appended
  after the V8.5.1 state layout so all existing BSS addresses remain stable.
- Verified the runtime transitions `(0,0) -> advance (1,0) -> Open commit (2,2)
  -> edit (3,2) -> edit (4,2) -> Save commit (4,4) -> New (5,5)` through direct
  process-state reads and calls to the emitted commit helpers.
- Repeated the complete revision sequence for 10/10 clean Windows runs.
- Added a read-only 64-bit revision-equality helper as the single dirty-state
  derivation point, with normalized clean/dirty results and build assertions.
- Verified that an internally suppressed `EN_CHANGE` leaves revisions and dirty
  state unchanged; user notifications still advance the document revision.
- Routed New, Open, menu Exit and external window close through one pending
  destructive-action controller with Save/Discard/Cancel behavior.
- Made Save failure and dialog cancellation abort the pending destructive
  transition while preserving the dirty document.
- Added a Windows decision-matrix test covering clean close, Cancel/Discard/Save
  for dirty Close and New, Open cancellation, successful saved bytes, and failed
  Save preservation.
- Made Save As transactional with respect to document identity: the selected
  path remains a candidate until the write succeeds and its handle closes.
  Cancellation or failure therefore retains the previous `current_path`.
- Added a real Save As cancellation check and build-time assertions for the
  required close-handle, path-commit and saved-revision ordering.
- Replaced the one-shot save write with a complete-write loop that advances on
  partial success and rejects API failure, zero progress and counts above the
  requested remainder.
- Added a 512 KiB real-disk save check and build-time loop/back-edge guards.
- Added generator-controlled, test-only WriteFile wrappers for short success,
  zero success, first-call failure and partial-then-failure. Their binaries are
  visibly marked and isolated under ignored `bin/test/`; release bytes remain
  unchanged.
- Recorded the remaining direct-write data-loss behavior under injected failure
  as the concrete blocker for sibling temporary-file atomic replacement.
- Preserved all V8.5.1 machine-code and Windows GUI regression results.
- Kept the V8.5.1 current/release generator and binary unchanged.

V8.5.1 is the current public Preview baseline. Existing V8.4.23, V8.4.24 and the
external V8.5.0 reference remain frozen.

## V8.5.1 implemented

- Retains the pure Direct-PE pipeline, expanded V8.5 text layout, unified
  Markdown/Outline scan, and single-writer ViewState.
- Fixes message-loop fallthrough on window destruction and removes the
  disproved loader-reentry model and guard.
- Corrects the V8.5 ViewState commit branch: PREVIEW(1) had incorrectly taken
  the Source visibility path.
- Preserves indentation and spaces inside fenced code after the unified
  scanner's leading-space probe.
- Recreates word-wrapped EDIT controls empty, raises the text limit before
  loading the model, reloads the module handle, and preserves the unchanged
  Preview render model.
- Limits theme formatting to the actual Preview viewport plus 2,000 characters
  and clips large spans to that window.
- Uses one cached Outline scrollbar layout for paint, hit-test and drag,
  including cached travel/rectangles, floor row capacity, event-time MSG.pt,
  signed drag clamps and no thumb for a non-scrollable outline.
- Corrects the Windows smoke test: programmatic WM_SETTEXT does not emit
  EN_CHANGE, so the test now sends the child notification explicitly.

## V8.5.1 evidence

- Generator: `src/stabilization/generate_markdown_editor_v8_5_1.py`
- Candidate: `bin/stabilization/pemark_x64_v8_5_1.exe`
  (77,824 bytes; emitted text 27,066 bytes).
- Generator SHA256:
  `75e2312769cc398d73e39a4a67f80476bb3744a41ff26e45e5cd5a017f9e003c`
- EXE SHA256:
  `b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`
- Two consecutive builds produced the same EXE SHA256.
- 12/12 Unicorn machine-code groups passed, including 210 scrollbar boundary
  combinations and volatile-register/shadow-space poisoning.
- Corrected Windows smoke suite passed 17/17.
- Zero-debugger WM_CLOSE matrix passed 5/5 with exit code 0.
- Detailed record: `docs/V8_5_1_MERGE_RESULTS.md`; generated map:
  `docs/PE_MEMORY_MAP_V8_5_1.md`.

## Previous V8.4.24 stabilization

Frozen V8.4.23 remains unchanged. Work lives in src/stabilization and bin/stabilization.

## Scope
- Reproduce Windows baseline defects before changing runtime code.
- Single ViewController and canonical Outline navigation.
- Consolidated scrollbar geometry consumed by paint, hit-test and drag.
- Deterministic regression tests plus Windows GUI evidence.

## Baseline
Original handoff manifest hashes verified (126 entries); 40 Python files parse.
Portable build reproduces SHA256 50fdb51c28a90f9457d61761c923cd54f668de040e81941d99030fc42f2f2f4f.
GUI release gate remains pending; do not label this version stable.

## Implemented in the V8.4.24 candidate

- ViewController owns SOURCE/PREVIEW and surface visibility. Outline retains canonical source offsets and derives Preview positions without keeping live offsets in volatile API registers.
- One cached scrollbar state and geometry function serves painting, hit testing and dragging. Corrected reversed proportional-thumb branch, floor-based visible-row count, negative drag clamp, capture cancellation, and short-outline hover visibility.
- Queued drag events use MSG.pt instead of a later GetCursorPos result. Windows fast dragging previously became an unintended page click.
- Preview formatting uses the actual viewport bottom plus a 2,000-character margin and clips intersecting huge spans. Windows navigation exposed long stalls in the old fixed 40,000-character window.
- Fixed message-loop fallthrough after main-window destruction; exit now reaches cleanup/ExitProcess explicitly.
- Fixed fenced-code whitespace loss exposed by the Markdown matrix: line-start probing no longer repeats for every code character or consumes indentation.
- Word-wrap recreation uses the correct Source control style and preserves the unchanged Preview model, formatting and position.
- Large-file wrap recreation now reloads the module handle instead of reusing the file byte-count register; it creates an empty EDIT, raises its text limit, then sets document text. Passing the full large document at control creation caused the process to exit; correcting the module handle alone was insufficient. Windows verified wrap off/on and subsequent navigation after the two-stage load fix.

The last three changes are bounded fixes justified by regression evidence, beyond the initial two-controller scope. Production remains pure Python-emitted PE; Unicorn is a test-only dependency. No imports or shortcuts were added.

## Build and evidence

- Candidate: `bin/stabilization/direct_pe_markdown_editor_x64_v8_4_24.exe` (45,056 bytes).
- SHA256: `a0342cd8f7bd8a6c4118241621e54fed7b4b83401c881fdfc73cc7e6633ee260`.
- Emitted code: 26,878 / 28,672 bytes, leaving 1,794 bytes. Virtual BSS remains 121,106,432 bytes.
- 12 deterministic machine-code regression groups pass, including 210 geometry combinations; Win32 mocks poison volatile registers and shadow space and check ABI alignment.
- Results: `tests/results/final_machine_tests.json`, `final_pe_inspection.txt`, `stabilization.patch`; current symbol map: `docs/PE_MEMORY_MAP_V8_4_24.md`.
- Windows observations and exact build attribution: `docs/STABILIZATION_V8_4_24_RESULTS.md`.
- Current candidate Windows pass (2026-09-14): first large-file Source navigation and Preview toggle; Preview Chapters 1/50/100; 20 mode and 20 theme transitions; fast drag top/middle/end/back and track paging; normal process exit. See `final_gui_toggles.json` and `final_large_end.json`.
- Original handoff manifest: 125 entries unchanged; only `docs/PE_MEMORY_MAP.md` gained the candidate-map index. Frozen code and binaries match their original hashes.

## Remaining scope

Do not infer general file safety from these GUI fixes. Existing Save/Save As atomicity, short-write detection, unsaved-document protection, ANSI fallback and capacity limits remain separate audit items. The complete smoke/encoding/capacity suite has not yet been certified.
