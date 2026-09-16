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
