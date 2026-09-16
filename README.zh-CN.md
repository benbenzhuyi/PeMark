# PeMark · 码记

**Direct-PE Markdown 编辑器**

简体中文 | [English](README.md)

PeMark · 码记是一个原生 Windows x64 Markdown 编辑器。它由 Python 直接生成
PE32+ 文件结构和 AMD64 机器码字节。

生产版 EXE 不经过 C/C++、Rust 或 .NET 编译器，也不使用汇编器、链接器、
解释器打包器或内嵌 Python 运行时。Python 只在构建和测试阶段使用。

> **V8.6.1** 是当前发布快照。它保留 V8.5.4 的文档安全、动态容量与 PE 加固
> 基线，并加入合并后的 Codex 风格标题行、左右栏开关和 Fluent 工具图标。
> V8.6 的文件夹树与文件操作仍是后续切片。

## 主要功能

- 原生 Win32 x64 图形界面。
- Markdown 源码与格式化预览模式，并支持位置映射。
- 支持标题、粗体、斜体、行内代码、围栏代码块、引用、列表和链接。
- 预览渲染与大纲由同一次统一扫描生成。
- 支持明暗主题、缩放、自动换行、查找和替换。
- 构建结果确定：相同源码连续构建得到相同 EXE。
- 保留历史生成器和二进制，便于回归分析。

## 下载与校验

从 V8.6.1 发布/当前快照下载 `pemark_x64_v8_6_1.exe`（如果还没有附加二进制，
可直接用生成器本地构建）。

SHA-256：

```text
abd79de90999a70f3b5328c63cb73109ea0a38cac85c5ed59f197cab397ac4bc
```

当前 EXE 尚未进行数字签名。Windows SmartScreen 或安全软件可能显示警告。
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
python .\src\current\generate_markdown_editor_v8_6_1.py
```

输出文件为 `bin/current/pemark_x64_v8_6_1.exe`。

## 验证

```powershell
python .\tools\build_current.py
python .\tools\test_v8_5_1.py .\src\current\generate_markdown_editor_v8_6_1.py
python .\tools\inspect_pe.py .\bin\current\pemark_x64_v8_6_1.exe
python .\tools\smoke_test_v8_5_1.py .\bin\current\pemark_x64_v8_6_1.exe
```

GUI 冒烟测试必须在可交互的 Windows 桌面会话中运行。

当前验证结果：

- 13/13 组已生成机器码行为测试通过；
- 210/210 组大纲滚动条边界组合通过；
- 17/17 项 Windows GUI 冒烟检查通过；
- 5/5 次普通关闭均返回退出码 0；
- 打开/编码事务矩阵与原子保存故障注入通过；
- arena 分配失败与 140000 跨度容量用例通过；
- 连续两次构建的 EXE 哈希完全一致。

## 已知限制

V8.6.1 尚未完成以下发布门槛：

- V8.6 文件夹树的建模与新建/重命名/删除/刷新等操作；
- 新标题行的更广泛跨机器验证；
- 代码签名仍不在个人开源实验项目的范围内；
- 当前切片之外的工作区、高级编辑与 AI 功能。

请勿把重要文档只保存在本预览版中。

详细变更见 [V8.6.1 验证记录](docs/V8_6_1_RELEASE_RESULTS.md) 和
[中文文档索引](docs/README.zh-CN.md)。
安全问题报告方式见 [SECURITY.zh-CN.md](SECURITY.zh-CN.md)，参与开发请见
[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。

## 许可证

PeMark 使用 [MIT License](LICENSE)。[中文参考译文](LICENSE.zh-CN.md)
仅供阅读，英文原文具有法律效力。
