#!/usr/bin/env python3
"""Build-time-only WriteFile fault variants for the V8.5.2 save loop."""
import hashlib
from pathlib import Path
import tempfile
import time

from test_v8_5_2_destructive import App, EXE, GEN, CMD_NEW

WM_CLOSE = 0x0010


def build_variant(mode):
    source = GEN.read_text(encoding="utf-8")
    ns = {
        "__file__": str(GEN),
        "__name__": "__pemark_write_injection__",
        "WRITE_INJECTION_MODE": mode,
    }
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == f"pemark_x64_v8_5_2_write_{mode}.exe"
    assert "bin" in out.parts and "test" in out.parts
    return ns, out


def wait_clean_new(app, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        doc, saved = app.revisions()
        if app.text() == "" and doc == saved:
            return
        time.sleep(.02)
    raise AssertionError("saved New continuation did not commit")


def short_then_complete(ns, exe, target):
    app = App(ns, exe)
    text = "partial-write-loop-must-advance\r\n"
    try:
        app.write_path(target)
        app.set_text_dirty(text)
        app.post_command(CMD_NEW); app.click_dialog("PeMark", 6)
        wait_clean_new(app)
        assert target.read_bytes() == text.encode("utf-8")
        assert not Path(str(target) + ".pemark.tmp").exists()
        assert app.read32("inject_write_call_count") >= 2
        app.post_close(); assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def expected_failure(ns, exe, target, counter, expected_calls):
    target.write_bytes(b"ORIGINAL-TARGET")
    app = App(ns, exe)
    before = None
    try:
        app.write_path(target)
        before = app.set_text_dirty("late failure must preserve memory\r\n")
        app.post_close(); app.click_dialog("PeMark", 6)
        app.click_dialog("PeMark", 2, body_contains="Could not save")
        time.sleep(.1)
        assert app.proc.poll() is None
        assert app.revisions() == before
        assert app.text() == "late failure must preserve memory\r\n"
        assert app.read32("pending_destructive_action") == 0
        assert app.read32(counter) == expected_calls
        assert target.read_bytes() == b"ORIGINAL-TARGET"
        assert not Path(str(target) + ".pemark.tmp").exists()
        app.post_close(); app.click_dialog("PeMark", 7)
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def staging_collision_preserved(ns, exe, target):
    target.write_bytes(b"ORIGINAL-TARGET")
    stage = Path(str(target) + ".pemark.tmp")
    stage.write_bytes(b"PREEXISTING-STAGING-ARTIFACT")
    app = App(ns, exe)
    try:
        app.write_path(target)
        before = app.set_text_dirty("collision must not truncate either file\r\n")
        app.post_close(); app.click_dialog("PeMark", 6)
        app.click_dialog("PeMark", 2, body_contains="Could not save")
        assert app.proc.poll() is None
        assert app.revisions() == before
        assert target.read_bytes() == b"ORIGINAL-TARGET"
        assert stage.read_bytes() == b"PREEXISTING-STAGING-ARTIFACT"
        assert app.read32("inject_write_call_count") == 0
        app.post_close(); app.click_dialog("PeMark", 7)
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def main():
    release_hash = hashlib.sha256(EXE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="pemark-write-injection-") as temp:
        root = Path(temp)
        ns, exe = build_variant("short_then_complete")
        short_then_complete(ns, exe, root / "short.md")
        staging_collision_preserved(ns, exe, root / "collision.md")
        ns, exe = build_variant("zero_success")
        expected_failure(ns, exe, root / "zero.md", "inject_write_call_count", 1)
        ns, exe = build_variant("fail_first")
        expected_failure(ns, exe, root / "first.md", "inject_write_call_count", 1)
        ns, exe = build_variant("late_failure")
        expected_failure(ns, exe, root / "late.md", "inject_write_call_count", 2)
        ns, exe = build_variant("flush_failure")
        expected_failure(ns, exe, root / "flush.md", "inject_flush_call_count", 1)
        ns, exe = build_variant("replace_failure")
        expected_failure(ns, exe, root / "replace.md", "inject_replace_call_count", 1)
    assert hashlib.sha256(EXE.read_bytes()).hexdigest() == release_hash
    print("PASS atomic WriteFile injection: short->complete; zero-success rejected; "
          "first failure; partial-then-failure; flush failure; replace failure; "
          "original target and preexisting staging artifact preserved; "
          "staging files cleaned; release candidate unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
