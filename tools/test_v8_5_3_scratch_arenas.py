#!/usr/bin/env python3
"""V8.5.3 decode/encode scratch arenas: sizing, reuse and failure safety."""
import ctypes as c
import hashlib
import os
from pathlib import Path
import tempfile
import time

from test_v8_5_2_destructive import App
from test_v8_5_2_open_encoding import write_wstr

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
LARGE = ROOT / "tests/large_regression_1_2mb.md"
CMD_OPEN_SELECTED = 1901
CHUNK = 65536
k32 = c.windll.kernel32


def build(mode="release"):
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_scratch_arenas__",
          "OPEN_TEST_BUILD": True, "ARENA_ALLOC_INJECTION_MODE": mode}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    expected = (f"pemark_x64_{VERSION_TAG}_open_transaction_test.exe"
                if mode == "release"
                else f"pemark_x64_{VERSION_TAG}_{mode.split('_')[0]}_alloc_{mode}.exe")
    assert out.name == expected, out.name
    return ns, out


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError(message)


def open_selected(app, path, timeout=40):
    write_wstr(app, "temp_path", path)
    app.post_command(CMD_OPEN_SELECTED)
    wait_for(lambda: app.read_path() == str(path), timeout,
             "Open did not commit %s" % path.name)


def sizes(app):
    return (app.read32("byte_capacity"), app.read32("wide_capacity"))


def sizing_and_reuse(release_hash):
    ns, exe = build()
    app = App(ns, exe)
    try:
        before = sizes(app)
        assert app.read64("bytebuf") == 0 and app.read64("widebuf") == 0, \
            "startup must not pre-allocate scratch arenas"
        open_selected(app, SMALL)
        byte_cap, wide_cap = sizes(app)
        assert byte_cap % CHUNK == 0 and wide_cap % CHUNK == 0, (byte_cap, wide_cap)
        assert app.read64("bytebuf") and app.read64("widebuf")
        assert byte_cap >= SMALL.stat().st_size + 2, (byte_cap, SMALL.stat().st_size)
        # A large document must grow both arenas; the buffers stay where they were
        # only if the existing block already fits, otherwise a new one is owned.
        open_selected(app, LARGE)
        large_byte, large_wide = sizes(app)
        assert large_byte >= LARGE.stat().st_size, (large_byte, LARGE.stat().st_size)
        assert large_wide >= app.read32("document_len"), \
            (large_wide, app.read32("document_len"))
        assert large_byte % CHUNK == 0 and large_wide % CHUNK == 0
        # Reopening the small document must reuse, not shrink.
        open_selected(app, SMALL)
        assert sizes(app) == (large_byte, large_wide), sizes(app)
        assert before == (0, 0)
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS scratch arenas start empty, grow in aligned blocks with the "
          "document, and are never shrunk")


def save_round_trip(release_hash):
    ns, exe = build()
    app = App(ns, exe)
    try:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "round_trip.md"
            target.write_bytes(SMALL.read_bytes())
            open_selected(app, target)
            original = target.read_bytes()
            # Touch the document so Save performs a real encoding pass.
            app.set_text_dirty(SMALL.read_text("utf-8") + "tail\n")
            app.post_command(1003)  # CMD_SAVE
            wait_for(lambda: app.revisions()[0] == app.revisions()[1], 20,
                     "Save did not commit")
            saved = target.read_bytes()
            assert saved != original and saved.endswith(b"tail\n"), saved[-16:]
            byte_cap, wide_cap = sizes(app)
            assert byte_cap >= len(saved)
            assert wide_cap >= app.read32("document_len")
            app.post_close()
            assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS Save encodes through the scratch arenas and reports committed "
          "bytes back to the target file")


def injected_failure(mode, counter, release_hash, unchanged):
    """unchanged='both' for the first arena, 'wide' when byte grew first.

    Arena capacity is reusable cache, not document state: a committed block
    stays owned after a later failure in the same operation. The document,
    path and revisions must still be untouched, and the arena that failed must
    keep its previous pointer and capacity.
    """
    ns, exe = build(mode)
    app = App(ns, exe)
    try:
        open_selected(app, SMALL)
        before = {
            "text": app.text(), "path": app.read_path(), "revisions": app.revisions(),
            "sizes": sizes(app), "byte": app.read64("bytebuf"),
            "wide": app.read64("widebuf"),
        }
        errors = app.read32("open_alloc_error_count")
        write_wstr(app, "temp_path", LARGE)
        app.post_command(CMD_OPEN_SELECTED)
        wait_for(lambda: app.read32("open_alloc_error_count") >= errors + 1, 20,
                 "injected scratch arena failure was not observed (%s)" % mode)
        assert app.read32(counter) == 2, (mode, app.read32(counter))
        assert app.text() == before["text"]
        assert app.read_path() == before["path"]
        assert app.revisions() == before["revisions"]
        if unchanged == "both":
            assert sizes(app) == before["sizes"], sizes(app)
            assert app.read64("bytebuf") == before["byte"]
            assert app.read64("widebuf") == before["wide"]
        else:
            assert app.read32("wide_capacity") == before["sizes"][1], sizes(app)
            assert app.read64("widebuf") == before["wide"]
            assert app.read32("byte_capacity") >= before["sizes"][0], sizes(app)
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS injected %s failure preserves document, path, revisions and the "
          "previous arenas" % mode)


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    sizing_and_reuse(release_hash)
    save_round_trip(release_hash)
    injected_failure("byte_fail_second", "inject_byte_alloc_call_count",
                     release_hash, "both")
    injected_failure("wide_fail_second", "inject_wide_alloc_call_count",
                     release_hash, "wide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
