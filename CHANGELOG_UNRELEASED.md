# PeMark V8.6 (unreleased)

V8.5.4 shipped as the first stable release; its full record is
`docs/CHANGELOG_V8_5_4.md`.

## V8.6.1 — Custom title row and six tool icons

The main window now uses a merged 32px title row instead of the native
caption + menu bar pair. The row is owned by a `DirectPE_Caption` child so its
paint, hit-test and hover state stay in one place:

```
[left switch] [PeMark·码记] [File Edit Markdown View Help] ... [save]
[find] [render/source] [dark/light] [gear] [right sidebar] [min] [max] [close]
```

The six tool icons follow the Markra/Codex line style, share one 24px slot and
one theme palette, and invalidate only the caption surface on hover. Save,
find, render/source and dark/light post the existing command IDs, so the
replacement row does not create a second state owner. The left switch posts
the existing `View → Left Sidebar` command (`1307`). The gear and right-sidebar
buttons are deliberate placeholders: they paint and hover today, but a click
has no action. `CAPTION_MODE=system` rebuilds the original native
caption + menu bar path for comparison and fallback.

Evidence: `tools/test_v8_6_caption.py` checks the no-caption/resizable style,
the 32px full-width row, the shared rect table, hover on the right-sidebar
placeholder, inert placeholder clicks, and the live left switch;
`smoke_test_v8_5_1.py` is 17/17; the panel, theme, navigation, keymap and
workspace suites remain green. The candidate now reports V8.6.1.

Scope revision (2026-09-16): the file panel is being redesigned to follow the
Rabbit editor's explorer — an expandable directory tree with new/rename/delete/
refresh/collapse — replacing the earlier "single flat list, read-only" decision.
The design, the Rabbit reference behaviour and the remaining slices A–E are in
`docs/FILE_PANEL_REDESIGN.md`; no code has been written against it yet.

## Keymap alignment with Rabbit

Shared actions now use Rabbit's keys: `Ctrl+Shift+S` saves as, `Ctrl+Shift+O`
opens a folder, `Ctrl+W` closes the document, and `Ctrl+B` toggles the whole
left sidebar (the View item is renamed `Left Sidebar`). The status bar moved to
the freed `Ctrl+Alt+S`, Insert Link to `Ctrl+Alt+L` and Code Block to
`Ctrl+Alt+K`, which leaves `Ctrl+K` and `Ctrl+Shift+K` free for the V9 AI quick
edit and V8.7's Delete Line.

`docs/KEYBINDINGS.md` holds the full mapping, the conflict decisions and the
reserved keys for later milestones. Build-time assertions tie the accelerator
table to the menu hints, and `tools/test_v8_6_keymap.py` parses the shipped
table out of the running process and verifies the reserved keys stay unused.

## V8.6.1 — Sidebar split into two panels (slice 0)

The outline and the file browser are no longer two modes of one ListBox. The
sidebar now holds two independent lists stacked vertically: the file panel owns
`hwnd_files` plus its own gutter, the outline keeps `hwnd_outline`, and
`resize_children` splits the available height between them. Each list owns its
content — workspace entries in the file panel, document headings in the outline
— so editing a document can no longer disturb the file list, and the earlier
`panel_mode` "one list at a time" semantics are gone.

Row drawing decides its data source from the control ID (14 = file panel), so
neither list can read the other's tables. The status bar path segment now
follows the workspace directly instead of the panel mode.

The frame around those lists is live. Each panel has a 28px header and the two
are separated by a draggable 4px divider:

- a single header click is held for 250ms and then walks
  `half → minimized → maximized → half`, matching Rabbit's `setTimeout`
  behaviour; deferring the first click is what keeps the second click of a
  double click on a header that has not moved yet;
- a double click (same header, within 500ms, timed with `GetMessageTime`)
  cancels the pending single click and swaps minimized/maximized, so the three
  reachable states are exactly Rabbit's;
