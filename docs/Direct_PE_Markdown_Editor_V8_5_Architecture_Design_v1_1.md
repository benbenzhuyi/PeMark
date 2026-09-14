# PeMark · 码记（Direct-PE Markdown Editor）新架构设计文档

> Architecture Design Revision 1.1 — incorporates V8.4.20 real-device findings on custom scrollbar ownership and paint lifecycle.

**文档版本：1.0**  
**设计目标版本：V8.5**  
**验证/过渡版本：V8.4.20**  
**生成方式约束：继续保持“直接生成 PE32+ / x86-64 机器码，不调用 C/C++ 编译器、汇编器或链接器”**

---

## 1. 文档目的

V8.4 系列已经证明：一个大模型可以在没有传统编译链的条件下，直接构造一个可运行、可迭代、具备 Markdown 编辑、渲染、大纲、主题、状态栏、查找替换和大文件支持的 Windows x64 GUI 应用。

但 V8.4.9～V8.4.19 的迭代也暴露出一个典型工程问题：**局部修复开始彼此耦合**。例如：

- 为解决 Outline 滚动条显示问题，引入独立 SCROLLBAR；
- 为解决 SCROLLBAR 与 ListBox 重绘竞争，又引入 gutter / clip / frame repaint；
- 主题切换、滚动、Outline 显隐、Preview 懒格式化、窗口布局之间相互触发；
- 一个局部的 Win32 控件行为变化，可能影响另一个完全不相关的模块。

因此，从 V8.5 开始，软件必须从“功能堆叠型”结构迁移为**分层、单向数据流、明确所有权、集中布局/主题/视图状态管理**的新架构。

V8.4.20 不作为 V8.5 的最终实现，而作为**架构预演版（Architecture Preview）**：优先验证最容易反复出问题的 UI 基础设施——Layout、Theme、Outline Scrollbar、Viewport 状态——是否可以按新架构原则稳定运行。

---

# 2. 总体设计原则

## 2.1 单一事实来源（Single Source of Truth）

文档内容只允许有一个权威来源：

```text
Document Model
Canonical Markdown / UTF-16 / CRLF
```

Source Editor、Markdown Renderer、Outline、Position Map 都只能从 Document Model 派生，不允许彼此回写。

禁止：

```text
Preview -> Source
Outline -> Source
Preview -> Outline
```

允许：

```text
Source Edit -> Document Model
Document Model -> Parser
Parser -> Render Model / Outline Model / Position Map
```

---

## 2.2 单向数据流

```text
                   User Input
                       |
                       v
                 Source Editor
                       |
                       v
                 Document Model
                       |
                       v
                 Markdown Parser
          +------------+-------------+
          |            |             |
          v            v             v
    Render Model  Outline Model  Position Map
          |            |             |
          +------------+-------------+
                       |
                       v
                View Controller
                       |
                       v
                    UI Layer
```

任何 UI 控件都不能成为业务状态的唯一保存位置。

---

## 2.3 视觉宽度与交互命中宽度分离

以后所有“看起来应该细、但鼠标应该容易抓住”的控件都遵循这一原则。

示例：

```text
Visual Divider: 1 px
Resize Hit Zone: 8 px

Scrollbar thumb visual width: 6~8 px
Scrollbar hit/gutter width: system scrollbar metric / DPI adaptive
```

这条原则适用于：

- Outline / Editor 分隔线；
- Overlay Scrollbar；
- 窗口 resize grip；
- 可拖动边界。

---

## 2.4 几何布局只有一个权威计算点

禁止多个模块分别调用 `MoveWindow()` 并各自计算坐标。

统一由：

```text
Layout Manager
```

计算并输出：

```text
LayoutRect
├─ menuBand
├─ content
├─ outlineContent
├─ outlineScrollbarGutter
├─ outlineDivider
├─ outlineResizeHitZone
├─ documentSurface
└─ statusBar
```

其他模块只能消费这些结果。

---

## 2.5 Theme 只改变 Palette，不改变业务逻辑

Light / Dark 不能触发 Markdown 重解析、Document Model 重建或 Outline 重建。

```text
Theme change
    -> Palette swap
    -> invalidate affected surfaces
```

不允许：

