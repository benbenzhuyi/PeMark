"""Windows runtime regression for the V8.6.3 GDI-scaled DPI context."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXE = Path(os.environ.get(
    "PEMARK_EXE", ROOT / "bin" / "candidate" / "pemark_x64_v8_6_candidate.exe"
))
CLASS_MAIN = "DirectPE_Notepad_Main"
UNAWARE_GDISCALED = ctypes.c_void_p(-5 & 0xFFFFFFFFFFFFFFFF)

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                            ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowDpiAwarenessContext.argtypes = [wintypes.HWND]
user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
user32.AreDpiAwarenessContextsEqual.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.AreDpiAwarenessContextsEqual.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL


def find_window(pid: int, timeout: float = 8.0) -> int:
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                       wintypes.LPARAM)
    matches: list[int] = []

    def callback(hwnd: int, _: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            class_name = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, class_name, len(class_name))
            if class_name.value == CLASS_MAIN:
                matches.append(int(hwnd))
                return False
        return True

    callback_fn = callback_type(callback)
    deadline = time.time() + timeout
    while time.time() < deadline:
        matches.clear()
        user32.EnumWindows(callback_fn, 0)
        if matches:
            return matches[0]
        time.sleep(0.05)
    raise AssertionError("candidate did not create its main window")


def main() -> int:
    process = subprocess.Popen([str(EXE)], cwd=EXE.parent)
    try:
        hwnd = find_window(process.pid)
        context = user32.GetWindowDpiAwarenessContext(hwnd)
        assert context, "GetWindowDpiAwarenessContext failed"
        assert user32.AreDpiAwarenessContextsEqual(
            ctypes.c_void_p(context), UNAWARE_GDISCALED
        ), f"unexpected DPI awareness context: {context!r}"
        print("PASS DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED")
        assert user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        assert process.wait(timeout=5) == 0
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
