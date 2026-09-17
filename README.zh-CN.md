# PeMark · 码记

**Direct-PE Markdown 编辑器**

简体中文 | [English](README.md)

PeMark · 码记是一个原生 Windows x64 Markdown 编辑器。Python 直接生成其
PE32+ 映像与 AMD64 机器码字节；生产版 EXE 不经过编译器、汇编器、链接器、
托管编译器、解释器打包器或内嵌 Python 运行时。

> **V8.6.3** 是当前稳定版。它保留 V8.5.4 的文档安全、动态容量与 PE 权限
> 分离基线，并完成 V8.6 桌面工作区、自定义标题行、大文档预览滚动修复和
> 高 DPI 字体清晰度优化。

## 主要功能

- 原生 Win32 x64 图形界面和紧凑的自定义标题/菜单行。
- Markdown 源码与格式化预览模式，并支持位置映射。
- 支持标题、粗体、斜体、行内代码、围栏代码块、引用、列表和链接。
- 预览渲染与大纲由同一次统一扫描生成。
- 可展开的工作区文件树，带 Fluent 文件夹/文档图标、键盘导航、内联重命名、
  新建文件/文件夹、回收站删除、复制路径、刷新和全部折叠。
- 支持明暗主题、缩放、自动换行、查找和替换。
- 使用 GDI 缩放 DPI 感知，在缩放显示器上清晰绘制编辑区、菜单和侧边栏文字。
- 确定性 Direct-PE 构建，六个权限分离的 PE 节、ASLR，且不存在可写可执行节。

## 下载与校验

从 [PeMark V8.6.3 正式版](https://github.com/benbenzhuyi/PeMark/releases/tag/v8.6.3)
下载 `pemark_x64_v8_6_3.exe`。

SHA-256：

```text
6b26585bb453010e358c726931d96f43cf5c4ef27cd02d1aff6101ad378698df
```

当前 EXE 尚未进行数字签名，Windows SmartScreen 或安全软件可能显示警告。
运行前请核对哈希。

## 系统和构建要求

运行环境：

- 64 位 Windows 10 或 Windows 11；
- Windows 自带的 `msftedit.dll` Rich Edit 组件。

构建和确定性测试：

- Python 3.10 或更高版本；
- 仅用于测试的 `unicorn`。

```powershell
python -m pip install -r requirements-dev.txt
python .\src\current\generate_markdown_editor_v8_6_3.py
```

输出文件为 `bin/current/pemark_x64_v8_6_3.exe`。

## 验证

```powershell
python .\tools\build_current.py
python .\tools\test_v8_5_1.py .\src\current\generate_markdown_editor_v8_6_3.py
python .\tools\inspect_pe.py .\bin\current\pemark_x64_v8_6_3.exe
python .\tools\smoke_test_v8_5_1.py .\bin\current\pemark_x64_v8_6_3.exe
Get-FileHash -Algorithm SHA256 .\bin\current\pemark_x64_v8_6_3.exe
```

GUI 冒烟测试必须在可交互的 Windows 桌面会话中运行。

正式版验证包括：

- 连续两次构建得到预期 SHA-256；
- 13/13 组机器码行为测试与 210/210 组滚动条几何测试；
- 17/17 项 Windows GUI 冒烟检查与 5/5 次干净退出；
- 打开/编码、原子保存、破坏性转换和各 arena 故障注入套件；
- 工作区文件树、文件操作、键盘导航、自定义标题行、主题和 DPI 模式的真实进程测试；
- 六节权限为 RX/R/RW/RW/R/R，不存在 W+X 页面。

详细证据见 [V8.6.3 发布验证结果](docs/V8_6_3_RELEASE_RESULTS.md) 和
[中文文档索引](docs/README.zh-CN.md)。

## 已知限制

- EXE 尚未进行数字签名。
- 设置齿轮和右边栏开关目前是可悬停的视觉占位。
- unwind 表合法且可解析，但尚未证明从首个 PeMark 栈帧继续完整回溯；PeMark
  不使用异常，因此不影响当前行为。
- AI 集成和当前桌面工作区之外的高级编辑功能不在本版本范围内。

请保留重要文档的独立副本。

安全问题报告方式见 [SECURITY.zh-CN.md](SECURITY.zh-CN.md)，参与开发请见
[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。

## 许可证

PeMark 使用 [MIT License](LICENSE)。[中文参考译文](LICENSE.zh-CN.md)
仅供阅读，英文原文具有法律效力。
