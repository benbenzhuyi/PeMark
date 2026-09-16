#!/usr/bin/env python3
"""V8.5.3 exit gate: repeated Open/parse/close reaches a stable memory plateau."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import os
import json
from pathlib import Path
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
MAPPED = ROOT / "tests/position_map_300_chapters.md"
LARGE = ROOT / "tests/large_regression_1_2mb.md"
CMD_OPEN_SELECTED, CMD_NEW, CMD_PREVIEW = 1901, 1001, 1306
CYCLES = 12
k32, psapi, u32 = c.windll.kernel32, c.windll.psapi, c.windll.user32


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


def build(mode="release"):
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_memory_plateau__",
          "OPEN_TEST_BUILD": True, "ARENA_ALLOC_INJECTION_MODE": mode}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == f"pemark_x64_{VERSION_TAG}_open_transaction_test.exe", out.name
    return ns, out


def sample(app):
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = c.sizeof(counters)
    assert psapi.GetProcessMemoryInfo(app.handle, c.byref(counters), counters.cb)
    handles = w.DWORD()
    assert k32.GetProcessHandleCount(app.handle, c.byref(handles))
    return {"working_set": counters.WorkingSetSize,
            "private_usage": counters.PrivateUsage,
            "handle_count": handles.value}


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError(message)


def cycle(app, path):
    write_wstr(app, "temp_path", path)
    app.post_command(CMD_OPEN_SELECTED)
    wait_for(lambda: app.read_path() == str(path), 40,
             "Open did not commit %s" % path.name)
    # Parse again from Preview, then return to Source and start a new document.
    app.post_command(CMD_PREVIEW)
    time.sleep(.2)
    app.post_command(CMD_NEW)
    wait_for(lambda: app.read_path() == "", 20, "New did not clear the path")


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    app = App(ns, exe)
    samples = []
    try:
        time.sleep(.5)
        for index in range(CYCLES):
            for fixture in (SMALL, MAPPED, LARGE):
                cycle(app, fixture)
            samples.append(sample(app))
        early = samples[:4]
        late = samples[-4:]
        growth = {key: max(s[key] for s in late) - max(s[key] for s in early)
                  for key in ("working_set", "private_usage", "handle_count")}
        assert growth["handle_count"] <= 8, growth
        assert growth["private_usage"] <= 8 * 1024 * 1024, growth
        assert growth["working_set"] <= 16 * 1024 * 1024, growth
        result = {
            "schema": 1,
            "candidate_sha256": hashlib.sha256(EXE.read_bytes()).hexdigest(),
            "cycles": CYCLES,
            "opens_per_cycle": 3,
            "early_max": {key: max(s[key] for s in early) for key in growth},
            "late_max": {key: max(s[key] for s in late) for key in growth},
            "growth": growth,
            "arena_capacities": {
                "document": app.read32("document_capacity"),
                "byte": app.read32("byte_capacity"),
                "wide": app.read32("wide_capacity"),
                "render": app.read32("render_arena_capacity"),
            },
            "status": "PASS",
        }
        print(json.dumps(result, indent=2))
        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
