# 开发手册 — 纯二进制原生 Windows 开发

[English](DEVELOPMENT_MANUAL.md) | 简体中文

> V8.4 时代的历史手册。现行日常工作流政策见
> `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`。

## 目的

本手册是与 Codex 或其他编码代理一起继续开发 PeMark（Direct-PE Markdown
编辑器）的实践性日常指南。本项目有意不做常规的 Python GUI 应用：Python 只是
构建期的发射器；产出物是一个原生 Windows AMD64 PE 可执行文件。

## 1. 黄金工作流

每次变更都要：

1. 阅读相关架构/问题文档。
2. 复现当前基线并计算哈希。
3. 为一个有界的子系统变更建立分支/副本。
4. 先添加或确定一个确定性回归测试。
5. 修改生成器。
6. 运行 Python 语法检查 + PE 静态检查。
7. 在 Windows 上运行精确的回归序列。
8. 记录取证耗时/状态/日志，而不只是截图。
9. 更新 changelog、已知问题与哈希。
10. 之后才进入下一个子系统。

## 2. 构建模型

```text
Python 源生成器
    -> code/rdata/imports 的 bytearray
    -> x86-64 操作码 + rel32/RIP 修正
    -> PE 头/节
    -> 最终 .exe
```

不得向生产链路插入任何编译器/汇编器/链接器。反汇编器/调试器可用于分析。

## 3. 当时的源码组织

当时的生成器保留了 V8.4 血统的单体发射器形态，包含这些概念区域：

- 常量/RDATA 字符串
- BSS 符号分配
- 导入表构建器
- x64 发射器类
- 启动/窗口创建
- 消息泵
- 命令处理
- 文件 I/O 与解码
- Source/Preview 切换
- 大纲与滚动条处理
- Markdown 解析器/渲染缓冲/样式映射
- 主题/布局/状态栏逻辑
- 自定义 WndProc
- PE 写出器

V8.5 应在保持行为不变的前提下，把这些拆成显式的构建期发射器模块或清晰
分离的区段。

## 4. 安全的发射函数模板

写机器码字节之前，先记录：

```text
例程名:
输入:
返回值:
BSS 读取:
BSS 写入:
保存的非易失寄存器:
必须跨调用存活的易失值:
调用的 Win32/内部函数:
栈帧大小/对齐:
```

然后发射 prologue/body/epilogue。把每次调用都视为会破坏易失寄存器。

## 5. 状态所有权

永远不要通过再添加一个独立标志来解决 UI 问题。

目标所有权：

- 文档文本 -> DocumentModel
- SOURCE/PREVIEW -> ViewController
- 大纲条目/导航 -> OutlineController
- 滚动条几何/拖动 -> OutlineScrollState
- 所有窗格矩形 -> LayoutManager
- 颜色/画刷 -> ThemePalette
- 解析后的 Markdown 语义 -> Parser/RenderModel

## 6. 调试构建

强烈建议：添加诸如 `DEBUG_DIAGNOSTICS=True` 的生成器选项，按条件导入/使用
`OutputDebugStringW` 并发射状态轨迹。复杂消息排序不要依赖视觉推断。

有用的诊断量：

```text
DOC revision len
VIEW mode, visible HWNDs
OUTLINE selected index/source offset
MAP source->render result/render_len
SCROLL count/rows/top/max/track/thumb rect/drag
LAYOUT rectangles
THEME palette id
```

## 7. Windows 测试循环

测试首次加载缺陷时使用干净冷启动。多次模式切换之后再开始的测试可能掩盖
初始化 bug。

始终测试：

- Open 之后立即处于 Source
- 第一次点击大纲
- 第一次 Ctrl+Shift+P
- 第一次在 Preview 中点击大纲
- 文档开头/中间/结尾的导航
- 长大纲拖动滑块
- 悬停展开之前立即切换 Light/Dark
- 冷启动后打开大文档

## 8. 二进制体积/布局纪律

V8.5.4 使用 `docs/PE_MEMORY_MAP_V8_5_4.md` 记录的扩展布局。代码重叠异常
仍然属于构建布局失败，绝不允许绕过。

长期方向是在保持直接生成的前提下，采用 PE 布局分配器与多节结构。

## 9. 版本记录

- V8.4.23：冻结的交接快照。
- V8.4.24：仅做稳定化。
- V8.5.1：更早的公开 Preview 基线。
- V8.5.3：动态容量。
- V8.5.4：文档安全与 PE 加固，当时的公开 Preview 基线。

除非回归矩阵确实在 Windows 上通过，否则不得把构建标记为"stable"。

## 10. 文档维护

行为变更时，至少更新以下之一：

- `docs/CURRENT_CODE_AUDIT.md`
- `docs/FEATURE_AND_SHORTCUT_SPEC.md`
- `docs/WIN32_API_SURFACE.md`
- `docs/REGRESSION_TEST_PLAN.md`
- `docs/VERSION_HISTORY.md`
- `docs/DECISION_LOG.md`

交接包的目的就是取代对原始 ChatGPT 对话的依赖。
