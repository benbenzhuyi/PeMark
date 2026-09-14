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
- Candidate size: 77,824 bytes.
- Emitted text: 27,194 bytes, 128 bytes above V8.5.1.
- Candidate SHA-256:
  `19199bd3b352f9d4f003c3264b5084dd009557bd218feb7e8fc4d6d8013d34c5`.

## Remaining before promotion

- Add end-to-end Open and Save dialog automation when the document-safety work
  reaches successful Open fixtures and Save As path replacement. Existing-path
  Save is now covered through the real controller and disk bytes.
- Independently inspect helper bytes and every revision call site.
