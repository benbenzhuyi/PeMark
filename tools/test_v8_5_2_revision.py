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
PREFERRED_IMAGE_BASE = 0x140000000
WM_COMMAND, WM_SETTEXT, WM_CLOSE = 0x0111, 0x000C, 0x0010
EN_CHANGE, CMD_NEW = 0x0300, 1001
u32, k32 = c.windll.user32, c.windll.kernel32
psapi = c.windll.psapi
u32.FindWindowW.argtypes = [w.LPCWSTR, w.LPCWSTR]
u32.FindWindowW.restype = w.HWND
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.OpenProcess.restype = w.HANDLE
k32.ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p,
                                  c.c_size_t, c.POINTER(c.c_size_t)]
k32.ReadProcessMemory.restype = w.BOOL
k32.CreateRemoteThread.argtypes = [w.HANDLE, c.c_void_p, c.c_size_t,
                                    c.c_void_p, c.c_void_p, w.DWORD,
                                    c.POINTER(w.DWORD)]
k32.CreateRemoteThread.restype = w.HANDLE
k32.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
k32.WaitForSingleObject.restype = w.DWORD
k32.GetExitCodeThread.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
k32.GetExitCodeThread.restype = w.BOOL
k32.CloseHandle.argtypes = [w.HANDLE]
k32.CloseHandle.restype = w.BOOL
psapi.EnumProcessModules.argtypes = [w.HANDLE, c.POINTER(w.HMODULE),
                                     w.DWORD, c.POINTER(w.DWORD)]
psapi.EnumProcessModules.restype = w.BOOL


def wait_main(pid):
    for _ in range(100):
        matches = []
        @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        def visit(hwnd, _):
            window_pid = w.DWORD()
            u32.GetWindowThreadProcessId(hwnd, c.byref(window_pid))
            if window_pid.value == pid:
                name = c.create_unicode_buffer(64)
                u32.GetClassNameW(hwnd, name, 64)
                if name.value == "DirectPE_Notepad_Main":
                    matches.append(hwnd)
            return True
        u32.EnumWindows(visit, 0)
        if matches:
            return matches[0]
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


def wait_edit(main, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        hwnd = find_edit(main)
        if hwnd:
            return hwnd
        time.sleep(.05)
    return 0


def main():
    ns = load_generator(GEN)
    bsyms = ns["bsyms"]
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
    main_hwnd = wait_main(proc.pid)
    if not main_hwnd:
        proc.kill(); raise AssertionError("main window not found")
    access = 0x001F0FFF
    handle = k32.OpenProcess(access, False, proc.pid)
    if not handle:
        proc.kill(); raise c.WinError(c.get_last_error())
    module, needed = w.HMODULE(), w.DWORD()
    if not psapi.EnumProcessModules(handle, c.byref(module), c.sizeof(module),
                                    c.byref(needed)):
        proc.kill(); raise c.WinError(c.get_last_error())
    image_base = c.cast(module, c.c_void_p).value
    assert image_base == PREFERRED_IMAGE_BASE, \
        f"unexpected image base: 0x{image_base:X}"
    def read64(name):
        value, count = c.c_uint64(), c.c_size_t()
        ok = k32.ReadProcessMemory(handle, c.c_void_p(image_base + bsyms[name]),
                                   c.byref(value), 8, c.byref(count))
        if not ok:
            raise c.WinError(c.get_last_error())
        assert count.value == 8, f"short read for {name}: {count.value}"
        return value.value
    def expect(expected, stage):
        actual = (read64("document_revision"), read64("saved_revision"))
        assert actual == expected, f"{stage}: expected {expected}, got {actual}"
    def wait_expect(expected, stage, timeout=3.0):
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            actual = (read64("document_revision"), read64("saved_revision"))
            if actual == expected:
                return
            time.sleep(.02)
        expect(expected, stage)
    def run_remote(label):
        address = image_base + ns["TEXT_RVA"] + ns["em"].labels[label]
        thread_id = w.DWORD()
        thread = k32.CreateRemoteThread(handle, None, 0, c.c_void_p(address),
                                        None, 0, c.byref(thread_id))
        if not thread:
            raise c.WinError(c.get_last_error())
        try:
            if k32.WaitForSingleObject(thread, 5000) != 0:
                raise RuntimeError(f"remote helper timeout: {label}")
            exit_code = w.DWORD()
            if not k32.GetExitCodeThread(thread, c.byref(exit_code)):
                raise c.WinError(c.get_last_error())
            return exit_code.value
        finally:
            k32.CloseHandle(thread)
    try:
        edit = wait_edit(main_hwnd)
        assert edit, "edit control not ready"
        expect((0, 0), "initial")
        helper_result = run_remote("advance_document_revision")
        assert helper_result == 1, f"advance helper returned {helper_result}"
        expect((1, 0), "direct advance helper")
        run_remote("commit_clean_document")
        expect((2, 2), "open commit")
        changed = c.c_wchar_p("# changed\r\n")
        u32.SendMessageW(edit, WM_SETTEXT, 0, c.cast(changed, c.c_void_p).value)
        u32.SendMessageW(main_hwnd, WM_COMMAND, (EN_CHANGE << 16) | 1, edit)
        time.sleep(.2)
        expect((3, 2), "edit")
        u32.SendMessageW(main_hwnd, WM_COMMAND, (EN_CHANGE << 16) | 1, edit)
        time.sleep(.2)
        expect((4, 2), "second edit")
        run_remote("mark_document_saved")
        wait_expect((4, 4), "save commit")
        u32.SendMessageW(main_hwnd, WM_COMMAND, CMD_NEW, 0)
        time.sleep(.2)
        expect((5, 5), "new")
        u32.PostMessageW(main_hwnd, WM_CLOSE, 0, 0)
        assert proc.wait(timeout=5) == 0
        print("PASS revision ownership: initial=(0,0), edit=(1,0), "
              "open=(2,2), edit=(3,2), second-edit=(4,2), "
              "save=(4,4), new=(5,5), exit=0")
    finally:
        k32.CloseHandle(handle)
        if proc.poll() is None:
            proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
