# PeMark 未发布变更

[English](CHANGELOG_UNRELEASED.md) | 简体中文

V8.6.5 已于 2026-09-19 发布；发布记录见
`docs/V8_6_5_RELEASE_RESULTS.md`，GitHub 发布说明见
`docs/RELEASE_V8_6_5_GITHUB.md`。V8.6.3 于 2026-09-18 发布，记录在
`docs/CHANGELOG_V8_6_3.md`。

## 接管审计（2026-09-18）

纯文档变更；未修改生成器、二进制或测试：

- `CODEX_START_HERE.md` 基线从 V8.6.1 更新到 V8.6.3（版本、生成器、
  二进制、SHA-256、验证记录、首次会话命令与当前优先级）；
- 为 `docs/ROADMAP.md`、`docs/KNOWN_ISSUES_AND_TECH_DEBT.md` 与
  `DEVELOPMENT_MANUAL.md` 添加历史标注，因为它们的 V8.4 时代内容已被
  `MILESTONE_PLAN.md`、`V8_6_3_RELEASE_RESULTS.md` 与
  `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md` 取代；
- `HANDOFF_CHECKLIST.md` 的历史指针更新到 V8.6.3 基线；
- 在接管主机上重新验证基线：两次连续构建复现 `5fe17a49…`，机器码回归
  13/13 组，PE 检查为六节 RX/R/RW/RW/R/R 且无 W+X 页，GUI 冒烟 17/17
  并干净退出（退出码 0）。

## 中文版文档（2026-09-18）

- 为六个接管文档新增简体中文版本：`CODEX_START_HERE.zh-CN.md`、
  `DEVELOPMENT_MANUAL.zh-CN.md`、`HANDOFF_CHECKLIST.zh-CN.md`、
  `docs/ROADMAP.zh-CN.md`、`docs/KNOWN_ISSUES_AND_TECH_DEBT.zh-CN.md` 与
  本 `CHANGELOG_UNRELEASED.zh-CN.md`；
- 对应的英文原版顶部增加了语言切换链接；
- 英文版为该仓库的工作语言：内容变更先更新英文版，再同步中文版；
- 双语文档规则已固化为 `AGENTS.md`（"Change discipline" 一节）的常设仓库
  约束：以后所有新生成的项目文档必须同时提供英文与简体中文两个版本。

## V8.6.4 — V8.6 工作区收尾（2026-09-18）

生成器 `src/current/generate_markdown_editor_v8_6_4.py`；二进制
`bin/current/pemark_x64_v8_6_4.exe`；确定性构建哈希
`e7924842c33237dbdc5d37f492bccff367bf0086333bf91bc823b6231571d1ac`。

### View 菜单面板开关改为互斥最大化开关

`View → Files Panel`（1308）与 `View → Outline Panel`（1309）原先共用旧版
`set_panel_mode` 切换。现在它们驱动与标题栏头部相同的
`files_state` / `outline_state` 三态状态机：

- 点击未勾选项 = 将自身最大化（`state = 0`）并将另一面板最小化
  （`state = 2`）；菜单勾选遵循同一规则，只有
  （最大化，最小化）这一对才带勾，half/half 不勾；
- 点击已勾选项 = 恢复默认 half/half 布局，两项勾选均清除；
- 标题栏单击/双击三态循环在 `resize_children` 后调用
  `sync_panel_menu`，无论从哪个表面触发，勾选始终与标题栏头部同步。

### 预留的右侧栏入口（Ctrl+J）

`View → Right Sidebar`（1315，`Ctrl+J`）是 V9 AI 右侧栏的刻意预留位。
它翻转 `right_sidebar_visible` 并同步菜单勾选；V8.6 布局暂不消费该状态。
V9 的 AI 侧栏布局与标题行右侧栏按钮将共同消费它。

### 内存内最近文件列表（File 菜单，容量 10）

`open_commit` 在提交 `current_path` 后调用 `push_recent_path` +
`rebuild_recent_menu`。最近列表位于 BSS（`recent_paths`，10 × 512 WCHAR
槽位，`recent_count`）：

- 只有成功的打开事务才推进；New、Close 与 Save As 不入列；
- 重复打开已在列表中的文件时先删旧条目再移到头部，列表永不保留重复项；
- 列表在 10 条饱和；第 11 个不同文件挤出最旧的尾部条目；
- `rebuild_recent_menu` 以静态命令段（`file_menu_base_count`，启动时
  一次性捕获为总项数减去尾部 separator + Exit）为基准删除 File 菜单尾差，
  再重新追加 `[分隔符, 最近文件项, 分隔符, Exit]`，保证 Exit 始终在最后且
  永不重复；
- 最近文件项（命令 1316–1325）通过共享的打开事务重新打开：
  `temp_path ← recent[idx]`、`open_bypass_picker = 1`、
  `pending_destructive_action = 2`，然后进入 `destructive_request`。
  既有未保存保护、解码与提交路径完全复用，未做改动；
- 超出范围的最近命令（索引 ≥ `recent_count`）被忽略。

新增导入：`GetMenuItemCount`、`RemoveMenu`。

### 构建期断言与回归覆盖

