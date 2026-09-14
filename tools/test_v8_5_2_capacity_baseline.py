#!/usr/bin/env python3
"""Freeze the pre-arena V8.5.2 Outline and process-resource baseline."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import time

from test_v8_5_2_destructive import App, EXE, GEN
from test_v8_5_2_open_encoding import build_test_candidate, write_wstr

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/outline_2600_headings.md"
CMD_OPEN_SELECTED = 1901
k32 = c.windll.kernel32
psapi = c.windll.psapi


class PROCESS_MEMORY_COUNTERS_EX(c.Structure):
    _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD),
                ("PeakWorkingSetSize", c.c_size_t),
                ("WorkingSetSize", c.c_size_t),
                ("QuotaPeakPagedPoolUsage", c.c_size_t),
                ("QuotaPagedPoolUsage", c.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", c.c_size_t),
                ("QuotaNonPagedPoolUsage", c.c_size_t),
                ("PagefileUsage", c.c_size_t),
                ("PeakPagefileUsage", c.c_size_t),
                ("PrivateUsage", c.c_size_t)]


def read_u32(app, address):
    value, count = c.c_uint32(), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(address),
                                 c.byref(value), 4, c.byref(count))
    assert count.value == 4
    return value.value


def resource_sample(app):
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = c.sizeof(counters)
    assert psapi.GetProcessMemoryInfo(app.handle, c.byref(counters), counters.cb)
    handles = w.DWORD()
    assert k32.GetProcessHandleCount(app.handle, c.byref(handles))
    return {"working_set": counters.WorkingSetSize,
            "private_usage": counters.PrivateUsage,
            "pagefile_usage": counters.PagefileUsage,
            "handle_count": handles.value}


def main():
    raw = FIXTURE.read_bytes()
    text = raw.decode("utf-8")
    headings = [line for line in text.splitlines()
                if line.startswith("#") and " Heading " in line]
    assert len(headings) == 2600
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").replace(
        "\n", "\r\n")
    expected_last_offset = canonical.index("### Heading 2048")
    ns, exe = build_test_candidate()
    app = App(ns, exe)
    try:
        write_wstr(app, "temp_path", FIXTURE)
        app.post_command(CMD_OPEN_SELECTED)
        deadline = time.perf_counter() + 10
        while time.perf_counter() < deadline:
            if app.read_path() == str(FIXTURE) and app.read32("outline_count"):
                break
            time.sleep(.05)
        actual = app.read32("outline_count")
        assert actual == 2048, f"pre-arena baseline changed: {actual}"
        array = app.base + app.bsyms["outline_srcpos"]
        last_offset = read_u32(app, array + (actual - 1) * 4)
        assert last_offset == expected_last_offset, (last_offset,
                                                      expected_last_offset)
        result = {"schema": 1, "candidate_sha256": hashlib.sha256(
                      EXE.read_bytes()).hexdigest(),
                  "fixture": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
                  "working_tree_fixture_sha256": hashlib.sha256(raw).hexdigest(),
                  "fixture_headings": len(headings),
                  "outline_capacity": 2048,
                  "observed_outline_count": actual,
                  "last_observed_heading": 2048,
                  "last_observed_source_offset": last_offset,
                  "resources": resource_sample(app),
                  "status": "KNOWN_CAPACITY_FAILURE"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        app.post_close()
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
