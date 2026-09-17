# PeMark DirectWrite 渲染现代化计划（草案）

状态：**Draft / 等待最小视觉 POC 决策**  
适用范围：V8.6.1 之后的渲染实验；不改变 V8.6.1 当前发布行为  
核心原则：第一阶段只回答“DirectWrite 是否让用户明显更满意”；在得到明确肯定前，
不引入 Markdown、滚动、PositionMap 和大文档。

## 1. 决策摘要

当前 Preview 是 `RICHEDIT50W`：解析器生成 `previewbuf`、样式区间和
`render_srcmap`，RichEdit 负责换行、滚动、布局和绘制，PeMark 通过
`EM_SETCHARFORMAT` 给可见区套用语义样式。文件树与 Outline 则是 GDI
owner-draw ListBox。用户看到的差异既包含字形光栅化，也包含字号、颜色、行距、
内容宽度和留白，不能把全部差异简单归因于 GDI。

下一步不直接替换正式 Preview，而是新增一个与正式程序隔离的
**DirectWrite Typography Lab**。它在一个固定尺寸窗口内并排显示：

1. 现有 RichEdit 路径；
2. DirectWrite + Direct2D 路径。

两侧使用写死在 `.rdata` 中的同一段中文样本，以及完全相同的字体、实际 DIP 字号、
字重、颜色、背景、内容宽度、内边距、行距和 DPI。它不打开文件、不解析 Markdown、
不滚动、不跳转，也不接触 PositionMap。只有通过人工视觉验收，才开始讨论真实
Preview。

## 2. 对外部建议的采纳与修正

采纳：

- 渲染层可以渐进替换，DocumentModel、Markdown 扫描器、Outline、PositionMap、
  文件事务和 PE 安全结构不需要推倒重来。
- 第一目标只应是只读 Preview，不应同时自研 Source 编辑器。
- WebView2 可以快速得到 Chromium 风格，但会改变 Direct-PE 原生实验的边界，
  因而不作为当前路线。
- 必须先做控制变量的 A/B 实验，而不是凭理论直接重构。

修正：

- `DirectWrite -> GDI bitmap` 并非本项目最小实现。将完整
  `IDWriteTextLayout` 绘制到 GDI 表面需要应用实现 `IDWriteTextRenderer` 回调；
  在手写 Win64 机器码中，这意味着额外的 COM 对象、回调 vtable、
  `DrawGlyphRun`、下划线和删除线实现。
- 首个 POC 采用 `ID2D1HwndRenderTarget + IDWriteTextLayout`。
  Direct2D 可直接 `DrawTextLayout`，机器码侧只需作为 COM 调用者，不必先成为
  COM 回调提供者。
- 当前 Preview 不只是“最后一步画字”。RichEdit 还拥有换行、滚动、可见区、
  文本坐标和缩放。正式替换 Preview 时必须明确接管这些职责。
- Windows 自带 `msftedit.dll` 的 `RICHEDIT50W` 不能作为
  `EM_SWITCHTOD2D` 的可靠迁移方案；实验不依赖这一条版本不稳定的捷径。

## 3. 范围与非目标

本轮范围：

- 证明 DirectWrite 对 PeMark 中文正文、标题与深色主题的实际视觉收益；
- 建立 Direct-PE 可复用的 Direct2D/DirectWrite COM 调用基础；
- 若视觉门通过，实现只读 Preview 的滚动、缩放、主题、Outline 跳转和大文档
  可见区渲染；
- Preview 稳定后，再评估文件树和 Outline 的文字绘制迁移。

本轮不做：

- 不重写 Source 编辑器；
- 不处理 IME、编辑光标、选择、Undo/Redo 和可访问性编辑模型；
- 不引入 WebView2、Chromium、编译器、汇编器或链接器；
- 不把实验路径默认启用到正式 V8.6.1；
- 不在视觉收益未经确认前改写现有 Preview 状态机。

## 4. 目标架构

