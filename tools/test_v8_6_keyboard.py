#!/usr/bin/env python3
"""V8.6.1 slice 5: keyboard navigation and selection persistence in the tree."""
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
WM_KEYDOWN = 0x0100
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
VK_RETURN = 0x0D
VK_BACK = 0x08
LB_GETCOUNT = 0x018B
LB_GETCURSEL = 0x0188
LB_SETCURSEL = 0x0186
ROW_HEIGHT = 30

u32, k32 = c.windll.user32, c.windll.kernel32
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.GetGUIThreadInfo.argtypes = [w.DWORD, c.c_void_p]
u32.GetGUIThreadInfo.restype = w.BOOL


class GUITHREADINFO(c.Structure):
    _fields_ = [("cbSize", w.DWORD), ("flags", w.DWORD), ("hwndActive", w.HWND),
                ("hwndFocus", w.HWND), ("hwndCapture", w.HWND),
                ("hwndMenuOwner", w.HWND), ("hwndMoveSize", w.HWND),
                ("hwndCaret", w.HWND), ("rcCaret", w.RECT)]


def focused_window(app):
    """GetFocus() is per-thread, so ask the target thread through its GUI info."""
    thread = u32.GetWindowThreadProcessId(app.main, None)
    info = GUITHREADINFO()
    info.cbSize = c.sizeof(GUITHREADINFO)
    if not u32.GetGUIThreadInfo(thread, c.byref(info)):
        return None
    return info.hwndFocus or None


def load_ns():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN.resolve()), "__name__": "__pemark_keyboard__"}
    exec(compile(source.split("\nout = ")[0], str(GEN), "exec"), ns)
    return ns


def write_wstr(app, symbol, text):
    raw = (str(text) + "\0").encode("utf-16le")
    count = c.c_size_t()
    source = c.create_string_buffer(raw)
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), source,
        len(raw), c.byref(count)) and count.value == len(raw)


def read_wstr(app, symbol, size=1024):
    raw, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), raw, size,
        c.byref(got))
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


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


def index_of(app, leaf):
    for index, path in enumerate(tree_paths(app)):
        if path.rsplit("\\", 1)[-1].lower() == leaf.lower():
            return index
    raise AssertionError(f"{leaf} is not in the tree: {tree_paths(app)}")


def selected_path(app, list_hwnd):
    index = u32.SendMessageW(list_hwnd, LB_GETCURSEL, 0, 0)
    if index < 0:
        return None
    paths = tree_paths(app)
    return paths[index] if index < len(paths) else None


def click_row(list_hwnd, index):
    """A real click, so the ListBox takes the keyboard focus."""
    point = 6 | ((index * ROW_HEIGHT + 10) << 16)
    u32.SendMessageW(list_hwnd, WM_LBUTTONDOWN, MK_LBUTTON, point)
    u32.SendMessageW(list_hwnd, WM_LBUTTONUP, 0, point)


def press(app, vk):
    assert u32.PostMessageW(app.main, WM_KEYDOWN, vk, 0)
    time.sleep(.15)


def main():
    ns = load_ns()
    with tempfile.TemporaryDirectory(prefix="pemark-keyboard-") as temp:
        # Backspace walks up from the workspace root, so give it a parent that
        # contains nothing else: the assertion then has exactly one candidate.
        base = Path(temp)
        root = base / "workspace"
        (root / "sub").mkdir(parents=True)
        (root / "sub" / "inner.md").write_text("# inner\n", encoding="utf-8")
        (root / "a.md").write_text("# a\n", encoding="utf-8")
        (root / "b.md").write_text("# b\n", encoding="utf-8")

        app = App(ns, EXE)
        try:
            list_hwnd = app.read64("hwnd_files")
            write_wstr(app, "tree_root_path", root)
            write_wstr(app, "ws_root_path", root)
            write_wstr(app, "ws_current_path", root)
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: any(p.endswith("a.md") for p in tree_paths(app)), 5,
                     "the temporary workspace did not replace the default one")
            assert u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 3

            # 1. Focus the list, then Enter on the directory expands it while the
            #    selected row survives the rebuild.
            sub_index = index_of(app, "sub")
            click_row(list_hwnd, sub_index)
            wait_for(lambda: focused_window(app) == list_hwnd, 3,
                     "clicking a row must leave the keyboard focus in the list")
            press(app, VK_RETURN)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 4,
                     3, "Enter on a directory did not expand it")
            assert app.read32("tree_expanded_count") == 1
            assert selected_path(app, list_hwnd) == str(root / "sub"), \
                "expanding must keep the directory row selected"

            # 2. Enter again collapses it; the same row is still selected.
            press(app, VK_RETURN)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 3,
                     3, "Enter on an expanded directory did not collapse it")
            assert app.read32("tree_expanded_count") == 0
            assert selected_path(app, list_hwnd) == str(root / "sub"), \
                "collapsing must keep the directory row selected"

            # 3. Keyboard-only flow: expand, move to the file, open it with Enter,
            #    and the focus must still be in the panel afterwards.
            press(app, VK_RETURN)
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 4,
                     3, "the directory did not expand again")
            inner_index = index_of(app, "inner.md")
            u32.SendMessageW(list_hwnd, LB_SETCURSEL, inner_index, 0)
            press(app, VK_RETURN)
            wait_for(lambda: app.read_path().lower().endswith("inner.md"), 5,
                     "Enter on a file did not open it through the Open transaction")
            assert focused_window(app) == list_hwnd, \
                "opening a file must not steal the focus from the list"
            assert selected_path(app, list_hwnd) == str(root / "sub" / "inner.md")

            # 4. Backspace goes up only while the list owns the focus.
            press(app, VK_BACK)
            wait_for(lambda: read_wstr(app, "tree_root_path").lower() ==
                     str(base).lower(), 5,
                     "Backspace did not make the parent directory the new root")
            wait_for(lambda: u32.SendMessageW(list_hwnd, LB_GETCOUNT, 0, 0) == 1,
                     3, "the parent directory must show its own children")
            assert tree_paths(app) == [str(root)], tree_paths(app)

            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS keyboard: Enter expands/collapses a directory and opens a "
                  "file through the Open transaction, the selected row survives "
                  "both rebuilds, the focus stays in the panel, and Backspace "
                  "walks up")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
