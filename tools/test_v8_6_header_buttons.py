#!/usr/bin/env python3
"""V8.6.1 slice 4: file-header buttons (collapse all / refresh) and hover."""
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
CMD_REFRESH_TREE = 1313
CMD_COLLAPSE_ALL = 1314
WM_COMMAND = 0x0111
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LIST_ACTIVATE = 0x8007
MK_LBUTTON = 0x0001
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
LB_GETCOUNT = 0x018B
LB_GETCURSEL = 0x0188
LB_SETCURSEL = 0x0186

u32, k32 = c.windll.user32, c.windll.kernel32
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.SetCursorPos.argtypes = [c.c_int, c.c_int]
u32.mouse_event.argtypes = [w.DWORD, w.DWORD, w.DWORD, w.DWORD, c.c_void_p]
u32.SetWindowPos.argtypes = [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int,
                             c.c_int, w.UINT]
u32.GetForegroundWindow.restype = w.HWND


class POINT(c.Structure):
    _fields_ = [("x", w.LONG), ("y", w.LONG)]


def load_ns():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN.resolve()), "__name__": "__pemark_hdr_buttons__"}
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


def rect(app, symbol):
    base = app.base + app.bsyms[symbol]
    raw, got = c.create_string_buffer(16), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(base), raw, 16,
                                 c.byref(got))
    return c.cast(raw, c.POINTER(c.c_int32))[0:4]


def rows(app):
    pointer = app.read64("tree_rows")
    count = app.read32("tree_row_count")
    raw, got = c.create_string_buffer(count * 544), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(pointer), raw,
                                 len(raw), c.byref(got))
    return [raw.raw[index * 544:index * 544 + 1040]
            .decode("utf-16le").split("\0", 1)[0] for index in range(count)]


def read_wstr(app, symbol, size=1024):
    raw, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), raw, size,
        c.byref(got))
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def select_leaf(app, list_hwnd, leaf):
    for index, path in enumerate(rows(app)):
        if path.rsplit("\\", 1)[-1].lower() == leaf.lower():
            u32.SendMessageW(list_hwnd, LB_SETCURSEL, index, 0)
            return index
    raise AssertionError(f"{leaf} is not in the tree")


def hover_symbol(app, symbol):
    """Put the real pointer on a cached header-button rectangle."""
    raise_window(app)
    left, top, right, bottom = rect(app, symbol)
    client_x = (left + right) // 2
    client_y = app.read32("content_y") + (top + bottom) // 2
    point = POINT(client_x, client_y)
    assert u32.ClientToScreen(app.main, c.byref(point))
    assert u32.SetCursorPos(point.x, point.y)
    u32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, None)


def raise_window(app):
    """Keep the window under the pointer: real clicks need it on top."""
    u32.SetWindowPos(app.main, w.HWND(HWND_TOPMOST), 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    if int(u32.GetForegroundWindow() or 0) != int(app.main):
        u32.SetForegroundWindow(app.main)
    time.sleep(.15)


def click_header_button(app, symbol, hot_id, effect=None, attempts=3):
    """Hover the cached rectangle, then click it with real input.

    PostMessage leaves a mouse message's MSG.pt at (0,0) on this system, so a
    posted WM_LBUTTONDOWN cannot be used: the pump hit test reads MSG.pt. The
    hover is verified first, which also proves the window really owns the point
    under the pointer.
    """
    for _ in range(attempts):
        hover_symbol(app, symbol)
        deadline = time.perf_counter() + 2
        while time.perf_counter() < deadline:
            if app.read32("files_btn_hot") == hot_id:
                break
            time.sleep(.03)
        else:
            continue
        u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
        time.sleep(.06)
        u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
        if effect is None:
            return
        deadline = time.perf_counter() + 2
        while time.perf_counter() < deadline:
            if effect():
                return
            time.sleep(.05)
    raise AssertionError(f"clicking {symbol} had no effect")


def hover(app, client_x, client_y):
    point = POINT(client_x, client_y)
    assert u32.ClientToScreen(app.main, c.byref(point))
    assert u32.SetCursorPos(point.x, point.y)
    u32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, None)
    time.sleep(.05)


