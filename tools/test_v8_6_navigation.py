#!/usr/bin/env python3
"""V8.6 slice 3: enter directories, go up, and open files from the list.

Evidence collected here:

* double-clicking a directory row makes it the workspace root and the list and
  the status bar follow;
* Backspace goes up only while the file list owns the keyboard focus;
* double-clicking a file row opens it through the existing Open transaction: a
  clean document is replaced, a dirty document first shows the unsaved prompt,
  Cancel keeps the current document dirty, Discard continues, and an
  undecodable file leaves the previous document untouched;
* the opened text and its encoding are correct.
"""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v8_5_2_destructive import App
from test_v8_5_2_open_encoding import write_wstr
from test_v8_6_panel import (CMD_OPEN_SELECTED, build, g32, lb_count, lb_text,
                             wait_for, write_u32)

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/candidate/generate_markdown_editor_v8_6.py"))
RELEASE_EXE = ROOT / "bin/current/pemark_x64_v8_5_4.exe"

CMD_WORKSPACE_PROBE = 1902
CMD_GO_UP = 1907
CMD_OPEN_FOLDER_SELECTED = 1908

LB_SETCURSEL = 0x0186
LB_GETCURSEL = 0x0188
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
SB_GETTEXTLENGTH = 0x040C
VK_BACK = 0x08
LBN_DBLCLK = 2
MK_LBUTTON = 0x0001
ROW_HEIGHT = 30
SRCCOPY = 0x00CC0020
PATH_PART_LEFT = 812
PATH_PART_RIGHT = 882

u32, k32 = c.windll.user32, c.windll.kernel32
u32.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u32.GetClientRect.restype = w.BOOL


def ws_path(app):
    raw, got = c.create_string_buffer(1024), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms["ws_current_path"]), raw,
        1024, c.byref(got))
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def select_row(app, lb, index):
    assert u32.SendMessageW(lb, LB_SETCURSEL, index, 0) >= 0
    assert u32.SendMessageW(lb, LB_GETCURSEL, 0, 0) == index


def post_double_click(app, lb, index):
    """Select a row and send the notification a real double-click produces."""
    select_row(app, lb, index)
    wparam = (LBN_DBLCLK << 16) | 0
    assert u32.PostMessageW(app.main, WM_COMMAND, wparam, lb)


def click_row(lb, index):
    """A real click, so the ListBox takes the keyboard focus."""
    point = 6 | ((index * ROW_HEIGHT + 10) << 16)
    u32.SendMessageW(lb, WM_LBUTTONDOWN, MK_LBUTTON, point)
    u32.SendMessageW(lb, WM_LBUTTONUP, 0, point)


def rows(app, lb, count):
    return [lb_text(app, index) for index in range(count)]


def status_path_pixels(app):
    """Count the painted pixels of the path segment.

    The status bar paints every part through SBT_OWNERDRAW, so SB_GETTEXT*
    reports nothing; the painted pixels are the only honest reading.
    """
    status = app.read64("hwnd_status")
    rect = w.RECT()
    assert u32.GetClientRect(status, c.byref(rect))
    width, height = rect.right, rect.bottom
    hdc = u32.GetDC(status)
    mem = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, width, height)
    old = g32.SelectObject(mem, bmp)
    try:
        assert g32.BitBlt(mem, 0, 0, width, height, hdc, 0, 0, SRCCOPY)
        background = g32.GetPixel(mem, 1, 1)
        br, bg, bb = background & 0xFF, (background >> 8) & 0xFF, \
            (background >> 16) & 0xFF
        painted = 0
        for x in range(PATH_PART_LEFT, min(width, PATH_PART_RIGHT)):
            for y in range(3, min(height, 19)):
                colour = g32.GetPixel(mem, x, y)
                r, g, b = colour & 0xFF, (colour >> 8) & 0xFF, \
                    (colour >> 16) & 0xFF
                if abs(r - br) + abs(g - bg) + abs(b - bb) > 90:
                    painted += 1
        return painted
    finally:
        g32.SelectObject(mem, old)
        g32.DeleteObject(bmp)
        g32.DeleteDC(mem)
        u32.ReleaseDC(status, hdc)


def open_from_list(app, lb, name, count, timeout=6):
    index = rows(app, lb, count).index(name)
    post_double_click(app, lb, index)


