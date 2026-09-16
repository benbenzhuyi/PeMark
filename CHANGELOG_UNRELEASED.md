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
