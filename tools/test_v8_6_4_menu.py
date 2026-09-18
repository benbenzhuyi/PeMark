#!/usr/bin/env python3
"""V8.6.4: exclusive panel switches, the reserved right sidebar, recent files.

Evidence collected here:

* the View menu panel entries are exclusive maximize switches: selecting
  Files Panel drives files_state to 0 (maximized) with outline_state 2
  (minimized), selecting Outline Panel is symmetric, and selecting the
  already-checked entry restores the default half/half split with both
  checks cleared. The menu check follows the same rule: it is set only for
  the (maximized, minimized) pair, never for half/half;
* the reserved Right Sidebar entry (Ctrl+J, command 1315) toggles
  right_sidebar_visible together with its menu check, and the V8.6 layout
  never consumes the state;
* opening a document through the shared Open transaction pushes it onto the
  recent list, the File menu tail is rebuilt with exactly one Exit that
  stays in the last position (the static separator + Exit tail is rebuilt
  too, never duplicated), duplicates are moved to the head instead of
  appended, the list saturates at 10 entries with the oldest one dropped,
  a recent menu command reopens the file through the same Open transaction,
  and an out-of-range recent command is ignored without touching state.
"""
import ctypes as c
from ctypes import wintypes as w
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v8_5_2_destructive import App

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/current/generate_markdown_editor_v8_6_4.py"))

CMD_TREE_REBUILD = 1910
CMD_PANEL_FILES = 1308
CMD_PANEL_OUTLINE = 1309
CMD_RIGHT_SIDEBAR = 1315
CMD_RECENT_FIRST = 1316
CMD_RECENT_LAST = 1325

WM_APP = 0x8000
WM_LIST_ACTIVATE = WM_APP + 7
LB_GETCOUNT = 0x018B
LB_SETCURSEL = 0x0186
MF_BYCOMMAND = 0x0000
MF_BYPOSITION = 0x0400
MF_CHECKED = 0x0008
MF_SEPARATOR = 0x0800
RECENT_SLOT = 1024          # bytes per recent_paths entry (512 WCHAR)
RECENT_CAPACITY = 10

u32, k32 = c.windll.user32, c.windll.kernel32
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.GetMenuState.argtypes = [c.c_void_p, w.UINT, w.UINT]
u32.GetMenuState.restype = w.UINT
u32.GetMenuItemCount.argtypes = [c.c_void_p]
u32.GetMenuItemCount.restype = c.c_int
u32.GetMenuStringW.argtypes = [c.c_void_p, w.UINT, c.c_wchar_p, c.c_int, w.UINT]
u32.GetMenuStringW.restype = c.c_int


def build():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_menu_test__",
          "OPEN_TEST_BUILD": True}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    version_tag = GEN.stem.replace("generate_markdown_editor_", "")
    assert out.name == f"pemark_x64_{version_tag}_open_transaction_test.exe", out.name
    return ns, out


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.03)
    raise AssertionError(message)


def write_wstr(app, symbol, value):
    raw = (str(value) + "\0").encode("utf-16le")
    source, count = c.create_string_buffer(raw), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), source,
        len(raw), c.byref(count)) and count.value == len(raw)


def menu_checked(hmenu, command):
    state = u32.GetMenuState(hmenu, command, MF_BYCOMMAND)
    assert state != 0xFFFFFFFF, "command %d is not in the menu" % command
    return bool(state & MF_CHECKED)


def menu_item_count(hmenu):
    count = u32.GetMenuItemCount(hmenu)
    assert count >= 0
    return count


def menu_item_text(hmenu, position):
    buffer = c.create_unicode_buffer(1024)
    got = u32.GetMenuStringW(hmenu, position, buffer, 1024, MF_BYPOSITION)
    assert got >= 0
    return buffer.value


def menu_item_is_separator(hmenu, position):
    return bool(u32.GetMenuState(hmenu, position, MF_BYPOSITION) & MF_SEPARATOR)


