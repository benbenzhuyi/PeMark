#!/usr/bin/env python3
"""Windows matrix for the V8.5.2 shared destructive-transition controller."""
import ctypes as c
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from test_stabilization import load_generator

ROOT = Path(__file__).resolve().parents[1]
# 默认验证开发通道。发布验证可用环境变量指向 src/current 与发布二进制。
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR", ROOT / "src/candidate/generate_markdown_editor_v8_5_2.py"))
EXE = Path(os.environ.get(
    "PEMARK_EXE", ROOT / "bin/candidate/pemark_x64_v8_5_2_candidate.exe"))
WM_COMMAND, WM_SETTEXT, WM_GETTEXT, WM_CLOSE = 0x0111, 0x000C, 0x000D, 0x0010
BM_CLICK, EN_CHANGE = 0x00F5, 0x0300
CMD_NEW, CMD_OPEN, CMD_SAVEAS = 1001, 1002, 1004
u32, k32, psapi = c.windll.user32, c.windll.kernel32, c.windll.psapi

u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.PostMessageW.restype = w.BOOL
u32.WaitForInputIdle.argtypes = [w.HANDLE, w.DWORD]
u32.WaitForInputIdle.restype = w.DWORD
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.OpenProcess.restype = w.HANDLE
k32.ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p,
                                  c.c_size_t, c.POINTER(c.c_size_t)]
k32.ReadProcessMemory.restype = w.BOOL
k32.WriteProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p,
                                   c.c_size_t, c.POINTER(c.c_size_t)]
k32.WriteProcessMemory.restype = w.BOOL
k32.CloseHandle.argtypes = [w.HANDLE]
k32.CloseHandle.restype = w.BOOL
psapi.EnumProcessModules.argtypes = [w.HANDLE, c.POINTER(w.HMODULE),
                                     w.DWORD, c.POINTER(w.DWORD)]
psapi.EnumProcessModules.restype = w.BOOL

def enum_windows(pid, class_name=None, title=None):
    found = []
    @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def visit(hwnd, _):
        window_pid = w.DWORD()
        u32.GetWindowThreadProcessId(hwnd, c.byref(window_pid))
        if window_pid.value != pid:
            return True
        cls, text = c.create_unicode_buffer(64), c.create_unicode_buffer(256)
        u32.GetClassNameW(hwnd, cls, 64)
        u32.GetWindowTextW(hwnd, text, 256)
        if (class_name is None or cls.value == class_name) and \
           (title is None or text.value == title):
            found.append(hwnd)
        return True
    u32.EnumWindows(visit, 0)
    return found


