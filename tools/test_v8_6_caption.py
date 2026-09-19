#!/usr/bin/env python3
"""V8.6.3 custom title row, version label and placeholder icons.

This is a deterministic Windows test of the real candidate or release process:

* the main window has no native caption, but still has a thick frame;
* one 32px DirectPE_Caption child spans the full client width;
* the shared caption rect table contains the left switch, five menu entries,
  six tool icons and three window buttons, all inside the row;
* moving over the right-sidebar placeholder highlights it, and leaving clears
  the highlight;
* clicking the right-sidebar/gear placeholders does not change document state;
* clicking the left switch still posts the existing View -> Left Sidebar
  command, so the replacement row does not create a second state owner.
"""
import ctypes as c
from ctypes import wintypes as w
import os
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v8_5_2_destructive import App

ROOT = Path(__file__).resolve().parents[1]
GEN = Path(os.environ.get(
    "PEMARK_GENERATOR",
    ROOT / "src/candidate/generate_markdown_editor_v8_6.py"))
# The expected version label comes from manifest.json. Hard-coding it here made
# this test fail on every release after V8.6.3 even though the title row itself
# was correct.
SNAPSHOT = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))[
    "current_snapshot"]

u32, k32 = c.windll.user32, c.windll.kernel32
u32.IsWindowVisible.argtypes = [w.HWND]
u32.IsWindowVisible.restype = w.BOOL
u32.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u32.GetClientRect.restype = w.BOOL
u32.GetWindowRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
u32.GetWindowRect.restype = w.BOOL
u32.GetWindowLongW.argtypes = [w.HWND, c.c_int]
u32.GetWindowLongW.restype = c.c_long
u32.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
u32.GetWindowTextW.restype = c.c_int
u32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
u32.SendMessageW.restype = w.LPARAM

WM_MOUSEMOVE = 0x0200
WM_MOUSELEAVE = 0x02A3
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
CAPTION_H = 32

CAP_RECT = {
    "toggle": 0, "title": 1, "file": 2, "edit": 3, "markdown": 4,
    "view": 5, "help": 6, "save": 7, "find": 8, "viewmode": 9,
    "theme": 10, "gear": 11, "rightbar": 12, "min": 13, "max": 14,
    "close": 15,
}
CAP_ID = {
    "toggle": 1, "file": 2, "edit": 3, "markdown": 4, "view": 5,
    "help": 6, "save": 10, "find": 11, "viewmode": 12, "theme": 13,
    "gear": 14, "rightbar": 15, "min": 16, "max": 17, "close": 18,
}


def build():
    source = GEN.read_text(encoding="utf-8")
    ns = {"__file__": str(GEN), "__name__": "__pemark_caption_test__"}
    exec(compile(source, str(GEN), "exec"), ns)
    return ns


def wait_for(predicate, timeout, message):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError(message)


def read_rects(app):
    size = len(CAP_RECT) * 16
    raw, got = c.create_string_buffer(size), c.c_size_t()
    assert k32.ReadProcessMemory(
        app.handle, c.c_void_p(app.base + app.bsyms["caption_rects"]),
        raw, size, c.byref(got)) and got.value == size
    return {
        name: tuple(int.from_bytes(raw.raw[i * 16 + j * 4:
                                               i * 16 + j * 4 + 4],
                                   "little", signed=True)
                    for j in range(4))
        for name, i in CAP_RECT.items()
    }


def send_point(hwnd, msg, point, wparam=0):
    x, y = point
    u32.SendMessageW(hwnd, msg, wparam, (y << 16) | (x & 0xFFFF))


def center(rect):
    left, top, right, bottom = rect
    return (left + right) // 2, (top + bottom) // 2


