# PeMark 长期系统架构设计

文档状态：现行规范  
适用基线：PeMark V8.5.1 Preview  
规划范围：V8.5.2 至 V9

## 1. 文档目的

本文定义 PeMark 后续发展的长期边界、系统分层、状态所有权、安全模型和
跨架构实验方法。新增功能必须服从本文；V8.4 审计与交接材料仅作为历史证据，
除非现行文档明确重新采纳其中的结论。

本文描述约束与目标状态，不描述执行顺序，也不构成一次性实现义务。版本边界、
验收 gate 和当前优先级以 `MILESTONE_PLAN.md` 与
`DEVELOPMENT_MANUAL_V8_5_PLUS.md` 为准；本文中尚未实现的机制按风险分批到达，
不得为了让结构图成立而提前实现。

PeMark 同时服务两个目标：

1. 成为可靠、快速、节制资源的 Windows 原生 Markdown 编辑器；
2. 验证 AI 辅助工程能否改变高度原生软件的开发与维护成本。

产品正确性优先于实验结论。即使 Direct-PE 在某一复杂度之后失去经济优势，
也属于有效实验结果。

## 2. 永久约束

### 2.1 纯 Direct-PE 生产链

正式 EXE 必须由 Python 直接生成 PE32+ 映像、AMD64 指令、导入表与数据，
不得使用编译器、汇编器、链接器、托管运行时或解释器打包器。

反汇编器、调试器、分析器、性能工具和独立对照程序可以用于验证，但不得成为
PeMark 正式 EXE 的构建依赖。

### 2.2 目标平台

首要目标为 Windows x64 桌面环境。每个发布清单应记录实际测试过的 Windows
版本、CPU、DPI、主题和限制。硬件专项优化必须由测量证明，并保留通用路径或
明确兼容边界。

### 2.3 证据驱动

行为修改必须有确定性验收用例；性能修改必须有固定工作负载上的前后数据；
截图只能证明外观，不能单独证明状态、控制流、时序或数据完整性。

### 2.4 可靠性先于功能扩张

V8.5 阶段先完成文件安全、动态容量、可观测性与 PE 加固，再进入工作区、
高级编辑器和 AI 功能。

## 3. 架构质量排序

发生取舍时，按以下顺序决策：

1. 数据完整性；
2. 行为正确性；
3. 故障恢复能力；
4. 安全边界；
5. 可观测性；
6. 性能与资源效率；
7. Agent 可理解、可验证的维护性；
8. 二进制体积。

体积始终记录，但不得默认优先于前七项。

## 4. 目标系统结构

```text
Windows 消息 / 命令 / 文件与网络完成事件
                    |
                    v
               Event Router
                    |
       +------------+-------------+
       |            |             |
       v            v             v
 CommandController ViewController TaskScheduler
       |            |             |
       +------------+-------------+
                    v
              ApplicationState
                    |
       +------------+-------------+
       |            |             |
       v            v             v
 DocumentModel WorkspaceModel SettingsModel
       |
       v
 MarkdownParser -----> SemanticModel
       |                 |      |
       v                 v      v
 RenderModel       OutlineModel PositionMap
       |                 |      |
       +-----------------+------+
                         v
        Source | Preview | Outline | Status
                         |
                         v
          Layout + Theme + Accessibility
```

V9 的网络与 AI 层必须作为异步服务进入，不得直接写 DocumentModel 或 UI 控件。

## 5. 状态域与唯一所有者

| 状态域 | 唯一事实源 | 派生状态 |
|---|---|---|
| 文档文本 | `DocumentModel` | Source、RenderModel |
| 文件身份 | `DocumentModel` | 标题、状态栏、最近文件 |
| 未保存状态 | `revision != saved_revision` | 提示与状态显示 |
| SOURCE/PREVIEW | `ViewController` | HWND 可见性、菜单勾选 |
| Markdown 语义 | `SemanticModel` | Outline、样式、渲染文本 |
| 导航坐标 | Source UTF-16 offset | 通过 PositionMap 映射 |
| 窗格矩形 | `LayoutManager` | 移动、绘制、命中测试 |
| 大纲滚动几何 | `OutlineScrollState` | 绘制、hover、drag |
| 主题资源 | `ThemePalette` | 控件与自绘表面 |
| 动态内存 | 对应 arena 所有者 | parser/render/outline 视图 |
| 异步操作 | 对应 task 所有者 | 完成事件与 UI 状态 |

任何消息处理器都不得通过 HWND 偶然可见性、控件文本或重新计算的几何建立第二套
事实源。所有派生模型都携带来源 revision；revision 不一致时禁止使用。

## 6. 文档生命周期

```text
EMPTY -> LOADING -> CLEAN -> DIRTY -> SAVING -> CLEAN
                    |         |        |
                    |         |        +-> SAVE_FAILED -> DIRTY
                    |         +-> CLOSE_CONFIRMATION
                    +-> RELOADING
```

V8.5.2 目标结构：

```text
DocumentModel {
    text_ptr, text_len_u16, text_capacity_u16;
    revision, saved_revision;
    path_ptr, path_len_u16;
    input_encoding, preferred_eol;
    load_state, save_state;
}
```

`dirty` 必须由 revision 推导，不能成为独立布尔值。程序内部设置 Source 文本时
必须抑制编辑通知，避免产生虚假 revision。

### 6.1 原子保存事务

Save 与 Save As 共用同一事务：

1. 验证目标路径；
2. 对不可变的当前 revision 进行编码；
3. 写入同目录临时文件，循环处理短写和零写入；
4. 按发布策略刷新临时文件；
5. 原子替换目标，并在支持时保留可恢复旧副本；
6. 只有替换成功后才更新路径和 `saved_revision`；
7. 任一步失败都保留内存文档的 dirty 状态和最后一份完好目标文件。