- the divider highlights with the accent colour and shows `IDC_SIZENS` while
  hovered or dragged. Dragging converts the pointer's absolute position into
  `panel_split` and clamps it to `[80, 920]` per-mille, so neither panel can be
  squeezed below a usable strip.

Still open in slice 0: the file panel's own scrollbar ownership (the overlay
still serves the outline), `View → Files/Outline Panel` becoming visibility
switches, and the directory tree itself (slice 1).

Evidence: `tools/test_v8_6_panel.py` rewritten for the two-panel layout (both
lists visible and stacked, each owning its content, directory/file colours in
both themes, scrollbar geometry following the panel height) and extended with
real pointer input: hover highlight, `+80px` drag arithmetic, both clamp ends,
the full single-click tristate walk and all three double-click transitions;
`tools/test_v8_6_navigation.py` now drives the file panel. Full V8.5.4 suite,
the slice 1–4 suites and `smoke_test_v8_5_1.py` (17/17) pass.

`tools/test_v8_5_1.py` keeps its role as the static machine-code regression
suite: the emulated bootstrap now runs `resize_children` so the scrollbar
scenarios consume the published `outline_list_h` instead of the whole content
height, and the height/top matrix drives that same symbol. It still passes
against the V8.5.1–V8.5.4 generators.

## V8.6.1 — Fixes found by real testing

Four defects reported from hands-on use are fixed:

1. **Theme switch left the sidebar frame stale.** The two 28px headers, the 4px
   divider and the gutter are owner-drawn children; swapping the brushes is not
   enough, and nothing repainted them until a resize (hiding and reopening the
   sidebar) happened to. `apply_theme` now invalidates and updates every frame
   window explicitly, so a theme switch repaints the frame immediately.
2. **The file panel had no scrollbar and ignored the wheel.** It first gained a
   native `WS_VSCROLL` bar; the follow-up section below replaces that with the
   shared thin overlay so both panels match. The wheel routing (three rows per
   notch, clamped to `max(0, count - visibleRows)`) is shared by both.
3. **The outline scrollbar looked thicker and off-theme.** That bar was the
   gutter painting the *stale light* brush from item 1; once the frame repaints,
   the gutter carries the panel background and only the thin hover thumb shows.
   `tools/test_v8_6_theme_picker.py` pins the palette of all four frame windows
   in both themes.
4. **Open Folder used a different dialog family than Open File.** The legacy
   `SHBrowseForFolderW` tree is now only the fallback: the primary path is the
   modern common item dialog (`CoCreateInstance(CLSID_FileOpenDialog)` +
   `FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM`, `GetResult` →
   `GetDisplayName(SIGDN_FILESYSPATH)`), which shares its look, keyboard and
   theme with `GetOpenFileNameW`. Cancelling changes nothing; the legacy path
   stays for machines where the class is unavailable.

One engineering lesson is now enforced at build time: a command handler that is
entered by `jmp` from the message pump must reserve a stack frame that is a
multiple of 16. The first version of the picker used `0x38`, which left every
API call misaligned; `CoCreateInstance` then failed with what looked like "class
not registered" (`REGDB_E_CLASSNOTREG`) instead of working. The new assertion
scans every routed command label for exactly that mistake.

Evidence: `tools/test_v8_6_theme_picker.py` (frame palette in three theme
transitions, file-list scrollbar theme, in-process `CoCreateInstance` +
`GetOptions`, the opened dialog carries the shell DirectUI view, cancel keeps
the workspace root) and the extended `tools/test_v8_6_panel.py` (native
`WS_VSCROLL` style, wheel arithmetic, both clamps).

## V8.6.1 — Sidebar looks: one thin scrollbar, menu font, tree next

Hands-on review against Rabbit made two visual gaps explicit, and both are now
closed:

