#!/usr/bin/env python3
"""Capture repeatable V8.5.1 launch/resource/close baseline on Windows."""
import argparse
import ctypes
from ctypes import wintypes
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time

WM_CLOSE = 0x0010
CLASS_MAIN = "DirectPE_Notepad_Main"
user32 = ctypes.windll.user32


def percentile(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def wait_window(timeout=8.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        hwnd = user32.FindWindowW(CLASS_MAIN, None)
        if hwnd:
            return hwnd
        time.sleep(0.005)
    return 0


def process_memory(pid):
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    k32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    handle = k32.OpenProcess(0x0410, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        pmc = PMC(); pmc.cb = ctypes.sizeof(pmc)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        handles = wintypes.DWORD()
        if not k32.GetProcessHandleCount(handle, ctypes.byref(handles)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {"working_set": pmc.WorkingSetSize,
                "peak_working_set": pmc.PeakWorkingSetSize,
                "private_commit": pmc.PagefileUsage,
                "handle_count": handles.value}
    finally:
        k32.CloseHandle(handle)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe", nargs="?", default="bin/current/pemark_x64_v8_5_1.exe")
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--idle-ms", type=int, default=250)
    ap.add_argument("--output", default="tests/results/v8_5_1_baseline.json")
    args = ap.parse_args()
    if args.runs < 1:
        ap.error("--runs must be positive")
    exe = Path(args.exe).resolve()
    samples = []
    for index in range(args.runs):
        started = time.perf_counter_ns()
        proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
        hwnd = wait_window()
        interactive = time.perf_counter_ns()
        if not hwnd:
            proc.kill(); raise RuntimeError(f"run {index + 1}: main window timeout")
        time.sleep(args.idle_ms / 1000)
        resources = process_memory(proc.pid)
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        rc = proc.wait(timeout=5)
        samples.append({"run": index + 1,
                        "launch_to_window_ms": (interactive - started) / 1_000_000,
                        "exit_code": rc, **resources})
    launches = [x["launch_to_window_ms"] for x in samples]
    def median_field(name):
        return statistics.median(x[name] for x in samples)

    result = {
        "schema": 1,
        "kind": "PeMark V8.5.1 pre-V8.5.2 baseline",
        "environment": {"platform": platform.platform(),
                        "processor": platform.processor(),
                        "machine": platform.machine(),
                        "logical_cpus": os.cpu_count()},
        "artifact": {"path": str(exe.relative_to(Path.cwd())),
                     "size": exe.stat().st_size,
                     "sha256": sha256(exe.read_bytes()).hexdigest()},
        "protocol": {"runs": args.runs, "idle_ms": args.idle_ms,
                     "classification": "warm/mixed; OS cache not flushed"},
        "summary": {"launch_ms_p50": statistics.median(launches),
                    "launch_ms_p95": percentile(launches, .95),
                    "launch_ms_p99": percentile(launches, .99),
                    "working_set_median": median_field("working_set"),
                    "peak_working_set_median": median_field("peak_working_set"),
                    "private_commit_median": median_field("private_commit"),
                    "handle_count_median": median_field("handle_count"),
                    "all_exit_zero": all(x["exit_code"] == 0 for x in samples)},
        "samples": samples,
        "validity_limits": ["FindWindow marks window creation, not first painted frame",
                            "This initial script captures launch/idle/close only"]}
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