```text
Theme change
    -> reparse Markdown
    -> rebuild render text
    -> rebuild outline
```

---

## 2.6 交互优先，维护任务延后

滚轮、拖动、缩放、选择、光标移动必须优先保持即时响应。

昂贵任务采用：

- debounce；
- lazy formatting；
- viewport-only update；
- dirty range；
- cache。

---

# 3. 新架构总览

```text
+----------------------------------------------------------+
|                         APP                              |
|                                                          |
|  +-------------------- AppState ----------------------+  |
|  | current file / flags / zoom / theme / mode / UI   |  |
|  +-----------------------------------------------------+  |
|                          |                               |
|             +------------+------------+                  |
|             |                         |                  |
|             v                         v                  |
|      Document Domain              UI State              |
|                                                          |
|  +------------------+       +-------------------------+  |
|  | Document Model   |       | View Controller         |  |
|  +--------+---------+       | caret / viewport / mode |  |
|           |                 +-----------+-------------+  |
|           v                             |                |
|  +------------------+                   v                |
|  | Markdown Parser  |            +--------------+         |
|  +----+----+----+---+            | Layout Mgr   |         |
|       |    |    |                +------+-------+         |
|       |    |    |                       |                 |
|       v    v    v                       v                 |
| Render  Outline  Position          UI Surfaces            |
| Model   Model    Map          Source / Preview / Outline  |
|                               Scrollbar / Status / Menu   |
|                                                          |
|              +-------------------------------+           |
|              | Theme Palette / UI Metrics    |           |
|              +-------------------------------+           |
+----------------------------------------------------------+
```

---

# 4. 模块设计

## 4.1 AppState

集中保存全局状态，但不保存大文本本体。

建议字段：

```text
AppState
├─ current_path
├─ document_dirty
├─ preview_mode
├─ outline_visible
├─ status_visible
├─ word_wrap
├─ zoom_pct
├─ theme_id
├─ encoding
├─ eol_mode
└─ window/session flags
```

### 不变量

- UI 菜单勾选必须只反映 AppState；
- 菜单命令先更新 AppState，再通知对应 Controller；
- 主题状态不能分散存到多个控件中。

---

## 4.2 Document Model

### 责任

- 保存 Markdown 原文；
- 内部统一 UTF-16；
- 内部统一 CRLF；
- 保存 document length / revision；
- 保存 dirty range。

```text
DocumentModel
├─ text[]
├─ length
├─ revision
├─ dirty_start
├─ dirty_end
└─ line index (future)
```

### 文件打开

```text
File bytes
 -> decode
 -> normalize line endings
 -> Document Model
 -> Source View
 -> Parser
```

### 文件保存

```text
Document Model
 -> target encoding
 -> file
```

Source EDIT 不再是“保存前临时抓全文”的权威数据库。

---

## 4.3 Markdown Parser

V8.5 必须只有**一套** Markdown 解析状态机。

输出三个派生模型：

```text
Markdown Parser
├─ Render Model
├─ Outline Model
└─ Position Map
```

### Block Parser

统一维护：

- Heading H1-H6；
- Paragraph；
- fenced code block；
- block quote；
- list；
- horizontal rule；
- future table/task list。

### Inline Parser

统一维护：

- bold；
- italic；
- inline code；
- link；
- future strikethrough/image。

### Fenced Code 状态

必须记录：

```text
fence_char
fence_length
inside_fence
```

Outline Parser 不再自行扫描 `#`，而直接消费 Parser 产生的 Heading 节点。

---

## 4.4 Render Model

Render Model 不等同于 RichEdit。

```text
RenderModel
├─ text
├─ text_length
├─ spans[]
│  ├─ start
│  ├─ end
│  ├─ semantic_type
│  └─ semantic_flags
└─ revision
```

semantic_type 示例：

```text
BODY
H1...H6
BOLD
ITALIC
INLINE_CODE
CODE_BLOCK
LINK
QUOTE
LIST_MARKER
```

Theme 不改变 semantic_type，只改变 semantic_type -> Style 的映射。

---

## 4.5 Outline Model

```text
OutlineNode
├─ source_pos
├─ render_pos
├─ level
├─ title_start
├─ title_len
└─ parent/next (future tree)
```

### 原则

