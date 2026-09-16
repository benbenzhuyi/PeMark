#!/usr/bin/env python3
"""V8.6 slice 1: directory enumeration, filtering, ordering and error paths."""
import ctypes as c
import hashlib
import os
import shutil
import struct
import tempfile
from pathlib import Path
import time

from test_v8_5_2_destructive import App
from test_v8_5_2_open_encoding import write_wstr

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/candidate/generate_markdown_editor_v8_6.py"))
RELEASE_EXE = ROOT / "bin/current/pemark_x64_v8_5_4.exe"
CMD_WORKSPACE_PROBE = 1902
WS_STRIDE = 544
WS_NAME_UNITS = 260
WS_OFF_ATTRIBUTES = 520
WS_OFF_KIND = 524
WS_OFF_SIZE_LOW = 528
WS_OFF_SIZE_HIGH = 532
WS_OFF_WRITE_TIME = 536
FILE_ATTRIBUTE_DIRECTORY = 0x10
FILETIME_EPOCH_DELTA = 11644473600
# Any of these is a clear "this is not an enumerable directory" answer:
# FILE_NOT_FOUND / PATH_NOT_FOUND / FILENAME_EXCED_RANGE / DIRECTORY / ACCESS_DENIED
NOT_A_DIRECTORY_ERRORS = (2, 3, 5, 206, 267)
k32 = c.windll.kernel32


def build():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_workspace_test__",
          "OPEN_TEST_BUILD": True}
    exec(compile(source, str(GEN), "exec"), ns)
    out = Path(ns["out"])
    assert out.name == "pemark_x64_v8_6_open_transaction_test.exe", out.name
    return ns, out


def make_fixture(directory):
    root = Path(directory) / "workspace"
    (root / "docs").mkdir(parents=True)
    (root / "empty").mkdir()
    (root / "中文目录").mkdir()
    (root / "docs" / "inner.md").write_text("# inner\n", encoding="utf-8")
    for name in ("a.md", "B.MARKDOWN", "c.txt", "d.MD", "skip.bin", "note"):
        (root / name).write_text("x\n", encoding="utf-8")
    return root


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.03)
    raise AssertionError(message)


def probe(app, path):
    write_wstr(app, "temp_path", path)
    app.post_command(CMD_WORKSPACE_PROBE)
    # The probe is synchronous inside the message loop; give it a moment and
    # then require a settled state (entries present or an error recorded).
    time.sleep(.4)


def read_entries(app, count):
    if count == 0:
        return []
    pointer = app.read64("ws_entries")
    assert pointer, "workspace arena was not published"
    size = count * WS_STRIDE
    buf, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(app.handle, c.c_void_p(pointer), buf, size,
                                 c.byref(got)) and got.value == size
    entries = []
    for index in range(count):
        chunk = buf.raw[index * WS_STRIDE:(index + 1) * WS_STRIDE]
        name = chunk[:WS_NAME_UNITS * 2].decode("utf-16le").split("\x00", 1)[0]
        size_low = struct.unpack_from("<I", chunk, WS_OFF_SIZE_LOW)[0]
        size_high = struct.unpack_from("<I", chunk, WS_OFF_SIZE_HIGH)[0]
        entries.append({
            "name": name,
            "attributes": struct.unpack_from("<I", chunk, WS_OFF_ATTRIBUTES)[0],
            "kind": struct.unpack_from("<I", chunk, WS_OFF_KIND)[0],
            "size": size_low | (size_high << 32),
            "written": struct.unpack_from("<Q", chunk, WS_OFF_WRITE_TIME)[0],
        })
    return entries


def filetime_of(path):
    """Windows FILETIME (100 ns ticks since 1601) for a local file."""
    return int((os.stat(path).st_mtime + FILETIME_EPOCH_DELTA) * 10_000_000)


def read_list(app):
    return app.read32("ws_entry_count"), read_entries(app, app.read32("ws_entry_count"))


