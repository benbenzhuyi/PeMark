#!/usr/bin/env python3
"""Windows runtime regression for V8.5.2 revision ownership."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import subprocess
import sys
import time

from test_stabilization import load_generator

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "src/candidate/generate_markdown_editor_v8_5_2.py"
EXE = ROOT / "bin/candidate/pemark_x64_v8_5_2_candidate.exe"
IMAGE_BASE = 0x140000000
WM_COMMAND, WM_SETTEXT, WM_CLOSE = 0x0111, 0x000C, 0x0010
EN_CHANGE, CMD_NEW = 0x0300, 1001
u32, k32 = c.windll.user32, c.windll.kernel32


def wait_main():
    for _ in range(100):
        hwnd = u32.FindWindowW("DirectPE_Notepad_Main", None)
        if hwnd:
            return hwnd
        time.sleep(.05)
    return 0


def find_edit(main):
    result = []
    @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def visit(hwnd, _):
        name = c.create_unicode_buffer(32)
        u32.GetClassNameW(hwnd, name, 32)
        if name.value.lower() == "edit":
            result.append(hwnd)
        return True
    u32.EnumChildWindows(main, visit, 0)
    return result[0] if result else 0


def main():
    ns = load_generator(GEN)
    bsyms = ns["bsyms"]
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
    main_hwnd = wait_main()
    if not main_hwnd:
        proc.kill(); raise AssertionError("main window not found")
    access = 0x1010
    handle = k32.OpenProcess(access, False, proc.pid)
    if not handle:
        proc.kill(); raise c.WinError(c.get_last_error())
    def read32(name):
        value, count = w.DWORD(), c.c_size_t()
        ok = k32.ReadProcessMemory(handle, c.c_void_p(IMAGE_BASE + bsyms[name]),
                                   c.byref(value), 4, c.byref(count))
        if not ok:
            raise c.WinError(c.get_last_error())
        return value.value
    try:
        assert (read32("document_revision"), read32("saved_revision")) == (0, 0)
        edit = find_edit(main_hwnd)
        assert edit
        u32.SendMessageW(edit, WM_SETTEXT, 0, "# changed\r\n")
        u32.SendMessageW(main_hwnd, WM_COMMAND, (EN_CHANGE << 16) | 1, edit)
        time.sleep(.2)
        assert (read32("document_revision"), read32("saved_revision")) == (1, 0)
        u32.SendMessageW(main_hwnd, WM_COMMAND, CMD_NEW, 0)
        time.sleep(.2)
        assert (read32("document_revision"), read32("saved_revision")) == (2, 2)
        u32.PostMessageW(main_hwnd, WM_CLOSE, 0, 0)
        assert proc.wait(timeout=5) == 0
        print("PASS revision ownership: initial=(0,0), edit=(1,0), new=(2,2), exit=0")
    finally:
        k32.CloseHandle(handle)
        if proc.poll() is None:
            proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())