- Outline 只消费 Markdown Parser 的 Heading 节点；
- 不允许自行重新识别 Markdown；
- 点击 Outline 通过 Position Map 导航；
- 以后可以自然扩展折叠树，而不改 Markdown Parser。

---

## 4.6 Position Map

用于 Source / Preview / Outline 三者坐标统一。

```text
source_offset <-> render_offset
```

需要支持：

- caret mapping；
- selection mapping；
- viewport anchor mapping；
- outline navigation。

### Anchor

切换模式时保存：

```text
ViewAnchor
├─ document/source position
├─ caret offset
├─ selection
├─ top visible source position
└─ fractional viewport position (future)
```

不再依赖 Win32 EDIT/RichEdit 的“视觉行号”互相换算。

---

# 5. View Controller

View Controller 是 Document/Render 与 Win32 控件之间的唯一中介。

```text
ViewController
├─ enter_source_mode()
├─ enter_preview_mode()
├─ capture_anchor()
├─ restore_anchor()
├─ set_zoom()
├─ navigate_to_source_pos()
└─ on_viewport_changed()
```

### Source/Preview 切换

```text
capture ViewAnchor
 -> hide old view
 -> show new view
 -> map anchor
 -> restore viewport
```

切换模式绝不能修改 Document Model。

---

# 6. Preview Rendering Pipeline

## 6.1 两阶段渲染

### 阶段 A：Parse / Model

```text
Document revision changed
 -> Parser
 -> Render Model
```

只在文档内容变化时执行。

### 阶段 B：Viewport Formatting

```text
viewport changed
 -> find spans intersecting viewport
 -> apply only visible/near-visible styles
```

缩放、主题、滚动不能触发阶段 A。

---

## 6.2 大文件策略

目标：1 MB 级 Markdown 在 Preview 中仍保持交互即时。

```text
全文：只保留 Render Model / span metadata
屏幕：只格式化 visible range + preload margin
```

建议：

```text
preload margin = viewport 前后约 1~2 屏
```

避免固定 40K 字符这种与屏幕尺寸无关的魔法数。

---

## 6.3 Dirty Range

文档编辑后，不立即全量重建未来所有结构。

V8.5 第一阶段可以仍做全文 Parser，但接口必须支持：

```text
parse(document, dirty_range)
```

为未来 incremental parse 留接口。

---

# 7. Layout Manager

## 7.1 UiMetrics

所有像素尺寸集中管理：

```text
UiMetrics
├─ outline_default_width
├─ outline_min_width
├─ outline_max_width
├─ divider_visual_width = 1
├─ divider_hit_width = 8
├─ scrollbar_gutter_width
├─ scrollbar_thumb_visual_width
├─ editor_margin = 10
├─ outline_row_height
├─ status_height
└─ dpi
```

禁止在业务函数中出现散落的 `228 / 17 / 8 / 10 / 30` 等硬编码。

---

## 7.2 LayoutRect

一次计算全部几何：

```text
LayoutRect
├─ outline_content
├─ outline_scroll_gutter
├─ divider_visual
├─ divider_hit_zone
├─ document
├─ status
└─ corner
```

### 关键不变量

所有内容区统一：

```text
content_top = 0
content_bottom = client_h - status_h
```

Outline、Scrollbar、Divider、Document 的 Y/H 必须来自同一个 `contentRect`。

---

# 8. Outline Scrollbar 新设计

这是 V8.4.20 的重点验证模块。

## 8.1 放弃的方案

V8.4 已经验证以下方案长期成本过高：

1. ListBox non-client `WS_VSCROLL` 动态 Show/Hide；
2. 用额外 window 裁原生 scrollbar 1~2px；
3. 独立经典 `SCROLLBAR` 子控件依赖 Windows theme；
4. scrollbar 与 ListBox 绘制区域重叠。

---

## 8.2 V8.5 目标方案：自绘 Overlay Scrollbar

```text
Outline Content | Permanent Gutter | Divider | Editor
```

gutter 永远存在，因此 Outline 宽度永远不因 scrollbar 显隐变化。

### 视觉

- idle：不显示或极弱 track；
- hover：显示 thumb；
- drag：thumb 高亮；
- Light/Dark 颜色完全由 Theme Palette 决定。