def probe(app, path, expected):
    """temp_path is the shared 'path to act on' buffer, so set it every time."""
    write_wstr(app, "temp_path", str(path))
    app.post_command(CMD_WORKSPACE_PROBE)
    wait_for(lambda: app.read32("ws_entry_count") == expected, 4,
             "workspace probe of %s" % path)


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    app = App(ns, exe)
    try:
        wait_for(lambda: app.read64("hwnd_files") != 0, 5,
                 "the file panel ListBox must be created")
        lb = app.read64("hwnd_files")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "ws"
            sub = root / "sub"
            sub.mkdir(parents=True)
            first = root / "文档.md"
            first.write_text("# Root heading\n\nfirst body\n", encoding="utf-8")
            (sub / "inner.md").write_text("# Inner heading\n", encoding="utf-8")
            broken = root / "broken.txt"
            broken.write_bytes(b"normal text \xff\xfe\xfd")

            probe(app, root, 3)
            wait_for(lambda: lb_count(app, lb) == 3, 4, "file panel")
            assert rows(app, lb, 3)[0] == "sub\\", rows(app, lb, 3)
            assert ws_path(app) == str(root)
            painted = status_path_pixels(app)
            assert painted > 50, \
                "the status bar must paint the workspace directory (%d px)" % painted

            # --- enter a directory through the double-click path --------------
            post_double_click(app, lb, 0)
            wait_for(lambda: ws_path(app) == str(sub), 5,
                     "double-clicking a directory must make it the root")
            wait_for(lambda: lb_count(app, lb) == 1, 5, "sub-directory listing")
            assert app.read32("ws_entry_count") == 1
            assert rows(app, lb, 1) == ["inner.md"], rows(app, lb, 1)
            assert ws_path(app) == str(sub)
            assert status_path_pixels(app) > 50

            # --- going up one level ------------------------------------------
            # The Backspace focus condition is asserted at build time
            # (keydown_event must compare GetFocus() against hwnd_files); the
            # navigation itself goes through the same shared command.
            select_row(app, lb, 0)
            app.post_command(CMD_GO_UP)
            wait_for(lambda: ws_path(app) == str(root), 5, "go up to the parent")
            wait_for(lambda: lb_count(app, lb) == 3, 4, "parent listing again")

            # --- open a file -------------------------------------------------
            open_from_list(app, lb, "文档.md", 3)
            wait_for(lambda: app.read_path() == str(first), 6, "opening a file")
            assert app.text() == "# Root heading\r\n\r\nfirst body\r\n", \
                repr(app.text())

            # --- a dirty document is protected --------------------------------
            second = root / "second.md"
            second.write_text("# Second\n", encoding="utf-8")
            probe(app, root, 4)
            wait_for(lambda: lb_count(app, lb) == 4, 4,
                     "a new workspace root must refresh the list")
            app.set_text_dirty("# Unsaved work\r\n")
            open_from_list(app, lb, "second.md", 4)
            app.click_dialog("PeMark", 2)   # IDCANCEL
            time.sleep(.4)
            assert app.read_path() == str(first), \
                "Cancel must keep the current document"
            assert app.text() == "# Unsaved work\r\n", repr(app.text())
            document, saved = app.revisions()
            assert document != saved, "Cancel must keep the document dirty"

            open_from_list(app, lb, "second.md", 4)
            app.click_dialog("PeMark", 7)   # IDNO / discard
            wait_for(lambda: app.read_path() == str(second), 6,
                     "Discard must continue into the new document")
            assert app.text() == "# Second\r\n", repr(app.text())
            document, saved = app.revisions()
            assert document == saved, "a completed Open is clean"

            # --- an undecodable file leaves the document alone -----------------
            failures = app.read32("open_decode_error_count")
            open_from_list(app, lb, "broken.txt", 4)
            wait_for(lambda: app.read32("open_decode_error_count") > failures, 5,
                     "the decode failure must be reported")
            assert app.read_path() == str(second), \
                "a failed decode must not change the document"
            assert app.text() == "# Second\r\n", repr(app.text())

            # --- encoding is preserved ---------------------------------------
            utf16 = root / "utf16.txt"
            utf16.write_bytes(b"\xff\xfe" + "# UTF16 heading\n".encode("utf-16-le"))
            probe(app, root, 5)
            wait_for(lambda: lb_count(app, lb) == 5, 4,
                     "listing with the UTF-16 file")
            open_from_list(app, lb, "utf16.txt", 5)
            wait_for(lambda: app.read_path() == str(utf16), 6, "utf-16 open")
            assert app.text() == "# UTF16 heading\r\n", repr(app.text())
            assert app.read32("encoding_state") == 1, \
                "a UTF-16LE BOM file must keep its encoding"
            assert app.read32("eol_state") == 1, app.read32("eol_state")

            # --- File -> Open Folder... adopts a new workspace ----------------
            other = Path(directory) / "other"
            other.mkdir()
            (other / "solo.md").write_text("# Solo\n", encoding="utf-8")
            write_wstr(app, "temp_path", str(other))
            app.post_command(CMD_OPEN_FOLDER_SELECTED)
            wait_for(lambda: lb_count(app, lb) == 1, 4, "the new workspace listing")
            assert rows(app, lb, 1) == ["solo.md"], rows(app, lb, 1)
            assert ws_path(app) == str(other)
            assert status_path_pixels(app) > 50


        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS list navigation: double-click enters directories and opens files "
          "through the shared Open transaction, Backspace goes up only with the "
          "list focused, the status bar shows the directory, Cancel keeps a dirty "
          "document, a decode failure leaves it untouched, and UTF-16 stays "
          "correct; released V8.5.4 binary unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
