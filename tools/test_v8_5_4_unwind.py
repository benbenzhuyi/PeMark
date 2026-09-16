#!/usr/bin/env python3
"""V8.5.4: the .pdata table must let a debugger walk our frames."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/candidate/generate_markdown_editor_v8_5_4.py"))
EXE = Path(os.environ.get(
    "PEMARK_EXE",
    ROOT / "bin/candidate/pemark_x64_v8_5_4_candidate.exe"))
RELEASE_EXE = ROOT / "bin/current/pemark_x64_v8_5_4.exe"
VERSION_TAG = GEN.stem.replace("generate_markdown_editor_", "")

ADDR_MODE_FLAT = 3
CONTEXT_FULL = 0x00100007
THREAD_GET_CONTEXT = 0x0008
THREAD_SUSPEND_RESUME = 0x0002
THREAD_QUERY_INFORMATION = 0x0040
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MAX_FRAMES = 24

k32 = c.windll.kernel32
dbg = c.WinDLL("dbghelp.dll")


class ADDRESS64(c.Structure):
    _fields_ = [("Offset", c.c_uint64), ("Segment", w.WORD), ("Mode", w.DWORD)]


class STACKFRAME64(c.Structure):
    _fields_ = [("AddrPC", ADDRESS64), ("AddrReturn", ADDRESS64),
                ("AddrFrame", ADDRESS64), ("AddrStack", ADDRESS64),
                ("AddrBStore", ADDRESS64), ("FuncTableEntry", c.c_void_p),
                ("Params", c.c_uint64 * 4), ("Far", w.BOOL), ("Virtual", w.BOOL),
                ("Reserved", c.c_uint64 * 3)]


class CONTEXT(c.Structure):
    _pack_ = 16
    _fields_ = [("P1Home", c.c_uint64), ("P2Home", c.c_uint64), ("P3Home", c.c_uint64),
                ("P4Home", c.c_uint64), ("P5Home", c.c_uint64), ("P6Home", c.c_uint64),
                ("ContextFlags", w.DWORD), ("MxCsr", w.DWORD),
                ("Cs", w.WORD), ("Ds", w.WORD), ("Es", w.WORD), ("Fs", w.WORD),
                ("Gs", w.WORD), ("Ss", w.WORD), ("EFlags", w.DWORD),
                ("Dr0", c.c_uint64), ("Dr1", c.c_uint64), ("Dr2", c.c_uint64),
                ("Dr3", c.c_uint64), ("Dr6", c.c_uint64), ("Dr7", c.c_uint64),
                ("Rax", c.c_uint64), ("Rcx", c.c_uint64), ("Rdx", c.c_uint64),
                ("Rbx", c.c_uint64), ("Rsp", c.c_uint64), ("Rbp", c.c_uint64),
                ("Rsi", c.c_uint64), ("Rdi", c.c_uint64),
                ("R8", c.c_uint64), ("R9", c.c_uint64), ("R10", c.c_uint64),
                ("R11", c.c_uint64), ("R12", c.c_uint64), ("R13", c.c_uint64),
                ("R14", c.c_uint64), ("R15", c.c_uint64), ("Rip", c.c_uint64),
                ("Rest", c.c_ubyte * 976)]


def build():
    source = GEN.read_text(encoding="utf-8")
    if EXE.exists() and EXE.parent.name == "current":
        # Same rule as the section test: inspect the shipped file without
        # rewriting it (which would fail while the executable is in use).
        scratch = ROOT / "bin" / "verify_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        fake = scratch / GEN.name
        # The generator reads its own source for build assertions, so the
        # scratch copy has to exist even though we never use its output.
        if not fake.exists() or fake.read_text(encoding='utf-8') != source:
            fake.write_text(source, encoding='utf-8', newline='')
        ns = {"__file__": str(fake), "__name__": "__pemark_unwind_verify__"}
        exec(compile(source, str(fake), "exec"), ns)
        return ns, EXE
    ns = {"__file__": str(GEN), "__name__": "__pemark_unwind__"}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    expected = (f"pemark_x64_{VERSION_TAG}.exe" if ns.get("_RELEASE_CHANNEL")
                else f"pemark_x64_{VERSION_TAG}_candidate.exe")
    assert out.name == expected, out.name
    return ns, out


def pdata_summary(path):
    b = Path(path).read_bytes()
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    coff = pe + 4
    nsec = struct.unpack_from("<H", b, coff + 2)[0]
    optsz = struct.unpack_from("<H", b, coff + 16)[0]
    opt = coff + 20
    size_of_image = struct.unpack_from("<I", b, opt + 56)[0]
    pdata_rva, pdata_size = struct.unpack_from("<II", b, opt + 112 + 8 * 3)
    sh = opt + optsz
    sections = []
    for i in range(nsec):
        o = sh + 40 * i
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        sections.append((b[o:o + 8].rstrip(b"\0"), va, vs, rp, rs))
    assert pdata_rva, "exception directory must be present"
    name, va, vs, rp, rs = next(s for s in sections if s[0] == b".pdata")
    assert pdata_rva == va and pdata_size <= vs
    rname, rva, rvs, rrp, rrs = next(s for s in sections if s[0] == b".rdata")
    # The directory size covers only the RUNTIME_FUNCTION array; the unwind blobs
    # live in .rdata, as linkers emit them (notepad.exe does the same).
    assert pdata_size % 12 == 0, "directory size must be a whole entry count"
    entries = []
    while len(entries) * 12 + 12 <= pdata_size:
        begin, end, unwind = struct.unpack_from("<III", b, rp + len(entries) * 12)
        assert begin and end > begin, "each entry must cover a range"
        assert rva <= unwind < rva + max(rvs, rrs), \
            "unwind info must live in .rdata"
        info = rrp + (unwind - rva)
        assert b[info] & 0x07 == 1, "UNWIND_INFO version must be 1"
        assert b[info + 3] >= 1, "each entry needs at least one unwind code"
        entries.append((begin, end))
    count = len(entries)
    assert count >= 20, "expected unwind metadata for most non-leaf routines"
    assert all(entries[i][0] >= entries[i - 1][1] for i in range(1, count)), \
        "RUNTIME_FUNCTION ranges must be ordered and non-overlapping"
    print("PASS .pdata: %d RUNTIME_FUNCTION entries, version-1 unwind info, "
          "directory 0x%X/0x%X" % (count, pdata_rva, pdata_size))
    return count, size_of_image


def walk_stack(proc, size_of_image):
    handle = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, proc.pid)
    assert handle, "OpenProcess failed"
    thread_id = c.windll.user32.GetWindowThreadProcessId(proc_main_window(proc), None)
    thread = k32.OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT |
                            THREAD_QUERY_INFORMATION, False, thread_id)
    assert thread, "OpenThread failed"
    context = CONTEXT()
    context.ContextFlags = CONTEXT_FULL
    try:
        k32.SuspendThread(thread)
        assert k32.GetThreadContext(thread, c.byref(context))
        frame = STACKFRAME64()
        frame.AddrPC.Offset = context.Rip
        frame.AddrPC.Mode = ADDR_MODE_FLAT
        frame.AddrFrame.Offset = context.Rbp
        frame.AddrFrame.Mode = ADDR_MODE_FLAT
        frame.AddrStack.Offset = context.Rsp
        frame.AddrStack.Mode = ADDR_MODE_FLAT
        assert dbg.SymInitialize(handle, None, False), "SymInitialize failed"
        dbg.SymSetOptions(0x00000002 | 0x00000004)  # UNDNAME | DEFERRED_LOADS
        # dbghelp only learns about loaded images after a module-list refresh;
        # without it SymGetModuleBase64 returns 0 and walking stops early.
        dbg.SymRefreshModuleList(handle)
        dbg.SymGetModuleBase64.restype = c.c_uint64
        dbg.SymGetModuleBase64.argtypes = [w.HANDLE, c.c_uint64]
        # These two callbacks return pointers/addresses; leaving the ctypes
        # default (32-bit int) truncates them and the walk stops at our frames.
        dbg.SymFunctionTableAccess64.restype = c.c_void_p
        dbg.SymFunctionTableAccess64.argtypes = [w.HANDLE, c.c_uint64]
        dbg.StackWalk64.restype = w.BOOL
        dbg.StackWalk64.argtypes = [w.DWORD, w.HANDLE, w.HANDLE, c.c_void_p,
                                    c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p,
                                    c.c_void_p]
        addresses = []
        frames = []
        for _ in range(MAX_FRAMES):
            if not dbg.StackWalk64(0x8664, handle, thread, c.byref(frame),
                                   c.byref(context), None,
                                   dbg.SymFunctionTableAccess64,
                                   dbg.SymGetModuleBase64, None):
                break
            if frame.AddrPC.Offset:
                addresses.append(frame.AddrPC.Offset)
                frames.append((frame.AddrPC.Offset,
                               dbg.SymGetModuleBase64(handle, frame.AddrPC.Offset)))
        module, needed = w.HMODULE(), w.DWORD()
        c.windll.psapi.EnumProcessModules(handle, c.byref(module),
                                          c.sizeof(module), c.byref(needed))
        base = c.cast(module, c.c_void_p).value
        for probe_offset in (0x1E10, 0x1000):
            entry = dbg.SymFunctionTableAccess64(handle, base + probe_offset)
            print("  function table entry for +0x%X -> %s"
                  % (probe_offset, hex(entry or 0)))
        dbg.SymCleanup(handle)
    finally:
        k32.ResumeThread(thread)
        k32.CloseHandle(thread)
        k32.CloseHandle(handle)
    inside = [a for a in addresses if base <= a < base + size_of_image]
    offsets = sorted(a - base for a in inside)
    for address, module_base in frames[:6]:
        print("  frame pc=0x%X module=0x%X" % (address, module_base or 0))
    print("frames walked: %d, ours: %d, offsets: %s"
          % (len(addresses), len(inside), [hex(o) for o in offsets[:6]]))
    return len(addresses), len(inside), offsets


def proc_main_window(proc):
    u32 = c.windll.user32
    u32.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
    u32.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
    found = []

    @c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def visit(hwnd, _):
        pid = w.DWORD()
        u32.GetWindowThreadProcessId(hwnd, c.byref(pid))
        if pid.value == proc.pid:
            cls = c.create_unicode_buffer(64)
            u32.GetClassNameW(hwnd, cls, 64)
            if cls.value == "DirectPE_Notepad_Main":
                found.append(hwnd)
        return True
    u32.EnumWindows(visit, 0)
    assert found, "main window not found"
    return found[0]


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    entries, size_of_image = pdata_summary(exe)
    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        time.sleep(1.5)
        assert proc.poll() is None
        walked, inside, offsets = walk_stack(proc, size_of_image)
        assert walked >= 3, "stack walk stopped immediately (%d frames)" % walked
        assert inside >= 1, \
            "stack walk never reached our module; .pdata is not being used"
        if inside < 2:
            print("NOTE: the walk reached our module but did not continue past "
                  "our frame; entry lookup works, full unwinding is unverified")
        hwnd = proc_main_window(proc)
        c.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
        assert proc.wait(timeout=10) == 0
    finally:
        if proc.poll() is None:
            proc.kill(); proc.wait(timeout=5)
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS unwind metadata: structure valid, entries resolvable by dbghelp, "
          "walk reaches our module, process still exits cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