def main():
    ns = build()
    app = App(ns, Path(ns["out"]))
    try:
        main_hwnd = app.main
        title = c.create_unicode_buffer(160)
        assert u32.GetWindowTextW(main_hwnd, title, len(title))
        expected_label = (SNAPSHOT if GEN.parent.name == "current"
                          else SNAPSHOT + " Candidate")
        assert expected_label in title.value, title.value
        caption = app.read64("hwnd_caption")
        assert caption and u32.IsWindowVisible(caption), \
            "the custom caption child must exist and be visible"
        assert app.read64("hfont_icons"), \
            "the Fluent/MDL2 icon font must be created (or fall back to the panel font)"

        style = u32.GetWindowLongW(main_hwnd, GWL_STYLE)
        assert not (style & WS_CAPTION), \
            "native caption must be removed (style=%#x)" % style
        assert style & WS_THICKFRAME, "the window must stay resizable"

        client = w.RECT()
        assert u32.GetClientRect(main_hwnd, c.byref(client))
        crect = w.RECT()
        assert u32.GetWindowRect(caption, c.byref(crect))
        assert crect.bottom - crect.top == CAPTION_H, \
            "caption row must be exactly %dpx" % CAPTION_H
        assert crect.right - crect.left == client.right, \
            "caption row must span the full client width (caption=%d client=%d)" % (
                crect.right - crect.left, client.right)

        rects = read_rects(app)
        for name, rect in rects.items():
            l, t, r, b = rect
            assert 0 <= l < r <= client.right, (name, rect, client.right)
            assert 0 <= t < b <= CAPTION_H, (name, rect)

        ordered_icons = ["save", "find", "viewmode", "theme", "gear",
                         "rightbar"]
        for left_name, right_name in zip(ordered_icons, ordered_icons[1:]):
            assert rects[left_name][2] <= rects[right_name][0], \
                (left_name, right_name, rects[left_name], rects[right_name])
        assert rects["rightbar"][2] <= rects["min"][0], \
            "the right-sidebar placeholder must stay left of the window buttons"

        # Hover the Codex-style right-sidebar placeholder. It is deliberately
        # inert, but it must paint a hot state exactly like the other icons.
        rightbar_pt = center(rects["rightbar"])
        send_point(caption, WM_MOUSEMOVE, rightbar_pt)
        wait_for(lambda: app.read32("caption_hot") == CAP_ID["rightbar"], 2,
                 "right-sidebar placeholder did not become hot")
        send_point(caption, WM_MOUSELEAVE, (0, 0))
        wait_for(lambda: app.read32("caption_hot") == 0, 2,
                 "caption hover did not clear on mouse leave")

        # Click the two placeholders. They must not mutate document/view state.
        preview_before = app.read32("preview_flag")
        outline_before = app.read32("outline_flag")
        for name in ("gear", "rightbar"):
            pt = center(rects[name])
            send_point(caption, WM_MOUSEMOVE, pt)
            send_point(caption, WM_LBUTTONDOWN, pt, 1)
            send_point(caption, WM_LBUTTONUP, pt, 0)
            wait_for(lambda: app.read32("caption_press") == 0, 2,
                     "%s placeholder left a pressed state" % name)
        assert app.read32("preview_flag") == preview_before
        assert app.read32("outline_flag") == outline_before
        assert app.proc.poll() is None, "placeholder click must not kill the app"

        # The left switch is not a placeholder: it uses the existing command.
        toggle_pt = center(rects["toggle"])
        send_point(caption, WM_LBUTTONDOWN, toggle_pt, 1)
        send_point(caption, WM_LBUTTONUP, toggle_pt, 0)
        wait_for(lambda: app.read32("outline_flag") == 0, 3,
                 "left switch did not hide the sidebar")
        send_point(caption, WM_LBUTTONDOWN, toggle_pt, 1)
        send_point(caption, WM_LBUTTONUP, toggle_pt, 0)
        wait_for(lambda: app.read32("outline_flag") == 1, 3,
                 "left switch did not restore the sidebar")

        app.post_close()
        assert app.proc.wait(timeout=5) == 0
        print("PASS custom caption: %s title, 32px row, 6 tool "
              "icons, inert right-sidebar placeholder with hover, live left "
              "switch" % expected_label)
    finally:
        app.close_handle()


if __name__ == "__main__":
    main()
