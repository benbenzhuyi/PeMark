# Codex 从这里开始

[English](CODEX_START_HERE.md) | 简体中文

这是一个纯 Direct-PE 的 Windows x64 项目。Python 生成器直接发射 PE32+ 映像与
AMD64 机器码。正式构建不得使用编译器、汇编器、链接器、托管运行时或解释器
打包器。

## 当前基线

- 版本：V8.6.3（稳定版，2026-09-18 发布）。
- 生成器：`src/current/generate_markdown_editor_v8_6_3.py`。
- 二进制：`bin/current/pemark_x64_v8_6_3.exe`。
- 预期 EXE SHA-256：
  `5fe17a495f691747e33d3372a78f202b442ae67cf55af2414ecba4a769186b21`。
- 验证记录：`docs/V8_6_3_RELEASE_RESULTS.md`。

V8.5.4 与 V8.6.1 仍保留在 `src/current/` 与 `bin/current/` 中，作为更早的
稳定版本；V8.4.23 冻结在 `archive/` 下。描述早期交接的文档属于历史证据，
除非更新的文档把同一问题重新采纳为活动工作。

## 首次会话流程

1. 阅读 `AGENTS.md`。
2. 阅读 `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`。
3. 阅读 `docs/MILESTONE_PLAN.md`。
4. 阅读 `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`。
5. 阅读 `docs/V8_6_3_RELEASE_RESULTS.md`。
6. 阅读 `docs/WIN64_ABI_RULES.md` 与 `docs/FAILED_APPROACHES.md`。
7. 运行 `python tools/build_current.py`。
8. 运行
   `python tools/test_v8_5_1.py src/current/generate_markdown_editor_v8_6_3.py`。
9. 用 `python tools/inspect_pe.py bin/current/pemark_x64_v8_6_3.exe` 检查 PE。

任何 GUI、消息循环、主题、布局、控件重建或关闭路径的变更之后，都要在
交互式 Windows 桌面会话中运行 `tools/smoke_test_v8_5_1.py`。

## 当前优先级

V8.6.3 已完成 V8.6 桌面工作区（自定义标题行、Fluent 图标、可展开文件树、
文件操作、高 DPI 清晰度）。V8.6 的剩余工作是 File 菜单底部的内存内最近
文件列表，以及把 `View → Files/Outline Panel` 改为显隐开关；此后按
`docs/MILESTONE_PLAN.md` §7 进入 V8.7 高级编辑。

一次只处理一个所有权边界，并为每个修复增加确定性回归。在添加任何新机制之前，
先回答"这一步的最小充分工程量是什么"，并按层级执行验证（见
`docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md` 5.1）。