### 交互

```text
wheel -> ListBox top index -> update thumb
thumb drag -> top index -> LB_SETTOPINDEX
track click -> page up/down
```

### 几何

```text
visible_rows = content_height / row_height
max_top = max(0, count - visible_rows)
thumb_h = max(min_thumb, visible_rows / count * track_h)
thumb_y = top_index / max_top * (track_h - thumb_h)
```

### 重要原则

- Visual thumb width 与 Hit/Gutter width 分离；
- 不使用 Windows SCROLLBAR 皮肤，因此不会出现经典/现代风格切换竞态；
- 不与 ListBox non-client 区域发生任何关系。

---

## 8.3 V8.4.20 实测后的实现约束：Scrollbar 必须拥有自己的 WM_PAINT 生命周期

V8.4.20 的第一版自绘 Overlay Scrollbar 使用了 `STATIC + SS_OWNERDRAW`，由父窗口通过 `WM_DRAWITEM` 代为绘制。实机测试证明这种做法虽然在概念上已经脱离原生 scrollbar 皮肤，但仍然存在父/子窗口重绘时序依赖：主题切换后可能出现整条 gutter 被系统背景色填充、thumb 不出现、旧主题宽条残留。

因此 V8.5 将进一步明确：

- Outline scrollbar 必须使用**独立自定义 child window class**；
- scrollbar 自己处理 `WM_PAINT / WM_ERASEBKGND`；
- 不依赖 `STATIC + SS_OWNERDRAW -> parent WM_DRAWITEM`；
- gutter 背景与 thumb 在同一个 child window 内一次绘制完成；
- Theme Palette 只替换 brush/color state，然后 `InvalidateRect(scrollbar)`；
- scrollbar window 永久占据固定 gutter，显隐仅改变 thumb 的绘制状态，不改变任何窗口几何；
- scrollbar 的 input state（hover/drag/page-click）与 paint state 同属 Scrollbar Controller，不允许分散到多个控件。

目标结构：

```text
Outline ListBox | Custom Scroll Surface | 1px Divider | 8px Resize Hit Zone | Document
                | own WM_PAINT          |             | logical only      |
```

这样 Scrollbar 的几何、输入、绘制、主题全部由同一模块拥有，避免再次出现“某个窗口负责状态，另一个窗口负责背景，父窗口负责真正绘制”的跨层耦合。

---

# 9. Theme System

## 9.1 ThemePalette

```text
ThemePalette
├─ window_bg
├─ menu_bg
├─ status_bg
├─ outline_bg
├─ document_bg
├─ divider
├─ text_primary
├─ text_secondary
├─ H1...H6
├─ bold
├─ italic
├─ link
├─ code_text
├─ code_bg
├─ quote_text
├─ quote_bg
├─ scrollbar_thumb
└─ scrollbar_thumb_hot
```

## 9.2 Theme 切换流程

```text
AppState.theme = newTheme
 -> rebuild Palette brushes
 -> update native frame/menu theme
 -> invalidate UI surfaces
 -> Preview viewport style recolor only
```

不允许重解析 Markdown。

---

# 10. Event Router

现在的 message pump 已经承担过多特殊判断。V8.5 需要逻辑化为：

```text
Message Pump
 -> Event Router
    ├─ Command events
    ├─ Document events
    ├─ Viewport events
    ├─ Outline scroll events
    ├─ Splitter events
    ├─ Theme events
    └─ Timer/debounce events
```

即使最终仍然生成纯机器码，也应该在生成器层保持这些逻辑块的独立函数/标签。

---

# 11. 性能预算

目标设备：现代 Windows x64 桌面。

建议交互预算：

| 操作 | 目标 |
|---|---:|
| 光标移动 | < 16 ms |
| 普通滚轮 | < 16 ms / frame |
| Zoom | < 50 ms |
| Outline 拖动 | < 16 ms |
| Light/Dark | < 100 ms 首屏 |
| Source/Preview 已缓存切换 | < 150 ms |
| 500 KB 文档打开 | < 1 s 目标 |
| 1 MB Preview 首次建立 | 渐进显示，不能冻结数秒 |

绝不允许把“全文 RichEdit 格式消息循环”放在滚轮/鼠标移动热路径上。