def main():
    ns = load_ns()
    with tempfile.TemporaryDirectory(prefix="pemark-header-buttons-") as temp:
        root = Path(temp)
        (root / "a.md").write_text("# a\n", encoding="utf-8")
        (root / "b.md").write_text("# b\n", encoding="utf-8")
        (root / "sub").mkdir()
        (root / "sub" / "inner.md").write_text("# inner\n", encoding="utf-8")

        app = App(ns, EXE)
        try:
            list_hwnd = app.read64("hwnd_files")
            # Real clicks must land on this window, so keep it on top while the
            # pointer-driven steps run.
            raise_window(app)
            # The default workspace is the system Documents folder.
            default_root = read_wstr(app, "tree_root_path")
            assert default_root and Path(default_root).is_dir(), \
                f"the default workspace must be an existing directory: {default_root!r}"
            assert read_wstr(app, "ws_current_path") == default_root
            write_wstr(app, "tree_root_path", root)
            write_wstr(app, "ws_root_path", root)
            write_wstr(app, "ws_current_path", root)
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: any(p.endswith("a.md") for p in rows(app)), 5,
                     "the temporary workspace did not replace the default one")

            # 1. Both button rectangles live inside the header and never overlap.
            width = app.read32("outline_width")
            collapse = rect(app, "files_btn_collapse_rect")
            refresh = rect(app, "files_btn_refresh_rect")
            for name, box in (("collapse", collapse), ("refresh", refresh)):
                left, top, right, bottom = box
                assert 0 <= left < right <= width, f"{name} box {box}"
                assert 0 <= top < bottom <= 28, f"{name} box {box}"
            assert collapse[2] <= refresh[0], "the two buttons must not overlap"

            # 2. Expand a directory, then click "collapse all": the tree keeps
            #    only the first level and the panel state must not change.
            select_leaf(app, list_hwnd, "sub")
            u32.PostMessageW(app.main, WM_LIST_ACTIVATE, 0, 0)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 4,
                     3, "activating the directory did not expand it")
            state_before = app.read32("files_state")
            click_header_button(
                app, "files_btn_collapse_rect", 1,
                effect=lambda: app.read32("tree_expanded_count") == 0)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 3,
                     3, "collapse all must leave only the root's children")
            assert app.read32("files_state") == state_before, \
                "a header button must not walk the panel state machine"
            assert app.read32("panel_click_pending") == 0, \
                "a header button must not arm the single-click timer"

            # 3. Refresh keeps the selected row while picking up external changes.
            index = select_leaf(app, list_hwnd, "a.md")
            (root / "c.md").write_text("# c\n", encoding="utf-8")
            u32.PostMessageW(app.main, WM_COMMAND, CMD_REFRESH_TREE, 0)
            wait_for(lambda: any(p.endswith("c.md") for p in rows(app)), 5,
                     "refresh did not pick up the new file")
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCURSEL, 0, 0) == index,
                     5, "refresh did not restore the previous selection")

            # 4. Hovering the button highlights it; leaving clears the highlight.
            left, top, right, bottom = collapse
            hover(app, (left + right) // 2, app.read32("content_y") + (top + bottom) // 2)
            wait_for(lambda: app.read32("files_btn_hot") == 1, 3,
                     "hovering the collapse button did not set the highlight")
            hover(app, app.read32("outline_width") // 2, app.read32("content_y") + 14)
            wait_for(lambda: app.read32("files_btn_hot") == 0, 3,
                     "leaving the button did not clear the highlight")

            # 5. The File menu drives the same commands as the buttons.
            (root / "d.md").write_text("# d\n", encoding="utf-8")
            assert (root / "d.md").exists()
            time.sleep(.3)
            before = u32.SendMessageW(list_hwnd, LB_GETCURSEL, 0, 0)
            u32.PostMessageW(app.main, WM_COMMAND, CMD_REFRESH_TREE, 0)
            deadline = time.perf_counter() + 5
            while time.perf_counter() < deadline:
                if any(p.endswith("d.md") for p in rows(app)):
                    break
                time.sleep(.05)
            else:
                raise AssertionError(
                    "the menu command path did not refresh the tree: "
                    f"{rows(app)} (last error {app.read32('tree_last_error')}, "
                    f"cursel {u32.SendMessageW(list_hwnd, LB_GETCURSEL, 0, 0)}, "
                    f"before {before}, "
                    f"sel '{read_wstr(app, 'fo_sel_path_buf')}')")
            u32.PostMessageW(app.main, WM_COMMAND, CMD_COLLAPSE_ALL, 0)
            wait_for(lambda: app.read32("tree_expanded_count") == 0, 3,
                     "the menu command path did not collapse the tree")

            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS header buttons: cached geometry, click-to-collapse without "
                  "touching the panel state, refresh that keeps the selection and "
                  "picks up external files, hover highlight, and the same commands "
                  "from the File menu")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
