#!/usr/bin/env python3
"""Noninteractive Windows Open transaction and strict-encoding regression."""
import ctypes as c
import hashlib
from pathlib import Path
import time

from test_v8_5_2_destructive import App, EXE, GEN

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/v8_5_2/fixtures"
CMD_OPEN_SELECTED, CMD_PREVIEW = 1901, 1306
k32 = c.windll.kernel32


def build_test_candidate():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_open_test__",
          "OPEN_TEST_BUILD": True}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == "pemark_x64_v8_5_2_open_transaction_test.exe"
    assert "bin" in out.parts and "test" in out.parts
    return ns, out


def write_wstr(app, name, value):
    data = (str(value) + "\0").encode("utf-16le")
    source, count = c.create_string_buffer(data), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[name]), source, len(data),
        c.byref(count)) and count.value == len(data)


def normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


def wait_open(app, path, expected_text, expected_encoding, timeout=5):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if app.read_path() == str(path) and app.text() == expected_text:
            document, saved = app.revisions()
            assert document == saved
            assert app.read32("encoding_state") == expected_encoding
            assert app.read32("preview_flag") == 0
            return
        time.sleep(.03)
    raise AssertionError(
        f"Open did not commit {path}: path={app.read_path()!r}, text={app.text()!r}")


def successful_matrix(ns, exe):
    cases = [
        ("empty_utf8.md", "", 0),
        ("utf8_lf.md", normalized((FIXTURES / "utf8_lf.md").read_text("utf-8")), 0),
        ("utf8_crlf.md", normalized((FIXTURES / "utf8_crlf.md").read_text("utf-8")), 0),
        ("utf8_bom.md", normalized((FIXTURES / "utf8_bom.md").read_text("utf-8-sig")), 0),
        ("utf16le_bom.md", normalized((FIXTURES / "utf16le_bom.md").read_text("utf-16")), 1),
    ]
    app = App(ns, exe)
    try:
        for name, text, encoding in cases:
            path = FIXTURES / name
            write_wstr(app, "temp_path", path)
            app.post_command(CMD_OPEN_SELECTED)
            wait_open(app, path, text, encoding)
        app.post_close(); assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def rejected_preserves_transaction(ns, exe, path):
    app = App(ns, exe)
    try:
        old_path = path.parent / "committed-before-failed-open.md"
        app.write_path(old_path)
        before = app.set_text_dirty("dirty model survives rejected Open\r\n")
        app.post_command(CMD_PREVIEW)
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline and app.read32("preview_flag") != 1:
            time.sleep(.03)
        assert app.read32("preview_flag") == 1
        errors = app.read32("open_decode_error_count")
        write_wstr(app, "temp_path", path)
        app.post_command(CMD_OPEN_SELECTED)
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline:
            if app.read32("open_decode_error_count") == errors + 1:
                break
            time.sleep(.03)
        assert app.read32("open_decode_error_count") == errors + 1
        assert app.text() == "dirty model survives rejected Open\r\n"
        assert app.read_path() == str(old_path)
        assert app.revisions() == before
        assert app.read32("preview_flag") == 1
    finally:
        app.close_handle()


def main():
    release_hash = hashlib.sha256(EXE.read_bytes()).hexdigest()
    ns, exe = build_test_candidate()
    successful_matrix(ns, exe)
    rejected_preserves_transaction(ns, exe, FIXTURES / "malformed_utf8.md")
    rejected_preserves_transaction(ns, exe, FIXTURES / "embedded_nul_utf8.md")
    odd = FIXTURES / "odd_utf16le_bom.md"
    odd.write_bytes(b"\xff\xfeA")
    try:
        rejected_preserves_transaction(ns, exe, odd)
    finally:
        odd.unlink(missing_ok=True)
    assert hashlib.sha256(EXE.read_bytes()).hexdigest() == release_hash
    print("PASS noninteractive Open transaction: UTF-8, UTF-8 BOM, UTF-16LE BOM; "
          "malformed UTF-8, embedded NUL and odd UTF-16 rejected without "
          "model/path/view mutation; release candidate unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
