#!/usr/bin/env python3
"""Prove the retired 131072 style-span cap no longer truncates formatting."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import tempfile
import time

from test_v8_5_2_destructive import App, EXE
from test_v8_5_2_open_encoding import build_test_candidate, write_wstr

ROOT = Path(__file__).resolve().parents[1]
RETIRED_CAP = 131072
SPAN_LINES = 140000
CMD_OPEN_SELECTED = 1901
k32 = c.windll.kernel32


def read_u32(app, address):
    value, count = c.c_uint32(), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(address),
                                 c.byref(value), 4, c.byref(count))
    assert count.value == 4
    return value.value


def span_fixture(directory):
    path = Path(directory) / "style_spans_over_cap.md"
    path.write_bytes(b"*a*\n" * SPAN_LINES)
    return path


def main():
    ns, exe = build_test_candidate()
    app = App(ns, exe)
    try:
        with tempfile.TemporaryDirectory() as directory:
            fixture = span_fixture(directory)
            # Every "*a*" line is five UTF-16 units after LF -> CRLF normalization.
            canonical_length = SPAN_LINES * 5
            write_wstr(app, "temp_path", fixture)
            app.post_command(CMD_OPEN_SELECTED)
            deadline = time.perf_counter() + 30
            while time.perf_counter() < deadline:
                if (app.read_path() == str(fixture) and
                        app.read32("style_count") >= SPAN_LINES):
                    break
                time.sleep(.05)
            count = app.read32("style_count")
            assert app.read_path() == str(fixture)
            assert count == SPAN_LINES, f"style span cap regressed: {count}"
            assert count > RETIRED_CAP
            assert app.read32("document_len") == canonical_length, \
                (app.read32("document_len"), canonical_length)
            # One 'a' plus one CR per line is emitted into the render buffer.
            assert app.read32("render_len") == SPAN_LINES * 2, \
                (app.read32("render_len"), SPAN_LINES * 2)
            capacity = app.read32("style_capacity")
            assert capacity >= SPAN_LINES, (capacity, SPAN_LINES)
            start = app.read64("style_start")
            end = app.read64("style_end")
            style_type = app.read64("style_type")
            assert start and end and style_type
            assert end - start == capacity * 4
            assert style_type - end == capacity * 4
            # Each source line "*a*" becomes one italic span [2i, 2i+1).
            for index in (0, RETIRED_CAP - 1, RETIRED_CAP, SPAN_LINES - 1):
                span_start = read_u32(app, start + index * 4)
                span_end = read_u32(app, end + index * 4)
                span_kind = read_u32(app, style_type + index * 4)
                assert (span_start, span_end, span_kind) == \
                    (index * 2, index * 2 + 1, 11), \
                    (index, span_start, span_end, span_kind)
            result = {
                "schema": 1,
                "candidate_sha256": hashlib.sha256(EXE.read_bytes()).hexdigest(),
                "retired_style_cap": RETIRED_CAP,
                "observed_style_count": count,
                "style_capacity": capacity,
                "arena_bytes": capacity * 12,
                "fixture_lines": SPAN_LINES,
                "status": "PASS",
            }
            print(json.dumps(result, indent=2))
            app.post_close()
            assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
