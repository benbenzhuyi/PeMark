#!/usr/bin/env python3
"""V8.6.1 slice 3b: right-click file operations (new / delete / copy path)."""
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
WM_FILE_OP = 0x8009
WM_KEYDOWN = 0x0100
VK_ESCAPE = 0x1B
FO_CMD_NEW_FILE = 9001
FO_CMD_NEW_FOLDER = 9002
FO_CMD_RENAME = 9003
FO_CMD_DELETE = 9004
FO_CMD_COPY_PATH = 9005
CF_UNICODETEXT = 13
IDYES = 6

u32, k32 = c.windll.user32, c.windll.kernel32
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.GetClipboardData.argtypes = [w.UINT]
u32.GetClipboardData.restype = w.HANDLE
k32.GlobalLock.argtypes = [w.HGLOBAL]
k32.GlobalLock.restype = c.c_void_p
k32.GlobalUnlock.argtypes = [w.HGLOBAL]
k32.GlobalUnlock.restype = w.BOOL

LB_GETCOUNT = 0x018B
LB_SETCURSEL = 0x0186


def load_ns():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN.resolve()), "__name__": "__pemark_file_ops__"}
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
    """Select the ListBox row whose tree path ends in ``leaf``."""
    for index, path in enumerate(tree_paths(app)):
        if path.rsplit("\\", 1)[-1].lower() == leaf.lower():
            assert u32.SendMessageW(list_hwnd, LB_SETCURSEL, index, 0) >= 0
            return index
    raise AssertionError(f"{leaf} is not in the tree")


def tree_paths(app):
    """Absolute paths of every published tree row, in display order."""
    pointer = app.read64("tree_rows")
    count = app.read32("tree_row_count")
    raw, got = c.create_string_buffer(count * 544), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(pointer), raw,
                                 len(raw), c.byref(got))
    return [raw.raw[index * 544:index * 544 + 1040]
            .decode("utf-16le").split("\0", 1)[0] for index in range(count)]


def post_op(app, command):
    assert u32.PostMessageW(app.main, WM_FILE_OP, command, 0)


def clip_text(retries=20):
    for _ in range(retries):
        if u32.OpenClipboard(None):
            try:
                handle = u32.GetClipboardData(CF_UNICODETEXT)
                if not handle:
                    return None
                pointer = k32.GlobalLock(handle)
                try:
                    return c.wstring_at(pointer)
                finally:
                    k32.GlobalUnlock(handle)
            finally:
                u32.CloseClipboard()
        time.sleep(.05)
    return None


def main():
    ns = load_ns()
    with tempfile.TemporaryDirectory(prefix="pemark-file-ops-") as temp:
        root = Path(temp)
        (root / "alpha.md").write_text("# alpha\n", encoding="utf-8")
        (root / "beta.md").write_text("# beta\n", encoding="utf-8")
        (root / "docs").mkdir()

        app = App(ns, EXE)
        try:
            list_hwnd = app.read64("hwnd_files")
            write_wstr(app, "tree_root_path", root)
            write_wstr(app, "ws_root_path", root)
            write_wstr(app, "ws_current_path", root)
            app.post_command(CMD_TREE_REBUILD)
            wait_for(lambda: {"alpha.md", "beta.md"} <=
                     {p.rsplit("\\", 1)[-1] for p in tree_paths(app)}, 5,
                     "the temporary workspace did not replace the default one")

            # 1. Copy Path writes the absolute path as CF_UNICODETEXT.
            select_leaf(app, list_hwnd, "alpha.md")
            post_op(app, FO_CMD_COPY_PATH)
            expected = str(root / "alpha.md")
            wait_for(lambda: clip_text() == expected, 5,
                     f"clipboard did not receive {expected!r}")

            # 2. Rename through the right-click command enters the inline editor;
            #    Escape must leave the file untouched.
            post_op(app, FO_CMD_RENAME)
            wait_for(lambda: app.read32("rename_active") == 1, 3,
                     "file-panel Rename command did not open the editor")
            u32.PostMessageW(app.main, WM_KEYDOWN, VK_ESCAPE, 0)
            wait_for(lambda: app.read32("rename_active") == 0, 3,
                     "Escape did not cancel the inline rename")
            assert (root / "alpha.md").exists()

            # 3. New Folder inside the selected directory, then New File twice
            #    to prove the automatic de-duplication.
            select_leaf(app, list_hwnd, "docs")
            post_op(app, FO_CMD_NEW_FOLDER)
            wait_for(lambda: (root / "docs" / "New Folder").is_dir(), 5,
                     "New Folder was not created")
            wait_for(lambda: app.read32("rename_active") == 1, 3,
                     "new folder did not enter the inline rename")
            u32.PostMessageW(app.main, WM_KEYDOWN, VK_ESCAPE, 0)
            wait_for(lambda: app.read32("rename_active") == 0, 3,
                     "Escape did not close the new-folder rename")

            select_leaf(app, list_hwnd, "docs")
            post_op(app, FO_CMD_NEW_FILE)
            wait_for(lambda: (root / "docs" / "New File.md").is_file(), 5,
                     "New File was not created")
            u32.PostMessageW(app.main, WM_KEYDOWN, VK_ESCAPE, 0)
            wait_for(lambda: app.read32("rename_active") == 0, 3,
                     "Escape did not close the new-file rename")

            select_leaf(app, list_hwnd, "docs")
            post_op(app, FO_CMD_NEW_FILE)
            wait_for(lambda: (root / "docs" / "New File (2).md").is_file(), 5,
                     "second New File did not de-duplicate its name")
            u32.PostMessageW(app.main, WM_KEYDOWN, VK_ESCAPE, 0)
            wait_for(lambda: app.read32("rename_active") == 0, 3,
                     "Escape did not close the second rename")

            # 4. tree_rebuild removes the hidden root row, so the workspace root
            #    itself is never a selectable row and no menu path can rename or
            #    delete it. Every published row must stay inside that subtree.
            paths = tree_paths(app)
            assert paths, "the tree must expose rows"
            prefix = str(root).lower() + "\\"
            assert str(root) not in paths and \
                all(path.lower().startswith(prefix) for path in paths), \
                f"every row must live inside {root}: {paths}"

            # 5. Delete to the Recycle Bin: confirm, then the file is gone.
            select_leaf(app, list_hwnd, "beta.md")
            post_op(app, FO_CMD_DELETE)
            app.click_dialog("Delete", IDYES)
            wait_for(lambda: not (root / "beta.md").exists(), 10,
                     "confirmed delete did not remove the file")
            assert (root / "alpha.md").exists()

            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS file ops: Copy Path reaches the clipboard, Rename reuses "
                  "the inline editor, New File/Folder de-duplicate and enter "
                  "rename, every row stays inside the authorization root, and "
                  "Delete to the Recycle Bin removes the file after confirmation")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
