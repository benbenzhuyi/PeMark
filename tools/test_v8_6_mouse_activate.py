#!/usr/bin/env python3
"""V8.6.1 fix: a real mouse click on a tree row must open or toggle it.

The click is handled by the message pump through LB_ITEMFROMPOINT, so this
test uses the real pointer (SetCursorPos + mouse_event) exactly like a user.
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
    ROOT / "src/candidate/generate_markdown_editor_v8_6.py"))
EXE = Path(os.environ.get(
    "PEMARK_TREE_EXE",
    ROOT / "bin/candidate/pemark_x64_v8_6_candidate.exe"))

CMD_TREE_REBUILD = 1910
LB_GETCOUNT = 0x018B
ROW_HEIGHT = 30
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1

u32, k32 = c.windll.user32, c.windll.kernel32
u32.mouse_event.argtypes = [w.DWORD, w.DWORD, w.DWORD, w.DWORD, c.c_void_p]
u32.SetCursorPos.argtypes = [c.c_int, c.c_int]
u32.SetWindowPos.argtypes = [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int,
                             c.c_int, w.UINT]
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM


class POINT(c.Structure):
    _fields_ = [("x", w.LONG), ("y", w.LONG)]


class GUITHREADINFO(c.Structure):
    _fields_ = [("cbSize", w.DWORD), ("flags", w.DWORD), ("hwndActive", w.HWND),
                ("hwndFocus", w.HWND), ("hwndCapture", w.HWND),
                ("hwndMenuOwner", w.HWND), ("hwndMoveSize", w.HWND),
                ("hwndCaret", w.HWND), ("rcCaret", w.RECT)]


def load_ns():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN.resolve()), "__name__": "__pemark_mouse__"}
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


def tree_paths(app):
    pointer = app.read64("tree_rows")
    count = app.read32("tree_row_count")
    raw, got = c.create_string_buffer(count * 544), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(pointer), raw,
                                 len(raw), c.byref(got))
    return [raw.raw[index * 544:index * 544 + 1040]
            .decode("utf-16le").split("\0", 1)[0] for index in range(count)]


def leaf_index(app, leaf):
    for index, path in enumerate(tree_paths(app)):
        if path.rsplit("\\", 1)[-1].lower() == leaf.lower():
            return index
    raise AssertionError(f"{leaf} is not in the tree: {tree_paths(app)}")


def focused_window(app):
    thread = u32.GetWindowThreadProcessId(app.main, None)
    info = GUITHREADINFO()
    info.cbSize = c.sizeof(GUITHREADINFO)
    if not u32.GetGUIThreadInfo(thread, c.byref(info)):
        return None
    return info.hwndFocus or None


def raise_window(app):
    u32.SetWindowPos(app.main, w.HWND(HWND_TOPMOST), 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    if int(u32.GetForegroundWindow() or 0) != int(app.main):
        u32.SetForegroundWindow(app.main)
    time.sleep(.15)


def click_client(app, client_x, client_y):
    """Click a main-window client point with the real pointer."""
    point = POINT(client_x, client_y)
    assert u32.ClientToScreen(app.main, c.byref(point))
    raise_window(app)
    assert u32.SetCursorPos(point.x, point.y)
    u32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, None)
    time.sleep(.08)
    u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(.06)
    u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)


def click_row(app, index, attempts=3):
    """Click the middle of tree row ``index`` and wait for it to take effect."""
    for _ in range(attempts):
        click_client(app, 8, app.read32("files_list_y") + index * ROW_HEIGHT +
                     ROW_HEIGHT // 2)
        time.sleep(.3)
        if focused_window(app) == app.read64("hwnd_files"):
            return
    raise AssertionError("the real click never reached the file list")


def wait_change(app, before, timeout, message):
    wait_for(lambda: tree_paths(app) != before, timeout, message)


def main():
    ns = load_ns()
    with tempfile.TemporaryDirectory(prefix="pemark-mouse-") as temp:
        root = Path(temp)
        (root / "sub").mkdir(parents=True)
        (root / "sub" / "inner.md").write_text("# inner\n", encoding="utf-8")
        (root / "a.md").write_text("# a\n", encoding="utf-8")

        app = App(ns, EXE)
        try:
            list_hwnd = app.read64("hwnd_files")
            raise_window(app)
            write_wstr(app, "tree_root_path", root)
            write_wstr(app, "ws_root_path", root)
            write_wstr(app, "ws_current_path", root)
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: any(p.endswith("a.md") for p in tree_paths(app)), 5,
                     "the temporary workspace did not replace the default one")
            assert u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 2

            # 1. A real click on the directory row expands it.
            before = tree_paths(app)
            click_row(app, leaf_index(app, "sub"))
            wait_change(app, before, 3, "clicking the directory did not expand it")
            assert app.read32("tree_expanded_count") == 1
            assert focused_window(app) == list_hwnd, \
                "clicking a row must leave the focus in the list"

            # 2. Clicking the *already selected* directory collapses it again —
            #    this is exactly what the removed LBN_SELCHANGE path could not do.
            before = tree_paths(app)
            click_row(app, leaf_index(app, "sub"))
            wait_change(app, before, 3,
                        "clicking an already selected directory did not collapse it")
            assert app.read32("tree_expanded_count") == 0

            # 3. A real click on a file opens it through the Open transaction.
            click_row(app, leaf_index(app, "sub"))
            wait_for(lambda: app.read32("tree_expanded_count") == 1, 3,
                     "the directory did not expand again")
            click_row(app, leaf_index(app, "inner.md"))
            wait_for(lambda: app.read_path().lower().endswith("inner.md"), 5,
                     "clicking a file did not open it")
            assert focused_window(app) == list_hwnd, \
                "opening a file must not steal the focus from the list"

            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS mouse activation: a real click expands a directory, "
                  "collapses it again while it is already selected, opens a file "
                  "through the Open transaction and keeps the focus in the list")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