```text
DocumentModel revision N
        |
        v
Markdown scan / parse
        |
        +--> Outline entries (source offsets)
        +--> RenderSnapshot
               - UTF-16 render text
               - semantic spans
               - render -> source map
               - block ranges / kinds
                         |
              +----------+----------+
              |                     |
       Legacy adapter          DWrite adapter
       RichEdit Preview        PreviewSurface HWND
                                     |
                              DirectWrite layout
                                     |
                              Direct2D render target
```

`RenderSnapshot` 只描述不可变的 revision 结果，不拥有窗口，不调用绘图 API。
Legacy 与 DWrite 两个 adapter 消费同一份 snapshot，确保 A/B 比较不会混入解析差异。

## 5. 分阶段实施

### Phase 0：冻结基线与隔离实验

1. 把当前文件树图标工作保存到独立 WIP checkpoint；恢复“源码、EXE、内存图”
   三者一致的 V8.6.1 基线。
2. 新建实验生成器与输出：
   - `src/experiments/generate_renderer_lab.py`
   - `bin/experiments/pemark_renderer_lab_x64.exe`
3. Renderer Lab 仍由 Python 直接生成 PE32+/AMD64，不借助编译器、汇编器和链接器。
4. 正式 candidate 不新增菜单、不改变默认窗口、不携带实验分支。

通过门：正式 candidate 两次构建哈希一致，现有回归全绿；实验 EXE 可独立启动和
退出。

### Phase 1：最小 Typography POC

这是第一份交付物，也是第一道决策门。只在实验生成器中加入完成静态 A/B 所需的
最小代码：

- `DWriteCreateFactory` 与 `D2D1CreateFactory` 导入；
- 创建一个 RichEdit 对照面板和一个 DirectWrite/Direct2D 面板；
- 一个 text format、一个 text layout、背景 brush 和文字 brush；
- 固定窗口大小、固定栏宽、固定内容宽度和固定中文文本；
- 最小 `WM_PAINT` 与正常退出资源释放；
- ClearType 与 grayscale 可各输出一个实验 EXE 或固定配置截图，避免在 POC 中先做
  设置界面。

本阶段明确禁止：

- Markdown 解析和样式 span；
- 文件打开；
- 滚轮、滚动条和虚拟化；
- Outline、PositionMap、跳转与 Source/Preview 切换；
- resize、DPI 动态切换、主题设置 UI；
- 真实 PeMark Preview 的任何修改。

唯一验收问题：

> 在排版参数完全相同的情况下，DirectWrite 是否让用户明显更满意？

**Gate A：必须是明确的视觉收益。** 如果反馈只是“好像好一点”，项目到此停止，
不为小幅改善重构 Preview。只有反馈达到“这才是我要的”这一等级，才进入 Phase 2。

### Phase 2：通过视觉门后的 Direct-PE 图形 ABI 基础

Gate A 通过后，才把 POC 扩展为可复用基础：

- 完整 GUID、D2D/DWrite 结构体与常量声明；
- `com_call(object, slot, ...)` 发射辅助器；
- `safe_release`、HRESULT 捕获和失败注入；
- 设备无关资源与设备相关资源的明确生命周期；
- `D2DERR_RECREATE_TARGET` 后的资源销毁与重建；
- `WM_SIZE` resize、`WM_DPICHANGED` 和多次最小化/恢复；
- 参数 JSON、耗时采样及 100%、125%、150% DPI 矩阵。

所有 COM slot 必须从 Windows SDK 接口顺序建立声明表，并用结构断言固定；禁止在
调用点散落裸 vtable 偏移。每次间接调用遵守 Win64 shadow space、16 字节栈对齐和
volatile register 规则。

通过门：浅色/深色各连续 resize 100 次，最小化/恢复 30 次，DPI 切换后仍可绘制；
退出后无进程残留，无持续增长的 GDI/USER handle。

### Phase 2B：严格控制变量的完整 A/B 矩阵

