# V8.5.2 Document Revision Candidate Results

Scope: first bounded production change; candidate channel only

## Change

- Added 64-bit `document_revision` and `saved_revision` to the end of runtime
  state, preserving every V8.5.1 BSS symbol address.
- Reserved `(0,0)` for the process-initial empty document.
- User `EN_CHANGE` advances document revision after suppression is checked.
- New and all three successful Open decode branches advance once and commit the
  same saved revision.
- Successful current Save copies document revision to saved revision.
- Revision wrap skips zero.
- Added the read-only `is_document_dirty` leaf helper. It derives dirty state
  exclusively from the full 64-bit revision equality and normalizes its return
  value to zero or one; no independent dirty flag exists.
- Routed New, Open, menu Exit and external `WM_CLOSE` through one destructive
  transition controller. Dirty transitions offer Save/Discard/Cancel; a Save
  continues only after the existing save path reaches its commit point.
- Save failure and file-dialog cancellation clear the pending transition and
  keep the current document alive.
- Save As keeps the selected path in `temp_path`, writes that candidate, and
  copies it to `current_path` only after successful `WriteFile` and
  `CloseHandle`. Cancel and failure retain the previous path.
- Replaced the one-shot `WriteFile` call with a complete-write loop. Each
  successful partial write advances the byte pointer and reduces remaining;
  API failure, zero progress, or a count above remaining enters save failure.

No title marker, encoding change, save-byte algorithm change, allocator change,
import change or PE section change is included.

## Ownership gate

Build-time assertions require the revision fields to be written only by their
leaf helpers. They also require four clean-document commit call sites, two
revision-advance call sites and two mark-saved call sites.

## Runtime evidence

`tools/test_v8_5_2_revision.py` reads the emitted process state directly and
invokes the emitted commit helpers at their generated code addresses. It waits
for the edit control so the process startup sequence is complete before taking
the initial state sample:

```text
initial: (document_revision, saved_revision) = (0, 0)
direct revision helper:                      = (1, 0)
successful Open commit helper:               = (2, 2)
suppressed internal EN_CHANGE:                = (2, 2), clean
user edit:                                   = (3, 2)
second user edit:                            = (4, 2)
successful Save commit helper:               = (4, 4)
New:                                         = (5, 5)
normal close exit code:                  = 0
```

## Regression evidence

- 12/12 prior emitted-machine-code behavior groups passed.
- 210/210 scrollbar boundary combinations passed.
- 17/17 prior Windows GUI smoke checks passed.
- PE inspection passed with the same import surface and section model.
- The full revision sequence passed 10/10 consecutive Windows runs.
- Clean/dirty helper results were checked at every transition; a forced
  `suppress_edit_change=1` notification left both revisions unchanged.
- The destructive matrix passed for clean Close; dirty Close
  Cancel/Discard/Save; dirty New Cancel/Discard/Save; dirty Open decision
  Cancel and picker Cancel; and failed Save during Close. It checks text,
  revisions, pending action, exit code and successful-save bytes.
- Save As cancellation was exercised through the real file picker, and
  build-time ordering assertions require `close handle -> commit path -> mark
  saved` on its success path.
- A 512 KiB document saved through the real controller matched the expected
  UTF-8 bytes. Build assertions require the `WriteFile` back edge and both
  zero-progress and excessive-count failure branches.
- Build-time-only I/O variants passed for short-write completion,
  zero-success rejection, first-call failure, partial-then-failure, flush
  failure, atomic-replace failure, staging-create failure and close-status
  failure with cleanup retry. Test
  executables are visibly titled, emitted only under ignored `bin/test/`, and
  leave the release candidate hash unchanged.
- Save now writes a sibling `.pemark.tmp` with `CREATE_NEW`, loops to completion,
  flushes, checks close and commits with
  `MoveFileExW(REPLACE_EXISTING | WRITE_THROUGH)`. All tested pre-commit failures
  preserve the old target, old path, dirty revisions and any preexisting staging
  artifact; newly owned staging files are removed.
- A staging collision now has a dedicated recovery message and cancels the
  pending destructive transition. The normative ownership, discovery and
  manual recovery behavior is recorded in `V8_5_2_RECOVERY_POLICY.md`.
- Open now has a single success commit point after read and encoding validation.
  Strict UTF-8, UTF-8 BOM and UTF-16LE BOM pass through a noninteractive Windows
  test build; malformed UTF-8, embedded NUL and odd-byte UTF-16 retain the old
  model, path, revisions and Preview mode.
- The Open path now loops until the file-size snapshot is completely read.
  Seven-byte short reads complete successfully; zero progress, first-call
  failure and partial-then-failure preserve the full prior transaction.
- Open commits encoding and preferred EOL with the document. Noninteractive
  delete-and-recreate tests prove byte-identical Save round-trips for UTF-8,
  UTF-8 BOM, UTF-16LE BOM, CRLF, LF, CR, and BOM-only empty files.
- Unicorn executes the emitted EOL detection/serialization helpers directly and
  verifies revision wraparound skips the reserved zero value. The check runs in
  the CI entrypoint rather than relying only on source inspection.
- The pre-arena capacity test opens the frozen 2600-heading fixture and observes
  exactly 2048 Outline entries, ending at Heading 2048. This converts the known
  fixed-array truncation into a deterministic CI baseline for Phase E.
- The first Phase E slice replaces `outline_srcpos`, `outline_renderpos`, and
  `outline_level` with pointers into one dynamically sized arena. The same test
  now requires 2600 entries and verifies first/middle/last stored offsets and
  actual Source navigation.
- Outline capacity is now reserved from the candidate's exact normalized length
  before Open mutates the active model. Injected failure on the first growth
  allocation preserves model, path, revisions, encoding, EOL, view state,
  Outline count, pointers, and sampled prior arena bytes.
- The second Phase E slice retires the fixed 131072-entry Markdown style table.
  `style_start`, `style_end` and `style_type` are now segments of one
  `VirtualAlloc` arena sized `max(4096, normalized_length/2 + 16)` entries, and
  `apply_styles` refuses to run before that arena exists. Fixed tables accounted
  for 3 x 512 KiB of the previous BSS; `bss_vsize` dropped from 121,081,856 to
  119,508,992 bytes.
- A 140,000-span regression document records 140,000 spans (the retired cap
  would have truncated at 131,072) with verified arena geometry and
  first/cap-boundary/last span payloads.
- `tools/test_v8_5_2_style_alloc_injection.py` proves that a failed style-arena
  growth leaves the active document, metadata, view state and previous arena
  untouched, and that a failed first allocation publishes no arena at all.
- Candidate size: 78,336 bytes.
- Emitted text: 29,466 bytes, 2,400 bytes above V8.5.1.
- Candidate SHA-256:
  `e134e6d2419574aacf975b217a610aebbb6a5070e36f20ef25d83d3e6ce1857a`.

## Promotion path

V8.5.2 is scoped to document safety (see `MILESTONE_PLAN.md`). Dynamic capacity
continues as V8.5.3, so the remaining arena migrations no longer block this
release.

Before promotion:

- rerun the Commit and Milestone gates on the release commit;
- record the known limits: the document, render and position-map buffers are
  still fixed, oversized input is rejected explicitly rather than truncated, and
  interrupted-save recovery follows `V8_5_2_RECOVERY_POLICY.md`;
- keep the V8.5.1 baseline binaries untouched.
