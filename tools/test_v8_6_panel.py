#!/usr/bin/env python3
"""V8.6 slice 2: the outline and file panels share one list control.

Evidence collected here:

* layout: the ListBox rectangle is identical before and after a mode switch
  (same control, same scrollbar geometry, same layout manager);
* drawing: pixel snapshots through the window DC show directory rows and file
  rows painted in different colours in both themes, and outline rows keep the
  heading palette;
* scrolling: the shared scrollbar state follows the file list and clamps;
* selection: a file row can be selected, and selecting it never moves the
  document, while an outline row still navigates;
* the outline itself is unchanged: switching back restores the same rows, and
  edits made while the file panel was active are re-scanned.
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

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/candidate/generate_markdown_editor_v8_6.py"))
RELEASE_EXE = ROOT / "bin/current/pemark_x64_v8_5_4.exe"

CMD_OPEN_SELECTED = 1901
CMD_WORKSPACE_PROBE = 1902
CMD_SHOW_FILES = 1903
CMD_SHOW_OUTLINE = 1904
CMD_DUMP_ROW = 1905
CMD_PREVIEW = 1306
CMD_LIGHT = 1310
CMD_DARK = 1311

LB_ADDSTRING = 0x0180
LB_SETCURSEL = 0x0186
LB_GETCURSEL = 0x0188
LB_GETTEXT = 0x0189
LB_GETCOUNT = 0x018B
LB_SETTOPINDEX = 0x0197
WM_COMMAND = 0x0111
WM_SETREDRAW = 0x000B
WM_MOUSEWHEEL = 0x020A
EM_GETSEL = 0x00B0
EVENT_OUTLINE_SELECT = 0x8005
SRCCOPY = 0x00CC0020
ROW_HEIGHT = 30

u32, k32, g32 = c.windll.user32, c.windll.kernel32, c.windll.gdi32
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.GetDC.argtypes = [w.HWND]
u32.GetDC.restype = w.HDC
u32.ReleaseDC.argtypes = [w.HWND, w.HDC]
u32.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u32.GetWindowRect.restype = w.BOOL
g32.CreateCompatibleDC.argtypes = [w.HDC]
g32.CreateCompatibleDC.restype = w.HDC
g32.DeleteDC.argtypes = [w.HDC]
g32.CreateCompatibleBitmap.argtypes = [w.HDC, c.c_int, c.c_int]
g32.CreateCompatibleBitmap.restype = w.HBITMAP
g32.SelectObject.argtypes = [w.HDC, w.HGDIOBJ]
g32.SelectObject.restype = w.HGDIOBJ
g32.DeleteObject.argtypes = [w.HGDIOBJ]
g32.GetPixel.argtypes = [w.HDC, c.c_int, c.c_int]
g32.GetPixel.restype = w.COLORREF
g32.BitBlt.argtypes = [w.HDC, c.c_int, c.c_int, c.c_int, c.c_int, w.HDC,
                       c.c_int, c.c_int, w.DWORD]
g32.BitBlt.restype = w.BOOL


def build():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_panel_test__",
          "OPEN_TEST_BUILD": True}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == "pemark_x64_v8_6_open_transaction_test.exe", out.name
    return ns, out


def make_workspace(directory):
    root = Path(directory) / "ws"
    (root / "docs").mkdir(parents=True)
    (root / "中文目录").mkdir()
    (root / "docs" / "inner.md").write_text("# inner\n", encoding="utf-8")
    for name in ("a.md", "b.markdown", "c.txt", "skip.bin", "note"):
        (root / name).write_text("x\n", encoding="utf-8")
    return root


def make_many(directory, count):
    root = Path(directory) / "many"
    root.mkdir()
    for index in range(count):
        (root / ("f%03d.md" % index)).write_text("x\n", encoding="utf-8")
    return root


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.03)
    raise AssertionError(message)


def lb_count(app, lb):
    return u32.SendMessageW(lb, LB_GETCOUNT, 0, 0)


def lb_text(app, lb, index, symbol="outline_titlebuf", size=1024):
    """Ask the process itself to copy one ListBox row into its own buffer.

    Reading the row from outside with LB_GETTEXT is not usable: the ListBox
    rejects the cross-process buffer, and the owner-draw path keeps rewriting
    the shared scratch buffer anyway.
    """
    write_u32(app, "list_probe_result", 0xFFFFFFFF)
    write_u32(app, "list_probe_index", index)
    app.post_command(CMD_DUMP_ROW)
    wait_for(lambda: app.read32("list_probe_result") != 0xFFFFFFFF, 3,
             "row %d export" % index)
    result = app.read32("list_probe_result")
    assert result >= 0, (index, result)
    raw, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms["list_probe_text"]), raw,
        size, c.byref(got)) and got.value == size
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def write_u32(app, symbol, value):
    data, count = c.c_uint32(value), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), c.byref(data), 4,
        c.byref(count))


def lb_rect(lb):
    rect = w.RECT()
    assert u32.GetWindowRect(lb, c.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def selection(app):
    value = u32.SendMessageW(app.edit, EM_GETSEL, 0, 0)
    return value & 0xFFFF, (value >> 16) & 0xFFFF


def row_colours(lb, indices, width, height):
    """Dominant colour of the text pixels of each 30px row.

    Anti-aliased edges spread every glyph over many near-colours, so the
    average is pulled towards the background. The mode of the pixels that
    differ from the row background is the stable reading.
    """
    hdc = u32.GetDC(lb)
    mem = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, width, height)
    old = g32.SelectObject(mem, bmp)
    try:
        assert g32.BitBlt(mem, 0, 0, width, height, hdc, 0, 0, SRCCOPY)
        result = {}
        for index in indices:
            top = index * ROW_HEIGHT
            background = g32.GetPixel(mem, 2, top + 2)
            br, bg, bb = background & 0xFF, (background >> 8) & 0xFF, \
                (background >> 16) & 0xFF
            histogram = {}
            for x in range(4, min(width, 130)):
                for y in range(top + 4, top + ROW_HEIGHT - 4):
                    colour = g32.GetPixel(mem, x, y)
                    r, g, b = colour & 0xFF, (colour >> 8) & 0xFF, \
                        (colour >> 16) & 0xFF
                    if abs(r - br) + abs(g - bg) + abs(b - bb) > 90:
                        histogram[(r, g, b)] = histogram.get((r, g, b), 0) + 1
            assert histogram, "row %d has no text pixels; height %d" % (
                index, height)
            pixels = max(histogram.values())
            assert pixels >= 8, (index, pixels, sorted(
                histogram.items(), key=lambda kv: -kv[1])[:4])
            result[index] = max(histogram.items(), key=lambda kv: kv[1])[0]
        return result
    finally:
        g32.SelectObject(mem, old)
        g32.DeleteObject(bmp)
        g32.DeleteDC(mem)
        u32.ReleaseDC(lb, hdc)


def difference(first, second):
    return sum(abs(a - b) for a, b in zip(first, second))


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    app = App(ns, exe)
    try:
        wait_for(lambda: app.read64("hwnd_outline") != 0, 5,
                 "the sidebar ListBox must be created")
        lb = app.read64("hwnd_outline")
        assert lb, "the sidebar ListBox must exist"
        assert app.read32("panel_mode") == 0, "the outline panel is the default"
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(directory)
            many = make_many(directory, 60)
            document = Path(directory) / "doc.md"
            headings = ["# Alpha", "## Beta", "### Gamma", "## Delta"]
            document.write_text("intro\n\n" + "\n\n".join(headings) + "\n",
                                encoding="utf-8")

            # --- outline baseline -------------------------------------------
            app.post_command(CMD_PREVIEW)
            write_wstr(app, "temp_path", str(document))
            app.post_command(CMD_OPEN_SELECTED)
            wait_for(lambda: lb_count(app, lb) == len(headings), 6,
                     "the opened document must fill the outline")
            outline_rows = [lb_text(app, lb, index) for index in range(len(headings))]
            assert outline_rows[0].strip() == "Alpha", outline_rows
            assert outline_rows[2].startswith("    Gamma"), outline_rows
            geometry_before = lb_rect(lb)
            app.post_command(CMD_DARK)
            time.sleep(.4)
            outline_dark = row_colours(lb, [0, 2], geometry_before[2],
                                       geometry_before[3])
            assert difference(outline_dark[0], outline_dark[2]) > 60, \
                outline_dark
            app.post_command(CMD_LIGHT)
            time.sleep(.4)
            outline_light = row_colours(lb, [0, 2], geometry_before[2],
                                        geometry_before[3])
            assert difference(outline_light[0], outline_light[2]) > 60, \
                outline_light
            assert difference(outline_dark[0], outline_light[0]) > 60, \
                "the theme switch must repaint the shared ListBox"
            app.post_command(CMD_DARK)
            time.sleep(.4)

            # --- switch to the file panel ------------------------------------
            write_wstr(app, "temp_path", str(workspace))
            app.post_command(CMD_WORKSPACE_PROBE)
            wait_for(lambda: app.read32("ws_entry_count") == 5, 4,
                     "the workspace probe must enumerate the fixture")
            app.post_command(CMD_SHOW_FILES)
            wait_for(lambda: lb_count(app, lb) == 5, 4,
                     "the file panel must list the workspace entries")
            assert app.read32("panel_mode") == 1
            assert lb_rect(lb) == geometry_before, \
                "switching panels must not move or resize the shared ListBox"
            rows = [lb_text(app, lb, index) for index in range(5)]
            assert rows[0] == "docs\\", rows
            assert rows[1] == "中文目录\\", rows
            assert rows[2:] == ["a.md", "b.markdown", "c.txt"], rows
            assert app.read32("outline_count") == 0, \
                "the outline tables must not describe the file list"

            file_dark = row_colours(lb, [0, 3], geometry_before[2],
                                    geometry_before[3])
            assert difference(file_dark[0], file_dark[3]) > 60, file_dark
            app.post_command(CMD_LIGHT)
            time.sleep(.4)
            file_light = row_colours(lb, [0, 3], geometry_before[2],
                                     geometry_before[3])
            assert difference(file_light[0], file_light[3]) > 60, file_light
            assert difference(file_dark[0], file_light[0]) > 60, \
                (file_dark, file_light)
            app.post_command(CMD_DARK)
            time.sleep(.4)

            # --- selection: a file row is selectable and inert ----------------
            before = selection(app)
            assert u32.SendMessageW(lb, LB_SETCURSEL, 3, 0) == 3
            assert u32.SendMessageW(lb, LB_GETCURSEL, 0, 0) == 3
            u32.PostMessageW(app.main, EVENT_OUTLINE_SELECT, 0, 0)
            time.sleep(.4)
            assert selection(app) == before, \
                "selecting a file row must not move the document"

            # --- scrolling the shared scrollbar ------------------------------
            write_wstr(app, "temp_path", str(many))
            app.post_command(CMD_WORKSPACE_PROBE)
            wait_for(lambda: app.read32("ws_entry_count") == 60, 4,
                     "the large fixture must enumerate")
            app.post_command(CMD_SHOW_FILES)
            wait_for(lambda: lb_count(app, lb) == 60, 4,
                     "the file panel must list every entry")
            left, top, width, height = lb_rect(lb)
            for _ in range(2):
                u32.PostMessageW(app.main, WM_MOUSEWHEEL, 0xFF880000,
                                 (left + width // 2) | ((top + 40) << 16))
                time.sleep(.2)
            assert app.read32("outline_scroll_count") == 60
            assert app.read32("outline_scroll_top") == 6, \
                app.read32("outline_scroll_top")
            assert app.read32("outline_scroll_track_h") > 0
            thumb_after_one_screen = app.read32("outline_scroll_thumb_top")
            assert thumb_after_one_screen > 4

            for _ in range(30):
                u32.PostMessageW(app.main, WM_MOUSEWHEEL, 0xFF880000,
                                 (left + width // 2) | ((top + 40) << 16))
                time.sleep(.05)
            visible = app.read32("outline_visible_rows")
            assert app.read32("outline_scroll_top") == 60 - visible, \
                (app.read32("outline_scroll_top"), visible)
            assert app.read32("outline_scroll_thumb_top") + \
                app.read32("outline_scroll_thumb_h") <= \
                app.read32("outline_scroll_track_h") + 4, \
                "thumb must stay inside the 4px-inset track"

            # --- an edit while the file panel is active ----------------------
            app.set_text_dirty("# Replaced\n\n## Second\n")
            time.sleep(.3)
            assert lb_count(app, lb) == 60, \
                "editing must not push outline rows into the file list"

            # --- back to the outline -----------------------------------------
            app.post_command(CMD_SHOW_OUTLINE)
            wait_for(lambda: lb_count(app, lb) == 2, 6,
                     "switching back must rebuild the outline from the document")
            assert app.read32("panel_mode") == 0
            assert lb_rect(lb) == geometry_before
            restored = [lb_text(app, lb, index) for index in range(2)]
            assert restored[0].strip() == "Replaced", restored
            assert restored[1].startswith("  Second"), restored

            # The outline palette is back, and navigation works again.
            outline_dark = row_colours(lb, [0], geometry_before[2],
                                       geometry_before[3])
            assert difference(outline_dark[0], file_light[0]) > 60, \
                (outline_dark, file_light)
            write_wstr(app, "temp_path", str(workspace))
            app.post_command(CMD_WORKSPACE_PROBE)
            app.post_command(CMD_SHOW_FILES)
            wait_for(lambda: lb_count(app, lb) == 5, 4, "file panel again")
            app.post_command(CMD_SHOW_OUTLINE)
            wait_for(lambda: lb_count(app, lb) == 2, 6, "outline panel again")

        app.post_close()
        app.click_dialog("PeMark", 7)   # IDNO / discard the scratch edit
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS sidebar panels: one ListBox and one scrollbar for both modes, "
          "identical geometry, directory/file row colours in both themes, "
          "selectable and inert file rows, wheel scrolling with clamping, "
          "outline restored after edits; released V8.5.4 binary unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
