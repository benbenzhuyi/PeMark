#!/usr/bin/env python3
"""V8.6.1 slice 3a: inline tree-row rename with authorization and duplicate checks."""
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
    ROOT / "src/candidate/generate_markdown_editor_v8_6.py"))
EXE = Path(os.environ.get(
    "PEMARK_TREE_EXE",
    ROOT / "bin/candidate/pemark_x64_v8_6_candidate.exe"))

CMD_TREE_REBUILD = 1910
WM_RENAME_BEGIN = 0x8008
WM_KEYDOWN = 0x0100
WM_CHAR = 0x0102
WM_SETTEXT = 0x000C
LB_SETCURSEL = 0x0186
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B

u32, k32 = c.windll.user32, c.windll.kernel32
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM


def load_ns():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN.resolve()), "__name__": "__pemark_rename__"}
    exec(compile(source.split("\nout = ")[0], str(GEN), "exec"), ns)
    return ns


def write_wstr(app, symbol, text):
    raw = (str(text) + "\0").encode("utf-16le")
    count = c.c_size_t()
    source = c.create_string_buffer(raw)
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), source,
        len(raw), c.byref(count)) and count.value == len(raw)


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError(message)


def select_leaf(app, list_hwnd, leaf):
    pointer = app.read64("tree_rows")
    count = app.read32("tree_row_count")
    raw, got = c.create_string_buffer(count * 544), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(pointer), raw,
                                 len(raw), c.byref(got))
    row_index = None
    for index in range(count):
        block = raw.raw[index * 544:(index + 1) * 544]
        path = block[:520].decode("utf-16le").split("\0", 1)[0]
        if path.lower().endswith(leaf.lower()):
            row_index = index
            break
    assert row_index is not None, leaf
    for item in range(u32.SendMessageW(list_hwnd, 0x018B, 0, 0)):
        if u32.SendMessageW(list_hwnd, 0x0199, item, 0) == row_index:
            u32.SendMessageW(list_hwnd, LB_SETCURSEL, item, 0)
            return
    raise AssertionError("leaf not projected: %s" % leaf)


def begin(app, list_hwnd, item_index=0):
    u32.SendMessageW(list_hwnd, LB_SETCURSEL, item_index, 0)
    assert u32.PostMessageW(app.main, WM_RENAME_BEGIN, 0, 0)
    wait_for(lambda: app.read32("rename_active") == 1, 3,
             "rename editor did not open")


def commit(app, name):
    rename = app.read64("hwnd_rename")
    u32.SendMessageW(rename, 0x00B1, 0, 0xFFFFFFFF)
    for ch in name:
        u32.SendMessageW(rename, WM_CHAR, ord(ch), 0)
    assert u32.PostMessageW(app.main, WM_KEYDOWN, VK_RETURN, 0)
    wait_for(lambda: app.read32("rename_active") == 0, 3,
             "rename commit did not finish")


def cancel(app, name):
    rename = app.read64("hwnd_rename")
    u32.SendMessageW(rename, 0x00B1, 0, 0xFFFFFFFF)
    for ch in name:
        u32.SendMessageW(rename, WM_CHAR, ord(ch), 0)
    assert u32.PostMessageW(app.main, WM_KEYDOWN, VK_ESCAPE, 0)
    wait_for(lambda: app.read32("rename_active") == 0, 3,
             "rename cancel did not finish")


def main():
    ns = load_ns()
    with tempfile.TemporaryDirectory(prefix="pemark-rename-") as temp:
        root = Path(temp)
        old = root / "old.md"
        old.write_text("# old\n", encoding="utf-8")

        app = App(ns, EXE)
        try:
            list_hwnd = app.read64("hwnd_files")
            write_wstr(app, "tree_root_path", root)
            write_wstr(app, "ws_root_path", root)
            write_wstr(app, "ws_current_path", root)
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: u32.SendMessageW(list_hwnd, 0x018B, 0, 0) == 1,
                     3, "rename fixture did not list")

            begin(app, list_hwnd)
            commit(app, "new.md")
            assert (root / "new.md").exists() and not old.exists()

            duplicate = root / "duplicate.md"
            duplicate.write_text("# duplicate\n", encoding="utf-8")
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: u32.SendMessageW(list_hwnd, 0x018B, 0, 0) == 2,
                     3, "duplicate fixture did not list")
            select_leaf(app, list_hwnd, "duplicate.md")
            begin(app, list_hwnd)
            commit(app, "new.md")
            assert duplicate.exists(), "duplicate rename must be rejected"

            select_leaf(app, list_hwnd, "duplicate.md")
            begin(app, list_hwnd)
            commit(app, "bad\\name.md")
            assert duplicate.exists(), "separator rename must be rejected"

            select_leaf(app, list_hwnd, "duplicate.md")
            begin(app, list_hwnd)
            cancel(app, "cancelled.md")
            assert duplicate.exists(), "escape must not rename"

            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS rename: commit, duplicate rejection, separator "
                  "rejection and escape cancel")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
