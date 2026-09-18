# PeMark V8.6.4 启动崩溃求助文档

## 项目背景

PeMark 是一个**纯 Direct-PE 手工生成的 Windows x64 GUI 应用**（Markdown 编辑器）。
不用 C/Rust/汇编器/链接器——Python 生成器直接构造 PE32+ 映像的每一个字节：
.text（机器码）、.rdata（字符串/数据）、.idata（导入表）、.bss（虚拟 BSS）、.reloc（重定位表）、.pdata（栈回溯元数据）。

## 崩溃现象

- **退出码**：0xC0000005 (STATUS_ACCESS_VIOLATION)
- **崩溃位置**：USER32.dll + 0xF95F
- **崩溃字节**：`44 8B 02` = `mov r8, [rdx]`，rdx 可能为 0 导致访问违例
- **崩溃时机**：进程启动后 ~3 秒内（在消息循环开始之前）
- **影响范围**：release exe 和 open_transaction_test exe 都崩溃

## 已排除的原因

### 1. PE 结构（已验证正确）
```
.text:  RVA 0x1000, vsize 0xF000, raw 0x400+0xF000, chars 0x60000020
.rdata: RVA 0x10000, vsize 0x3000, raw 0xF400+0x3000, chars 0x40000040
.idata: RVA 0x13000, vsize 0x2000, raw 0x12400+0x2000, chars 0xC0000040
.bss:   RVA 0x15000, vsize 0x19000, raw 0+0, chars 0xC0000080
.reloc: RVA 0x2E000, vsize 0x400, raw 0x2D400+0x400, chars 0x42000040
.pdata: RVA 0x2F000, vsize 0x600, raw 0x2E400+0x600, chars 0x40000040
```

### 2. 导入表（已验证正确）
- Import Directory: RVA=0x13000, Size=0xDC (220 bytes = 11 descriptors)
- 第一个 descriptor: ILT=0x130E0, Name=0x13A40 (KERNEL32.dll), IAT=0x13590
- IAT 条目正确指向 hint/name 结构体
- 入口点第一条 `call [IAT[fn]]` 指向 SetProcessDpiAwarenessContext，已验证 IAT 条目值正确

### 3. 入口点机器码（已验证正确）
```
48 81 EC 88 00 00 00   sub rsp, 0x88
B9 FB FF FF FF         mov ecx, 0xFFFFFFFB (DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED)
48 63 C9               movsxd rcx, ecx
FF 15 9B 28 01 00      call [IAT[SetProcessDpiAwarenessContext]]
```
- 已验证 SetProcessDpiAwarenessContext 在 USER32.dll 中存在且可调用（Python ctypes 测试通过，返回 1）
- IAT 相对位移计算正确

### 4. 窗口句柄 NULL 检查
- 所有 CreateWindowExW 调用后都有 `test64('rax'); jcc(0x84,'exit')` NULL 检查
- apply_theme 中的 InvalidateRect 对 hwnd_caption 和面板框架有 `test64 + jcc` NULL 保护
- 但 line 5819 的 8 个 InvalidateRect 调用（hwnd_edit/outline/splitter/outline_scroll/files_scroll/preview/files/status/corner）**没有 NULL 检查**
- 这些窗口在 line 1427 apply_theme 调用时都已创建（只有 hwnd_edit 在 line 2208 创建，晚于 apply_theme）

### 5. DLL 特性
- 原始值: 0x0022 (NX_COMPAT | DYNAMIC_BASE)
- 已尝试添加 TERMINAL_SERVER_AWARE (0x0002) → 0x0024，仍崩溃
- 当前值: 0x0022

### 6. 代码审查
- 入口点 (line 1086-1430)：BSS 默认值初始化、LoadLibraryW uxtheme、RegisterClassExW × 3（主窗口+滚动面+标题栏）、CreateWindowExW × 15（主窗口+子窗口）、菜单构建、load_default_workspace → apply_theme → update_preview → resize_children → sync_outline_scrollbar → sync_panel_menu → update_status → init_done=1
- apply_theme (line 5724-5827)：删除旧 brushes（有 NULL 保护）→ 按 theme_dark 创建新 brushes → SetMenuInfo → uxtheme dark mode → DwmSetWindowAttribute → InvalidateRect 所有子窗口
- resize_children (line 3502-3598)：MoveWindow 所有子窗口
- load_default_workspace (line 4397-4408)：SHGetFolderPathW → GetFileAttributesW → workspace_set_root → set_panel_mode(1)
- 所有代码路径看起来合理

## 调试工具尝试

### 1. Win32 调试 API（CreateProcessW + WaitForDebugEvent + ContinueDebugEvent）
- 成功捕获崩溃地址：USER32.dll+0xF95F
- GetThreadContext 始终返回全零 CONTEXT（即使使用 THREAD_GET_CONTEXT 权限）
- 说明线程还没执行到任何用户代码就崩溃了（初始 CONTEXT）
- 无法获取完整调用栈