def read_recent(app, index):
    raw, count = c.create_string_buffer(RECENT_SLOT), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle,
        c.c_void_p(app.base + app.bsyms["recent_paths"] + index * RECENT_SLOT),
        raw, RECENT_SLOT, c.byref(count)) and count.value == RECENT_SLOT
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def assert_file_menu_shape(app, hmenu, base, expected_count, note):
    """The dynamic tail must be [sep, recent items..., sep, Exit] exactly.

    An empty list keeps the startup shape [static commands, sep, Exit]; a
    non-empty list inserts the entries between two separators before Exit.
    """
    expected_total = base + 2 if not expected_count else base + 2 + \
        expected_count + 1
    count = menu_item_count(hmenu)
    assert count == expected_total, \
        "%s: expected %d items, got %d" % (note, expected_total, count)
    assert menu_item_is_separator(hmenu, base), \
        "%s: the tail must start with a separator" % note
    for index in range(expected_count):
        assert menu_item_text(hmenu, base + 1 + index) == \
            read_recent(app, index), \
            "%s: recent item %d must show its stored path" % (note, index)
    exit_text = menu_item_text(hmenu, count - 1)
    assert exit_text.startswith("E&xit"), \
        "%s: Exit must stay last, got %r" % (note, exit_text)
    exits = sum(1 for position in range(count)
                if menu_item_text(hmenu, position).startswith("E&xit"))
    assert exits == 1, "%s: Exit must appear exactly once, got %d" % (note,
                                                                     exits)


def activate_tree_row(app, list_hwnd, index):
    u32.SendMessageW(list_hwnd, LB_SETCURSEL, index, 0)
    u32.PostMessageW(app.main, WM_LIST_ACTIVATE, 0, 0)