1. **One scrollbar implementation for both panels.** The file panel's native
   `WS_VSCROLL` bar (17px, arrow buttons, system colour) is gone. Each panel now
   reserves the same 17px strip and hosts its own surface of the shared
   `DirectPEOutlineScroll` class, painted by one code path: the track takes the
   panel background and only a **6px centred thumb** is drawn, in the theme's
   scrollbar colour. The thumb rect is published by the panel's layout routine
   (`scroll_layout` / `files_scroll_layout`) and used by both the painter and
   the hit test, so the two bars cannot drift apart. Both are shown whenever the
   list overflows (Rabbit-like) instead of appearing only on hover, and both
   support thumb drag and track paging.

   Follow-up: the first cut drew a flat 11px rectangle, which still read as
   "thick and ugly" next to the document's native bar. The thumb is now a
   rounded capsule drawn with `RoundRect` under `NULL_PEN`, and it mirrors the
   native behaviour exactly - **6px while the pointer is away, 11px plus the hot
   colour as soon as it reaches the strip** (`*_scroll_hot`, recomputed by the
   hover handler). Both panels share that geometry rule, so they stay identical.
2. **Panel titles use the menu bar font.** `Files` / `Outline` were drawn with
   the default owner-draw font. The app now reads
   `SystemParametersInfoW(SPI_GETNONCLIENTMETRICS)` and builds the header font
   from `lfMenuFont`, selecting it explicitly into the paint DC, so the titles
   match the menu bar's face and size. If the query fails it falls back to the
   status-bar font.

File-header comments in `docs/FILE_PANEL_REDESIGN.md` were updated to record the
final decision and why the native-scrollbar detour was dropped.

What is still visibly behind Rabbit is the file tree itself (expand arrows,
per-type icons, indentation) and the outline's richer row rendering — that is
slice 1/2 of the redesign plan, tracked in the same document.

Build-time assertions keep the two bars unified: the file list may not carry
`WS_VSCROLL`, both surfaces must come from the shared class, the paint path may
not recompute thumb geometry, and both layouts must publish the same 6px
centred rect plus the always-visible rule.

## V8.6.1 — Sidebar strips repaint, drag no longer smears

Three defects reported from use, all in the same area:

1. **A lighter gutter column at startup.** The scroll surfaces were hidden
   whenever a list did not overflow, so nothing painted that 17px strip and the
   window background showed through instead of the panel background. The
   surfaces are now permanently shown while the sidebar is visible: they always
   paint the strip in the panel colour, and only the *thumb* depends on the
   overflow (6px calm / 11px hot).
2. **Dragging the sidebar smeared the document.** `resize_children` moved and
   resized the document surfaces without invalidating them, so RichEdit kept
   stale pixels until an unrelated repaint. The resize path now forces
   `RDW_INVALIDATE|RDW_ERASE|RDW_ALLCHILDREN` on both surfaces and re-syncs the
   file scrollbar.
3. **Repeated sidebar toggles left document text glued to the scroll strip.**
   Same root cause as (1): with the surface hidden, that strip was never
   repainted, so whatever the document had drawn there stayed. With the surface
   always visible and repainted on every resize, the strip can no longer hold
   stale content.

Evidence: `tools/test_v8_6_theme_picker.py` toggles the sidebar three times and
asserts both strips stay visible, keep the panel background pixel, and that the
preview surface is byte-identical to a forced clean repaint; build-time
assertions forbid hiding the surfaces while the sidebar is visible and require
the resize repaint plus the file-scrollbar resync.

## V8.6.1 — Sidebar scrollbars are Windows-native now

The custom overlay scrollbar experiment is over: both panels use the ListBox's
own scrollbar, exactly like the document uses the EDIT's.

* Both list boxes are created with `WS_VSCROLL | LBS_DISABLENOSCROLL`: the bar is
  native (so **dragging the thumb works**, with the system's thin/thick hover
  behaviour and no custom hit-testing), and it stays in place when the list fits
  so the text width never jumps.
* Both lists get `AllowDarkModeForWindow` + `SetWindowTheme`, the same treatment
  the document surface gets, so in dark mode the sidebar bars look like the
  document's instead of the light classic bar.
