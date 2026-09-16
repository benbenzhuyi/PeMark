# -*- coding: utf-8 -*-
"""
Windows 注入式冒烟回归测试（无需截图/computer-use）。

原理：对纯 Win32 程序，SendMessage(WM_COMMAND) 即等价于用户点击菜单项；
EnumChildWindows + WS_VISIBLE 即等价于"看"窗口状态；进程存活即等价于
"没有崩溃退出"。SendMessage 是同步调用——若命令处理中崩溃，后续调用
立即失败，天然检测崩溃。

覆盖（AGENTS V8.4.24 完成门槛的自动化子集）：
  1. 启动 → 主窗口出现，初始 Source 态（恰好一个可见 RichEdit）
  2. cmd_new（set_view_mode 路径——V8.5.0 首次构建的崩溃点）
  3. WM_SETTEXT 注入后显式投递 EN_CHANGE → 大纲 LISTBOX 条目数 > 0
     （V8.4.25 统一扫描器实机验证）
  4. 预览切换 → 可见 RichEdit 翻转（ViewState 不变量实机验证）
  5. 20 次连续模式切换 → 存活 + 最终态正确
  6. 主题切换 / 换行切换（cmd_wrap 路径——V8.5.0 改动点）/ 大纲切换
  7. WM_CLOSE → 进程干净退出

用法：python tools\smoke_test.py [exe路径]
退出码 0 = 全部通过。
"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
import os

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
WM_SETTEXT = 0x000C
EN_CHANGE = 0x0300
WM_GETTEXTLENGTH = 0x000E
BM_CLICK = 0x00F5
LB_GETCOUNT = 0x018B
LB_SETCURSEL = 0x0186
LBN_SELCHANGE = 1
WS_VISIBLE = 0x10000000

CLASS_MAIN = 'DirectPE_Notepad_Main'

# 命令 ID（与生成器 command 分发表一致）
CMD_NEW, CMD_WRAP, CMD_PREVIEW, CMD_OUTLINE = 1001, 1304, 1306, 1307
CMD_THEME_TOGGLE = 1312

results = []

def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL') + f'  {name}' + (f'  [{detail}]' if detail else ''))

def find_main(timeout_ms=8000):
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        h = u32.FindWindowW(CLASS_MAIN, None)
        if h:
            return h
        time.sleep(0.1)
    return 0

def discard_unsaved_prompt(hwnd, timeout_ms=1500):
    """V8.5.2+ may protect a dirty close. Click IDNO (Discard) when that
    owner-modal prompt appears; older baselines close without a prompt."""
    wanted_pid = wt.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(wanted_pid))
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        matches = []
        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def cb(h, _):
            pid = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            cls = ctypes.create_unicode_buffer(32)
            u32.GetClassNameW(h, cls, 32)
            if pid.value == wanted_pid.value and cls.value == '#32770':
                matches.append(h)
            return True
        u32.EnumWindows(cb, 0)
        if matches:
            button = u32.GetDlgItem(matches[0], 7)  # IDNO = discard
            if button:
                u32.SendMessageW(button, BM_CLICK, 0, 0)
                return True
        time.sleep(.05)
    return False

def count_dialogs(hwnd):
    """Number of owner-modal dialogs (#32770) currently owned by that process."""
    wanted_pid = wt.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(wanted_pid))
    found = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        pid = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        cls = ctypes.create_unicode_buffer(32)
        u32.GetClassNameW(h, cls, 32)
        if pid.value == wanted_pid.value and cls.value == '#32770':
            found.append(h)
        return True
    u32.EnumWindows(cb, 0)
    return len(found)

def child_windows(hwnd):
    """返回 [(hwnd, 类名, 是否可见)]。可见性查 GWL_STYLE(-16) 的
    WS_VISIBLE（注意不是 EXSTYLE）；类名用小写规范化（标准控件
    'EDIT'/'LISTBOX' 被 Windows 规范化为 'Edit'/'ListBox'）。"""
    out = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(h, buf, 64)
        out.append((h, buf.value.lower(), bool(u32.GetWindowLongW(h, -16) & WS_VISIBLE)))
        return True
    u32.EnumChildWindows(hwnd, cb, 0)
    return out

def doc_surfaces(hwnd):
    """两个文档表面：源码 = 'edit'（RichEdit 实例），预览 = 'richedit50w'。"""
    return [(h, cls, vis) for h, cls, vis in child_windows(hwnd)
            if cls in ('edit', 'richedit50w')]

def listbox(hwnd):
    for h, cls, vis in child_windows(hwnd):
        if cls == 'listbox':
            return h
    return 0

def send_cmd(hwnd, cid):
    u32.SendMessageW(hwnd, WM_COMMAND, cid & 0xFFFF, 0)

def alive(proc):
    return proc.poll() is None

def must_alive(proc, name):
    ok = alive(proc)
    check(name + ' 进程存活', ok, f'exitcode={proc.poll()}' if not ok else '')
    return ok

