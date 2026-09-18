# PeMark V8.6.4 回归测试 — 完整对话记录

> 项目：PeMark（纯 Direct-PE 手工生成 PE32+ 的 Markdown 编辑器）
> 日期：2026-09-18
> 状态：崩溃排查中

---

## 1. 任务背景

用户要求：**"继续完成刚才中断的 PeMark 回归测试"**

上一轮 Agent 因 131072 token 上限中断，中断位置在"构建 + 回归验证"。
已完成的工作（不重新实现、不 reset）：
- `hbrush_border` BSS 符号分配（RVA 0x15E58）
- 主题切换时的 brush 创建/删除
- 退出时 brush 释放
- `WM_NCPAINT` 1px 窗口边缘线绘制

用户原话：
> "先构建，再运行相关回归；如果失败，只针对实际失败原因修复，不要重新设计这一功能。"

---

## 2. 已完成的工作（本轮）

### 2.1 git status 报告

执行 `git status`，结果：
- 13 个已修改文件
- 11 个未跟踪文件

### 2.2 测试脚本修复

**test_v8_6_keymap.py**（上一轮已修复）：
- GEN 默认值从 V8.6 改为 V8.6.4 生成器
- RELEASE_EXE 从 V8.5.4 改为 V8.6.4
- `build(GEN)` 传参

**test_v8_6_panel.py**（上一轮已修复）：
- build 函数接受可选 gen_path 参数

### 2.3 构建验证

- 重新构建确认哈希一致（确定性验证通过）
- 当前 SHA-256: `09b6b18f8a2c8bafc7262d8c15bb30763ca2331788c7dfc80a6f1e6bd84c1f3d`

### 2.4 回归测试结果

| 测试 | 结果 | 详情 |
|------|------|------|
| inspect_pe.py | PASS | PE 结构正确，6 个节，336 个 BSS 符号无重叠 |
| test_v8_6_4_menu.py | FAIL | exe 启动崩溃（init_done 未设置） |
| test_v8_6_keymap.py | 未运行 | 依赖 exe 能启动 |
| test_v8_6_panel.py | 未运行 | 依赖 exe 能启动 |
| smoke_test_v8_5_1.py | FAIL | 前 7 项 PASS，第 3 次预览切换时进程退出 |

---

## 3. 崩溃排查过程

### 3.1 崩溃现象

- **退出码**：0xC0000005 (STATUS_ACCESS_VIOLATION)
- **崩溃位置**：USER32.dll + 0xF95F
- **崩溃字节**：`44 8B 02` = `mov r8, [rdx]`，rdx 可能为 0
- **崩溃时机**：进程启动后 ~3 秒内（消息循环之前）
- **影响范围**：release exe 和 open_transaction_test exe 都崩溃

### 3.2 诊断脚本开发

#### _crash_diag.py（第一版）
- 使用 CreateProcessW(CREATE_DEBUG_ONLY) + WaitForDebugEvent 循环
- 多次修复 ctypes 问题：
  - DEBUG_EVENT 结构体 Union 嵌套
  - `pi.dwProcessId.value` → `int` 类型判断
  - `EnumProcessModulesEx` → `psapi.EnumProcessModules`
  - `GetModuleBaseNameW` int overflow → 设置 argtypes
  - `ReadProcessMemory` int overflow → 设置 argtypes
  - 事件码：0=CREATE_PROCESS, 1=EXCEPTION, 2=CREATE_THREAD, 3=EXIT_THREAD, 4=EXIT_PROCESS, 5=LOAD_DLL, 6=UNLOAD_DLL
  - 跳过断点异常（0x80000002/0x80000003/0x80000004）
- 结果：成功捕获崩溃地址 USER32.dll+0xF95F

#### _crash_diag2.py（第二版）
- 尝试读取 CONTEXT64 和栈回溯
- 发现 CONTEXT64 结构体缺少 `ContextFlags` 字段（导致偏移错位）
- 结果：GetThreadContext 返回 ok=1 但所有寄存器为 0

#### _crash_diag3.py（第三版）
- 修复 CONTEXT64 结构体（添加 ContextFlags 字段）
- 使用 THREAD_GET_CONTEXT 权限打开线程
- 结果：GetThreadContext ok=1，但所有寄存器仍为 0

#### _crash_diag4.py（第四版）
- 添加 SuspendThread + GetThreadContext 后备方案
- 修复 get_modules 中 size 未初始化 bug
- 结果：SuspendThread 返回 0（成功），GetThreadContext 仍返回全零

**关键发现**：GetThreadContext 始终返回全零 CONTEXT，说明线程还没执行到任何用户代码就崩溃了（初始 CONTEXT 状态）。

### 3.3 代码审查