def wait_window(pid, class_name, title=None, timeout=5.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        matches = enum_windows(pid, class_name, title)
        if matches:
            return matches[0]
        time.sleep(.03)
    return 0


def find_edit(main):
    found = []
    @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def visit(hwnd, _):
        cls = c.create_unicode_buffer(32)
        u32.GetClassNameW(hwnd, cls, 32)
        if cls.value.lower() == "edit":
            found.append(hwnd)
        return True
    u32.EnumChildWindows(main, visit, 0)
    return found[0] if found else 0


class App:
    def __init__(self, ns, exe=EXE):
        self.ns, self.bsyms = ns, ns["bsyms"]
        exe = Path(exe)
        self.proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
        assert u32.WaitForInputIdle(w.HANDLE(self.proc._handle), 5000) == 0
        self.main = wait_window(self.proc.pid, "DirectPE_Notepad_Main")
        assert self.main
        deadline = time.perf_counter() + 5
        self.edit = find_edit(self.main)
        while not self.edit and time.perf_counter() < deadline:
            time.sleep(.03)
            self.edit = find_edit(self.main)
        assert self.edit
        self.handle = k32.OpenProcess(0x001F0FFF, False, self.proc.pid)
        assert self.handle
        module, needed = w.HMODULE(), w.DWORD()
        assert psapi.EnumProcessModules(self.handle, c.byref(module),
                                        c.sizeof(module), c.byref(needed))
        self.base = c.cast(module, c.c_void_p).value

    def close_handle(self):
        if self.handle:
            k32.CloseHandle(self.handle)
            self.handle = None
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)

    def revisions(self):
        values = []
        for name in ("document_revision", "saved_revision"):
            value, count = c.c_uint64(), c.c_size_t()
            assert k32.ReadProcessMemory(self.handle,
                c.c_void_p(self.base + self.bsyms[name]), c.byref(value), 8,
                c.byref(count)) and count.value == 8
            values.append(value.value)
        return tuple(values)

    def read32(self, name):
        value, count = w.DWORD(), c.c_size_t()
        assert k32.ReadProcessMemory(self.handle,
            c.c_void_p(self.base + self.bsyms[name]), c.byref(value), 4,
            c.byref(count)) and count.value == 4
        return value.value

    def read64(self, name):
        value, count = c.c_uint64(), c.c_size_t()
        assert k32.ReadProcessMemory(self.handle,
                                     c.c_void_p(self.base + self.bsyms[name]),
                                     c.byref(value), 8, c.byref(count))
        assert count.value == 8
        return value.value

    def write_path(self, path):
        data = (str(path) + "\0").encode("utf-16le")
        count = c.c_size_t()
        source = c.create_string_buffer(data)
        assert k32.WriteProcessMemory(self.handle,
            c.c_void_p(self.base + self.bsyms["current_path"]), source,
            len(data), c.byref(count)) and count.value == len(data)

    def read_path(self):
        raw, count = c.create_string_buffer(1024), c.c_size_t()
        assert k32.ReadProcessMemory(self.handle,
            c.c_void_p(self.base + self.bsyms["current_path"]), raw, 1024,
            c.byref(count)) and count.value == 1024
        return raw.raw.decode("utf-16le").split("\0", 1)[0]

    def set_text_dirty(self, text):
        value = c.create_unicode_buffer(text)
        u32.SendMessageW(self.edit, WM_SETTEXT, 0,
                         c.cast(value, c.c_void_p).value)
        u32.SendMessageW(self.main, WM_COMMAND, (EN_CHANGE << 16) | 1,
                         self.edit)
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline:
            doc, saved = self.revisions()
            if doc != saved:
                return doc, saved
            time.sleep(.02)
        raise AssertionError("edit did not become dirty")

    def text(self):
        buf = c.create_unicode_buffer(1024)
        u32.SendMessageW(self.edit, WM_GETTEXT, len(buf),
                         c.cast(buf, c.c_void_p).value)
        return buf.value

    def post_command(self, command):
        assert u32.PostMessageW(self.main, WM_COMMAND, command, 0)

    def post_close(self):
        assert u32.PostMessageW(self.main, WM_CLOSE, 0, 0)

    def click_dialog(self, title, button_id, timeout=5.0, body_contains=None):
        deadline = time.perf_counter() + timeout
        seen = []
        while time.perf_counter() < deadline:
            for dialog in enum_windows(self.proc.pid, "#32770", title):
                children = []
                @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
                def visit(child, _):
                    label = c.create_unicode_buffer(128)
                    u32.GetWindowTextW(child, label, 128)
                    children.append((u32.GetDlgCtrlID(child), label.value))
                    return True
                u32.EnumChildWindows(dialog, visit, 0)
                seen = children
                if body_contains and not any(body_contains in label
                                             for _, label in children):
                    continue
                button = u32.GetDlgItem(dialog, button_id)
                if button:
                    u32.SendMessageW(button, BM_CLICK, 0, 0)
                    return
            time.sleep(.03)
        raise AssertionError(f"button {button_id} not found in dialog: {title}; "
                             f"seen control IDs={seen}, exit={self.proc.poll()}")

    def wait_dialog_closed(self, title, timeout=5.0):
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            if not enum_windows(self.proc.pid, "#32770", title):
                return
            time.sleep(.03)
        raise AssertionError(f"dialog did not close: {title}")

