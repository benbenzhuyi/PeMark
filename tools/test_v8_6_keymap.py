#!/usr/bin/env python3
"""V8.6 keymap: the shipped accelerator table and menu hints agree with Rabbit.

The accelerator table is emitted into the binary, so this test parses the table
out of the running process instead of trusting the generator source, and it also
reads the menu strings from the image to prove the hints a user sees match the
keys that actually work.
"""
import ctypes as c
import hashlib
import os
import struct
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v8_5_2_destructive import App
from test_v8_5_2_open_encoding import write_wstr
from test_v8_6_panel import build, wait_for

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/current/generate_markdown_editor_v8_6_4.py"))
RELEASE_EXE = ROOT / "bin/current/pemark_x64_v8_6_4.exe"

FVIRTKEY, FSHIFT, FCONTROL, FALT = 0x01, 0x04, 0x08, 0x10
CTRL, CTRL_SHIFT, CTRL_ALT = FVIRTKEY | FCONTROL, \
    FVIRTKEY | FCONTROL | FSHIFT, FVIRTKEY | FCONTROL | FALT
ACCEL_SIZE = 6

k32 = c.windll.kernel32

# Accelerator table: (flags, virtual key) -> command, and the menu hint that must
# advertise it. Rabbit parity is the reason each of these exists.
EXPECTED = [
    ((CTRL, 0x4E), 1001, None),
    ((CTRL, 0x4F), 1002, None),
    ((CTRL, 0x53), 1003, None),
    ((CTRL_SHIFT, 0x53), 1004, "m_saveas"),
    ((CTRL_SHIFT, 0x4F), 1006, "m_openfolder"),
    ((CTRL, 0x57), 1007, "m_close"),
    ((CTRL, 0x42), 1307, "m_outline"),
    ((CTRL, 0x4A), 1315, "m_right_sidebar"),
    ((CTRL_ALT, 0x53), 1305, "m_status"),
    ((CTRL_SHIFT, 0x50), 1306, None),
    ((CTRL_ALT, 0x4B), 1406, "m_md_codeblock"),
    ((CTRL_ALT, 0x4C), 1409, "m_md_link"),
    ((CTRL_ALT, 0x54), 1312, None),
]

# Keys Rabbit already owns; PeMark must leave them free until the matching
# feature lands, otherwise the later feature cannot take them without a break.
# Ctrl+J used to sit here: V8.6.4 took it for the reserved right sidebar
# entry, so it moved into EXPECTED above.
RESERVED = [(CTRL, 0x4B), (CTRL_SHIFT, 0x4B), (CTRL, 0x4C), (CTRL_SHIFT, 0x4C),
            (CTRL, 0x44), (FALT, 0x4C)]


def accel_table(app, ns):
    count = ns["ACCEL_COUNT"]
    address = app.base + ns["rsyms"]["accels"]
    raw, got = c.create_string_buffer(count * ACCEL_SIZE), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(address), raw,
                                 count * ACCEL_SIZE, c.byref(got))
    assert got.value == count * ACCEL_SIZE, got.value
    table = {}
    for index in range(count):
        flags, _pad, vk, cmd = struct.unpack_from("<BBHH", raw.raw,
                                                  index * ACCEL_SIZE)
        assert (flags, vk) not in table, "duplicate accelerator %02X/%04X" % (
            flags, vk)
        table[(flags, vk)] = cmd
    return table


def image_wstring(app, ns, symbol, limit=128):
    address = app.base + ns["rsyms"][symbol]
    raw, got = c.create_string_buffer(limit * 2), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(address), raw,
                                 limit * 2, c.byref(got))
    return raw.raw.decode("utf-16le").split("\0", 1)[0]


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build(GEN)
    app = App(ns, exe)
    try:
        table = accel_table(app, ns)
        for key, command, symbol in EXPECTED:
            assert table.get(key) == command, \
                "accelerator %02X/%04X must map to %d, got %r" % (
                    key[0], key[1], command, table.get(key))
            if symbol:
                hint = image_wstring(app, ns, symbol)
                assert hint.endswith(hint_for(symbol)), (symbol, hint)
        for key in RESERVED:
            assert key not in table, \
                "accelerator %02X/%04X is reserved for a later feature" % key

        # Close reuses the destructive guard and ends on an empty clean document.
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory) / "doc.md"
            document.write_text("# Heading\n\nbody\n", encoding="utf-8")
            write_wstr(app, "temp_path", str(document))
            app.post_command(1901)
            wait_for(lambda: app.read_path() == str(document), 6, "opening a file")
            assert app.text().startswith("# Heading")
            app.post_command(1007)
            wait_for(lambda: app.read_path() == "", 6, "Close must clear the path")
            assert app.text() == "", repr(app.text())
            document_revision, saved_revision = app.revisions()
            assert document_revision == saved_revision, "Close leaves a clean document"

        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS keymap: %d accelerators parsed from the image, Rabbit-parity keys "
          "and their menu hints agree, keys reserved for later features stay "
          "free, and Close clears the document through the shared guard; "
          "released V8.5.4 binary unchanged" % len(table))
    return 0


def hint_for(symbol):
    return {
        "m_saveas": "Ctrl+Shift+S",
        "m_openfolder": "Ctrl+Shift+O",
        "m_close": "Ctrl+W",
        "m_outline": "Ctrl+B",
        "m_right_sidebar": "Ctrl+J",
        "m_status": "Ctrl+Alt+S",
        "m_md_codeblock": "Ctrl+Alt+K",
        "m_md_link": "Ctrl+Alt+L",
    }[symbol]


if __name__ == "__main__":
    raise SystemExit(main())
