#!/usr/bin/env python3
"""V8.6.1 slice 2: file-tree ListBox projection and activation."""
import ctypes as c
from ctypes import wintypes as w
from collections import Counter
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
WM_APP = 0x8000
WM_LIST_ACTIVATE = WM_APP + 7
LB_GETCOUNT = 0x018B
LB_GETCURSEL = 0x0188
LB_SETCURSEL = 0x0186
LB_GETITEMDATA = 0x0199
LB_GETTEXT = 0x0189
LB_GETITEMRECT = 0x0198
LB_SETITEMDATA = 0x019A

u32, k32, g32 = c.windll.user32, c.windll.kernel32, c.windll.gdi32
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.GetDC.argtypes = [w.HWND]
u32.GetDC.restype = w.HDC
u32.ReleaseDC.argtypes = [w.HWND, w.HDC]
g32.GetPixel.argtypes = [w.HDC, c.c_int, c.c_int]
g32.GetPixel.restype = w.COLORREF


class RECT(c.Structure):
    _fields_ = [("left", c.c_long), ("top", c.c_long),
                ("right", c.c_long), ("bottom", c.c_long)]


def load_ns():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN.resolve()), "__name__": "__pemark_tree_ui__"}
    exec(compile(source.split("\nout = ")[0], str(GEN), "exec"), ns)
    return ns


def write_u32(app, symbol, value):
    data, count = c.c_uint32(value), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), c.byref(data),
        4, c.byref(count)) and count.value == 4


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


def read_wstr_symbol(app, symbol, size=1024):
    raw, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), raw, size,
        c.byref(got))
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def item_data(app, list_hwnd, index):
    return u32.SendMessageW(list_hwnd, LB_GETITEMDATA, index, 0)


def item_text(list_hwnd, index):
    buf = c.create_unicode_buffer(512)
    assert u32.SendMessageW(list_hwnd, LB_GETTEXT, index, c.addressof(buf)) >= 0
    return buf.value


def item_rect(list_hwnd, index):
    rect = RECT()
    assert u32.SendMessageW(list_hwnd, LB_GETITEMRECT, index,
                            c.addressof(rect)) != -1
    return rect


def ink_pixels(list_hwnd, left, top, right, bottom):
    """Count pixels that differ from the modal row background colour."""
    assert u32.UpdateWindow(list_hwnd)
    hdc = u32.GetDC(list_hwnd)
    assert hdc
    try:
        pixels = [g32.GetPixel(hdc, x, y)
                  for y in range(top, bottom)
                  for x in range(left, right)]
    finally:
        u32.ReleaseDC(list_hwnd, hdc)
    pixels = [value for value in pixels if value != 0xFFFFFFFF]
    assert pixels
    background, _ = Counter(pixels).most_common(1)[0]
    return sum(value != background for value in pixels)


def main():
    ns = load_ns()
    with tempfile.TemporaryDirectory(prefix="pemark-tree-ui-") as temp:
        root = Path(temp)
        (root / "a_dir").mkdir()
        (root / "a_dir" / "child.md").write_text("# child\n", encoding="utf-8")

        app = App(ns, EXE)
        try:
            wait_for(lambda: app.read32("init_done") == 1, 5,
                     "application initialization did not finish")
            list_hwnd = app.read64("hwnd_files")
            write_wstr(app, "tree_root_path", root)
            write_wstr(app, "ws_root_path", root)
            write_wstr(app, "ws_current_path", root)
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 1
                     and item_text(list_hwnd, 0) == "a_dir",
                     3, "temporary tree did not replace the startup workspace")
            count = u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0)
            assert count == 1, count
            assert item_data(app, list_hwnd, 0) == 0
            assert item_text(list_hwnd, 0) == "a_dir", item_text(list_hwnd, 0)
            row0 = item_rect(list_hwnd, 0)
            time.sleep(.1)
            assert ink_pixels(list_hwnd, 8, row0.top + 3, 20, row0.bottom - 3) > 4, \
                "collapsed directory arrow was not painted"
            assert ink_pixels(list_hwnd, 20, row0.top + 3, 40, row0.bottom - 3) > 4, \
                "closed-folder Fluent icon was not painted"
            # First select the directory and activate it; the tree must expand.
            u32.SendMessageW(list_hwnd, LB_SETCURSEL, 0, 0)
            u32.PostMessageW(app.main, WM_LIST_ACTIVATE, 0, 0)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) > count,
                     3, "directory activation did not expand the tree")
            count = u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0)
            assert count == 2, count
            assert item_data(app, list_hwnd, 1) == 1
            assert item_text(list_hwnd, 0) == "a_dir"
            assert item_text(list_hwnd, 1) == "child.md"
            row1 = item_rect(list_hwnd, 1)
            time.sleep(.1)
            assert ink_pixels(list_hwnd, 36, row1.top + 3, 56, row1.bottom - 3) > 4, \
                "document Fluent icon was not painted at depth 1"
            # Select the file and activate it; the shared Open transaction must
            # commit its path.
            u32.SendMessageW(list_hwnd, LB_SETCURSEL, 1, 0)
            u32.PostMessageW(app.main, WM_LIST_ACTIVATE, 0, 0)
            wait_for(lambda: app.read_path().lower().endswith("child.md"), 3,
                     "file activation did not commit current_path")
            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS tree UI: pure row names, segmented arrow/folder/document "
                  "glyphs, directory expand and file activation through the "
                  "shared Open transaction")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