def scenario_clean_close(ns):
    app = App(ns)
    try:
        app.post_close()
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def scenario_close_cancel_discard(ns):
    app = App(ns)
    try:
        before = app.set_text_dirty("close cancel sentinel\r\n")
        app.post_close(); app.click_dialog("PeMark", 2)  # IDCANCEL
        time.sleep(.1)
        assert app.proc.poll() is None and app.revisions() == before
        assert app.text() == "close cancel sentinel\r\n"
        app.post_close(); app.click_dialog("PeMark", 7)  # IDNO / Discard
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def scenario_new_cancel_discard(ns):
    app = App(ns)
    try:
        before = app.set_text_dirty("new cancel sentinel\r\n")
        app.post_command(CMD_NEW); app.click_dialog("PeMark", 2)
        time.sleep(.1)
        assert app.revisions() == before and app.text() == "new cancel sentinel\r\n"
        app.post_command(CMD_NEW); app.click_dialog("PeMark", 7)
        deadline = time.perf_counter() + 3
        while time.perf_counter() < deadline and app.text():
            time.sleep(.02)
        doc, saved = app.revisions()
        assert app.text() == "" and doc == saved and doc > before[0]
        app.post_close(); assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def scenario_open_cancel(ns):
    app = App(ns)
    try:
        before = app.set_text_dirty("open cancel sentinel\r\n")
        app.post_command(CMD_OPEN); app.click_dialog("PeMark", 2)
        time.sleep(.1)
        assert app.revisions() == before and app.text() == "open cancel sentinel\r\n"
        app.post_command(CMD_OPEN); app.click_dialog("PeMark", 7)
        app.click_dialog("Open Markdown or text file", 2)  # picker Cancel
        app.wait_dialog_closed("Open Markdown or text file")
        assert app.revisions() == before and app.text() == "open cancel sentinel\r\n"
        app.post_close(); app.click_dialog("PeMark", 7)
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def scenario_save_then_close_or_new(ns, target, command,
                                    text="saved through controller\r\n"):
    app = App(ns)
    try:
        app.write_path(target)
        app.set_text_dirty(text)
        if command == WM_CLOSE:
            app.post_close()
        else:
            app.post_command(command)
        app.click_dialog("PeMark", 6)  # IDYES / Save
        if command == WM_CLOSE:
            assert app.proc.wait(timeout=5) == 0
        else:
            deadline = time.perf_counter() + 3
            while time.perf_counter() < deadline and app.text():
                time.sleep(.02)
            doc, saved = app.revisions()
            assert app.text() == "" and doc == saved
            app.post_close(); assert app.proc.wait(timeout=5) == 0
        assert target.read_bytes() == text.encode("utf-8")
    finally:
        app.close_handle()


def scenario_save_failure_cancels_close(ns, invalid_target):
    app = App(ns)
    try:
        app.write_path(invalid_target)
        before = app.set_text_dirty("must survive failed save\r\n")
        app.post_close(); app.click_dialog("PeMark", 6)
        app.click_dialog("PeMark", 2, body_contains="Could not save")
        time.sleep(.1)
        assert app.proc.poll() is None
        assert app.revisions() == before and app.text() == "must survive failed save\r\n"
        assert app.read32("pending_destructive_action") == 0
        app.post_close(); app.click_dialog("PeMark", 7)
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def scenario_saveas_cancel_preserves_path(ns, old_path):
    app = App(ns)
    try:
        app.write_path(old_path)
        before = app.set_text_dirty("save as transaction\r\n")
        app.post_command(CMD_SAVEAS)
        app.click_dialog("Save Markdown file as", 2)
        time.sleep(.1)
        assert app.read_path() == str(old_path) and app.revisions() == before

        app.post_close(); app.click_dialog("PeMark", 7)
        assert app.proc.wait(timeout=5) == 0
    finally:
        app.close_handle()


def main():
    ns = load_generator(GEN)
    scenario_clean_close(ns)
    scenario_close_cancel_discard(ns)
    scenario_new_cancel_discard(ns)
    scenario_open_cancel(ns)
    with tempfile.TemporaryDirectory(prefix="pemark-v852-") as temp:
        root = Path(temp)
        scenario_save_then_close_or_new(ns, root / "close-save.md", WM_CLOSE)
        scenario_save_then_close_or_new(ns, root / "new-save.md", CMD_NEW)
        large_text = ("0123456789abcdef" * 32768) + "\r\n"
        scenario_save_then_close_or_new(ns, root / "large-save.md", CMD_NEW,
                                        large_text)
        scenario_save_failure_cancels_close(ns, root / "missing" / "fail.md")
        scenario_saveas_cancel_preserves_path(ns, root / "old.md")
    print("PASS destructive matrix: clean close; Close Cancel/Discard/Save; "
          "New Cancel/Discard/Save; Open decision Cancel and picker Cancel; "
          "failed Save preserves dirty document and cancels Close; Save As "
          "cancel preserves the original path; 512 KiB save bytes match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