#### 入口点（line 1086-1430）
```
entry_first_run:
  sub rsp, 0x88
  mov ecx, 0xFFFFFFFB          ; DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED
  movsxd rcx, ecx
  call [IAT[SetProcessDpiAwarenessContext]]
  
  GetModuleHandleW → r15
  ; BSS 默认值初始化（~30 个符号）
  GetSystemMetrics(2) → scrollbar_w
  LoadLibraryW("uxtheme.dll") → GetProcAddress × 3（ordinal 133/135/136）
  InitCommonControlsEx
  RegisterClassExW × 3（主窗口 + 滚动面 + 标题栏）
  CreateWindowExW × 15（主窗口 + 子窗口）
  菜单构建
  GetMenuItemCount
  load_default_workspace
  apply_theme
  update_preview
  resize_children
  sync_outline_scrollbar
  sync_panel_menu
  update_status
  init_done = 1
  msg_loop: GetMessageW / TranslateMessage / DispatchMessageW
```

#### apply_theme（line 5724-5827）
- 删除旧 brushes（12 个，每个都有 `test64 + jcc` NULL 保护）
- 按 theme_dark 创建新 brushes（dark: 0x1A1A1A 等 / light: 0xFFFFFF 等）
- SetMenuInfo
- uxtheme dark mode 设置
- DwmSetWindowAttribute
- **line 5819**：8 个 InvalidateRect 调用**没有 NULL 检查**
  - hwnd_edit, hwnd_outline, hwnd_splitter, hwnd_outline_scroll, hwnd_files_scroll, hwnd_preview, hwnd_files, hwnd_status, hwnd_corner
- **line 5820-5825**：hwnd_caption 和面板框架的 InvalidateRect **有** `test64 + jcc` NULL 保护

#### 关键发现：hwnd_edit 创建时机
- `hwnd_edit` 在 line 2208 创建（晚于 line 1427 的 apply_theme 调用）
- 所以 apply_theme 执行时 `hwnd_edit = 0`（BSS 初始化为 0）
- line 5819 的 `InvalidateRect(hwnd_edit=0, ...)` 可能崩溃
- **但这是老代码**，之前版本（旧 exe 哈希 86fcb71f）能启动到第 3 次预览切换才崩溃

#### 窗口句柄 NULL 检查
- 所有 CreateWindowExW 调用后都有 `test64('rax'); jcc(0x84,'exit')` 检查
- 15 个 CreateWindowExW 调用，全部有 NULL 检查

### 3.4 PE 结构验证

#### 节布局（inspect_pe.py 输出）
```
file=bin\current\pemark_x64_v8_6_4.exe size=190976
machine=0x8664 sections=6 optional=0x020B entryRVA=0x1000
imageBase=0x140000000 imageSize=0x30000 subsystem=2 dllChars=0x0140

section .text:   RVA=0x1000  VS=0xF000  raw=0x400+0xF000   chars=0x60000020
section .rdata:  RVA=0x10000 VS=0x3000 raw=0xF400+0x3000  chars=0x40000040
section .idata:  RVA=0x13000 VS=0x2000 raw=0x12400+0x2000 chars=0xC0000040
section .bss:    RVA=0x15000 VS=0x19000 raw=0+0            chars=0xC0000080
section .reloc:  RVA=0x2E000 VS=0x400  raw=0x2D400+0x400  chars=0x42000040
section .pdata:  RVA=0x2F000 VS=0x600  raw=0x2E400+0x600  chars=0x40000040
```

#### 导入表验证
- Import Directory: RVA=0x13000, Size=0xDC（11 个 descriptor）
- 第一个 descriptor: ILT=0x130E0, Name=0x13A40 (KERNEL32.dll), IAT=0x13590
- IAT_RVA=0x13590, IAT_SIZE=0x4B0
- 入口点第一条 `call [IAT[fn]]` → SetProcessDpiAwarenessContext，IAT 条目值正确

#### 入口点机器码验证
```
48 81 EC 88 00 00 00   sub rsp, 0x88
B9 FB FF FF FF         mov ecx, 0xFFFFFFFB
48 63 C9               movsxd rcx, ecx
FF 15 9B 28 01 00      call [IAT[SetProcessDpiAwarenessContext]]
```
- IAT 相对位移 0x1289B → IAT RVA 0x138B0 → hint/name 正确指向 "SetProcessDpiAwarenessContext"

#### DLL 特性
- 原始值: 0x0022 (NX_COMPAT | DYNAMIC_BASE)
- 已尝试添加 TERMINAL_SERVER_AWARE (0x0002) → 0x0024，仍崩溃
- 已恢复为 0x0022

### 3.5 API 测试

#### SetProcessDpiAwarenessContext（Python ctypes 测试）
```
SetProcessDpiAwarenessContext: FOUND at <_FuncPtr object>
Calling with DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED (-5): Return: 1
Calling with -1 (UNAWARE): Return: 0
Calling with -2 (SYSTEM): Return: 0
GetModuleHandleW(0): Handle: 0x-10E60000
```
- 函数存在且可调用，返回 1（成功）

### 3.6 关键矛盾

1. **PE 结构正确**但 exe 在启动 3 秒内崩溃
2. **IAT 条目正确**（第一条 call 指向 SetProcessDpiAwarenessContext）
3. **SetProcessDpiAwarenessContext 存在且可调用**（Python 测试通过）
4. **所有窗口句柄都有 NULL 检查**（CreateWindowExW 后）
5. **但崩溃在 USER32.dll 内部**（不是我们的 .text 节）
6. **GetThreadContext 返回全零**（线程还没执行任何用户代码）

