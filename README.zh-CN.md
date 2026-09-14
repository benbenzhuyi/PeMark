# PeMark · 码记

**Direct-PE Markdown 编辑器**

简体中文 | [English](README.md)

PeMark · 码记是一个原生 Windows x64 Markdown 编辑器。它由 Python 直接生成
PE32+ 文件结构和 AMD64 机器码字节。

生产版 EXE 不经过 C/C++、Rust 或 .NET 编译器，也不使用汇编器、链接器、
解释器打包器或内嵌 Python 运行时。Python 只在构建和测试阶段使用。

> **V8.5.1 Preview** 是当前公开预览版。编辑、预览、大纲、主题、自动换行、
> 大文档导航和正常退出已经通过回归测试；文件安全相关功能仍在完善。

## 主要功能

- 原生 Win32 x64 图形界面。
- Markdown 源码与格式化预览模式，并支持位置映射。
- 支持标题、粗体、斜体、行内代码、围栏代码块、引用、列表和链接。
- 预览渲染与大纲由同一次统一扫描生成。
- 支持明暗主题、缩放、自动换行、查找和替换。
- 构建结果确定：相同源码连续构建得到相同 EXE。
- 保留历史生成器和二进制，便于回归分析。

## 下载与校验

V8.5.1 Preview 发布后，从 GitHub Releases 下载
`pemark_x64_v8_5_1.exe`。

SHA-256：

```text
b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f
```

当前 EXE 尚未进行数字签名。由于它采用直接生成的 PE 结构和单一 RWX 节，
Windows SmartScreen 或安全软件可能显示警告。运行前请核对哈希。

## 系统和构建要求

运行环境：

- 64 位 Windows 10 或 Windows 11；
- Windows 自带的 `msftedit.dll` Rich Edit 组件。

构建和确定性测试：

- Python 3.10 或更高版本；
- 仅用于测试的 `unicorn`。

```powershell
python -m pip install -r requirements-dev.txt
python .\src\current\generate_markdown_editor_v8_5_1.py
```

输出文件为 `bin/current/pemark_x64_v8_5_1.exe`。

## 验证

```powershell
python .\tools\build_current.py
python .\tools\test_v8_5_1.py .\src\current\generate_markdown_editor_v8_5_1.py
python .\tools\inspect_pe.py .\bin\current\pemark_x64_v8_5_1.exe
python .\tools\smoke_test_v8_5_1.py .\bin\current\pemark_x64_v8_5_1.exe
```

GUI 冒烟测试必须在可交互的 Windows 桌面会话中运行。

当前验证结果：

- 12/12 组已生成机器码行为测试通过；
- 210/210 组大纲滚动条边界组合通过；
- 17/17 项 Windows GUI 冒烟检查通过；
- 5/5 次普通关闭均返回退出码 0；
- 连续两次构建的 EXE 哈希完全一致。

## 已知限制

V8.5.1 尚未完成以下发布门槛：

- Save/Save As 原子写入；
- 短写检测和恢复；
- 未保存内容保护；
- 异常编码和旧编码回退；
- 全部文件大小与内部容量边界；
- 代码签名、ASLR 和 RX/R/RW 分节。

请勿把重要文档只保存在本预览版中。

详细变更见 [V8.5.1 中文发布说明](docs/RELEASE_V8_5_1_PREVIEW.zh-CN.md) 和
[中文文档索引](docs/README.zh-CN.md)。
安全问题报告方式见 [SECURITY.zh-CN.md](SECURITY.zh-CN.md)，参与开发请见
[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。

## 许可证

PeMark 使用 [MIT License](LICENSE)。[中文参考译文](LICENSE.zh-CN.md)
仅供阅读，英文原文具有法律效力。
