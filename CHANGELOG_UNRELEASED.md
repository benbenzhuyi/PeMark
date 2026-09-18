# PeMark unreleased changes

[简体中文](CHANGELOG_UNRELEASED.zh-CN.md) | English

V8.6.3 shipped on 2026-09-18. Its full record is
`docs/CHANGELOG_V8_6_3.md`.

## Takeover audit (2026-09-18)

Documentation-only changes; no generator, binary or test modifications:

- `CODEX_START_HERE.md` baseline updated from V8.6.1 to V8.6.3 (version,
  generator, binary, SHA-256, validation record, first-session commands and
  current priorities);
- historical markers added to `docs/ROADMAP.md`,
  `docs/KNOWN_ISSUES_AND_TECH_DEBT.md` and `DEVELOPMENT_MANUAL.md`, because
  their V8.4-era content had been superseded by `MILESTONE_PLAN.md`,
  `V8_6_3_RELEASE_RESULTS.md` and `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`;
- `HANDOFF_CHECKLIST.md` historical pointer updated to the V8.6.3 baseline;
- baseline re-verified on the takeover host: two consecutive builds
  reproduced `5fe17a49…`, machine-code regression 13/13 groups,
  PE inspection six-section RX/R/RW/RW/R/R with no W+X page, GUI smoke
  17/17 with clean exit code 0.

## Simplified Chinese editions (2026-09-18)

- Simplified Chinese editions added for the six takeover documents:
  `CODEX_START_HERE.zh-CN.md`, `DEVELOPMENT_MANUAL.zh-CN.md`,
  `HANDOFF_CHECKLIST.zh-CN.md`, `docs/ROADMAP.zh-CN.md`,
  `docs/KNOWN_ISSUES_AND_TECH_DEBT.zh-CN.md` and
  `CHANGELOG_UNRELEASED.zh-CN.md`;
- the English originals gained language switch links;
- English remains the repository's working language: change the English
  original first, then mirror the update in the Chinese edition;
- the bilingual-document rule is now a standing repository constraint in
  `AGENTS.md` ("Change discipline"): every new project document ships in both
  English and Simplified Chinese editions.

## V8.6.4 — V8.6 workspace close-out (2026-09-18)

Generator `src/current/generate_markdown_editor_v8_6_4.py`; binary
`bin/current/pemark_x64_v8_6_4.exe`; deterministic build hash
`e7924842c33237dbdc5d37f492bccff367bf0086333bf91bc823b6231571d1ac`.

### View menu panel switches are now exclusive maximize toggles

`View → Files Panel` (1308) and `View → Outline Panel` (1309) used to share the
legacy `set_panel_mode` toggle. They now drive the same `files_state` /
`outline_state` three-state machine that the title-bar headers use:

- selecting an unchecked entry maximizes itself (`state = 0`) and minimizes
  the other panel (`state = 2`); the menu check follows the same rule, so only
  the `(maximized, minimized)` pair carries a check, never half/half;
- selecting the already-checked entry restores the default half/half split
  with both checks cleared;
- the title-bar single/double-click three-state cycle calls
  `sync_panel_menu` after `resize_children`, so the checks stay in lockstep
  with the headers regardless of which surface drove the change.

### Reserved Right Sidebar entry (Ctrl+J)

`View → Right Sidebar` (1315, `Ctrl+J`) is a deliberate placeholder for the
V9 AI right sidebar. It toggles `right_sidebar_visible` and its menu check;
the V8.6 layout does not consume the state yet. The V9 AI sidebar layout and
the caption right-sidebar button will both consume it.

### In-memory recent file list (File menu, capacity 10)

`open_commit` now calls `push_recent_path` + `rebuild_recent_menu` after
committing `current_path`. The recent list lives in BSS (`recent_paths`,
10 × 512 WCHAR slots, `recent_count`):

- only a successful Open transaction pushes; New, Close and Save As do not;
- reopening a file already in the list removes the old entry first and moves
  it to the head, so the list never holds duplicates;
- the list saturates at 10; the 11th distinct file evicts the oldest tail;
- `rebuild_recent_menu` trims the File menu tail from the static command
  segment (`file_menu_base_count`, captured once at startup as total minus the
  trailing separator + Exit) and re-appends `[separator, recent items,
  separator, Exit]`, so Exit always stays last and never duplicates;
- a recent entry (commands 1316–1325) reopens its file through the shared
  Open transaction: `temp_path ← recent[idx]`, `open_bypass_picker = 1`,
  `pending_destructive_action = 2`, then `destructive_request`. The existing
  unsaved protection, decode and commit path is reused unchanged;
- an out-of-range recent command (index ≥ `recent_count`) is ignored.

New imports: `GetMenuItemCount`, `RemoveMenu`.

### Build-time and regression coverage

- build-time assertions verify the new command routes (1308–1325, 1315),
  the accelerator entry `(FVIRTKEY|FCONTROL, 0x4A, 1315)`, the BSS fields,
  the `push_recent_path` + `rebuild_recent_menu` calls inside `open_commit`,
  the `lstrcpyW` + bypass-picker + destructive-request path in
  `cmd_recent_open`, the trim-by-position + re-append-Exit logic in
  `rebuild_recent_menu`, and that `file_menu_base_count` is captured as
  total − 2 so Exit cannot duplicate;
- `tools/test_v8_6_4_menu.py` drives a real process: exclusive maximize with
  check parity, Ctrl+J toggle, recent push/dedup/head-move/saturation/
  eviction, single-Exit tail rebuild, transaction reuse, out-of-range
  protection;
- `tools/test_v8_6_keymap.py` moved `Ctrl+J` from the reserved set into the
  expected table and checks the `m_right_sidebar` hint;
- existing suites stay green: `test_v8_6_panel`, `smoke_test_v8_5_1` (17/17),
  `test_stabilization`, `test_v8_6_tree_ui`, `test_v8_6_navigation`,
  `test_v8_6_keymap`, `test_v8_6_caption`, `test_v8_6_dpi`,
  `test_v8_6_theme_picker`, `test_v8_6_tree_model`,
  `test_v8_6_workspace_enum`.

### Build-time bug fixes caught before release

1. `file_menu_base_count` initially captured the full static item count
   including the trailing separator + Exit, so the first rebuild appended a
   second Exit. Fixed to `GetMenuItemCount() − 2`;
2. `cmd_right_sidebar` used `jcc(0x84)` (JE) instead of `0x85` (JNE) on the
   `test32` of `right_sidebar_visible`, so the toggle left the flag at zero.
   Fixed.