### 3.7 可能的根因假设

| 假设 | 描述 | 可能性 |
|------|------|--------|
| A. 栈对齐 | entry point 被加载器调用时 RSP 对齐状态不正确 | 中 |
| B. .bss 虚拟节 | 加载器是否正确分配了 100KB 的 BSS 内存 | 中 |
| C. USER32 内部初始化 | 第一个 USER32 调用触发内部初始化，依赖我们 PE 中缺失的结构 | 高 |
| D. 某个 Win32 API 收到无效参数 | 崩溃在 `mov r8, [rdx]`，rdx 为 NULL | 中 |
| E. 加载器期望的特定结构 | TLS 回调、.rdata 中的特殊结构等 | 低 |

---

## 4. 代码关键位置索引

### 生成器：`src/current/generate_markdown_editor_v8_6_4.py`（~8000 行）

| 功能 | 行号 |
|------|------|
| 版本标签 | 116 |
| CUSTOM_CAPTION | 63-68 |
| DLL_CHARACTERISTICS | 72 |
| 导入表声明 | 815-839 |
| build_idata() | 841-880 |
| E 类（代码发射器） | 886-950 |
| BSS 符号分配 | 356-431 |
| hbrush_border 分配 | 431 |
| 入口点 | 1086-1430 |
| SetProcessDpiAwarenessContext 调用 | 1099 |
| 窗口类注册 | 1150-1272 |
| CreateWindowExW 调用 | 1273-1419 |
| apply_theme 调用 | 1427 |
| init_done 发布 | 1430 |
| 消息循环 | 1432+ |
| resize_children | 3502-3598 |
| load_default_workspace | 4397-4408 |
| workspace_set_root | 4412-4423 |
| apply_theme | 5724-5827 |
| InvalidateRect 无 NULL 检查 | 5819 |
| InvalidateRect 有 NULL 检查 | 5820-5825 |
| WM_NCPAINT | 6133-6153 |
| exit 清理链 | 5920-5935 |
| PE 构建（节布局） | 7140-7350 |
| 可选头 | 7328-7344 |
| 节表 | 7349-7351 |

### 测试脚本

| 文件 | 用途 |
|------|------|
| tools/test_v8_6_4_menu.py | V8.6.4 核心回归（互斥最大化、Ctrl+J、最近文件） |
| tools/test_v8_6_keymap.py | 加速器表验证 |
| tools/test_v8_6_panel.py | sidebar 面板回归 |
| tools/smoke_test_v8_5_1.py | 冒烟回归（启动/新建/大纲/预览/主题/换行/大纲开关/退出） |
| tools/inspect_pe.py | PE 结构检查 |

### 诊断脚本（临时）

| 文件 | 用途 |
|------|------|
| _crash_diag.py | 第一版诊断（基本异常捕获） |
| _crash_diag2.py | 第二版（CONTEXT + 栈回溯） |
| _crash_diag3.py | 第三版（修复 ContextFlags） |
| _crash_diag4.py | 第四版（SuspendThread 后备） |
| _check_iat.py | IAT 条目检查（有 bug） |
| _check_iat2.py | IAT 条目检查（正确版本） |
| _check_opt.py | 可选头 + 数据目录检查 |
| _check_imports.py | 导入 descriptor 检查（有 bug） |
| _check_raw.py | 原始文件偏移检查（正确版本） |
| _test_dpi.py | SetProcessDpiAwarenessContext API 测试 |
| _step_trace.py | 单步跟踪（已编写未运行） |

---

## 5. 求助文档

已生成 `CRASH_DIAGNOSIS_HELP.md`，包含：
- 项目背景
- 崩溃现象
- 已排除的 6 个原因
- 调试工具尝试
- 关键矛盾
- 5 个可能的根因假设
- 5 个需要帮助的具体问题
- 关键文件索引
- 构建命令和复现步骤

---

## 6. 下一步计划

1. **运行 _step_trace.py**：单步跟踪前 30 条指令，找到具体崩溃指令
2. **检查栈对齐**：验证 entry point 被调用时 RSP % 16 == 0
3. **检查 .bss 分配**：验证加载器是否正确分配了 BSS 内存
4. **检查 hwnd_edit 时序**：确认 apply_theme 调用时 hwnd_edit 是否确实为 0
5. **对比旧 exe（86fcb71f）和新 exe（09b6b18f）的 PE 结构差异**
6. **修复崩溃后重新运行全部回归**

---

## 7. 用户消息记录

1. "只执行 git status 并简要告诉我结果。不要读取任何源码，不要搜索文件，不要执行其他操作。"
2. "继续完成刚才中断的 PeMark 回归测试"
3. "继续"
4. "Continue"
5. "别在这里闭着眼睛转圈拉磨了，把你遇到的问题总结一下，写个求助文档，我让ChatGPT帮你解决。"
6. "我怎样把当前对话记录导出为md文件？"
7. "把当前对话的所有内容生成一份完整md文档"
