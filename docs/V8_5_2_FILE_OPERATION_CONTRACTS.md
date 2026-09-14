# V8.5.2 File Operation Contracts

Status: implementation gate  
Baseline: V8.5.1 Preview

## Shared invariants

- `DocumentModel` is the only canonical text.
- `dirty := revision != saved_revision`.
- File identity changes only after a successful load or replacement.
- Failure and cancellation leave the prior model, path and disk file unchanged.
- No success UI may precede the operation's commit point.
- All byte counts use checked arithmetic and complete-read/write loops.

## FILE-NEW-001 New from clean

Given a clean document, New creates an empty untitled model, increments revision
as required by the chosen initialization rule, sets `saved_revision` equal to
the new revision and loads its Source projection. No disk operation occurs.

## FILE-NEW-002 New from dirty

New first obtains Save/Discard/Cancel. Save continues only after save commit;
Discard creates the empty model without writing; Cancel preserves text, path,
selection, view and dirty state.

## FILE-OPEN-001 Successful open

Read and decode into scratch storage, normalize into a candidate DocumentModel,
then commit text/path/encoding/EOL/revisions together. The first visible state is
SOURCE. Parser-derived models are either current for the committed revision or
explicitly dirty for rebuild.

## FILE-OPEN-002 Failed open

Missing, denied, shared, oversized, malformed or allocation-failed input reports
one actionable error. The prior document and all its derived models remain
usable. Every acquired handle and scratch arena is released.

## FILE-OPEN-003 Open while dirty

Use the same unsaved controller as New and Close. Failed Save behaves as Cancel.

## FILE-SAVE-001 Existing path

Snapshot `(revision,text,path,encoding,EOL)`, encode to scratch, write a sibling
temporary file to completion, flush according to policy and atomically replace
the target. Only then set `saved_revision` to the snapshot revision. If the
document changes during the operation, it remains dirty after commit.

## FILE-SAVEAS-001 New path

Canceling the picker changes nothing. Successful replacement commits the new
path and saved revision together. Failure retains the previous path and dirty
state and does not create a partial destination.

## FILE-WRITE-001 Short write

When WriteFile succeeds with `0 < written < remaining`, advance by `written`
and retry. A successful zero-byte write with remaining data is a failure to
prevent an infinite loop. Arithmetic and pointer advancement are checked.

## FILE-REPLACE-001 Failure preservation

Failure before replacement leaves the old target byte-identical. Failure during
replacement follows the documented Win32 primitive guarantees and exposes any
recovery artifact. Temporary-file cleanup never deletes the last recoverable
copy.

## FILE-CLOSE-001 Clean close

Clean close releases owned resources and reaches ExitProcess with code 0.

## FILE-CLOSE-002 Dirty close

Save/Discard/Cancel have the same meanings as FILE-NEW-002. Window destruction
occurs only after a continue result. Save failure keeps the window open.

## Encoding contract

V8.5.2 required inputs are UTF-8, UTF-8 BOM and UTF-16LE BOM. Malformed UTF-8
must not silently pass through ACP fallback. Any legacy fallback is a separate,
visible policy. Internal CRLF normalization and preferred output EOL are stored
separately. Round-trip expectations are fixture-specific and explicit.

## Acceptance evidence

Each contract requires a deterministic routine test, a Windows integration case
and post-operation verification of model/path/revisions, destination bytes,
temporary artifacts and live handles.

