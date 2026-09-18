# 已知问题与技术债务

[English](KNOWN_ISSUES_AND_TECH_DEBT.md) | 简体中文

> V8.4.23 历史快照。两个 P0 均已由 V8.4.24 稳定化线解决；P1 架构债务已由
> V8.5.1–V8.5.4 关闭（统一 Markdown 扫描、ViewController 所有权、动态
> arena、六节 PE + ASLR），P2 测试债务由 `tools/` 下的 Windows GUI 回归
> 工具关闭。现行发布门禁与限制见 `V8_6_3_RELEASE_RESULTS.md` 与根目录
> `manifest.json`。

## P0 — V8.4.23 中的活动功能缺陷

### P0-001 Preview 大纲导航可能把每一项都映射到文档末尾

已确认根因：`navigate_outline` 中被 `IsWindowVisible` 破坏的易失 RAX 数组
偏移。见 `CURRENT_CODE_AUDIT.md` 与
`patches/P0_PREVIEW_OUTLINE_RAX_CLOBBER.md`。

### P0-002 自定义大纲滚动条滑块不可靠地可见/可拖动

现场复现。确切的单行根因未确立。当前架构把状态/几何分散在多个例程中。
需要的响应：有界的控制器/状态重构，而不是继续堆补丁。

## P1 — 架构债务

- 多套视图状态表示（`preview_flag`、可见性、`view_hwnd`）。
- Outline 与 Preview 分别独立扫描 Markdown。
- 固定 2048 条大纲容量。
- 固定 131072 样式跨度容量。
- 固定 4 MiB 文件上限 / 大型静态缓冲区。
- 布局计算仍分散在多个例程，而非单一真正的 LayoutManager。
- 消息泵拦截子窗口鼠标消息，同时充当控制器。
- 自定义滚动表面的绘制、hover、命中测试与拖动尚未消费同一份不可变几何
  记录。

## P1 — 构建布局债务

当时的文本区段距 RDATA 仅剩约 1.2 KiB 余量。主要代码增长需要 PE 布局重构。

## P2 — PE 加固债务

- 单一 RWX 节
- 无重定位/ASLR
- 无 `.pdata` unwind 元数据
- 无 CFG 元数据
- 静态数据无只读分离

这些不是当时 UI bug 的成因，但如果该实验要变成长期产品，它们很重要。

## P2 — 测试债务

在 Codex/代理能在带调试/插桩的 Windows 上运行之前，许多视觉/状态修复由
用户手工验证。构建（半）自动化的 Windows 回归工具是接管的早期任务之一。