* Both lists now span the whole sidebar width; the reserved gutter, the overlay
  surface windows, the owner-drawn gutter and the custom input interception are
  gone. Three guard jumps keep the retired overlay path out of the mouse
  pipeline (`lbd_after_frame` → splitter test, `lbu_not_scroll` → files test,
  `mousemove_not_divider_drag` → hover).
* The wheel still routes by pointer hit-test (so a panel scrolls without being
  focused first) and drives `LB_SETTOPINDEX`, which keeps the native thumb in
  sync.

The bug behind "the outline thumb cannot be dragged" was structural: the custom
hit test compared the pointer's *client* coordinates against the overlay's
*local* thumb rectangle, so every press looked like a track click. Native
scrollbars remove the whole class of problem.

Retired but not yet deleted: the overlay routines (`scroll_layout`,
`sync_*_scrollbar`, `*_scroll_drag_move`, `update_*_hover`, `scrollproc`) and
their BSS fields are now unreachable dead code. Their deletion is the immediate
follow-up cleanup; the wheel scratch fields (`files_scroll_*`) are still live.

Evidence: `tools/test_v8_6_panel.py` asserts both lists report
`WS_VSCROLL|LBS_DISABLENOSCROLL`, that both span the sidebar width, and that the
wheel still scrolls three rows per notch with both clamps;
`tools/test_v8_6_theme_picker.py` checks the two list backgrounds and the
document-repaint invariant through repeated sidebar toggles. Build-time
assertions pin the styles, the dark-mode opt-in for both lists, the retired
overlay class never being created and the three guard jumps.

## V8.6.1 — Preview wheel scrolling no longer fights the viewport

Two rendered-mode symptoms, one root cause. The 180 ms deferred "format the
visible window" pass ended in `restore_surface_state`, which scrolled to the
saved top anchor and *then* re-applied `EM_SETSEL`. RichEdit scrolls the caret
into view whenever the selection is set, so every deferred pass yanked the
viewport back to the caret - and the caret stays where the user last edited
(usually far above), which is exactly the reported "scroll to the document end
and it jumps back / seems to keep scrolling". Because hiding Markdown markers
reflows the text, a single formatting pass could also push a region into view
that it never formatted, leaving raw source on screen until the next nudge.

Fixes: restore the selection *before* the anchor scroll so the anchor wins;
run the visible-window formatting twice (the second pass covers whatever the
first pass reflowed into view, and re-applying the same character formats is
idempotent); raise the forward margin from 2000 to 6000 characters so a fast
flick cannot outrun the formatted window.

Evidence: a probe with a 400-chapter document in Preview mode - 25 wheel
notches put the first visible line at 73, and after the deferred refresh
settled it reads 124 (it advances with the reflow instead of jumping back);
`tools/test_v8_5_1.py` was updated for the new margin and passes.

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

## Slice 4 (part 1) — Menu entries that make the panels reachable

The panel mechanisms from slices 2 and 3 existed only behind test-build
commands, so a user could not reach them at all. This adds the two entries:

- `File → Open Folder...` browses for a directory with `SHBrowseForFolderW`
  (the returned PIDL is released with `ILFree`), adopts it as the workspace root
  and switches to the file panel;
- `View → Files Panel` and `View → Outline Panel` drive the same `panel_mode`
  through the shared `set_panel_mode`, and `sync_panel_menu` keeps their mutual
  check state equal to `panel_mode`.

Evidence: `tools/test_v8_6_panel.py` now switches the panel through the real
menu command ids and asserts the `MF_CHECKED` state of both items follows
`panel_mode` while the ListBox rectangle stays unchanged;
`tools/test_v8_6_navigation.py` adopts a second workspace through the
Open-Folder path and asserts the list, the current directory and the status bar
all follow. The only part of slice 4 still open is the in-memory recent-file
list at the bottom of the File menu.
