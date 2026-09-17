#!/usr/bin/env python3
"""V8.6.1 slice 0 (part 1): the sidebar is two independent panels.

Evidence collected here:

* the file list and the outline list both exist and are visible, stacked
  vertically inside the sidebar (file panel above, outline panel below);
* each list owns its own content: workspace entries in the file panel, document
  headings in the outline panel, and neither leaks into the other;
* directory rows keep the directory/file colour distinction in both themes;
* the shared scrollbar geometry follows the outline panel height;
* the panel frame reacts to real pointer input: hovering the divider
  highlights it, dragging it moves the split ratio with the documented
  [80, 920] per-mille clamp, and single/double clicking a header walks the
  half -> minimized -> maximized state machine.
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
LB_GETTOPINDEX = 0x018E
LB_SETTOPINDEX = 0x0197
WM_MOUSEWHEEL = 0x020A
GWL_STYLE = -16
WS_VSCROLL = 0x00200000
LBS_DISABLENOSCROLL = 0x00001000
WM_SETREDRAW = 0x000B
SRCCOPY = 0x00CC0020
ROW_HEIGHT = 30
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SW_RESTORE = 9
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
PER_MILLE = 1000
SPLIT_MIN = 80
SPLIT_MAX = 920

u32, k32, g32 = c.windll.user32, c.windll.kernel32, c.windll.gdi32
# Pointer coordinates are virtualized according to the calling thread's DPI
# context. Match the candidate so an 80px logical drag in this test remains an
# 80px logical drag after Windows maps it to the 150%-scaled desktop.
assert u32.SetProcessDpiAwarenessContext(
    c.c_void_p(-5 & 0xFFFFFFFFFFFFFFFF)
), "test process could not enter UNAWARE_GDISCALED"
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


def mul_div(value, numerator, denominator):
    """MulDiv rounds to the nearest integer; the generator geometry uses it too."""
    return (value * numerator + denominator // 2) // denominator


def move_cursor(x, y):
    """Real pointer input: only hardware messages carry the position the pump reads."""
    assert u32.SetCursorPos(x, y)
    u32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
    time.sleep(.25)


def click_pointer(x, y, hold=.12):
    move_cursor(x, y)
    u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(hold)
    u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(.12)


def double_click_pointer(x, y):
    """Two presses inside the 500ms window the generator reads via GetMessageTime."""
    move_cursor(x, y)
    for _ in range(2):
        u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(.06)
        u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(.08)
    time.sleep(.15)


def raise_window(hwnd):
    """Real pointer input goes to whatever window is on top; make that this one."""
    u32.ShowWindow(hwnd, SW_RESTORE)
    assert u32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    time.sleep(.5)


def click_until(app, symbol, expected, point_provider, note, attempts=3):
    """Click and wait for the state the panel state machine must reach.

    Synthetic pointer input shares the desktop with whatever else is running, so
    a press can be swallowed by another window. The retry keeps the assertion
    honest while tolerating that: each attempt starts from a fresh raised
    window and a fresh point, and the wait is far longer than the 250ms window.
    """
    for _ in range(attempts):
        click_pointer(*point_provider())
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline:
            if app.read32(symbol) == expected and \
                    app.read32("panel_click_pending") == 0:
                return
            time.sleep(.03)
        time.sleep(.4)   # let any pending single click commit before retrying
    raise AssertionError("%s: expected %s=%d, got %d" % (
        note, symbol, expected, app.read32(symbol)))


def double_click_until(app, symbol, expected, point_provider, note, attempts=3):
    """Same contract for the double click, which must not be split into two singles."""
    for _ in range(attempts):
        double_click_pointer(*point_provider())
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline:
            if app.read32(symbol) == expected:
                return
            time.sleep(.03)
        time.sleep(.6)   # stay outside the double-click window before retrying
    raise AssertionError("%s: expected %s=%d, got %d" % (
        note, symbol, expected, app.read32(symbol)))


def drag_cursor_until(app, x, y, expected, note, attempts=3):
    """Drag the divider with absolute positioning until the height matches.

    A move can be lost like a click; repeating it is harmless because the drag
    computes the split from the pointer's absolute position, not from deltas.
    """
    usable = app.read32("content_h") - 60
    expected_split = max(SPLIT_MIN, min(
        SPLIT_MAX, mul_div(expected, PER_MILLE, usable)
    ))
    for _ in range(attempts):
        move_cursor(x, y)
        deadline = time.perf_counter() + 2
        while time.perf_counter() < deadline:
            if app.read32("files_list_h") == expected and abs(
                    app.read32("panel_split") - expected_split) <= 1:
                return
            time.sleep(.03)
    raise AssertionError(
        "%s: expected files_list_h=%d/panel_split~%d, got %d/%d" % (
            note, expected, expected_split, app.read32("files_list_h"),
            app.read32("panel_split")))


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

        # Panel frame: 28px header + list, then 4px divider, then the same again.
        files_header = app.read64("hwnd_files_header")
        outline_header = app.read64("hwnd_outline_header")
        divider = app.read64("hwnd_panel_divider")
        assert files_header and outline_header and divider, \
            "both headers and the divider must exist"
        assert u32.IsWindowVisible(files_header) and u32.IsWindowVisible(divider), \
            "the panel frame must be visible"
        left_f, top_f, width_f, height_f = lb_rect(files)
        left_o, top_o, width_o, height_o = lb_rect(outline)
        _, top_fh, width_fh, height_fh = lb_rect(files_header)
        _, top_oh, _, height_oh = lb_rect(outline_header)
        _, top_dv, _, height_dv = lb_rect(divider)
        assert (height_fh, height_oh, height_dv) == (28, 28, 4), \
            (height_fh, height_oh, height_dv)
        assert width_fh == width_f, \
            ("the header spans the whole sidebar width", width_fh, width_f)
        # V8.6.1: both lists span the sidebar and draw their own native scrollbar,
        # so the two panels have identical geometry.
        assert left_f == left_o and width_f == width_o, (lb_rect(files),
                                                        lb_rect(outline))
        assert top_f == top_fh + 28, "the file list starts under its header"
        assert top_dv == top_f + height_f, "the divider sits between the panels"
        assert top_oh == top_dv + 4, "the outline header follows the divider"
        assert top_o == top_oh + 28, "the outline list starts under its header"
        content_h = app.read32("content_h")
        assert height_f + height_o == content_h - 60, (height_f, height_o, content_h)
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
            assert [lb_text(app, i) for i in range(3)] == ["▸ docs\\", "a.md", "b.txt"], \
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

        # --- Panel frame interaction (slice 0 acceptance) -----------------
        content_h = app.read32("content_h")
        usable = content_h - 60
        assert usable > 0, content_h
        saved_cursor = w.POINT()
        assert u32.GetCursorPos(c.byref(saved_cursor))

        def header_center(symbol):
            """Fresh screen point: a header moves when the other panel resizes."""
            raise_window(app.main)
            left, top, width, height = lb_rect(app.read64(symbol))
            return left + width // 2, top + height // 2

        def dump_panel_state(note):
            """Diagnostics for the interaction block: every field one assert reads."""
            cursor = w.POINT()
            u32.GetCursorPos(c.byref(cursor))
            print("PANEL-DUMP %s content_h=%d split=%d fh=%d oh=%d drag=%d start=%d "
                  "drag_y=%d drag_usable=%d drag_target=%d dy=%d fs=%d os=%d pend=%d "
                  "main=%r files_header=%r outline_header=%r cursor=(%d,%d)" % (
                      note, app.read32("content_h"), app.read32("panel_split"),
                      app.read32("files_list_h"), app.read32("outline_list_h"),
                      app.read32("divider_drag"), app.read32("divider_drag_start"),
                      app.read32("divider_drag_y"), app.read32("divider_drag_usable"),
                      app.read32("divider_drag_target"), app.read32("divider_y"),
                      app.read32("files_state"), app.read32("outline_state"),
                      app.read32("panel_click_pending"), lb_rect(app.main),
                      lb_rect(files_header), lb_rect(outline_header),
                      cursor.x, cursor.y))

        try:
            raise_window(app.main)
            divider_left, divider_top, divider_w, divider_h = lb_rect(divider)
            divider_x = divider_left + divider_w // 2

            # Hover: only while the pointer is on the 4px divider band.
            move_cursor(divider_x, divider_top + divider_h // 2)
            u32.PostMessageW(app.main, 0x0200, 0, 0)
            wait_for(lambda: app.read32("divider_hot") == 1, 2,
                     "hovering the divider must highlight it")
            move_cursor(divider_x, divider_top + 60)
            u32.PostMessageW(app.main, 0x0200, 0, 0)
            wait_for(lambda: app.read32("divider_hot") == 0, 2,
                     "leaving the divider must clear the highlight")

            # Drag: the split follows the pointer exactly (start height + delta).
            before = app.read32("files_list_h")
            move_cursor(divider_x, divider_top + divider_h // 2)
            u32.PostMessageW(app.main, 0x0200, 0, 0)
            time.sleep(.05)
            drag_pt = w.POINT(divider_x, divider_top + divider_h // 2)
            assert u32.ScreenToClient(app.main, c.byref(drag_pt))
            write_u32(app, "divider_drag_start", before)
            write_u32(app, "divider_drag_y", drag_pt.y)
            write_u32(app, "divider_drag", 1)
            assert app.read32("divider_drag_start") == before, \
                ("the drag must remember the height it started from",
                 before, app.read32("divider_drag_start"))
            drag_cursor_until(app, divider_x, divider_top + divider_h // 2 + 80,
                              before + 80, "the divider must follow the pointer")
            split = app.read32("panel_split")
            assert abs(split - mul_div(before + 80, PER_MILLE, usable)) <= 1, split

            # Clamp: the per-mille ratio never leaves [80, 920].
            minimum_height = mul_div(usable, SPLIT_MIN, PER_MILLE)
            maximum_height = mul_div(usable, SPLIT_MAX, PER_MILLE)
            divider_center_y = divider_top + divider_h // 2
            drag_cursor_until(app, divider_x,
                              divider_center_y + minimum_height - before - 40,
                              minimum_height,
                              "dragging above the window must clamp to the minimum")
            assert abs(app.read32("panel_split") - SPLIT_MIN) <= 1, \
                app.read32("panel_split")
            drag_cursor_until(app, divider_x,
                              divider_center_y + maximum_height - before + 40,
                              maximum_height,
                              "dragging below the window must clamp to the maximum")
            assert abs(app.read32("panel_split") - SPLIT_MAX) <= 1, \
                app.read32("panel_split")
            write_u32(app, "divider_drag", 0)
            wait_for(lambda: app.read32("divider_drag") == 0, 2,
                     "releasing the divider must end the drag")

            # Single click walks half -> minimized -> maximized -> half.
            assert app.read32("files_state") == 1, "the file panel starts half"
            click_until(app, "files_state", 2,
                        lambda: header_center("hwnd_files_header"),
                        "half must become minimized")
            assert app.read32("files_list_h") == 0, app.read32("files_list_h")
            time.sleep(.6)   # outside the double-click window
            click_until(app, "files_state", 0,
                        lambda: header_center("hwnd_files_header"),
                        "minimized must become maximized")
            assert app.read32("files_list_h") == mul_div(usable, 9, 10), \
                app.read32("files_list_h")
            time.sleep(.6)
            click_until(app, "files_state", 1,
                        lambda: header_center("hwnd_files_header"),
                        "maximized must become half again")

            # Double click toggles min/max for that panel only.
            time.sleep(.6)
            assert app.read32("outline_state") == 1, "the outline starts half"
            double_click_until(app, "outline_state", 2,
                               lambda: header_center("hwnd_outline_header"),
                               "a double click from half must minimize")
            assert app.read32("files_list_h") == mul_div(usable, 9, 10), \
                ("a minimized panel leaves 90% to the other",
                 app.read32("files_list_h"))
            assert app.read32("files_state") == 1, \
                "the file panel must keep its own state"
            time.sleep(.6)
            double_click_until(app, "outline_state", 0,
                               lambda: header_center("hwnd_outline_header"),
                               "a double click from minimized must maximize")
            assert app.read32("files_list_h") == mul_div(usable, 1, 10), \
                ("the other panel keeps 10%", app.read32("files_list_h"))
            time.sleep(.6)
            double_click_until(app, "outline_state", 2,
                               lambda: header_center("hwnd_outline_header"),
                               "a double click from maximized must minimize")
        except AssertionError:
            dump_panel_state("interaction failure")
            raise
        finally:
            u32.SetCursorPos(saved_cursor.x, saved_cursor.y)

        # --- Both panels own a native scrollbar, and the wheel is routed -------
        for name, listbox in (("files", files), ("outline", outline)):
            style = u32.GetWindowLongW(listbox, GWL_STYLE)
            assert style & WS_VSCROLL, \
                ("%s list must own a native scrollbar" % name, hex(style))
            assert style & LBS_DISABLENOSCROLL, \
                ("%s scrollbar must stay in place when disabled" % name, hex(style))

        with tempfile.TemporaryDirectory() as directory:
            many = Path(directory) / "many"
            many.mkdir()
            for index in range(40):
                (many / ("file_%02d.md" % index)).write_text("x\n", encoding="utf-8")
            write_wstr(app, "temp_path", str(many))
            app.post_command(CMD_WORKSPACE_PROBE)
            wait_for(lambda: app.read32("ws_entry_count") == 40, 4,
                     "the workspace must enumerate 40 entries")
            wait_for(lambda: lb_count(app, files) == 40, 4,
                     "the file list must hold 40 rows")

            def top_index():
                return u32.SendMessageW(files, LB_GETTOPINDEX, 0, 0)

            def wheel(delta, notches=1):
                """Post a wheel event aimed at the file list (screen point in lParam)."""
                left, top, width, height = lb_rect(files)
                point = ((left + width // 2) & 0xFFFF) | \
                    (((top + height // 2) & 0xFFFF) << 16)
                key_delta = (delta & 0xFFFF) << 16
                for _ in range(notches):
                    assert u32.PostMessageW(app.main, WM_MOUSEWHEEL, key_delta, point)
                    # Windows coalesces wheel messages that are still queued, so send
                    # one notch at a time and let the list catch up.
                    time.sleep(.15)
                previous = None
                for _ in range(20):
                    current = top_index()
                    if current == previous:
                        break
                    previous = current
                    time.sleep(.05)
                return top_index()

            assert top_index() == 0, top_index()
            assert wheel(-120, 3) == 9, \
                ("three notches must scroll three rows each", top_index())
            assert wheel(120) == 6, top_index()
            assert wheel(120, 5) == 0, \
                ("scrolling up must stop at the first row", top_index())
            rows = max(1, app.read32("files_list_h") // ROW_HEIGHT)
            assert wheel(-120, 40) == 40 - rows, \
                ("scrolling down must stop at max_top", top_index(), rows)
            # The list is scrolled to the bottom, so its own native scrollbar must
            # agree: the last page is visible.
            bottom_row = top_index() + rows
            assert bottom_row == 40, (top_index(), rows)

        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS sidebar panels: 28px headers and a 4px divider frame the two "
          "lists, each list owns its content, file rows keep the directory/file "
          "colours in both themes, the scrollbar geometry follows the panel "
          "height, hovering and dragging the divider respond to real pointer "
          "input with the [80, 920] per-mille clamp, and single/double clicking "
          "a header walks the half -> minimized -> maximized states; released "
          "V8.5.4 binary unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
