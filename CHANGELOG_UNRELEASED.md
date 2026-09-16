# PeMark V8.6 (unreleased)

V8.5.4 shipped as the first stable release; its full record is
`docs/CHANGELOG_V8_5_4.md`.

V8.6 is scoped to "browse a directory and open files from it" while the
application still owns a single writable document. The plan
(`docs/MILESTONE_PLAN.md` §6) deliberately defers destructive file operations,
tree navigation, drag-and-drop, a background directory watcher and on-disk window
state, and reuses the existing self-drawn list, scrollbar geometry, layout
manager and theming instead of introducing `SysTreeView32`.

Four bounded slices: directory enumeration without UI, the sidebar file list,
entering directories and opening files through the existing Open transaction,
then menu/shortcut integration with an in-memory recent list.

Add entries here as each slice lands, with level-appropriate evidence.

## Slice 1 — WorkspaceModel and directory enumeration (no UI)

Complete. `workspace_set_root` records the root and current directory and
enumerates it with `FindFirstFileW`/`FindNextFileW`; `FindClose` always runs.
The entry table lives in its own growable arena and owns, per entry, the name
(260 UTF-16 units), the raw `dwFileAttributes`, the normalised directory kind,
the 64-bit size and the last-write `FILETIME`, in a 544-byte stride. `"."` and
`".."` are dropped, sub-directories and `.md`/`.markdown`/`.txt` files are kept,
and ordering is directories first, then case-insensitive name order. Empty,
missing, overlong, non-directory and access-denied paths publish a win32 error
with an empty list; a later valid directory enumerates normally.

Evidence: `tools/test_v8_6_workspace_enum.py` PASS (filtering, ordering,
Unicode and 255-character names, attribute/size/time ownership, 130 entries
across the 64-entry arena boundary, empty/missing/overlong/guarded directories,
recovery), full V8.5.4 suite re-run PASS, `smoke_test_v8_5_1.py` 17/17, released
V8.5.4 binary unchanged (`AA8DE9CD…`).

Two real defects were found and fixed while implementing the slice:

- Growing the workspace arena released the old block without copying it, so
  every entry collected before the 64-entry boundary was lost. The grow path
  now copies `count * 544` bytes before `VirtualFree`.
- Entry addressing was emitted as a hard-coded `index*512 + index*16` while the
  record grew to 544 bytes, which surfaced as empty names past the first block.
  Both call sites now use `index*512 + index*32`, and a build-time assertion
  ties `WS_STRIDE == 512 + 32` to the emitted code.

## Slice 2 — Sidebar panel modes over one list control

Complete. `panel_mode` selects what the existing sidebar ListBox shows: the
document outline (default) or the workspace entries. Both modes reuse the same
control, the same layout geometry, the same permanently reserved scrollbar
gutter and the same `sync_outline_scrollbar` state, so no second list, no second
scrollbar and no second theme path were introduced. `set_panel_mode` owns the
switch and `refresh_panel_list` owns "rebuild whichever list is current", which
also lets a new workspace root refresh an active file list.

Row drawing distinguishes the two kinds without new resources: directory rows
append a backslash and take the accent colour, file rows keep the body colour.
The file branch reads the kind straight out of the workspace arena and never
touches `outline_level`, which indexes a different table. While the file panel
is active the outline scan neither clears the shared ListBox nor appends rows to
it, and selecting a file row does not navigate the document.

Evidence: `tools/test_v8_6_panel.py` PASS — identical ListBox geometry across a
mode switch, pixel snapshots showing different row colours for directories and
files in both themes, the heading palette unchanged when the outline returns,
selectable but inert file rows, wheel scrolling of the shared scrollbar with
clamping to `count - visible_rows`, and an outline correctly rebuilt from edits
made while the file panel was showing. Full V8.5.4 suite, slice-1 suite and
`smoke_test_v8_5_1.py` 17/17 PASS; two builds byte-identical; released V8.5.4
binary unchanged.

One defect was found while implementing the slice: the outline scan cleared the
shared ListBox unconditionally, so editing the document while the file panel was
active emptied the file list.

## Slice 3 — Navigating the workspace and opening from the list

Complete. A double-click on a directory row makes it the workspace root and the
list follows; Backspace goes up one level, but only while the file list owns the
keyboard focus, so the editor keeps its normal delete behaviour. The status bar
gained a seventh part that publishes the workspace directory whenever the file
panel is showing and clears it otherwise.

A double-click on a file row does not introduce a second way to open a document.
It only fills `temp_path`, sets `pending_destructive_action = 2` and raises
`open_bypass_picker`, then enters the existing `destructive_request`. The shared
unsaved-changes controller runs first; once the user confirms, `destructive_open`
skips the picker for that one request and continues into the unchanged
`cmd_open_selected` read/decode/commit path. Cancelling clears the flag and keeps
the current document.

Evidence: `tools/test_v8_6_navigation.py` PASS — entering a directory through the
double-click notification, Backspace going up only with the list focused, the
status bar painting the directory (and clearing it for the outline panel), a
clean file opening with the right text, Cancel keeping a dirty document and its
revision gap, Discard continuing into the new document, an undecodable file
leaving the previous document untouched, and a UTF-16LE file keeping its
encoding. Full V8.5.4 suite, slice-1 and slice-2 suites and
`smoke_test_v8_5_1.py` 17/17 PASS; two builds byte-identical; released V8.5.4
binary unchanged.

One defect was found and fixed while implementing the slice: the new list
activation jumped into the never-returning Open path without discarding its own
return address, which left the stack permanently misaligned by eight bytes and
crashed the process inside the Open transaction.
