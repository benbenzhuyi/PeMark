# V8.6.4 工作区收尾验证结果

范围：V8.6 桌面工作区收尾。以下命令均在交互式 Windows 桌面会话中针对
`src/current/generate_markdown_editor_v8_6_4.py` 与
`bin/current/pemark_x64_v8_6_4.exe` 执行。

## 交付身份

| 项目 | 值 |
|---|---|
| 版本 | V8.6.4（工作区收尾） |
| 日期 | 2026-09-18 |
| 生成器 | `src/current/generate_markdown_editor_v8_6_4.py` |
| 生成器 SHA-256 | `f623b1042e1fd0b89c896be0c3dbce0866068af0df36c5855eeadf677dc6f35e` |
| 二进制 | `bin/current/pemark_x64_v8_6_4.exe` |
| 二进制大小 | 190,976 字节 |
| 二进制 SHA-256 | `e7924842c33237dbdc5d37f492bccff367bf0086333bf91bc823b6231571d1ac` |
| 机器码（.text） | 59,524 字节 |
| 虚拟 BSS | 102,400 字节 |
| PE 虚拟大小 | 196,608 字节 |

正式窗口标题为 `PeMark x64 V8.6.4 — Direct-PE Markdown Editor`。

## V8.6.4 用户可见变更

- **View → Files Panel / Outline Panel 改为互斥最大化开关**：
  两项菜单（命令 1308 / 1309）现在驱动与标题栏头部相同的
  `files_state` / `outline_state` 三态状态机：
  - 点击未勾选项 = 将自身最大化（`state = 0`）并将另一面板最小化（`state = 2`）；
    菜单勾选遵循同一规则，只有（最大化，最小化）这一对才带勾，half/half 不勾；
  - 点击已勾选项 = 恢复默认 half/half 布局，两项勾选均清除；
  - 标题栏单击/双击三态循环在 `resize_children` 后调用 `sync_panel_menu`，
    无论从哪个表面触发，勾选始终与标题栏头部同步。
- **预留的右侧栏入口（Ctrl+J）**：
  `View → Right Sidebar`（命令 1315，`Ctrl+J`）是 V9 AI 右侧栏的刻意预留位。
  它翻转 `right_sidebar_visible` 并同步菜单勾选；V8.6 布局暂不消费该状态。
  V9 的 AI 侧栏布局与标题行右侧栏按钮将共同消费它。
- **内存内最近文件列表（File 菜单，容量 10）**：
  `open_commit` 在提交 `current_path` 后调用 `push_recent_path` +
  `rebuild_recent_menu`。最近列表位于 BSS（`recent_paths`，10 × 512 WCHAR
  槽位，`recent_count`）：
  - 只有成功的打开事务才推进；New、Close 与 Save As 不入列；
  - 重复打开已在列表中的文件时先删旧条目再移到头部，列表永不保留重复项；
  - 列表在 10 条饱和；第 11 个不同文件挤出最旧的尾部条目；
  - `rebuild_recent_menu` 以静态命令段（`file_menu_base_count`，启动时一次性
    捕获为总项数减去尾部 separator + Exit）为基准删除 File 菜单尾差，再重新
    追加 `[分隔符, 最近文件项, 分隔符, Exit]`，保证 Exit 始终在最后且永不重复；
  - 最近文件项（命令 1316–1325）通过共享的打开事务重新打开：
    `temp_path ← recent[idx]`、`open_bypass_picker = 1`、
    `pending_destructive_action = 2`，然后进入 `destructive_request`。
    既有未保存保护、解码与提交路径完全复用，未做改动；
  - 超出范围的最近命令（索引 ≥ `recent_count`）被忽略。

新增导入：`GetMenuItemCount`、`RemoveMenu`。

## 发布门槛

| 检查项 | 结果 |
|---|---|
| 确定性构建 | 两次连续构建复现 `e7924842…` |
| 机器码回归 | 滚动条几何 thumb-ratio=JB、drag-clamp=JGE/JLE、LBUTTONDOWN=MSG.pt、thumb-min=32x4 全部通过 |
| 统一扫描 | 11 个语料库一致性通过；outline_push 在 pv8 循环内仅调用一次，旧扫描器已移除 |
| 视图状态/布局所有权 | preview_flag 与文档表面 ShowWindow 由 set_view_mode 族拥有，几何由 resize_children 族拥有，IsWindowVisible 已退役 |
| PE 检查 | PE32+ AMD64 GUI，六节 RX/R/RW/RW/R/R，无 W+X 页 |
| 导入表 | `GetMenuItemCount`/`RemoveMenu`/`DrawMenuBar`/`CreateAcceleratorTableW` 均在导入表 |
| 核心回归 `test_v8_6_4_menu.py` | 全绿：互斥最大化与勾选同步、Ctrl+J 翻转、最近文件推进/去重/移到头部/饱和/挤出/单 Exit 尾部重建、事务复用、超范围保护 |
| GUI 冒烟 `smoke_test_v8_5_1.py` | 17/17 通过；WM_CLOSE 干净退出码 0 |
| 主题切换 | 20 次连续模式切换存活，PREVIEW 不变量（恰好 1 个可见文档表面）保持 |
| 大纲开关 | 开/关均存活，条目数正确 |

## 已知限制

- 可执行文件未签名。
- Settings 齿轮按钮与右侧栏开关（Ctrl+J）为视觉占位；V8.6 布局暂不消费
  `right_sidebar_visible`，V9 AI 侧栏将共同消费该状态。
- `test_v8_6_panel.py` 在 divider hover 的 `SetCursorPos` 处依赖屏幕坐标，
  在高分屏/多显示器主机上可能因光标钳制而失败；该测试走真实鼠标指针，
  与本次代码改动（菜单/BSS/最近文件）无关。
- AI 集成与超出当前工作区的进阶编辑不在本版本范围内。

## 复现核心记录

```powershell
python -m py_compile src/current/generate_markdown_editor_v8_6_4.py
python src/current/generate_markdown_editor_v8_6_4.py
python tools/inspect_pe.py bin/current/pemark_x64_v8_6_4.exe
python tools/test_v8_6_4_menu.py
python tools/test_v8_6_keymap.py
python tools/test_v8_6_panel.py
python tools/smoke_test_v8_5_1.py bin/current/pemark_x64_v8_6_4.exe
```

## 发布前捕获的构建期 bug

1. `file_menu_base_count` 最初捕获了含尾部 separator + Exit 的完整静态项数，
   导致首次重建追加第二份 Exit。已修正为 `GetMenuItemCount() − 2`；
2. `cmd_right_sidebar` 在 `right_sidebar_visible` 的 `test32` 上用了
   `jcc(0x84)`（JE）而非 `0x85`（JNE），导致翻转后标志始终为零。已修正。

## 文档更新

- `CHANGELOG_UNRELEASED.md` / `CHANGELOG_UNRELEASED.zh-CN.md`：新增 V8.6.4 段；
- `docs/FEATURE_AND_SHORTCUT_SPEC.md`：File 菜单（最近文件）+ View 菜单（互斥最大化、Ctrl+J）；
- `docs/MILESTONE_PLAN.md` §6：切片 1 标记为已完成；
- `docs/CHANGELOG_V8_6_3.md` V8.6.1 段：澄清原生滚动条与自绘 overlay 的关系
  （滚动行为由原生 `WS_VSCROLL` 接管，自绘 overlay 仍是活跃回退/视觉层，
  并非死代码）。
