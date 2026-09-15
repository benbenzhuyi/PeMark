# Win32 API Surface — V8.5.2

Current imported APIs. When adding/removing imports, update this file and run PE inspection.

## KERNEL32.dll

`ExitProcess`, `CreateFileW`, `ReadFile`, `WriteFile`, `FlushFileBuffers`, `CloseHandle`, `VirtualAlloc`, `VirtualFree`, `MoveFileExW`, `DeleteFileW`, `GetLastError`, `GetFileSize`, `MultiByteToWideChar`, `WideCharToMultiByte`, `lstrcpyW`, `lstrlenW`, `GetModuleHandleW`, `CompareStringOrdinal`, `LoadLibraryW`, `GetProcAddress`, `MulDiv`

`VirtualAlloc` and `VirtualFree` own the V8.5.2 dynamic Outline arena.

## USER32.dll

`CreateWindowExW`, `GetMessageW`, `TranslateMessage`, `DispatchMessageW`, `IsWindow`, `CreateMenu`, `CreatePopupMenu`, `AppendMenuW`, `GetWindowTextLengthW`, `GetWindowTextW`, `SetWindowTextW`, `SendMessageW`, `MoveWindow`, `SetWindowPos`, `MessageBoxW`, `SetFocus`, `RegisterClassExW`, `DefWindowProcW`, `PostQuitMessage`, `PostMessageW`, `LoadCursorW`, `DestroyWindow`, `ShowWindow`, `CheckMenuItem`, `GetWindowRect`, `GetClientRect`, `wsprintfW`, `RegisterWindowMessageW`, `InvalidateRect`, `UpdateWindow`, `RedrawWindow`, `GetCursorPos`, `ScreenToClient`, `SetCapture`, `ReleaseCapture`, `SetCursor`, `BeginPaint`, `EndPaint`, `SetScrollRange`, `SetScrollPos`, `ShowScrollBar`, `GetKeyState`, `GetSystemMetrics`, `SetTimer`, `KillTimer`, `CreateAcceleratorTableW`, `TranslateAcceleratorW`, `DestroyAcceleratorTable`, `IsDialogMessageW`, `SetForegroundWindow`, `DrawMenuBar`, `DrawTextW`, `FillRect`, `GetMenuStringW`, `SetMenuInfo`, `GetWindowDC`, `ReleaseDC`, `GetMenuItemRect`

## COMDLG32.dll

`GetOpenFileNameW`, `GetSaveFileNameW`, `FindTextW`, `ReplaceTextW`

## SHLWAPI.dll

`StrStrW`, `StrStrIW`

## COMCTL32.dll

`InitCommonControlsEx`

## GDI32.dll

`CreateFontW`, `DeleteObject`, `CreateSolidBrush`, `SetTextColor`, `SetBkColor`, `SetBkMode`, `GetClipBox`, `SelectObject`, `SaveDC`, `RestoreDC`, `IntersectClipRect`

## UXTHEME.dll

`SetWindowTheme`

## DWMAPI.dll

`DwmSetWindowAttribute`
