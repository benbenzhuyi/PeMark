# V8.5.2 Save Recovery Policy

Status: normative for the V8.5.2 candidate

## Artifact identity

An interrupted save may leave one sibling recovery artifact named by appending
`.pemark.tmp` to the complete destination path. For example, `notes.md` uses
`notes.md.pemark.tmp`. The artifact is never the committed document until the
atomic replacement succeeds.

## Ownership and cleanup

- PeMark creates the staging path with `CREATE_NEW` and therefore never
  truncates a preexisting artifact.
- A running save owns the artifact only after its own create call succeeds.
- Write, flush, close-status and replace failures make a best-effort cleanup of
  an artifact owned by that save.
- An artifact found before creation is unowned. PeMark must not overwrite,
  replace or delete it automatically.
- Abrupt process or machine loss can leave an owned artifact on disk. After the
  process ends it is treated as unowned recovery evidence.

## Discovery and user action

V8.5.2 discovers an existing artifact when the next save attempts `CREATE_NEW`.
It cancels any pending destructive transition, keeps the active document dirty
and displays a dedicated message telling the user to inspect, rename or remove
the `.pemark.tmp` file before saving again.

The user may compare the artifact with the committed target, rename it to a
normal document, or remove it after deciding that it is obsolete. V8.5.2 does
not automatically merge, open or promote the artifact because it may contain a
partial encoded stream from an interrupted write.

## Limits

- The fixed suffix requires the destination path to contain at most 500 UTF-16
  code units within the current 512-unit path buffer.
- Recovery discovery occurs on Save/Save As for that destination; this version
  does not scan directories at startup.
- Cleanup failure leaves the artifact intact as recovery evidence and reports
  the save as failed.

## Acceptance evidence

`tools/test_v8_5_2_write_injection.py` verifies that a preexisting artifact and
the committed target remain byte-identical, the document remains dirty, the
pending Close is canceled and no write call begins. Other injected failures
verify cleanup for an artifact created by the current save.