def main():
    release_hash = hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest()
    ns, exe = build()
    app = App(ns, exe)
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = make_fixture(directory)
            probe(app, root)
            error = app.read32("ws_error")
            assert error == 0, error
            count, entries = read_list(app)
            names = [entry["name"] for entry in entries]
            assert count == 7, (count, names)
            assert names[0:3] == ["docs", "empty", "中文目录"], names
            assert names[3:] == ["a.md", "B.MARKDOWN", "c.txt", "d.MD"], names
            assert "skip.bin" not in names and "note" not in names
            # Directories carry the flag and the real attribute bit; files do not.
            assert [entry["kind"] for entry in entries] == [1, 1, 1, 0, 0, 0, 0], entries
            assert all(entry["attributes"] & FILE_ATTRIBUTE_DIRECTORY
                       for entry in entries[:3]), entries
            assert not any(entry["attributes"] & FILE_ATTRIBUTE_DIRECTORY
                           for entry in entries[3:]), entries

            # Size and last-write time belong to the entry, not to the loader
            # scratch buffer: compare files against the file system directly.
            for entry in entries[3:]:
                path = root / entry["name"]
                assert entry["size"] == os.stat(path).st_size, entry
                assert abs(entry["written"] - filetime_of(path)) <= 10_000_000, entry

            # Re-enumerating a different directory replaces the previous list.
            empty_root = Path(directory) / "only_files"
            empty_root.mkdir()
            (empty_root / "only.txt").write_text("x", encoding="utf-8")
            probe(app, empty_root)
            assert app.read32("ws_error") == 0
            _, small = read_list(app)
            assert [entry["name"] for entry in small] == ["only.txt"], small
            assert small[0]["size"] == 1, small

            # Empty directory: zero entries, no error.
            probe(app, root / "empty")
            assert app.read32("ws_entry_count") == 0
            assert app.read32("ws_error") == 0

            # Missing path: an error code is recorded and the list is empty.
            probe(app, Path(directory) / "does_not_exist")
            assert app.read32("ws_entry_count") == 0
            error = app.read32("ws_error")
            assert error in NOT_A_DIRECTORY_ERRORS, error
            print("missing path reported win32 error %d" % error)

            # A regular file is not an enumerable directory: same clear failure.
            probe(app, empty_root / "only.txt")
            assert app.read32("ws_entry_count") == 0
            error = app.read32("ws_error")
            assert error in NOT_A_DIRECTORY_ERRORS, error

            # Names at the 255-character component limit survive intact.
            long_names = Path(directory) / "longnames"
            long_names.mkdir()
            limit_name = "L" * 252 + ".md"
            assert len(limit_name) == 255, len(limit_name)
            (long_names / limit_name).write_text("x\n", encoding="utf-8")
            probe(app, long_names)
            assert app.read32("ws_error") == 0
            _, named = read_list(app)
            assert [entry["name"] for entry in named] == [limit_name], named

            # More entries than one 64-slot arena block: the table must grow and
            # stay ordered across the block boundary.
            many = Path(directory) / "many"
            many.mkdir()
            (many / "sub").mkdir()
            for index in range(129):
                (many / ("f%03d.md" % index)).write_text("x", encoding="utf-8")
            probe(app, many)
            assert app.read32("ws_error") == 0
            count, crowded = read_list(app)
            assert count == 130, count
            assert crowded[0]["name"] == "sub" and crowded[0]["kind"] == 1, crowded[0]
            assert [entry["name"] for entry in crowded[1:]] == \
                ["f%03d.md" % index for index in range(129)], crowded[1:4]

            # A path beyond MAX_PATH without the \\?\ prefix is refused with a
            # clear error instead of being truncated or crashing.
            deep_root = Path(directory) / "deep"
            deep_root.mkdir()
            deep = deep_root
            for _ in range(6):
                deep = deep / ("d" * 40)
            os.makedirs("\\\\?\\" + str(deep), exist_ok=True)
            try:
                assert len(str(deep)) > 260, len(str(deep))
                probe(app, deep)
                assert app.read32("ws_entry_count") == 0
                error = app.read32("ws_error")
                assert error in NOT_A_DIRECTORY_ERRORS, error
                print("overlong path reported win32 error %d" % error)
            finally:
                shutil.rmtree("\\\\?\\" + str(deep_root), ignore_errors=True)

            # A directory that the account may not list: the model must report a
            # win32 error or an empty list, and must never crash.
            guarded = Path("C:/System Volume Information")
            if guarded.is_dir():
                probe(app, guarded)
                count = app.read32("ws_entry_count")
                error = app.read32("ws_error")
                assert error != 0 or count == 0, (error, count)
                print("guarded directory reported error=%d count=%d" % (error, count))

            # Recovery: a valid directory after a failure enumerates again.
            probe(app, root)
            assert app.read32("ws_error") == 0
            assert app.read32("ws_entry_count") == 7

        app.post_close()
        assert app.proc.wait(timeout=10) == 0
    finally:
        app.close_handle()
    assert hashlib.sha256(RELEASE_EXE.read_bytes()).hexdigest() == release_hash
    print("PASS workspace enumeration: filtering, directory-first ordering, "
          "Unicode and 255-character names, attributes/size/time ownership, "
          "arena growth past 64 entries, empty, missing, overlong and guarded "
          "directories, recovery; released V8.5.4 binary unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
