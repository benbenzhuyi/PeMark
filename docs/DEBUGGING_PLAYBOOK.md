# Windows Debugging Playbook

Static checks in this package cannot prove GUI correctness. Run the executable on Windows.

## Baseline reproduction

```powershell
python .\src\current\generate_markdown_editor_v8_4_23.py
Get-FileHash .in\current\direct_pe_markdown_editor_x64_v8_4_23.exe -Algorithm SHA256
python .	ools\inspect_pe.py .in\current\direct_pe_markdown_editor_x64_v8_4_23.exe
```

Adjust generator output path first or copy the produced binary into `bin/current` for comparison.

## Crash debugging

With WinDbg/x64dbg or equivalent:

- break on access violation
- capture RIP, RSP, volatile/nonvolatile registers
- disassemble around RIP
- map RIP back to emitted labels (add a symbol-map dump in the generator)
- inspect stack alignment at the last CALL

Recommended WinDbg concepts: break on AV, `r`, `k`, `u`, memory dump around pointers.

## State debugging

Add an optional debug generator mode that imports `OutputDebugStringW` and emits concise events:

```text
VIEW SOURCE->PREVIEW rev=12
OUTLINE select=45 source=123456 render=117890
SCROLL count=2300 rows=31 top=700 thumb=(4,145,8,44) drag=1
THEME dark=1
```

Do not ship this instrumentation in the final release if size matters; make it a build flag.

## Message debugging

For difficult Win32 behavior, log:

- WM_COMMAND / notification codes
- WM_SIZE
- WM_MOUSEMOVE / buttons / wheel
- WM_PAINT for custom surfaces
- show/hide transitions
- theme changes

Avoid logging every mouse move unless gated; logging itself can change timing.

## Debug principle

Do not infer a root cause solely from appearance. Confirm whether the bad pixels/state belong to:

- parent client background
- child client area
- non-client frame/scrollbar
- queued repaint
- Z-order overlap
- stale model state
- actual data corruption
