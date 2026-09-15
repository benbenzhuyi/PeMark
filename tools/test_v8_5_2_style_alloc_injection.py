#!/usr/bin/env python3
"""Verify that style-arena growth failure cannot partially commit Open."""
import ctypes as c
import hashlib
from pathlib import Path
import tempfile
import time

from test_v8_5_2_destructive import App, EXE, GEN
from test_v8_5_2_open_encoding import normalized, write_wstr

ROOT = Path(__file__).resolve().parents[1]
SMALL = ROOT / "tests/v8_5_2/fixtures/utf8_lf.md"
CMD_OPEN_SELECTED = 1901
SPAN_LINES = 140000
k32 = c.windll.kernel32
VERSION_TAG = GEN.stem.replace("generate_markdown_editor_", "")


def build(mode):
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_style_alloc_test__",
          "OPEN_TEST_BUILD": True, "ARENA_ALLOC_INJECTION_MODE": mode}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == f"pemark_x64_{VERSION_TAG}_style_alloc_{mode}.exe", out.name
    assert "bin" in out.parts and "test" in out.parts
    return ns, out


def span_fixture(directory):
    """A document whose italic span count exceeds the retired 131072 cap."""
    path = Path(directory) / "style_spans_over_cap.md"
    path.write_bytes(b"*a*\n" * SPAN_LINES)
    return path


def read_bytes(app, address, size):
    data, count = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(address), data, size,
                                 c.byref(count)) and count.value == size
    return data.raw


def wait_path(app, path, timeout=8):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline and app.read_path() != str(path):
        time.sleep(.03)
    assert app.read_path() == str(path)


def wait_open_alloc_errors(app, target, timeout=8):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if app.read32("open_alloc_error_count") >= target:
            return
        time.sleep(.03)
    raise AssertionError("Open did not report the injected arena failure")


def snapshot(app):
    state = {
        "text": app.text(), "path": app.read_path(),
        "revisions": app.revisions(),
        "encoding": app.read32("encoding_state"),
        "eol": app.read32("eol_state"),
        "preview": app.read32("preview_flag"),
        "count": app.read32("style_count"),
        "capacity": app.read32("style_capacity"),
        "start": app.read64("style_start"),
        "end": app.read64("style_end"),
        "type": app.read64("style_type"),
    }
    if state["start"]:
        state["arena_prefix"] = read_bytes(app, state["start"], 48)
    return state


def assert_unchanged(app, before):
    assert app.text() == before["text"]
    assert app.read_path() == before["path"]
    assert app.revisions() == before["revisions"]
    assert app.read32("encoding_state") == before["encoding"]
    assert app.read32("eol_state") == before["eol"]
    assert app.read32("preview_flag") == before["preview"]
    assert app.read32("style_count") == before["count"]
    assert app.read32("style_capacity") == before["capacity"]
    assert app.read64("style_start") == before["start"]
    assert app.read64("style_end") == before["end"]
    assert app.read64("style_type") == before["type"]
    if before["start"]:
        assert read_bytes(app, before["start"], 48) == before["arena_prefix"]


def growth_failure_preserves_document(release_hash):
    ns, exe = build("style_fail_second")
    app = App(ns, exe)
    try:
        deadline = time.perf_counter() + 3
        while (time.perf_counter() < deadline and
               app.read32("inject_style_alloc_call_count") == 0):
            time.sleep(.03)
        assert app.read32("inject_style_alloc_call_count") == 1
        assert app.read32("style_capacity") >= 4096
        write_wstr(app, "temp_path", SMALL)
        app.post_command(CMD_OPEN_SELECTED)
        wait_path(app, SMALL)
        assert app.text() == normalized(SMALL.read_text("utf-8"))
        assert app.read32("inject_style_alloc_call_count") == 1
        before = snapshot(app)
        errors = app.read32("open_alloc_error_count")
        with tempfile.TemporaryDirectory() as directory:
            large = span_fixture(directory)
            write_wstr(app, "temp_path", large)
            app.post_command(CMD_OPEN_SELECTED)
            wait_open_alloc_errors(app, errors + 1)
            assert app.read32("inject_style_alloc_call_count") == 2
            assert_unchanged(app, before)
        app.post_close()
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(EXE.read_bytes()).hexdigest() == release_hash
    print("PASS style arena growth failure preserves model, path, revisions, "
          "encoding, EOL, view and prior arena; release unchanged")


def immediate_failure_stays_safe(release_hash):
    ns, exe = build("style_fail_first")
    app = App(ns, exe)
    try:
        deadline = time.perf_counter() + 3
        while (time.perf_counter() < deadline and
               app.read32("inject_style_alloc_call_count") == 0):
            time.sleep(.03)
        assert app.read32("inject_style_alloc_call_count") == 1
        # The startup refresh could not reserve: no arena may be published and
        # no span may be recorded through a stale pointer.
        assert app.read32("style_capacity") == 0
        assert app.read64("style_start") == 0
        assert app.read32("style_count") == 0
        assert app.proc.poll() is None
        # A later Open retries the allocation and must succeed normally.
        write_wstr(app, "temp_path", SMALL)
        app.post_command(CMD_OPEN_SELECTED)
        wait_path(app, SMALL)
        assert app.text() == normalized(SMALL.read_text("utf-8"))
        assert app.read32("style_capacity") >= 4096
        assert app.read64("style_start") != 0
        app.post_close()
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(EXE.read_bytes()).hexdigest() == release_hash
    print("PASS failed first style allocation publishes no arena and stays "
          "alive; release unchanged")


def main():
    release_hash = hashlib.sha256(EXE.read_bytes()).hexdigest()
    growth_failure_preserves_document(release_hash)
    immediate_failure_stays_safe(release_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