必须测试磁盘满、拒绝访问、共享冲突、短写、零写入和用户取消。

### 6.2 破坏性转换

关闭、打开另一文件、新建和切换工作区都经过同一个未保存控制器，返回：

```text
SAVE_AND_CONTINUE | DISCARD_AND_CONTINUE | CANCEL
```

保存失败默认等同取消，除非用户之后明确选择其他动作。

### 6.3 编码策略

V8.5.2 必须可靠处理 UTF-8、UTF-8 BOM 和 UTF-16LE BOM。旧代码页回退必须
明确且可测试；不可解码输入不得静默替换字符。内部文本规范化与输入编码、原始
换行偏好分别记录。

## 7. 动态容量与内存模型

逐步用 VirtualAlloc-backed arena 替换巨型固定 BSS。首批 arena 包括：

- 文档 UTF-16 文本；
- 保存编码缓冲；
- 渲染文本；
- PositionMap；
- 语义/样式 span；
- Outline 条目与标题存储。

已迁移的 arena 必须记录所有者、有效长度、容量、元素步长和上限。增长使用
经过溢出检查的算术。分配失败必须保持原模型完整。

目标状态是 Parser 在 scratch arena 中生成整套 Semantic/Render/Outline/Map，
成功后通过指针与元数据交换提交，失败时不声明部分结果。这是方向而不是一次
性重构要求：每个 arena 可以独立迁移，迁移期间保持“旧固定数组不再单独作为
事实源”这一条即可。

动态分配只消除随意的固定上限，不代表无限输入。每个版本仍要声明已测试和安全
拒绝的最大值，字节数、UTF-16 单元、元素数、RVA 和文件偏移运算都必须先检查
加法与乘法溢出。

## 8. Parser、渲染与导航

一次解析产生 RenderModel、OutlineModel 和 PositionMap 所需的统一语义事件。

永久不变量：

- Outline 只保存 Source offset；
- PositionMap 单调且属于一个 document revision；
- Preview 不写回 DocumentModel；
- Theme 和 Zoom 不触发 Markdown 解析；
- 可见区样式处理不改变语义坐标；
- stale 或失败模型不得用于大纲跳转。

增量解析是后续优化，而非 V8.5.2 的必要前提。初期允许在受控 revision 边界
线性解析一次，但编辑通知需要 debounce，格式应用必须保持视口限定。

## 9. PE 映像目标

| Section | 内容 | 目标权限 |
|---|---|---|
| `.text` | 指令 | R-X |
| `.rdata` | 字符串、只读表 | R-- |
| `.idata` | 导入结构/IAT | loader-compatible |
| `.data` | 已初始化可变状态 | RW- |
| `.bss` | 零初始化状态 | RW- |
| `.pdata` | x64 unwind 表 | R-- |
| `.reloc` | 基址重定位 | R--/discardable |

PEBuilder 根据声明区域计算 RVA、raw offset、对齐和目录，禁止子系统硬编码其他
区域起点。最终目标是 W^X：可写数据不可执行。

每个 emitted function 声明范围、frame、非易失寄存器和 unwind 需求。构建时拒绝
区段重叠、越界 rel32、非法目录、frame 不平衡以及消息循环直落进可调用函数。

## 10. 可观测性

诊断构建仍保持 Direct-PE，可使用 OutputDebugStringW、计时器和固定大小事件环。
最低事件字段：

```text
timestamp, event_id, document_revision, view_mode,
operation_state, offset_or_count, win32_error
```

错误码必须在其他 API 覆盖前捕获。正式构建不得记录文档内容、API key 或隐私数据。

## 11. Workspace 与高级编辑边界

V8.6 才引入 WorkspaceModel。它拥有目录根与文件项，但打开文档仍统一进入
DocumentController。删除、重命名和覆盖属于显式破坏性操作。

V8.6 继续使用 RichEdit，除非测量证明其无法满足目标。自定义编辑表面需要独立
ADR、原型与下列完整设计：EditorModel、可见行布局、IME、可访问性、Undo 事务、
选择模型和虚拟化。不得把它作为局部控件替换处理。

## 12. V9 AI 边界

```text
UI command
 -> immutable request snapshot
 -> provider-neutral model
 -> asynchronous HTTP transport
 -> bounded JSON/SSE decoder
 -> token queue with backpressure
 -> UI completion message
 -> explicit insert/replace transaction
```

必须设计取消、超时、分块 UTF-8、跨包 JSON/SSE、响应大小上限、代理和服务错误。
网络回调不能直接改 UI 或文档。密钥不得进入仓库、文档、日志、崩溃证据或发布清单。

## 13. 跨架构实验

Rabbit 是产品行为参照，不是待翻译源码。Rabbit Electron、PeMark Direct-PE 和
未来 C++/Rust 原生对照组应执行相同版本的行为契约与工作负载。

实验必须分别报告：

- shipped footprint；
- runtime resource use；
- 工程投入、缺陷与维护成本。

实验快照在 Release/Research gate 上记录 commit、EXE hash、环境、契约版本、
工作负载 hash、p50/p95/p99、失败项、Agent 轮次、人工干预和有效性限制。
日常提交不需要这些字段。

## 14. 架构变更管理

修改永久约束、状态所有者、规范坐标、文件格式、平台边界、安全边界或公共行为时
必须留下决策记录。记录保持简短即可：背景、决定、备选、后果、回滚方式。ADR 是
为后续读者保留理由，不是交付文档。

架构只有在生成器、测试和运行证据一致时才算实现，规划文档本身不推进里程碑。