同一窗口放置等宽的 RichEdit 与 DWrite 面板，先使用固定的中文样本，再支持读取
指定 Markdown 文件的同一段落。对比参数由一个结构统一生成：

```text
font family      Microsoft YaHei UI
font size        17.0 DIP（记录窗口 DPI 与实际像素）
weight/style     Normal / Normal
foreground       同一个 sRGB 数值
background       同一个 sRGB 数值
content width    相同
padding          相同
line spacing     相同
locale           zh-CN
zoom             100%
```

DWrite 面板允许切换但不混用以下变量：

- Natural measuring + ClearType；
- Natural measuring + grayscale；
- GDI-compatible measuring（仅作控制组）。

Lab 输出：

- 同屏截图；
- 环境 JSON：Windows 版本、DPI、缩放、字体、颜色、行距、抗锯齿和 measuring mode；
- 两侧文本布局宽高、行数与首次布局/重绘耗时；
- 100%、125%、150% DPI 的固定测试矩阵。

这一阶段用于确定最终采用 ClearType、grayscale、Natural 或 GDI-compatible 中的
哪一种配置，不再重新证明是否值得迁移。配置确定后才进入 Phase 3。

### Phase 3：真实 Preview 功能原型

在 `RENDERER_EXPERIMENT` 构建中增加 `PreviewSurface`，但保留 Legacy Preview
作为一键回退和同内容对照。两个 surface 消费同一个 `RenderSnapshot`。

第一批 Markdown 契约：

- H1-H6；
- 正文与段落间距；
- 粗体、斜体、行内代码；
- 引用、无序列表；
- 围栏代码块；
- 链接的视觉样式。

PreviewSurface 首先只负责显示，不提供文本选择、复制和链接点击。缩放改变 DIP
字号和布局宽度；主题只替换 brushes；resize 只使受宽度影响的 layout 失效。

**Gate B：行为一致性。** 小/中型文档中，渲染文本、标题层级、Outline 目标、
主题、缩放和 Source/Preview 位置保持与 Legacy 契约一致。

### Phase 4：大文档布局与滚动

不得为 0.9MB 文档建立一个永久的整篇 `IDWriteTextLayout`。新增 block table：

```text
RenderBlock
- render_start / render_length
- source_start / source_end
- kind
- measured_height_or_estimate
- layout_revision
```

策略：

1. parser 在现有事务中发布 block table；失败不替换旧 snapshot；
2. 只创建 viewport + 上下 overscan 的 text layouts；
3. 缓存键至少包含 document revision、block index、content width、zoom；
4. 离屏 layout 按预算回收；
5. 维护 64 位逻辑 Y offset 与 block 高度前缀索引；
6. Outline 的 source offset 先经现有 PositionMap 找 render offset，再二分到 block；
7. 跳转目标 block 立即测量并绘制，不等待后续鼠标消息；
8. wheel、thumb drag 与 outline jump 只更新 viewport state，不触发全文排版。

性能门以现有 `v8_4_3_large_regression_test.md` 为基准：

- 打开速度不明显劣于当前稳定版；
- 大纲跳转后首个正确画面目标小于 100 ms；
- 快速滚轮/拖动停止后目标小于 100 ms 收敛到最终画面；
- 停止后不继续滚动，不显示原始 Markdown 源码，不依赖额外鼠标消息刷新；
- viewport paint p95 目标 16.7 ms，达不到时最低门为 33 ms；
- 20 次 Source/Preview、主题和大纲跳转后 revision、map 与选择锚点不漂移；
- 缓存有硬上限，长时间滚动无单调内存增长。

### Phase 5：正式 Preview 集成

Gate A/B 和大文档门全部通过后：

1. 新 ADR 替代 ADR-003，记录采用的抗锯齿、measuring mode 与回退策略；
2. ViewController 成为两个 surface 显示状态的唯一写者；
3. 正式构建先保留 Legacy fallback 开关；
4. 收集真实使用回归后才删除 RichEdit Preview 路径；
5. 此架构变更单独进入新版本线，不塞回已经确认范围的 V8.6.1。

