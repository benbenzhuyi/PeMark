#!/usr/bin/env python3
"""Noninteractive Windows Open transaction and strict-encoding regression."""
import ctypes as c
import hashlib
from pathlib import Path
import tempfile
import time

from test_v8_5_2_destructive import App, EXE, GEN

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/v8_5_2/fixtures"
CMD_OPEN_SELECTED, CMD_SAVE, CMD_PREVIEW = 1901, 1003, 1306
k32 = c.windll.kernel32


def build_test_candidate(read_mode="release"):
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_open_test__",
          "OPEN_TEST_BUILD": True, "OPEN_READ_INJECTION_MODE": read_mode}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    expected = ("pemark_x64_v8_5_2_open_transaction_test.exe" if read_mode == "release"
                else f"pemark_x64_v8_5_2_open_read_{read_mode}.exe")
    assert out.name == expected
    assert "bin" in out.parts and "test" in out.parts
    return ns, out


def write_wstr(app, name, value):
    data = (str(value) + "\0").encode("utf-16le")
    source, count = c.create_string_buffer(data), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[name]), source, len(data),
        c.byref(count)) and count.value == len(data)


def write_u32(app, name, value):
    data, count = c.c_uint32(value), c.c_size_t()
    assert k32.WriteProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms[name]), c.byref(data), 4,
        c.byref(count)) and count.value == 4


def normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


def wait_open(app, path, expected_text, expected_encoding, expected_eol, timeout=5):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if app.read_path() == str(path) and app.text() == expected_text:
            document, saved = app.revisions()
            assert document == saved
            assert app.read32("encoding_state") == expected_encoding
            actual_eol = app.read32("eol_state")
            assert actual_eol == expected_eol, \
                f"{path.name}: expected eol={expected_eol}, got {actual_eol}"
            assert app.read32("preview_flag") == 0
            return
        time.sleep(.03)
    raise AssertionError(
        f"Open did not commit {path}: path={app.read_path()!r}, text={app.text()!r}")


def successful_matrix(ns, exe):
    cases = [
        ("empty_utf8.md", "", 0, 0),
        ("utf8_lf.md", normalized((FIXTURES / "utf8_lf.md").read_text("utf-8")), 0, 1),
        ("utf8_crlf.md", normalized((FIXTURES / "utf8_crlf.md").read_text("utf-8")), 0, 0),
        ("utf8_bom.md", normalized((FIXTURES / "utf8_bom.md").read_text("utf-8-sig")), 2, 1),
        ("utf16le_bom.md", normalized((FIXTURES / "utf16le_bom.md").read_text("utf-16")), 1, 0),
    ]
    app = App(ns, exe)
    try:
        for name, text, encoding, eol in cases:
            path = FIXTURES / name
            write_wstr(app, "temp_path", path)
            app.post_command(CMD_OPEN_SELECTED)
            wait_open(app, path, text, encoding, eol)
        app.post_close(); assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def rejected_preserves_transaction(ns, exe, path,
                                   error_counter="open_decode_error_count",
                                   expected_read_calls=None):
    app = App(ns, exe)
    try:
        old_path = path.parent / "committed-before-failed-open.md"
        app.write_path(old_path)
        write_u32(app, "encoding_state", 2)
        write_u32(app, "eol_state", 1)
        before = app.set_text_dirty("dirty model survives rejected Open\r\n")
        app.post_command(CMD_PREVIEW)
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline and app.read32("preview_flag") != 1:
            time.sleep(.03)
        assert app.read32("preview_flag") == 1
        assert app.read32("encoding_state") == 2
        assert app.read32("eol_state") == 1
        errors = app.read32(error_counter)
        write_wstr(app, "temp_path", path)
        app.post_command(CMD_OPEN_SELECTED)
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline:
            if app.read32(error_counter) == errors + 1:
                break
            time.sleep(.03)
        assert app.read32(error_counter) == errors + 1
        assert app.text() == "dirty model survives rejected Open\r\n"
        assert app.read_path() == str(old_path)
        assert app.revisions() == before
        assert app.read32("preview_flag") == 1
        if expected_read_calls is not None:
            assert app.read32("inject_read_call_count") == expected_read_calls
    finally:
        app.close_handle()


def byte_roundtrip_matrix(ns, exe):
    cases = {
        "utf8_lf.md": "alpha\nbeta\n".encode("utf-8"),
        "utf8_bom_lf.md": b"\xef\xbb\xbf" + "alpha\nbeta\n".encode("utf-8"),
        "utf16_crlf.md": b"\xff\xfe" + "alpha\r\nbeta\r\n".encode("utf-16le"),
        "utf8_cr.md": "alpha\rbeta\r".encode("utf-8"),
        "empty_utf8_bom.md": b"\xef\xbb\xbf",
        "empty_utf16_bom.md": b"\xff\xfe",
    }
    with tempfile.TemporaryDirectory(prefix="pemark-roundtrip-") as folder:
        for name, expected in cases.items():
            path = Path(folder) / name
            path.write_bytes(expected)
            app = App(ns, exe)
            try:
                write_wstr(app, "temp_path", path)
                app.post_command(CMD_OPEN_SELECTED)
                deadline = time.perf_counter() + 5
                while time.perf_counter() < deadline and app.read_path() != str(path):
                    time.sleep(.03)
                assert app.read_path() == str(path), f"Open did not commit {name}"
                path.unlink()
                app.post_command(CMD_SAVE)
                deadline = time.perf_counter() + 5
                while time.perf_counter() < deadline:
                    if path.exists() and path.read_bytes() == expected:
                        break
                    time.sleep(.03)
                assert path.exists(), f"Save did not recreate {name}"
                assert path.read_bytes() == expected, \
                    f"byte round-trip changed {name}: {path.read_bytes()!r}"
                app.post_close(); assert app.proc.wait(timeout=5) == 0
            finally:
                app.close_handle()


def main():
    release_hash = hashlib.sha256(EXE.read_bytes()).hexdigest()
    ns, exe = build_test_candidate()
    successful_matrix(ns, exe)
    byte_roundtrip_matrix(ns, exe)
    rejected_preserves_transaction(ns, exe, FIXTURES / "malformed_utf8.md")
    rejected_preserves_transaction(ns, exe, FIXTURES / "embedded_nul_utf8.md")
    odd = FIXTURES / "odd_utf16le_bom.md"
    odd.write_bytes(b"\xff\xfeA")
    try:
        rejected_preserves_transaction(ns, exe, odd)
    finally:
        odd.unlink(missing_ok=True)
    ns, exe = build_test_candidate("short_then_complete")
    path = FIXTURES / "utf8_lf.md"
    app = App(ns, exe)
    try:
        write_wstr(app, "temp_path", path); app.post_command(CMD_OPEN_SELECTED)
        wait_open(app, path, normalized(path.read_text("utf-8")), 0, 1)
        assert app.read32("inject_read_call_count") >= 2
        app.post_close(); assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()
    for mode, calls in (("zero_success", 1), ("fail_first", 1),
                        ("late_failure", 2)):
        ns, exe = build_test_candidate(mode)
        rejected_preserves_transaction(ns, exe, path, "open_read_error_count",
                                       calls)
    assert hashlib.sha256(EXE.read_bytes()).hexdigest() == release_hash
    print("PASS noninteractive Open/Save transaction: UTF-8, UTF-8 BOM, UTF-16LE BOM; "
          "LF, CRLF and CR byte round-trips including empty BOM files; "
          "malformed UTF-8, embedded NUL and odd UTF-16 rejected without "
          "model/path/view mutation; short-read completion and zero/first/late "
          "read failures; release candidate unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