def main():
    exe = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join('bin', 'current', 'pemark_x64_v8_5_1.exe')
    print(f'目标：{exe}\n')
    proc = subprocess.Popen([exe], cwd=os.path.dirname(os.path.abspath(exe)))

    hwnd = find_main()
    check('启动：主窗口出现', hwnd != 0)
    if not hwnd:
        proc.kill()
        return 1

    # --- 1. 初始 Source 态：恰好一个可见文档表面 ---
    re_state = doc_surfaces(hwnd)
    check('初始 Source 态（恰好 1 个可见文档表面）',
          len(re_state) == 2 and sum(v for _, _, v in re_state) == 1,
          f'{len(re_state)} 个文档表面, 可见 {sum(v for _, _, v in re_state)}')
    must_alive(proc, '初始')

    # --- 2. cmd_new（set_view_mode 崩溃路径） ---
    send_cmd(hwnd, CMD_NEW)
    time.sleep(0.3)
    if not must_alive(proc, '新建（set_view_mode 路径）'):
        return 1

    # --- 3. 注入 markdown → 大纲构建（统一扫描器实机验证） ---
    doc = '\r\n'.join(
        [f'# 标题 {i}\r\n\r\n正文第 {i} 节。\r\n' for i in range(1, 31)]
        + ['```\r\n# 围栏内伪标题（不得进大纲）\r\n```\r\n', '## 尾部小节\r\n'])
    edit_h = None
    for h, cls, vis in child_windows(hwnd):
        if cls == 'edit' and vis:
            edit_h = h
            break
    u32.SendMessageW(edit_h, WM_SETTEXT, 0, doc)
    # Multiline EDIT does not emit EN_CHANGE for programmatic WM_SETTEXT.
    # Model the user-edit notification explicitly so this test exercises the
    # production WM_COMMAND -> private update -> unified scan path.
    u32.SendMessageW(hwnd, WM_COMMAND, (EN_CHANGE << 16) | 1, edit_h)
    time.sleep(0.8)
    must_alive(proc, '注入 30+ 标题文档')
    lb = listbox(hwnd)
    n = u32.SendMessageW(lb, LB_GETCOUNT, 0, 0) if lb else -1
    check('大纲条目数 = 31（30 主标题 + 尾部小节，围栏伪标题排除）',
          n == 31, f'实际 {n}')

    # --- 4. 预览切换：ViewState 不变量 ---
    send_cmd(hwnd, CMD_PREVIEW)
    time.sleep(0.8)
    must_alive(proc, '切预览（prepare/commit 路径）')
    re_state = doc_surfaces(hwnd)
    check('PREVIEW 态不变量（恰好 1 个可见文档表面）',
          len(re_state) == 2 and sum(v for _, _, v in re_state) == 1)

    # --- 5. 20 次连续切换（AGENTS 门槛） ---
    crash = False
    for i in range(20):
        send_cmd(hwnd, CMD_PREVIEW)
        time.sleep(0.25)
        if not alive(proc):
            crash = True
            check(f'20 连切换 @第 {i+1} 次', False, '进程退出')
            break
    if not crash:
        check('20 连续模式切换存活', True)
        re_state = doc_surfaces(hwnd)
        check('20 次后不变量（恰好 1 个可见文档表面）',
              len(re_state) == 2 and sum(v for _, _, v in re_state) == 1)
        # 回到 Source 供后续测试
        send_cmd(hwnd, CMD_PREVIEW)
        time.sleep(0.4)

    # --- 6. 主题 / 换行（cmd_wrap 重建 EDIT 路径）/ 大纲切换 ---
    send_cmd(hwnd, CMD_THEME_TOGGLE); time.sleep(0.4)
    must_alive(proc, '主题切换')
    send_cmd(hwnd, CMD_THEME_TOGGLE); time.sleep(0.4)
    must_alive(proc, '主题切换（回）')
    send_cmd(hwnd, CMD_WRAP); time.sleep(0.6)
    if not must_alive(proc, '换行切换（EDIT 重建 + commit 恢复）'):
        return 1
    re_state = doc_surfaces(hwnd)
    check('换行重建后不变量（恰好 1 个可见文档表面）',
          len(re_state) == 2 and sum(v for _, _, v in re_state) == 1)
    send_cmd(hwnd, CMD_OUTLINE); time.sleep(0.3)
    must_alive(proc, '大纲开')
    send_cmd(hwnd, CMD_OUTLINE); time.sleep(0.3)
    must_alive(proc, '大纲关')

    # --- 7. 干净退出 ---
    u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    # A dirty close legitimately waits for the unsaved prompt. Keep answering it
    # while waiting so a slow machine cannot turn a normal prompt into a timeout.
    rc = None
    deadline = time.perf_counter() + 15
    while time.perf_counter() < deadline:
        discard_unsaved_prompt(hwnd, timeout_ms=200)
        if proc.poll() is not None:
            rc = proc.returncode
            break
        time.sleep(.1)
    if rc is not None:
        check('WM_CLOSE 干净退出（退出码 0）', rc == 0, f'exitcode={rc}')
    else:
        # Distinguish "still waiting for an answer" from "genuinely stuck".
        check('WM_CLOSE 干净退出', False,
              f'超时未退出；待处理对话框={count_dialogs(hwnd)}')
        proc.kill()
        proc.wait(timeout=5)

    failed = [r for r in results if not r[1]]
    print(f'\n结果：{len(results) - len(failed)}/{len(results)} 通过')
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