---

# 12. 内存策略

当前 Direct-PE 版本通过大 BSS 静态预留空间换取实现简单，这是实验阶段可以接受的。

V8.5 建议分两阶段：

### 阶段 1
继续使用 BSS 固定容量，但按模型分区：

```text
Document Buffer
Render Buffer
Position Map
Style Span Pool
Outline Node Pool
```

### 阶段 2
使用 VirtualAlloc 动态提交内存，只按实际文档大小增长。

目标是减少当前百 MB 级虚拟 BSS 对扩展性的限制。

---

# 13. 错误与边界处理

必须统一：

- parser span overflow；
- outline node overflow；
- file too large；
- invalid encoding；
- incomplete Markdown constructs；
- API call failures。

任何容量达到上限时都应：

```text
降级显示 + 明确状态
```

而不是越界、崩溃或悄悄停止渲染。

---

# 14. 测试架构

## 14.1 回归测试文件

保留并扩展：

- 1 KB 普通 Markdown；
- 500 KB；
- 1 MB；
- 大量 H1-H6；
- 10 万 style spans；
- fenced code 极端案例；
- 超长 Outline 标题；
- LF / CRLF / CR；
- UTF-8 / UTF-16LE / ANSI。

## 14.2 必测交互矩阵

```text
Source / Preview
x
Light / Dark
x
Outline on/off
x
100% / 150% zoom
x
small / large document
```

每次结构改动后不再只测试“当前 bug”，而执行矩阵回归。

---

# 15. V8.4.20：架构预演版范围

V8.4.20 不一次性重写全部 Markdown 内核，而先验证新架构最关键的 UI 基础设施。

## 本版实施

1. **UI Metrics 集中化**：减少滚动条/分隔栏相关 magic numbers；
2. **Outline Scrollbar 重构**：移除独立传统 `SCROLLBAR` 皮肤，改为永久 gutter + 自绘 overlay thumb；
3. **Scrollbar geometry 与 state 独立**：top/count/visibleRows/thumbRect 集中计算；
4. **Theme Palette 试点**：scrollbar / divider 颜色不再依赖 Windows scrollbar theme；
5. **Scrollbar interaction 与 splitter interaction 完全分离**；
6. 保留 V8.4.19 已验证的大文件 Document Model / Preview / Outline 功能，避免一次性重写所有模块。

## 本版暂不实施

- 完整统一 Markdown AST；
- incremental parser；
- VirtualAlloc 动态内存；
- Preview 真正虚拟化；
- Outline tree collapse；
- 全量 Event Router 重构。

这些进入 V8.5 正式重构。

---

# 16. V8.5 重构迁移顺序

建议严格按以下顺序：

```text
Phase 0  冻结 V8.4.19/20 稳定基线
Phase 1  AppState + UiMetrics + ThemePalette + LayoutManager
Phase 2  Document Model API
Phase 3  统一 Markdown Parser / Render / Outline
Phase 4  Position Map / ViewAnchor
Phase 5  Preview viewport formatter
Phase 6  Event Router / debounce scheduler
Phase 7  VirtualAlloc / capacity cleanup
Phase 8  自动回归测试与性能基准
```

每一阶段必须保持可运行，不做“大爆炸式一次性重写”。

---

# 17. 架构验收标准

V8.5 架构完成的判断标准不是“功能更多”，而是：

1. 一个功能修改不会无关地影响另外两个模块；
2. Theme 不触发 Parse；
3. Layout 只有一个坐标计算源；
4. Source/Preview/Outline 使用同一个 Markdown 语义结果；
5. Scrollbar 不依赖控件 non-client redraw 竞态；
6. 超大文档滚轮、缩放、主题切换不会触发全文格式化；
7. 所有模式切换都能稳定保留文档位置；
8. 500 KB～1 MB 文档成为常规测试场景，而不是特殊 case。

---

## 结论

V8.4 系列完成了“直接机器码也能不断长成真实软件”的能力验证；V8.5 的目标则是验证第二件更重要的事情：

> **即使没有传统高级语言和编译器，也可以按照成熟的软件工程方法建立清晰、可维护、可测试的架构。**

V8.4.20 是从“持续补丁”转向“架构驱动演进”的第一步。
