#!/usr/bin/env python3
"""Verify that Outline arena growth failure cannot partially commit Open."""
import ctypes as c
import hashlib
from pathlib import Path
import time

from test_v8_5_2_destructive import App, EXE, GEN
from test_v8_5_2_open_encoding import normalized, write_wstr

ROOT = Path(__file__).resolve().parents[1]
SMALL = ROOT / "tests/v8_5_2/fixtures/utf8_lf.md"
LARGE = ROOT / "tests/outline_2600_headings.md"
CMD_OPEN_SELECTED = 1901
k32 = c.windll.kernel32


def build(mode):
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_alloc_test__",
          "OPEN_TEST_BUILD": True, "ARENA_ALLOC_INJECTION_MODE": mode}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == f"pemark_x64_v8_5_2_outline_alloc_{mode}.exe"
    return ns, out


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


def main():
    release_hash = hashlib.sha256(EXE.read_bytes()).hexdigest()
    ns, exe = build("fail_second")
    app = App(ns, exe)
    try:
        # Startup may finish its initial empty preview just before or after the
        # EDIT is discoverable, so wait until the minimum arena is installed.
        deadline = time.perf_counter() + 3
        while (time.perf_counter() < deadline and
               app.read32("inject_outline_alloc_call_count") == 0):
            time.sleep(.03)
        assert app.read32("inject_outline_alloc_call_count") == 1
        write_wstr(app, "temp_path", SMALL)
        app.post_command(CMD_OPEN_SELECTED); wait_path(app, SMALL)
        assert app.read32("inject_outline_alloc_call_count") == 1
        before = {
            "text": app.text(), "path": app.read_path(),
            "revisions": app.revisions(),
            "encoding": app.read32("encoding_state"),
            "eol": app.read32("eol_state"),
            "preview": app.read32("preview_flag"),
            "count": app.read32("outline_count"),
            "capacity": app.read32("outline_capacity"),
            "src": app.read64("outline_srcpos"),
            "render": app.read64("outline_renderpos"),
            "level": app.read64("outline_level"),
        }
        assert before["text"] == normalized(SMALL.read_text("utf-8"))
        before["arena_prefix"] = read_bytes(app, before["src"], 48)
        errors = app.read32("open_alloc_error_count")
        write_wstr(app, "temp_path", LARGE)
        app.post_command(CMD_OPEN_SELECTED)
        deadline = time.perf_counter() + 8
        while (time.perf_counter() < deadline and
               app.read32("open_alloc_error_count") == errors):
            time.sleep(.03)
        assert app.read32("open_alloc_error_count") == errors + 1
        assert app.read32("inject_outline_alloc_call_count") == 2
        assert app.text() == before["text"]
        assert app.read_path() == before["path"]
        assert app.revisions() == before["revisions"]
        assert app.read32("encoding_state") == before["encoding"]
        assert app.read32("eol_state") == before["eol"]
        assert app.read32("preview_flag") == before["preview"]
        assert app.read32("outline_count") == before["count"]
        assert app.read32("outline_capacity") == before["capacity"]
        assert app.read64("outline_srcpos") == before["src"]
        assert app.read64("outline_renderpos") == before["render"]
        assert app.read64("outline_level") == before["level"]
        assert read_bytes(app, before["src"], 48) == before["arena_prefix"]
        app.post_close(); assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(EXE.read_bytes()).hexdigest() == release_hash
    print("PASS Outline growth allocation failure preserves model, path, "
          "revisions, encoding, EOL, view and prior arena; release unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