### 2. SuspendThread + GetThreadContext
- SuspendThread 返回 0（成功）
- GetThreadContext 仍返回全零
- 说明线程在异常处理中，CONTEXT 未正确保存

### 3. 单步跟踪（STATUS_STEP_INTO）
- 脚本已编写（_step_trace.py）但尚未运行
- 预期可以跟踪前 30 条指令

### 4. ctypes 直接调用
- SetProcessDpiAwarenessContext(-5) → 返回 1（成功）
- GetModuleHandleW(None) → 返回有效句柄
- 说明这些 API 在 Python 进程中工作正常

## 关键矛盾

1. **PE 结构正确**但 exe 在启动 3 秒内崩溃
2. **IAT 条目正确**（第一条 call 指向 SetProcessDpiAwarenessContext 的 hint/name）
3. **SetProcessDpiAwarenessContext 存在且可调用**（Python 测试通过）
4. **所有窗口句柄都有 NULL 检查**（CreateWindowExW 后）
5. **但崩溃在 USER32.dll 内部**（不是我们的 .text 节）
6. **GetThreadContext 返回全零**（线程还没执行任何用户代码）

## 可能的根因假设

### A. 加载器初始化问题
- 崩溃在 USER32.dll 的早期初始化阶段（DPI awareness context 设置）
- 可能是我们的 PE 缺少某个加载器需要的结构（如 TLS 回调、.rdata 中的某个结构）
- 但 DYNAMIC_BASE 已设置，重定位表正确

### B. .bss 节权限
- .bss 的 characteristics = 0xC0000080 = UNINITIALIZED_DATA | READ | WRITE
- 但 .bss 在文件中 raw size = 0（正确，因为是虚拟 BSS）
- 加载器是否正确分配了 BSS 内存？

### C. 栈对齐
- 入口点 `sub rsp, 0x88` 后 RSP 对齐到 16 字节
- 但 Windows 加载器调用 entry point 时 RSP 是否已对齐？
- 标准约定：entry point 被调用时 RSP % 16 == 0，返回时 RSP % 16 == 8

### D. 某个 Win32 API 收到无效参数
- 崩溃在 `mov r8, [rdx]`，rdx 为 NULL
- 可能是 GetSystemMetrics、InitCommonControlsEx、RegisterClassExW 等
- 但这些都是标准 API，不太可能因 NULL 参数崩溃

### E. 首次 USER32 调用触发的内部初始化
- SetProcessDpiAwarenessContext 是第一个 USER32 调用
- 它可能触发 USER32.dll 的内部初始化（如消息队列、窗口类注册等）
- 这个初始化可能依赖某个我们 PE 中缺失的结构

## 需要帮助的问题

1. **纯手工 PE32+ 在 Windows 10/11 上启动时，第一个 USER32 API 调用崩溃在 USER32.dll 内部（+0xF95F），GetThreadContext 返回全零 CONTEXT——这是什么原因？**

2. **我们的 PE 结构（节布局、导入表、重定位表、pdata）都经过验证正确，但 exe 仍然崩溃。是否缺少某个 PE 结构或标志？**

3. **DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED (-5) 作为 SetProcessDpiAwarenessContext 的第一个参数，在进程初始化阶段调用是否安全？是否应该在更早/更晚的时机调用？**

4. **GetThreadContext 在 WaitForDebugEvent 异常事件后返回全零 CONTEXT（即使使用 THREAD_GET_CONTEXT 权限）——这是什么原因？是否有更好的方法获取崩溃时的寄存器状态？**

5. **纯手工 PE（不用链接器）在 Windows 上运行时，有哪些常见的"隐形"初始化需求是我们可能遗漏的？（如：TLS 回调、.rdata 中的特殊结构、加载器期望的特定标志等）**

## 关键文件

- 生成器：`src/current/generate_markdown_editor_v8_6_4.py`（~8000 行）
- 入口点：line 1086-1430
- apply_theme：line 5724-5827
- PE 构建：line 7140-7350
- 导入表构建：line 841-880
- 诊断脚本：`_crash_diag3.py`、`_crash_diag4.py`、`_check_iat2.py`、`_test_dpi.py`、`_step_trace.py`

## 构建命令

```bash
python src/current/generate_markdown_editor_v8_6_4.py
# 输出: bin/current/pemark_x64_v8_6_4.exe
# 当前 SHA-256: 09b6b18f8a2c8bafc7262d8c15bb30763ca2331788c7dfc80a6f1e6bd84c1f3d
```

## 复现步骤

1. 构建：`python src/current/generate_markdown_editor_v8_6_4.py`
2. 运行：`bin/current/pemark_x64_v8_6_4.exe`
3. 观察：窗口出现 ~1 秒后消失（崩溃），退出码 0xC0000005
4. 调试：`python _crash_diag4.py` → 显示 `CRASH: 0xC0000005 at USER32.dll+0xF95F`