### Phase 6：侧栏文字迁移（Preview 稳定后）

文件树与 Outline 先保留现有 ListBox、滚动、选择、鼠标和键盘逻辑，只替换
owner-draw 的文字/图标绘制：

- 用 `ID2D1DCRenderTarget::BindDC` 绑定 `WM_DRAWITEM` 提供的 HDC；
- DirectWrite 绘制文字，Direct2D 绘制选中背景和图标；
- 不在第一步重写 ListBox 或滚动条；
- 若 DC render target 实测不清晰或引入重绘问题，再提出独立 custom sidebar
  surface 方案。

这样可以先获得统一的文字质量，同时避开 PeMark 过去在自绘滚动条、Z-order 和
分散状态上已经验证过的失败路径。

## 6. 失败与回退设计

- DWrite/D2D factory 创建失败：实验构建显示明确错误；正式集成阶段回退 Legacy。
- `EndDraw == D2DERR_RECREATE_TARGET`：只丢弃设备相关资源，保留 snapshot 与布局
  数据，下一次 paint 重建。
- layout 或 block arena 分配失败：保留旧 revision，绝不发布半成品。
- 宽度/DPI/zoom 变化：递增 layout revision，旧 cache 不再可见后回收。
- 任何 surface 不得直接修改 DocumentModel。
- 所有 HRESULT 在下一次 API 调用覆盖前保存到诊断事件环。

## 7. 测试与证据

最低自动化矩阵：

- PE 静态检查、ASLR/DEP/unwind、确定性双构建；
- factory、format、layout、brush、render-target 分阶段失败注入；
- COM Release 次数与异常退出清理；
- 中文、英文、混排、emoji、长 URL、代码块、超长单行；
- 100/125/150% DPI，浅色/深色，resize/minimize/restore；
- source -> render -> block -> Y 映射单调性与边界；
- 小/中/大/超多标题语料；
- wheel、thumb、outline jump、mode/theme toggle 的可重复 UI 脚本；
- 截图必须同时记录参数 JSON，禁止只凭“看起来变好了”回忆比较。

人工验收保留决定权：文字清晰度属于产品观感，自动像素统计只能证明输出不同、
参数一致和帧稳定，不能替用户判断哪一个更舒服。

## 8. 建议的近期执行顺序

1. 保存当前文件树图标 WIP，恢复一致的 V8.6.1 基线；
2. 交付不含 Markdown、滚动和 PositionMap 的最小 Typography A/B EXE；
3. 用户只回答视觉收益是否足够明显；
4. 若答案不够明确，停止渲染迁移；
5. 若答案明确肯定，再完成 COM/Direct2D 基础和完整参数矩阵；
6. 配置确认后才实现真实 Markdown Preview；
7. 通过大文档门后再讨论正式版本号和侧栏迁移。

## 9. 主要依据

- Microsoft DirectWrite 与 GDI 互操作：
  https://learn.microsoft.com/windows/win32/directwrite/interoperating-with-gdi
- Microsoft Direct2D + DirectWrite 文本渲染：
  https://learn.microsoft.com/windows/win32/direct2d/direct2d-and-directwrite
- Microsoft DirectWrite 入门与多格式 TextLayout：
  https://learn.microsoft.com/windows/win32/directwrite/getting-started-with-directwrite
- Microsoft Direct2D HWND render target：
  https://learn.microsoft.com/windows/win32/direct2d/getting-started-with-direct2d
- Microsoft ID2D1DCRenderTarget：
  https://learn.microsoft.com/windows/win32/api/d2d1/nn-d2d1-id2d1dcrendertarget
- Microsoft RichEditD2D window controls 说明：
  https://devblogs.microsoft.com/math-in-office/richeditd2d-window-controls/
