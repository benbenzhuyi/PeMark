#!/usr/bin/env python3
"""V8.6.1 slice 0 (part 1): the sidebar is two independent panels.

Evidence collected here:

* the file list and the outline list both exist and are visible, stacked
  vertically inside the sidebar (file panel above, outline panel below);
* each list owns its own content: workspace entries in the file panel, document
  headings in the outline panel, and neither leaks into the other;
* directory rows keep the directory/file colour distinction in both themes;
* the shared scrollbar geometry follows the outline panel height.
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
CMD_DUMP_ROW = 1905
CMD_DARK = 1311
CMD_LIGHT = 1310

LB_GETCOUNT = 0x018B
WM_SETREDRAW = 0x000B
SRCCOPY = 0x00CC0020
ROW_HEIGHT = 30

u32, k32, g32 = c.windll.user32, c.windll.kernel32, c.windll.gdi32
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.GetDC.argtypes = [w.HWND]
u32.GetDC.restype = w.HDC
u32.ReleaseDC.argtypes = [w.HWND, w.HDC]
u32.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u32.IsWindowVisible.argtypes = [w.HWND]
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


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.03)
    raise AssertionError(message)


def write_u32(app, symbol, value):
    data, count = c.c_uint32(value), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), c.byref(data), 4,
        c.byref(count))


def lb_count(app, hwnd):
    return u32.SendMessageW(hwnd, LB_GETCOUNT, 0, 0)


def lb_text(app, index, size=1024):
    """Ask the process to copy one file-panel row into its own probe buffer."""
    write_u32(app, "list_probe_result", 0xFFFFFFFF)
    write_u32(app, "list_probe_index", index)
    app.post_command(CMD_DUMP_ROW)
    wait_for(lambda: app.read32("list_probe_result") != 0xFFFFFFFF, 3,
             "row %d export" % index)
    assert app.read32("list_probe_result") >= 0
    raw, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms["list_probe_text"]), raw,
        size, c.byref(got)) and got.value == size
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def lb_rect(hwnd):
    rect = w.RECT()
    assert u32.GetWindowRect(hwnd, c.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def row_colours(hwnd, indices, width, height):
    """Dominant colour of the text pixels of each 30px row."""
    hdc = u32.GetDC(hwnd)
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
            assert histogram, "row %d has no text pixels" % index
            result[index] = max(histogram.items(), key=lambda kv: kv[1])[0]
        return result
    finally:
        g32.SelectObject(mem, old)
        g32.DeleteObject(bmp)
        g32.DeleteDC(mem)
        u32.ReleaseDC(hwnd, hdc)


def difference(first, second):
    return sum(abs(a - b) for a, b in zip(first, second))


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    app = App(ns, exe)
    try:
        wait_for(lambda: app.read64("hwnd_files") != 0, 5,
                 "the file panel ListBox must be created")
        files = app.read64("hwnd_files")
        outline = app.read64("hwnd_outline")
        assert files and outline and files != outline, "two distinct lists"
        assert u32.IsWindowVisible(files) and u32.IsWindowVisible(outline), \
            "both panels must be visible"

        # Vertical stacking inside the sidebar.
        left_f, top_f, width_f, height_f = lb_rect(files)
        left_o, top_o, width_o, height_o = lb_rect(outline)
        assert left_f == left_o and width_f == width_o, (lb_rect(files), lb_rect(outline))
        assert top_o >= top_f + height_f, "the outline panel must sit below the files panel"
        content_h = app.read32("content_h")
        assert height_f + height_o <= content_h + 1, (height_f, height_o, content_h)
        assert height_f > 0 and height_o > 0

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "ws"
            (workspace / "docs").mkdir(parents=True)
            (workspace / "a.md").write_text("x\n", encoding="utf-8")
            (workspace / "b.txt").write_text("x\n", encoding="utf-8")
            (workspace / "skip.bin").write_text("x\n", encoding="utf-8")
            document = Path(directory) / "doc.md"
            headings = ["# Alpha", "## Beta", "### Gamma"]
            document.write_text("intro\n\n" + "\n\n".join(headings) + "\n",
                                encoding="utf-8")

            # The file panel shows the workspace entries on its own list.
            write_wstr(app, "temp_path", str(workspace))
            app.post_command(CMD_WORKSPACE_PROBE)
            wait_for(lambda: app.read32("ws_entry_count") == 3, 4,
                     "workspace enumeration")
            wait_for(lambda: lb_count(app, files) == 3, 4,
                     "the file panel must list the workspace entries")
            assert [lb_text(app, i) for i in range(3)] == ["docs\\", "a.md", "b.txt"], \
                [lb_text(app, i) for i in range(3)]
            assert lb_count(app, outline) == 0, \
                "workspace entries must not leak into the outline panel"

            # The outline panel shows the document headings on its own list.
            write_wstr(app, "temp_path", str(document))
            app.post_command(CMD_OPEN_SELECTED)
            wait_for(lambda: lb_count(app, outline) == len(headings), 6,
                     "the outline panel must show the document headings")
            assert lb_count(app, files) == 3, \
                "opening a document must not disturb the file panel"

            # Row colours still separate directories from files, in both themes.
            app.post_command(CMD_DARK)
            time.sleep(.4)
            dark = row_colours(files, [0, 1], width_f, height_f)
            assert difference(dark[0], dark[1]) > 60, dark
            app.post_command(CMD_LIGHT)
            time.sleep(.4)
            light = row_colours(files, [0, 1], width_f, height_f)
            assert difference(light[0], light[1]) > 60, light
            assert difference(dark[0], light[0]) > 60, (dark, light)
            app.post_command(CMD_DARK)
            time.sleep(.4)

            # The scrollbar geometry follows the outline panel, not the whole sidebar.
            assert app.read32("outline_list_h") == height_o, \
                (app.read32("outline_list_h"), height_o)
            assert app.read32("files_list_h") == height_f, \
                (app.read32("files_list_h"), height_f)

        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS sidebar panels: file and outline lists stack vertically, each "
          "owns its content, file rows keep the directory/file colours in both "
          "themes, and the scrollbar geometry follows the panel height; released "
          "V8.5.4 binary unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