- 构建期断言验证新命令路由（1308–1325、1315）、加速键项
  `(FVIRTKEY|FCONTROL, 0x4A, 1315)`、BSS 字段、`open_commit` 内的
  `push_recent_path` + `rebuild_recent_menu` 调用、`cmd_recent_open` 中的
  `lstrcpyW` + bypass-picker + destructive-request 路径、
  `rebuild_recent_menu` 的按位置删除 + 重新追加 Exit 逻辑，以及
  `file_menu_base_count` 以总项数 − 2 捕获以防 Exit 重复；
- `tools/test_v8_6_4_menu.py` 驱动真实进程：互斥最大化与勾选同步、
  Ctrl+J 翻转、最近文件的推进/去重/移到头部/饱和/挤出/单 Exit 尾部重建、
  事务复用与超范围保护；
- `tools/test_v8_6_keymap.py` 将 `Ctrl+J` 从预留集移入期望表，并检查
  `m_right_sidebar` 提示文本；
- 既有套件保持通过：`test_v8_6_panel`、`smoke_test_v8_5_1`（17/17）、
  `test_stabilization`、`test_v8_6_tree_ui`、`test_v8_6_navigation`、
  `test_v8_6_keymap`、`test_v8_6_caption`、`test_v8_6_dpi`、
  `test_v8_6_theme_picker`、`test_v8_6_tree_model`、
  `test_v8_6_workspace_enum`。

### 发布前捕获的构建期 bug

1. `file_menu_base_count` 最初捕获了含尾部 separator + Exit 的完整静态项数，
   导致首次重建追加第二份 Exit。已修正为 `GetMenuItemCount() − 2`；
2. `cmd_right_sidebar` 在 `right_sidebar_visible` 的 `test32` 上用了
   `jcc(0x84)`（JE）而非 `0x85`（JNE），导致翻转后标志始终为零。已修正。

## 窗口边框区隔度（已于 V8.6.5 发布，2026-09-19）

发布记录：`docs/V8_6_5_RELEASE_RESULTS.md`；GitHub 发布说明：
`docs/RELEASE_V8_6_5_GITHUB.md`。

生成器 `src/current/generate_markdown_editor_v8_6_5.py`；二进制
`bin/current/pemark_x64_v8_6_5.exe`；构建哈希
`a038974bcd61c6a2720af5fb40ef7ad0c5c12c3745d801b8ef06e119b3b679e9`
（text 59658，预算 61440）。

### 由实测而非猜色得出的根因

深浅两种主题下窗口都没有可见轮廓。以下结论全部来自在运行窗口上的实测
（Windows 11 内部版本 26200，150% 缩放），不是推断：

- 通过 `DWMWA_BORDER_COLOR`(34) 注入洋红后，窗口最外 2 个物理像素在一帧内变成
  洋红，且该颜色在窗口缩放后依然保留。说明窗口边框由 DWM 拥有，并合成在任何
  落在这些像素上的 GDI 绘制之上；
- 在 V8.6.4 的 `WM_NCCALCSIZE` 行为下（客户区等于整个窗口），DWM 干脆不绘制
  边框——所以旧的 `wp_ncpaint` `FillRect` 代码本身就没有属于自己的可见画布，
  这与"被铺满客户区的子窗口盖住"是两个独立原因；
- `DwmGetWindowAttribute(34)` 在本窗口上返回 `E_INVALIDARG`，而
  `DwmSetWindowAttribute(34)` 返回 `S_OK` 且立即生效：该边框色在此是只写的。

因此边框不可见有两个独立原因：客户区覆盖整个窗口，DWM 没有可绘制的边框条；
以及 `DWMWA_BORDER_COLOR` 被设成了背景本身（深色 `#202020` 上用的是
`#1A1A1A`，浅色底用的是纯白）。

### 修复

- `wp_nccalcsize` 现在把返回的客户区矩形四边各内缩 1px，恢复 DWM 绘制边框所需
  的那条 1px 非客户区。子控件相对客户区定位，因此会自动内移 1px，布局代码
  一行未改；
- `DWMWA_BORDER_COLOR` 随主题取值：深色 `#3C3C3C`、浅色 `#B0B0B0`。深色值来自
  对 Windows 资源管理器截图的逐像素测量——资源管理器深色边框在同样的 `#202020`
  底面上读数为 `#3C3C3C`，150% 缩放下宽 2 个物理像素——因此 PeMark 的边框在
  亮度与粗细上都与资源管理器一致，而不是先前明显偏亮的 `#555555`。浅色分支需要
  把颜色写入拆成两次，否则属性 34 会与属性 35/36 共用同一个白色值；
- `wp_ncpaint` 不再用 GDI 绘制四边。该路径不可能压过 DWM，两者并存时反而会
  产生四条颜色各异的边。

### 验证

- 构建期断言同时锁住两个前提：四条 `rgrc[0]` 内缩写入必须存在，`wp_ncpaint`
  中不得出现 `FillRect` 与 `GetWindowDC`，两个边框色必须存在，且属性 34 不得
  使用 `0x001A1A1A` 与 `0xFFFFFFFF`；
- 运行窗口的像素实测：浅色模式下四边读数统一为 `#B0B0B0`，深色模式下统一为
  `#3C3C3C`（与资源管理器相同的 2 个物理像素），实时切换 Light/Dark 时四边在
  一帧内同步变化。

### 已知后续项

边框改由 DWM 负责后，`hbrush_border` 已不再被任何绘制路径引用。为控制本次改动
范围暂时保留；删除它会牵动主题销毁链，应作为独立切片处理。
