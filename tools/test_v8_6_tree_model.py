#!/usr/bin/env python3
"""V8.6.1 file-tree model: visible rows and expansion state, without UI.

The test builds a temporary directory tree, points the process at it, writes
the expanded-path set directly into BSS, invokes the model-only rebuild
command, and parses the emitted row arena.
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
TREE_STRIDE = 544
TREE_OFF_PATH = 0
TREE_OFF_DEPTH = 520
TREE_OFF_FLAGS = 524
TREE_FLAG_DIR = 1
TREE_FLAG_EXPANDED = 2

k32 = c.windll.kernel32


def load_ns():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN.resolve()), "__name__": "__pemark_tree_test__"}
    exec(compile(source.split("\nout = ")[0], str(GEN), "exec"), ns)
    return ns


def write_u32(app, symbol, value):
    data, count = c.c_uint32(value), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[symbol]), c.byref(data),
        4, c.byref(count)) and count.value == 4


def write_wstr(app, address, text):
    raw = (str(text) + "\0").encode("utf-16le")
    count = c.c_size_t()
    source = c.create_string_buffer(raw)
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(address), source, len(raw), c.byref(count))
    return len(raw)


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError(message)


def read_rows(app):
    pointer = app.read64("tree_rows")
    count = app.read32("tree_row_count")
    assert pointer and count, (hex(pointer), count)
    raw, got = c.create_string_buffer(count * TREE_STRIDE), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(pointer), raw, len(raw), c.byref(got))
    rows = []
    for index in range(count):
        block = raw.raw[index * TREE_STRIDE:(index + 1) * TREE_STRIDE]
        path = block[:520].decode("utf-16le").split("\0", 1)[0]
        depth = int.from_bytes(block[520:524], "little", signed=True)
        flags = int.from_bytes(block[524:528], "little")
        rows.append((path, depth, flags))
    return rows


def expand(app, paths):
    write_u32(app, "tree_expanded_count", 0)
    for index, path in enumerate(paths):
        write_wstr(app, app.base + app.bsyms["tree_expanded"] + index * 1024,
                   path)
    write_u32(app, "tree_expanded_count", len(paths))
    app.post_command(CMD_TREE_REBUILD)
    time.sleep(.25)


def main():
    ns = load_ns()
    with tempfile.TemporaryDirectory(prefix="pemark-tree-") as temp:
        root = Path(temp)
        (root / "a_dir").mkdir()
        (root / "a_dir" / "nested").mkdir()
        (root / "a_dir" / "child.md").write_text("# child\n", encoding="utf-8")
        (root / "a_dir" / "nested" / "deep.txt").write_text(
            "deep\n", encoding="utf-8")
        (root / "b_file.md").write_text("# b\n", encoding="utf-8")
        (root / "c_file.txt").write_text("c\n", encoding="utf-8")
        (root / "ignored.bin").write_bytes(b"x")
        (root / ".hidden.md").write_text("hidden\n", encoding="utf-8")

        app = App(ns, EXE)
        try:
            write_wstr(app, app.base + app.bsyms["ws_root_path"], root)
            write_wstr(app, app.base + app.bsyms["ws_current_path"], root)
            write_wstr(app, app.base + app.bsyms["tree_root_path"], root)
            expand(app, [])
            wait_for(lambda: app.read32("tree_row_count") >= 3, 3,
                     "root tree rows did not appear")
            rows = read_rows(app)
            names = [Path(path).name or path for path, _, _ in rows]
            assert "ignored.bin" not in names, names
            assert ".hidden.md" not in names, names
            assert {"a_dir", "b_file.md", "c_file.txt"} <= set(names), names
            assert rows[0][2] & TREE_FLAG_DIR, rows

            a_dir = str(root / "a_dir")
            expand(app, [a_dir])
            wait_for(lambda: app.read32("tree_row_count") >= 5, 3,
                     "expanded tree rows did not appear")
            rows = read_rows(app)
            by_name = {Path(path).name or path: (depth, flags)
                       for path, depth, flags in rows}
            assert by_name["a_dir"][1] & TREE_FLAG_EXPANDED, by_name
            assert by_name["child.md"][0] == 1, by_name
            assert by_name["nested"][0] == 1, by_name

            nested = str(root / "a_dir" / "nested")
            expand(app, [a_dir, nested])
            wait_for(lambda: app.read32("tree_row_count") >= 6, 3,
                     "nested tree rows did not appear")
            rows = read_rows(app)
            by_name = {Path(path).name or path: (depth, flags)
                       for path, depth, flags in rows}
            assert by_name["deep.txt"][0] == 2, by_name

            missing = str(root / "does-not-exist")
            write_wstr(app, app.base + app.bsyms["tree_root_path"], missing)
            expand(app, [])
            wait_for(lambda: app.read32("tree_last_error") != 0, 3,
                     "missing root did not publish an error")
            app.post_close()
            assert app.proc.wait(timeout=5) == 0
            print("PASS tree model: filtered rows, expansion depth, directory "
                  "flags and unreadable-root error")
        finally:
            app.close_handle()


if __name__ == "__main__":
    main()
