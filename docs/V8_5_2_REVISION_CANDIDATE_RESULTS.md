# V8.5.2 Document Revision Candidate Results

Scope: first bounded production change; candidate channel only

## Change

- Added `document_revision` and `saved_revision` to runtime state.
- Reserved `(0,0)` for the process-initial empty document.
- User `EN_CHANGE` advances document revision after suppression is checked.
- New and all three successful Open decode branches advance once and commit the
  same saved revision.
- Successful current Save copies document revision to saved revision.
- Revision wrap skips zero.

No close prompt, title marker, encoding change, save-byte change, allocator
change, import change or PE section change is included.

## Ownership gate

Build-time assertions require the revision fields to be written only by their
leaf helpers. They also require four clean-document commit call sites, two
revision-advance call sites and two mark-saved call sites.

## Runtime evidence

`tools/test_v8_5_2_revision.py` reads the emitted process state directly:

```text
initial: (document_revision, saved_revision) = (0, 0)
user edit:                               = (1, 0)
New:                                     = (2, 2)
normal close exit code:                  = 0
```

## Regression evidence

- 12/12 prior emitted-machine-code behavior groups passed.
- 210/210 scrollbar boundary combinations passed.
- 17/17 prior Windows GUI smoke checks passed.
- PE inspection passed with the same import surface and section model.
- Candidate size: 77,824 bytes.
- Emitted text: 27,155 bytes, 89 bytes above V8.5.1.
- Candidate SHA-256:
  `e5d0df68af457712162d4d1bf18adc312c3647f77dcc1faf7cd821be14e10132`.

## Remaining before promotion

- Exercise successful Open revision commits through automated file-dialog or a
  deterministic test entry point.
- Exercise successful Save mark-saved behavior without changing the production
  file algorithm.
- Independently inspect helper bytes and every revision call site.
- Decide whether the revision counter should be 32-bit or widened before the
  public V8.5.2 state layout is frozen.

