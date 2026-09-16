#!/usr/bin/env python3
"""V8.5.3 render arena: geometry, mapping integrity and allocation failure."""
import ctypes as c
import hashlib
import os
import struct
from pathlib import Path
import time

from test_v8_5_2_destructive import App
from test_v8_5_2_open_encoding import normalized, write_wstr

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/candidate/generate_markdown_editor_v8_5_3.py"))
EXE = Path(os.environ.get(
    "PEMARK_EXE",
    ROOT / "bin/candidate/pemark_x64_v8_5_3_candidate.exe"))
# The published binary must stay byte-identical while a test runs.
RELEASE_EXE = ROOT / "bin/current/pemark_x64_v8_5_3.exe"
VERSION_TAG = GEN.stem.replace("generate_markdown_editor_", "")
SMALL = ROOT / "tests/v8_5_2/fixtures/utf8_lf.md"
MAPPED = ROOT / "tests/position_map_300_chapters.md"
CMD_OPEN_SELECTED = 1901
k32 = c.windll.kernel32


def build(mode="release"):
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_render_arena__",
          "OPEN_TEST_BUILD": True, "ARENA_ALLOC_INJECTION_MODE": mode}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    expected = (f"pemark_x64_{VERSION_TAG}_open_transaction_test.exe"
                if mode == "release"
                else f"pemark_x64_{VERSION_TAG}_render_alloc_{mode}.exe")
    assert out.name == expected, out.name
    return ns, out


def read_u32_array(app, address, count):
    size = count * 4
    buf, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(address), buf, size,
                                 c.byref(got)) and got.value == size
    return struct.unpack("<%dI" % count, buf.raw)


def wait_for(app, predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError(message)


def open_selected(app, path, timeout=20):
    write_wstr(app, "temp_path", path)
    app.post_command(CMD_OPEN_SELECTED)
    wait_for(app, lambda: app.read_path() == str(path), timeout,
             "Open did not commit %s" % path.name)


def geometry_and_mapping(release_hash):
    ns, exe = build()
    app = App(ns, exe)
    try:
        open_selected(app, SMALL)
        small_capacity = app.read32("render_arena_capacity")
        assert small_capacity >= 4096, small_capacity
        open_selected(app, MAPPED)
        document_len = app.read32("document_len")
        render_len = app.read32("render_len")
        capacity = app.read32("render_arena_capacity")
        map_ptr = app.read64("render_srcmap")
        text_ptr = app.read64("previewbuf")
        assert map_ptr and text_ptr
        assert capacity >= render_len >= 1, (capacity, render_len)
        assert capacity >= document_len + 1, (capacity, document_len)
        # One contiguous block: the render text follows the position map.
        assert text_ptr - map_ptr == capacity * 4, (text_ptr, map_ptr, capacity)
        # The map is monotonic, inside the document, and covers both ends.
        head = read_u32_array(app, map_ptr, 512)
        tail_count = 512
        tail = read_u32_array(app, map_ptr + (render_len - tail_count) * 4, tail_count)
        for sample in (head, tail):
            assert all(value < document_len for value in sample), "map out of range"
        assert all(b >= a for a, b in zip(head, head[1:])), "map not monotonic at head"
        assert all(b >= a for a, b in zip(tail, tail[1:])), "map not monotonic at tail"
        assert head[0] < 64, head[0]
        assert tail[-1] > document_len // 2, tail[-1]
        # Preview must still load the render text produced by the arena.
        preview = app.read64("hwnd_preview")
        assert preview
        app.post_command(1306)
        wait_for(app, lambda: app.read32("preview_flag") == 1, 10,
                 "Preview mode did not activate")
        length = c.windll.user32.SendMessageW(preview, 0x000E, 0, 0)
        assert length > render_len // 2, (length, render_len)
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS render arena geometry, mapping range/monotonicity and preview "
          "load; released V8.5.2 binary unchanged")


def growth_failure_preserves_document(release_hash):
    ns, exe = build("render_fail_second")
    app = App(ns, exe)
    try:
        wait_for(app, lambda: app.read32("inject_render_alloc_call_count") >= 1, 5,
                 "startup render arena was not requested")
        assert app.read32("inject_render_alloc_call_count") == 1
        assert app.read32("render_arena_capacity") >= 4096
        open_selected(app, SMALL)
        before = {
            "text": app.text(), "path": app.read_path(), "revisions": app.revisions(),
            "capacity": app.read32("render_arena_capacity"),
            "map": app.read64("render_srcmap"), "text_ptr": app.read64("previewbuf"),
            "map_head": read_u32_array(app, app.read64("render_srcmap"), 64),
        }
        errors = app.read32("open_alloc_error_count")
        write_wstr(app, "temp_path", MAPPED)
        app.post_command(CMD_OPEN_SELECTED)
        wait_for(app, lambda: app.read32("open_alloc_error_count") >= errors + 1, 10,
                 "injected render arena growth failure was not observed")
        assert app.read32("inject_render_alloc_call_count") == 2
        assert app.text() == before["text"]
        assert app.read_path() == before["path"]
        assert app.revisions() == before["revisions"]
        assert app.read32("render_arena_capacity") == before["capacity"]
        assert app.read64("render_srcmap") == before["map"]
        assert app.read64("previewbuf") == before["text_ptr"]
        assert read_u32_array(app, before["map"], 64) == before["map_head"]
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS failed render arena growth preserves document, path, revisions "
          "and the previous arena")


def first_failure_publishes_nothing(release_hash):
    ns, exe = build("render_fail_first")
    app = App(ns, exe)
    try:
        wait_for(app, lambda: app.read32("inject_render_alloc_call_count") >= 1, 5,
                 "startup render arena was not requested")
        assert app.read32("render_arena_capacity") == 0
        assert app.read64("render_srcmap") == 0
        assert app.read64("previewbuf") == 0
        assert app.proc.poll() is None
        open_selected(app, SMALL)
        assert app.read32("render_arena_capacity") >= 4096
        assert app.read64("render_srcmap") != 0
        assert app.text() == normalized(SMALL.read_text("utf-8"))
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS failed first render allocation publishes no arena and retries "
          "on the next Open")


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    geometry_and_mapping(release_hash)
    growth_failure_preserves_document(release_hash)
    first_failure_publishes_nothing(release_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