def main():
    ns, exe = build()
    with tempfile.TemporaryDirectory(prefix="pemark-recent-") as temp:
        root = Path(temp)
        names = ["a.md", "b.md"] + ["f%02d.md" % i for i in range(3, 12)]
        for name in names:
            (root / name).write_text("# %s\n" % name, encoding="utf-8")

        app = App(ns, exe)
        try:
            wait_for(lambda: app.read32("init_done") == 1, 5,
                     "application initialization did not finish")
            hmenu_file = app.read64("hmenu_file")
            hmenu_view = app.read64("hmenu_view")
            assert hmenu_file and hmenu_view

            # ---- initial state: half/half, nothing checked, empty recents ----
            assert app.read32("files_state") == 1 and \
                app.read32("outline_state") == 1, "default layout is half/half"
            assert not menu_checked(hmenu_view, CMD_PANEL_FILES), \
                "half/half must not check Files Panel"
            assert not menu_checked(hmenu_view, CMD_PANEL_OUTLINE), \
                "half/half must not check Outline Panel"
            assert app.read32("right_sidebar_visible") == 0 and \
                not menu_checked(hmenu_view, CMD_RIGHT_SIDEBAR), \
                "the reserved right sidebar starts hidden and unchecked"
            assert app.read32("recent_count") == 0
            base = app.read32("file_menu_base_count")
            assert base == 10, "the static command segment has 10 items"
            assert_file_menu_shape(app, hmenu_file, base, 0,
                                   "startup File menu")

            # ---- exclusive maximize switches ----
            app.post_command(CMD_PANEL_FILES)
            wait_for(lambda: app.read32("files_state") == 0 and
                     app.read32("outline_state") == 2, 3,
                     "Files Panel must maximize itself and minimize Outline")
            assert menu_checked(hmenu_view, CMD_PANEL_FILES) and \
                not menu_checked(hmenu_view, CMD_PANEL_OUTLINE), \
                "only the maximized panel may carry the check"
            app.post_command(CMD_PANEL_FILES)
            wait_for(lambda: app.read32("files_state") == 1 and
                     app.read32("outline_state") == 1, 3,
                     "selecting the checked entry must restore half/half")
            assert not menu_checked(hmenu_view, CMD_PANEL_FILES) and \
                not menu_checked(hmenu_view, CMD_PANEL_OUTLINE), \
                "restoring half/half must clear both checks"

            app.post_command(CMD_PANEL_OUTLINE)
            wait_for(lambda: app.read32("outline_state") == 0 and
                     app.read32("files_state") == 2, 3,
                     "Outline Panel must maximize itself and minimize Files")
            assert menu_checked(hmenu_view, CMD_PANEL_OUTLINE) and \
                not menu_checked(hmenu_view, CMD_PANEL_FILES), \
                "the checks stay exclusive"
            app.post_command(CMD_PANEL_OUTLINE)
            wait_for(lambda: app.read32("files_state") == 1 and
                     app.read32("outline_state") == 1, 3,
                     "the outline switch must restore half/half too")

            # ---- reserved right sidebar toggle ----
            app.post_command(CMD_RIGHT_SIDEBAR)
            wait_for(lambda: app.read32("right_sidebar_visible") == 1, 3,
                     "Ctrl+J must set the reserved flag")
            assert menu_checked(hmenu_view, CMD_RIGHT_SIDEBAR), \
                "the right sidebar menu entry must check with the flag"
            app.post_command(CMD_RIGHT_SIDEBAR)
            wait_for(lambda: app.read32("right_sidebar_visible") == 0, 3,
                     "Ctrl+J must clear the reserved flag again")
            assert not menu_checked(hmenu_view, CMD_RIGHT_SIDEBAR)

            # ---- recent list through the shared Open transaction ----
            list_hwnd = app.read64("hwnd_files")
            write_wstr(app, "tree_root_path", root)
            write_wstr(app, "ws_root_path", root)
            write_wstr(app, "ws_current_path", root)
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0)
                     == len(names), 3, "the temporary workspace did not load")

            # open a: recent grows to one entry, the menu tail follows
            activate_tree_row(app, list_hwnd, 0)
            wait_for(lambda: app.read_path().endswith("a.md"), 3,
                     "tree activation must open a.md")
            wait_for(lambda: app.read32("recent_count") == 1, 3,
                     "opening must push the file onto the recent list")
            assert read_recent(app, 0).endswith("a.md")
            assert_file_menu_shape(app, hmenu_file, base, 1, "one recent")

            # open b: newest first
            activate_tree_row(app, list_hwnd, 1)
            wait_for(lambda: app.read_path().endswith("b.md"), 3,
                     "tree activation must open b.md")
            wait_for(lambda: app.read32("recent_count") == 2, 3,
                     "the second file must extend the list")
            assert read_recent(app, 0).endswith("b.md") and \
                read_recent(app, 1).endswith("a.md"), \
                "the newest entry must sit at the head"
            assert_file_menu_shape(app, hmenu_file, base, 2, "two recents")

            # reopen a: deduplicated and moved to the head, no growth
            activate_tree_row(app, list_hwnd, 0)
            wait_for(lambda: app.read_path().endswith("a.md") and
                     app.read32("recent_count") == 2 and
                     read_recent(app, 0).endswith("a.md") and
                     read_recent(app, 1).endswith("b.md"), 3,
                     "reopening a file must move it to the head, not append")
            assert_file_menu_shape(app, hmenu_file, base, 2, "dedup rebuild")

            # a recent command reopens entry 1 (b.md) through the transaction
            app.post_command(CMD_RECENT_FIRST + 1)
            wait_for(lambda: app.read_path().endswith("b.md") and
                     read_recent(app, 0).endswith("b.md"), 3,
                     "a recent entry must reopen its file and take the head")
            assert app.read32("recent_count") == 2

            # out-of-range recent commands must be ignored
            before = app.read_path()
            app.post_command(CMD_RECENT_LAST)     # index 9, list holds 2
            time.sleep(.4)
            assert app.proc.poll() is None, \
                "an out-of-range recent command must not crash"
            assert app.read_path() == before and \
                app.read32("recent_count") == 2, \
                "an out-of-range recent command must be ignored"

            # ---- saturation: 11 distinct files, capacity 10 ----
            for index in range(2, len(names)):
                activate_tree_row(app, list_hwnd, index)
                name = names[index]
                wait_for(lambda name=name: app.read_path().endswith(name), 3,
                         "tree activation must open %s" % name)
            wait_for(lambda: app.read32("recent_count") == RECENT_CAPACITY,
                     3, "the recent list must saturate at 10 entries")
            assert read_recent(app, 0).endswith(names[-1]) and \
                read_recent(app, 1).endswith(names[-2]), \
                "the newest files must lead the saturated list"
            assert read_recent(app, RECENT_CAPACITY - 1).endswith(names[1]), \
                "the second file opened must be the oldest survivor"
            assert all(not read_recent(app, i).endswith("a.md")
                       for i in range(RECENT_CAPACITY)), \
                "the very first file must have been evicted"
            assert_file_menu_shape(app, hmenu_file, base, RECENT_CAPACITY,
                                   "saturated menu")

            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS V8.6.4 menu work: exclusive panel maximize switches "
                  "with checked-state parity, reserved Ctrl+J right sidebar "
                  "toggle, and a 10-entry recent list with dedup, head-move, "
                  "saturation, single-Exit tail rebuild, transaction reuse "
                  "and out-of-range protection")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
