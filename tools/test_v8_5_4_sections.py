#!/usr/bin/env python3
"""V8.5.4: section separation must hold on disk and in the loaded image."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
from pathlib import Path
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "src/candidate/generate_markdown_editor_v8_5_4.py"
EXE = ROOT / "bin/candidate/pemark_x64_v8_5_4_candidate.exe"
RELEASE_EXE = ROOT / "bin/current/pemark_x64_v8_5_3.exe"

SCN_EXECUTE = 0x20000000
SCN_READ = 0x40000000
SCN_WRITE = 0x80000000
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40

EXPECTED = [
    (b".text", 0x1000, 0xF000, 0x400, 0xF000, SCN_EXECUTE | SCN_READ | 0x20),
    (b".rdata", 0x10000, 0x3000, 0xF400, 0x3000, SCN_READ | 0x40),
    (b".idata", 0x13000, 0x1000, 0x12400, 0x1000, SCN_READ | SCN_WRITE | 0x40),
    (b".bss", 0x14000, 0x2000, 0x0, 0x0, SCN_READ | SCN_WRITE | 0x80),
    (b".reloc", 0x16000, 0x200, 0x15400, 0x200, SCN_READ | 0x02000000 | 0x40),
]
EXPECTED_PROTECT = [PAGE_EXECUTE_READ, PAGE_READONLY, PAGE_READWRITE, PAGE_READWRITE,
                    PAGE_READONLY]
PREFERRED_IMAGE_BASE = 0x140000000

u32, k32 = c.windll.user32, c.windll.kernel32
k32.VirtualQueryEx.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t]
k32.VirtualQueryEx.restype = c.c_size_t
u32.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
u32.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
u32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.OpenProcess.restype = w.HANDLE


class MEMORY_BASIC_INFORMATION(c.Structure):
    _fields_ = [("BaseAddress", c.c_void_p), ("AllocationBase", c.c_void_p),
                ("AllocationProtect", w.DWORD), ("RegionSize", c.c_size_t),
                ("State", w.DWORD), ("Protect", w.DWORD), ("Type", w.DWORD)]


def build():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_sections__"}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == "pemark_x64_v8_5_4_candidate.exe", out.name
    return ns, out


def parse_sections(path):
    b = Path(path).read_bytes()
    assert b[:2] == b"MZ"
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    assert b[pe:pe + 4] == b"PE\0\0"
    coff = pe + 4
    nsec = struct.unpack_from("<H", b, coff + 2)[0]
    optsz = struct.unpack_from("<H", b, coff + 16)[0]
    size_of_headers = struct.unpack_from("<I", b, coff + 20 + 60)[0]
    size_of_image = struct.unpack_from("<I", b, coff + 20 + 56)[0]
    image_base = struct.unpack_from("<Q", b, coff + 20 + 24)[0]
    dll_chars = struct.unpack_from("<H", b, coff + 20 + 70)[0]
    reloc_rva, reloc_size = struct.unpack_from("<II", b, coff + 20 + 112 + 8 * 5)
    sh = coff + 20 + optsz
    sections = []
    for i in range(nsec):
        o = sh + 40 * i
        name = b[o:o + 8].rstrip(b"\0")
        vs, va, rs, rp = struct.unpack_from("<IIII", b, o + 8)
        chars = struct.unpack_from("<I", b, o + 36)[0]
        sections.append((name, va, vs, rp, rs, chars))
    return {"sections": sections, "headers": size_of_headers, "image": size_of_image,
            "filesize": len(b), "image_base": image_base, "dll_chars": dll_chars,
            "reloc": (reloc_rva, reloc_size), "blob": b}


def on_disk(structure):
    sections, headers, image, filesize = (structure["sections"], structure["headers"],
                                          structure["image"], structure["filesize"])
    assert len(sections) == len(EXPECTED), "expected four sections"
    raw_end = headers
    for (name, va, vs, rp, rs, chars), (en, eva, evs, erp, ers, echars) in zip(sections, EXPECTED):
        assert name == en, (name, en)
        assert (va, vs, rp, rs) == (eva, evs, erp, ers), (name, va, vs, rp, rs)
        assert chars == echars, (name, hex(chars))
        assert not (chars & SCN_WRITE and chars & SCN_EXECUTE), \
            "%s must not be writable and executable" % name.decode()
        assert rp % 0x200 == 0 and va % 0x1000 == 0
        if rs:
            assert rp >= headers, name.decode()
            assert rp >= raw_end, "%s raw data overlaps" % name.decode()
            assert rp + rs <= filesize, "%s raw data exceeds the file" % name.decode()
            raw_end = rp + rs
        else:
            assert name == b".bss"
    assert image >= EXPECTED[-1][1] + EXPECTED[-1][2]
    # ASLR metadata: DYNAMIC_BASE plus a relocation table that tiles every page.
    assert structure["image_base"] == PREFERRED_IMAGE_BASE
    assert structure["dll_chars"] & 0x0040, "DYNAMIC_BASE must be declared"
    reloc_rva, reloc_size = structure["reloc"]
    assert (reloc_rva, reloc_size) == (EXPECTED[-1][1], reloc_size)
    assert reloc_size >= 12 and reloc_size % 4 == 0
    blob, cursor, blocks = structure["blob"], 0, 0
    file_off = sections[-1][3]
    while cursor < reloc_size:
        page, block = struct.unpack_from("<II", blob, file_off + cursor)
        assert block >= 12 and block % 4 == 0
        assert page % 0x1000 == 0
        entries = (block - 8) // 2
        for i in range(entries):
            value = struct.unpack_from("<H", blob, file_off + cursor + 8 + i * 2)[0]
            assert (value >> 12) == 0, "only ABSOLUTE entries are valid here"
        cursor += block
        blocks += 1
    assert cursor == reloc_size
    assert blocks == (0x16000 - 0x1000) // 0x1000
    print("PASS section table: 5 sections, RX/R/RW/RW/R, no W+X, relocation "
          "table covers every image page")


def loaded(struct_ns):
    ns, exe = struct_ns
    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        time.sleep(1.2)
        assert proc.poll() is None, "process exited early"
        handle = k32.OpenProcess(0x0410, False, proc.pid)  # QUERY_INFORMATION | VM_READ
        assert handle
        try:
            module, needed = w.HMODULE(), w.DWORD()
            assert c.windll.psapi.EnumProcessModules(
                handle, c.byref(module), c.sizeof(module), c.byref(needed))
            base = c.cast(module, c.c_void_p).value
            assert base != PREFERRED_IMAGE_BASE, \
                "DYNAMIC_BASE image loaded at its preferred base; ASLR is not active"
            for (name, va, vs, rp, rs, chars), expected in zip(EXPECTED, EXPECTED_PROTECT):
                mbi = MEMORY_BASIC_INFORMATION()
                assert k32.VirtualQueryEx(handle, c.c_void_p(base + va),
                                          c.byref(mbi), c.sizeof(mbi))
                protect = mbi.Protect
                assert protect == expected, \
                    "%s loaded with protection 0x%02X, expected 0x%02X" % (
                        name.decode(), protect, expected)
                assert protect != PAGE_EXECUTE_READWRITE, \
                    "%s must not be a writable executable page" % name.decode()
        finally:
            k32.CloseHandle(handle)
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
        assert found, "split image did not create its main window"
        u32.PostMessageW(found[0], 0x0010, 0, 0)
        assert proc.wait(timeout=10) == 0
    finally:
        if proc.poll() is None:
            proc.kill(); proc.wait(timeout=5)
    print("PASS loaded image: RX code, R rdata, RW idata/bss, clean windowed exit")


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    structure = parse_sections(exe)
    on_disk(structure)
    loaded((ns, exe))
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS released V8.5.3 binary unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
