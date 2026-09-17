#!/usr/bin/env python3
"""V8.5.3 document arena: reserved policy bound, block commit, failure safety."""
import ctypes as c
import hashlib
import os
from pathlib import Path
import tempfile
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
LARGE = ROOT / "tests/large_regression_1_2mb.md"
CMD_OPEN_SELECTED = 1901
WM_SETTEXT, EN_CHANGE, WM_COMMAND = 0x000C, 0x0300, 0x0111
COMMIT_CHUNK = 262144
# Unsaved-change prompt button IDs: 6 = Save, 7 = Discard, 2 = Cancel.
# Discarding is the only safe choice for a scratch edit; saving would write the
# scratch text back to whatever path the document came from.
DLG_DISCARD = 7
k32 = c.windll.kernel32
u32 = c.windll.user32


def build(mode="release"):
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_document_arena__",
          "OPEN_TEST_BUILD": True, "ARENA_ALLOC_INJECTION_MODE": mode}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    expected = (f"pemark_x64_{VERSION_TAG}_open_transaction_test.exe"
                if mode == "release"
                else f"pemark_x64_{VERSION_TAG}_document_alloc_{mode}.exe")
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


def read_model_head(app, count):
    pointer = app.read64("document_model")
    assert pointer
    buf, got = c.create_string_buffer(count * 2), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(pointer), buf, count * 2,
                                 c.byref(got)) and got.value == count * 2
    return buf.raw.decode("utf-16le")


def reserved_and_committed(release_hash):
    ns, exe = build()
    app = App(ns, exe)
    try:
        # Startup commits one block for the empty document.
        wait_for(lambda: app.read32("document_capacity") >= COMMIT_CHUNK, 5,
                 "startup document arena was not committed")
        pointer = app.read64("document_model")
        assert pointer, "document arena was not reserved"
        assert app.read32("document_capacity") % COMMIT_CHUNK == 0, \
            app.read32("document_capacity")
        open_selected(app, SMALL)
        small_capacity = app.read32("document_capacity")
        assert small_capacity == COMMIT_CHUNK, small_capacity
        assert read_model_head(app, 10).startswith("# UTF-8")
        # A large document must grow the commit in aligned blocks only.
        open_selected(app, LARGE)
        document_len = app.read32("document_len")
        capacity = app.read32("document_capacity")
        assert capacity >= document_len + 1, (capacity, document_len)
        assert capacity % COMMIT_CHUNK == 0, capacity
        assert capacity > small_capacity
        assert app.read64("document_model") == pointer, \
            "an existing reservation must be reused"
        assert app.text().startswith("#")
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS document arena reserves once, commits aligned blocks and grows "
          "for a 1.2 MB document; released binary unchanged")


def editor_growth_commits(release_hash):
    ns, exe = build()
    app = App(ns, exe)
    try:
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "editor_growth.md"
            scratch.write_bytes(SMALL.read_bytes())
            open_selected(app, scratch)
            before = app.read32("document_capacity")
            payload = "growth\r\n" * 40000
            value = c.create_unicode_buffer(payload)
            u32.SendMessageW(app.edit, WM_SETTEXT, 0, c.cast(value, c.c_void_p).value)
            u32.SendMessageW(app.main, WM_COMMAND, (EN_CHANGE << 16) | 1, app.edit)
            wait_for(lambda: app.read32("document_len") == len(payload), 20,
                     "editor sync did not update the model length")
            after = app.read32("document_capacity")
            assert after > before, (before, after)
            assert after >= len(payload) + 1
            assert after % COMMIT_CHUNK == 0, after
            assert read_model_head(app, 20).startswith("growth")
            # The document is dirty, so close goes through the unsaved prompt.
            app.post_close()
            app.click_dialog("PeMark", DLG_DISCARD)
            assert app.proc.wait(timeout=10) == 0
            assert scratch.read_bytes() == SMALL.read_bytes(), \
                "discarding a dirty close must not modify the opened file"
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS editor sync commits additional document blocks and keeps the "
          "model in step with the control")


def commit_failure_preserves_document(release_hash):
    ns, exe = build("document_fail_second")
    app = App(ns, exe)
    try:
        wait_for(lambda: app.read32("inject_document_alloc_call_count") >= 1, 5,
                 "startup document commit was not requested")
        assert app.read32("inject_document_alloc_call_count") == 1
        open_selected(app, SMALL)
        before = {
            "text": app.text(), "path": app.read_path(), "revisions": app.revisions(),
            "capacity": app.read32("document_capacity"),
            "pointer": app.read64("document_model"),
            "head": read_model_head(app, 16),
        }
        errors = app.read32("open_alloc_error_count")
        write_wstr(app, "temp_path", LARGE)
        app.post_command(CMD_OPEN_SELECTED)
        wait_for(lambda: app.read32("open_alloc_error_count") >= errors + 1, 20,
                 "injected document commit failure was not observed")
        assert app.read32("inject_document_alloc_call_count") == 2
        assert app.text() == before["text"]
        assert app.read_path() == before["path"]
        assert app.revisions() == before["revisions"]
        assert app.read32("document_capacity") == before["capacity"]
        assert app.read64("document_model") == before["pointer"]
        assert read_model_head(app, 16) == before["head"]
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS failed document commit preserves text, path, revisions and the "
          "previous contents")


def first_commit_failure_keeps_reservation(release_hash):
    ns, exe = build("document_fail_first")
    app = App(ns, exe)
    try:
        wait_for(lambda: app.read32("inject_document_alloc_call_count") >= 2, 5,
                 "startup document commit retry was not observed")
        # The policy bound is reserved before the first deliberately failed
        # commit. Startup now retries immediately; that retry must publish one
        # coherent committed block inside the same reservation.
        assert app.read32("inject_document_alloc_call_count") == 2
        assert app.read64("document_model") != 0
        assert app.read32("document_capacity") >= COMMIT_CHUNK
        assert app.proc.poll() is None
        open_selected(app, SMALL)
        assert app.read32("document_capacity") >= COMMIT_CHUNK
        assert app.text() == normalized(SMALL.read_text("utf-8"))
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS failed first document commit keeps its reservation and retries "
          "safely")


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    reserved_and_committed(release_hash)
    editor_growth_commits(release_hash)
    commit_failure_preserves_document(release_hash)
    first_commit_failure_keeps_reservation(release_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
