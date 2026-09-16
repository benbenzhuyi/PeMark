# Win32 API Surface — V8.6.1

Current imported APIs. When adding/removing imports, update this file and run PE inspection.

## KERNEL32.dll

`ExitProcess`, `CreateFileW`, `ReadFile`, `WriteFile`, `FlushFileBuffers`, `CloseHandle`, `VirtualAlloc`, `VirtualFree`, `MoveFileExW`, `DeleteFileW`, `GetLastError`, `GetFileSize`, `MultiByteToWideChar`, `WideCharToMultiByte`, `lstrcpyW`, `lstrlenW`, `GetModuleHandleW`, `CompareStringOrdinal`, `LoadLibraryW`, `GetProcAddress`, `MulDiv`, `FindFirstFileW`, `FindNextFileW`, `FindClose`

## USER32.dll

`CreateWindowExW`, `GetMessageW`, `TranslateMessage`, `DispatchMessageW`, `IsWindow`, `GetFocus`, `CreateMenu`, `CreatePopupMenu`, `AppendMenuW`, `GetWindowTextLengthW`, `GetWindowTextW`, `SetWindowTextW`, `SendMessageW`, `MoveWindow`, `SetWindowPos`, `MessageBoxW`, `SetFocus`, `RegisterClassExW`, `DefWindowProcW`, `PostQuitMessage`, `PostMessageW`, `LoadCursorW`, `DestroyWindow`, `ShowWindow`, `CheckMenuItem`, `GetWindowRect`, `GetClientRect`, `wsprintfW`, `RegisterWindowMessageW`, `InvalidateRect`, `UpdateWindow`, `RedrawWindow`, `GetCursorPos`, `ScreenToClient`, `SetCapture`, `ReleaseCapture`, `SetCursor`, `BeginPaint`, `EndPaint`, `SetScrollRange`, `SetScrollPos`, `ShowScrollBar`, `GetKeyState`, `GetSystemMetrics`, `SetTimer`, `KillTimer`, `GetMessageTime`, `CreateAcceleratorTableW`, `TranslateAcceleratorW`, `DestroyAcceleratorTable`, `IsDialogMessageW`, `SetForegroundWindow`, `DrawMenuBar`, `DrawTextW`, `FillRect`, `GetMenuStringW`, `SetMenuInfo`, `GetWindowDC`, `ReleaseDC`, `GetMenuItemRect`, `TrackPopupMenu`, `IsZoomed`, `TrackMouseEvent`, `SystemParametersInfoW`

## COMDLG32.dll

`GetOpenFileNameW`, `GetSaveFileNameW`, `FindTextW`, `ReplaceTextW`

## SHELL32.dll

`SHBrowseForFolderW`, `SHGetPathFromIDListW`, `ILFree`

## OLE32.dll

`CoInitializeEx`, `CoCreateInstance`, `CoTaskMemFree`

## SHLWAPI.dll

`StrStrW`, `StrStrIW`

## COMCTL32.dll

`InitCommonControlsEx`

## GDI32.dll

`CreateFontW`, `CreateFontIndirectW`, `DeleteObject`, `CreateSolidBrush`, `CreatePen`, `SetTextColor`, `SetBkColor`, `SetBkMode`, `GetClipBox`, `SelectObject`, `SaveDC`, `RestoreDC`, `IntersectClipRect`, `RoundRect`, `GetStockObject`, `MoveToEx`, `LineTo`, `Ellipse`, `Rectangle`

## UXTHEME.dll

`SetWindowTheme`

## DWMAPI.dll

`DwmSetWindowAttribute`
