#!/usr/bin/env python3
"""V8.6.1 fixes that came out of real testing: theme repaint and the folder picker.

Evidence collected here:

* switching the theme repaints the sidebar frame immediately - the two 28px
  headers and the 4px divider all match the new palette without hiding and
  reopening the sidebar (issue 1); the two lists keep the panel background and
  own native scrollbars that follow the theme (issues 2 and 3);
* the folder picker is the modern common item dialog, not the legacy
  SHBrowseForFolder tree (issue 4): the dialog that opens carries the DirectUI
  shell view, and CoCreateInstance(FileOpenDialog) succeeds in-process;
* cancelling the picker leaves the workspace root untouched and the app alive.
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

CMD_DARK = 1311
CMD_LIGHT = 1310
CMD_OPEN_SELECTED = 1901
CMD_WORKSPACE_PROBE = 1902
CMD_OPEN_FOLDER = 1006
CMD_FOLDER_COM_PROBE = 1909
CMD_TOGGLE_SIDEBAR = 1307
WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100


class BITMAPINFOHEADER(c.Structure):
    _fields_ = [("biSize", c.c_uint32), ("biWidth", c.c_int32),
                ("biHeight", c.c_int32), ("biPlanes", c.c_uint16),
                ("biBitCount", c.c_uint16), ("biCompression", c.c_uint32),
                ("biSizeImage", c.c_uint32), ("biX", c.c_int32),
                ("biY", c.c_int32), ("biClrUsed", c.c_uint32),
                ("biClrImportant", c.c_uint32)]

# Palette documented in the generator's apply_theme.
DARK_HEADER, DARK_DIVIDER, DARK_PANEL = 0x00202020, 0x001D1D1D, 0x001F1F1F
LIGHT_HEADER, LIGHT_DIVIDER, LIGHT_PANEL = 0x00F5F5F5, 0x00E8EAED, 0x00F3F3F3

u32, k32, g32 = c.windll.user32, c.windll.kernel32, c.windll.gdi32
u32.GetWindowDC.argtypes = [w.HWND]
u32.GetWindowDC.restype = w.HDC
u32.GetDC.argtypes = [w.HWND]
u32.GetDC.restype = w.HDC
u32.ReleaseDC.argtypes = [w.HWND, w.HDC]
u32.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
g32.GetPixel.argtypes = [w.HDC, c.c_int, c.c_int]
g32.GetPixel.restype = w.COLORREF
u32.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
g32.CreateCompatibleDC.argtypes = [w.HDC]
g32.CreateCompatibleDC.restype = w.HDC
g32.CreateCompatibleBitmap.argtypes = [w.HDC, c.c_int, c.c_int]
g32.CreateCompatibleBitmap.restype = w.HBITMAP
g32.SelectObject.argtypes = [w.HDC, w.HGDIOBJ]
g32.SelectObject.restype = w.HGDIOBJ
g32.DeleteObject.argtypes = [w.HGDIOBJ]
g32.DeleteDC.argtypes = [w.HDC]
g32.BitBlt.argtypes = [w.HDC, c.c_int, c.c_int, c.c_int, c.c_int, w.HDC,
                       c.c_int, c.c_int, w.DWORD]
g32.GetDIBits.argtypes = [w.HDC, w.HBITMAP, c.c_uint, c.c_uint, c.c_void_p,
                          c.c_void_p, c.c_uint]


def build():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_theme_picker_test__",
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


def pixel(hwnd, x, y):
    hdc = u32.GetDC(hwnd)
    try:
        return g32.GetPixel(hdc, x, y)
    finally:
        u32.ReleaseDC(hwnd, hdc)


def frame_pixel(hwnd):
    """Far-right pixel of the window frame: where a native scrollbar is drawn."""
    rect = w.RECT()
    assert u32.GetWindowRect(hwnd, c.byref(rect))
    hdc = u32.GetWindowDC(hwnd)
    try:
        return g32.GetPixel(hdc, rect.right - rect.left - 8,
                            (rect.bottom - rect.top) // 2)
    finally:
        u32.ReleaseDC(hwnd, hdc)


def brightness(colour):
    return ((colour & 0xFF) + ((colour >> 8) & 0xFF) + ((colour >> 16) & 0xFF)) / 3





def surface_bytes(hwnd):
    """Full client-area bitmap of a window, as raw BGRA bytes."""
    rect = w.RECT()
    assert u32.GetClientRect(hwnd, c.byref(rect))
    width, height = rect.right, rect.bottom
    hdc = u32.GetDC(hwnd)
    mem = g32.CreateCompatibleDC(hdc)
    bitmap = g32.CreateCompatibleBitmap(hdc, width, height)
    old = g32.SelectObject(mem, bitmap)
    try:
        assert g32.BitBlt(mem, 0, 0, width, height, hdc, 0, 0, 0x00CC0020)
        buffer = c.create_string_buffer(width * height * 4)
        info = BITMAPINFOHEADER()
        info.biSize = 40
        info.biWidth = width
        info.biHeight = -height
        info.biPlanes = 1
        info.biBitCount = 32
        g32.GetDIBits(mem, bitmap, 0, height, buffer, c.byref(info), 0)
        return buffer.raw
    finally:
        g32.SelectObject(mem, old)
        g32.DeleteObject(bitmap)
        g32.DeleteDC(mem)
        u32.ReleaseDC(hwnd, hdc)


def read_wstr(app, symbol, size=1024):
    raw, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), raw, size,
        c.byref(got))
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def top_level_windows(pid):
    found = []

    @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def callback(hwnd, _):
        owner = w.DWORD()
        u32.GetWindowThreadProcessId(hwnd, c.byref(owner))
        if owner.value == pid and u32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    u32.EnumWindows(callback, 0)
    return found


def class_names(hwnd):
    names = []

    @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def callback(hwnd_child, _):
        buffer = c.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd_child, buffer, 256)
        names.append(buffer.value)
        return True

    u32.EnumChildWindows(hwnd, callback, 0)
    return names


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    app = App(ns, exe)
    try:
        wait_for(lambda: app.read64("hwnd_panel_divider") != 0, 5,
                 "the panel frame must be created")
        headers = (app.read64("hwnd_files_header"), app.read64("hwnd_outline_header"))
        divider = app.read64("hwnd_panel_divider")
        assert all((headers[0], headers[1], divider)), "frame windows"

        # Issue 1 + 3: every theme switch repaints the frame with the new palette.
        # Both panels must be scrollable, otherwise their thin scrollbars are
        # hidden and there is nothing to compare.
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "many"
            workspace.mkdir()
            for index in range(40):
                (workspace / ("note_%02d.md" % index)).write_text(
                    "x\n", encoding="utf-8")
            document = Path(directory) / "long.md"
            document.write_text(
                "".join("# Chapter %d\n\ntext\n\n" % index
                        for index in range(1, 60)), encoding="utf-8")
            write_wstr(app, "temp_path", str(workspace))
            app.post_command(CMD_WORKSPACE_PROBE)
            wait_for(lambda: app.read32("ws_entry_count") == 40, 5,
                     "the workspace must enumerate the 40 files")
            write_wstr(app, "temp_path", str(document))
            app.post_command(CMD_OPEN_SELECTED)
            wait_for(lambda: app.read64("document_len") > 0, 5,
                     "the long document must be open")
            # Park the pointer over the document so neither thumb is "hot".
            u32.SetCursorPos(400, 300)
            time.sleep(.3)
            scrollbar_samples = {}
            for command, header, split, panel, label in (
                    (CMD_DARK, DARK_HEADER, DARK_DIVIDER, DARK_PANEL, "dark"),
                    (CMD_LIGHT, LIGHT_HEADER, LIGHT_DIVIDER, LIGHT_PANEL, "light"),
                    (CMD_DARK, DARK_HEADER, DARK_DIVIDER, DARK_PANEL, "dark again")):
                app.post_command(command)
                time.sleep(.5)
                for name, hwnd in (("files header", headers[0]),
                                   ("outline header", headers[1])):
                    got = pixel(hwnd, 40, 14)
                    assert got == header, (label, name, hex(got), hex(header))
                got = pixel(divider, 100, 2)
                assert got == split, (label, "divider", hex(got), hex(split))
                # Both lists keep the panel background and their own native
                # scrollbar in the frame; the bar must follow the app theme just
                # like the document's.
                for name, list_sym in (("files", "hwnd_files"),
                                       ("outline", "hwnd_outline")):
                    got = pixel(app.read64(list_sym), 10, 10)
                    assert got == panel, (label, name + " list background",
                                          hex(got), hex(panel))
                scrollbar_samples[label] = frame_pixel(app.read64("hwnd_files"))
            assert brightness(scrollbar_samples["dark"]) < brightness(
                scrollbar_samples["light"]) - 60, scrollbar_samples
            assert brightness(scrollbar_samples["dark again"]) < 100, \
                scrollbar_samples

            # Issues 1 + 3: the strips stay painted with the panel background
            # through repeated sidebar toggles, and the document surface never
            # keeps stale pixels (that is what showed up as smearing/residue).
            preview = app.read64("hwnd_preview")
            for round_index in range(3):
                app.post_command(CMD_TOGGLE_SIDEBAR)
                time.sleep(.5)
                app.post_command(CMD_TOGGLE_SIDEBAR)
                time.sleep(.7)
                for name, list_sym in (("files", "hwnd_files"),
                                       ("outline", "hwnd_outline")):
                    listbox = app.read64(list_sym)
                    assert u32.IsWindowVisible(listbox), \
                        (round_index, name, "the list must stay visible")
                after = surface_bytes(preview)
                u32.RedrawWindow(preview, None, None,
                                 RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN |
                                 RDW_UPDATENOW)
                u32.UpdateWindow(preview)
                time.sleep(.4)
                assert surface_bytes(preview) == after, \
                    (round_index, "the document surface kept stale pixels after "
                     "a sidebar toggle")

        # Issue 4, part 1: the picker object itself is a modern IFileOpenDialog.
        app.post_command(CMD_FOLDER_COM_PROBE)
        wait_for(lambda: app.read32("fod_probe_entered") == 1, 3,
                 "the folder COM probe must run")
        wait_for(lambda: app.read32("fod_probe_hresult") != 0
                 or app.read64("fod_ptr") != 0, 3, "CoCreateInstance(FileOpenDialog)")
        hresult = app.read32("fod_probe_hresult") & 0xFFFFFFFF
        assert hresult == 0, \
            ("CoCreateInstance(CLSID_FileOpenDialog) must succeed", hex(hresult))
        assert app.read64("fod_ptr") != 0, "the dialog object must be created"
        assert app.read32("fod_probe_options_hresult") & 0xFFFFFFFF == 0, \
            "IFileDialog::GetOptions must succeed"

        # Issue 4, part 2: the dialog that opens is the shell's common item
        # dialog (DirectUI view), not the legacy SHBrowseForFolder tree.
        root_before = read_wstr(app, "ws_root_path")
        pid = app.proc.pid
        known = set(top_level_windows(pid))
        u32.PostMessageW(app.main, WM_COMMAND, CMD_OPEN_FOLDER, 0)
        dialog = None
        deadline = time.perf_counter() + 8
        while time.perf_counter() < deadline and dialog is None:
            time.sleep(.3)
            for hwnd in top_level_windows(pid):
                if hwnd not in known:
                    dialog = hwnd
                    break
        assert dialog, "Open Folder must show a dialog"
        markers = set(class_names(dialog))
        assert "DirectUIHWND" in markers or "DUIViewWndClassName" in markers, \
            ("the folder picker must be the modern shell dialog", sorted(markers))
        u32.PostMessageW(dialog, WM_CLOSE, 0, 0)
        wait_for(lambda: not u32.IsWindow(dialog), 5,
                 "closing the picker must close the dialog")
        assert u32.IsWindow(app.main), "cancelling the picker must keep the app alive"
        assert read_wstr(app, "ws_root_path") == root_before, \
            "cancelling the picker must not adopt a new workspace root"

        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS theme + folder picker: the sidebar frame repaints immediately in "
          "both themes (headers, divider), both lists keep the panel background "
          "with native themed scrollbars, CoCreateInstance("
          "FileOpenDialog) and GetOptions succeed in-process, Open Folder opens "
          "the modern shell dialog and cancelling it changes nothing; released "
          "V8.5.4 binary unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
