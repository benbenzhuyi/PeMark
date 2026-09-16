# PeMark 清晰里程碑计划

文档状态：现行规范  
起点：V8.5.1 Preview

## 1. 规划原则

里程碑按依赖与风险排序，不按功能吸引力排序。只有验收证据齐全才算推进；日期、
代码量和完成百分比不能替代 release gate。

每一步只实现解决当前已证实问题所必需的最小机制。“可以再加一个检查”不是
实施的充分理由；局部合理的机制累积起来也可能不经济。

本文的版本顺序是当前假设，不是必须执行的命令。当实现证据表明某个后续阶段
应该提前，或某项设计不可行时，先修改本文再改代码。

前三阶段先建立安全的原生核心，随后才进入 Workspace、高级编辑和 AI。

## 2. 当前基线：V8.5.1 Preview

已经建立：

- 可重复的纯 Direct-PE 构建；
- 主窗口确定性正常退出；
- Preview、styles、PositionMap、Outline 统一 Markdown 扫描；
- 集中的 Source/Preview 转换；
- 围栏代码空白保真；
- 视口限定的 Preview 格式化；
- 大纲滚动条共享几何；
- Windows GUI 回归自动化。

公开限制：保存非原子、短写处理不完整、没有未保存保护、存在固定容量、虚拟 BSS
很大、PE 仍是单一 RWX section。

## 3. V8.5.2：Document Safety（当前发布目标）

### 范围

只包含已被证据证实的数据安全问题：未保存保护、事务化保存、编码保真。
动态容量与 PE 加固不属于本版本，它们分别是 V8.5.3 与 V8.5.4。

理由：把五组工作绑进一个里程碑，会让一个功能上已经可用的安全版本长期
无法发布。文件安全与动态容量之间只有弱依赖，可以分批交付。

### Phase A：规格与观测基础

- 建立 New/Open/Save/Save As/Close 的行为契约；
- 定义 document revision 与 saved revision；
- 设计 file I/O 和 allocation failure injection；
- 采集标准文档的耗时、内存、进程与 handle 基线；
- 将构建测试入口改为版本无关名称；
- 映射当前 load/save routines、buffers、capacities 和 ownership writes。

Exit gate：

- 所有文件操作都有 success/failure/cancel 契约；
- fixture 与基线 hash 已冻结；
- diagnostics 能标识 operation、revision 和 Win32 error；
- 除诊断外不改变正式行为。

### Phase B：Dirty state 与破坏性转换

- Source 编辑递增 document revision；
- dirty 由 revision equality 推导；
- New/Open/Close 统一进入 unsaved-change controller；
- 程序内部更新不会形成 false dirty；
- 保存失败后不得继续隐式破坏性操作。

Exit gate：

- Save/Discard/Cancel 全矩阵通过；
- 100 次 edit/mode/close 循环无状态分歧；
- focus、menu、title 和 dirty state 一致；
- V8.5.1 原有行为全部回归通过。

### Phase C：Transactional output

- 编码不可变 revision snapshot；
- 循环处理部分写入；
- 写 sibling temporary file 并原子替换；
- 定义 recovery 文件命名、发现与清理；
- 捕获并显示可行动的错误信息。

Exit gate：

- 支持编码与换行的 byte-for-byte round trip 通过；
- 每个 write/replace 边界注入失败后原文件保持完好；
- replacement 完成前不报告成功；
- 不遗留无归属 handle 或无政策的临时文件。

### Phase D：Encoding policy

- UTF-8、UTF-8 BOM、UTF-16LE BOM；
- 明确旧代码页 fallback；
- 编码和 EOL metadata 与内部规范化分离；
- undecodable/oversized 输入采用事务式失败。

Exit gate：

- 中文、英文、日韩、emoji、LF、CRLF、CR fixtures 通过；
- malformed input 行为明确；
- 无静默替换、截断或半更新 DocumentModel。

### V8.5.2 Release gate

- 无已知可复现数据丢失或退出崩溃；
- Commit/Milestone 两级 gate 在目标 Windows 环境通过：确定性构建、机器码
  回归、Open/编码事务、破坏性转换矩阵、Windows GUI 冒烟与退出码；
- 两次构建二进制一致；
- manifest 记录已知限制；
- 独立复核接受 file transaction。

性能分布、内存平台与 handle 长跑属于 Release/Research gate，不作为本版本的
阻塞条件。

## 4. V8.5.3：Dynamic Capacity

原 V8.5.2 的 Phase E。它在 V8.5.2 发布之后独立进行，避免继续阻塞安全版本。

### 目标

移除随文档规模静默截断的固定容量，并让分配失败不破坏当前文档。降低初始
commit 与 working set 是期望结果，不是硬性验收条件。

### 已完成的切片

- Outline 三表（srcpos/renderpos/level）迁入动态 arena；
- 样式三列（start/end/type）迁入动态 arena，131072 项上限已退役；
- 两个 arena 都在 Open 提交边界之前预留，增长失败保持旧文档与旧 arena 完整；
- 分配失败注入覆盖两个 arena；140000 跨度用例证明不再截断。
- 渲染侧缓冲区迁入一个连续 arena：位置映射（4 字节/单元）与渲染文本
  （2 字节/单元），容量为 `max(4096, 归一化长度 + 1)`；扫描越界保护改为读取
  已发布容量，虚拟 BSS 由 119.5 MB 降至 68.5 MB。
- document 文本改为"保留政策上限 + 512 KiB 单元块提交"的 arena：可见上限与
   规范化上限仍是 `WIDE_CHARS`，物理提交随内容增长；编辑器同步在读取前预留，
   失败时用不变的模型回滚控件显示。虚拟 BSS 进一步降至 51.5 MB。
- 最后两个固定缓冲区（解码/序列化 scratch 与文件字节）改为按操作规模提交的
   arena；编码 API 的上限改为读取已发布容量。虚拟 BSS 降至 8 KB，PE 虚拟
   尺寸由 51.6 MB 降至 86 KB。
- 完成 12 轮 Open(仅解析)+Preview(解析)+New 的重复循环测量：句柄零增长，
  私有内存首末四分之一区间增长约 1.6 MB，达到稳定平台。

### 剩余范围

- 按风险逐个迁移 document、encoded output、render、map 缓冲区；
- 迁移时保留最小必要不变式：单一事实源、提交点、失败不破坏旧模型；
- 完成重复 open/parse/close 的内存平台观察；
- 声明并测试最大输入与安全拒绝行为。

### Exit gate

- 保留的固定数组不再承担独立事实源；
- 每个已迁移 arena 的分配失败不会改变当前文档状态；
- 大规模输入不再静默截断；
- 重复 open/parse/close 后内存与 handle 有界。

以上四项均已由 `tools/test_v8_5_3_*.py` 覆盖。V8.5.3 的剩余工作只有发布
验证与文档冻结。

## 5. V8.5.4：Direct-PE Hardening

### 目标

把 loader-simple RWX 映像改造成分节、可重定位、可审计的 PE，同时保留直接生成。

### Deliverables

- 声明式 PE region/section allocator；
- `.text/.rdata/.idata/.data/.bss` 权限分离；
- base relocation 与 ASLR；
- 适用函数的 `.pdata`/unwind metadata；
- deterministic symbol/function-range map；
- directory、alignment、fixup、overlap 构建验证；
- CFG/CET 可行性结论及可行部分实现。

### 已完成的切片

- 单一可读可写可执行节已拆分为按权限分离的四个节：`.text`（RX 代码）、
  `.rdata`（R 字符串与只读表）、`.idata`（RW 导入表与 IAT）、`.bss`（RW 零
  初始化状态）；不存在同时可写且可执行的节。
- 每个节的 VirtualSize/SizeOfRawData 覆盖到下一节的 RVA 间距，raw 缓冲与 RVA
  计划保持一一对应。紧凑布局会被 Windows 以 `ERROR_BAD_EXE_FORMAT` 拒绝，
  该失败变体记录在 `FAILED_APPROACHES.md`。
- 新增 `tools/test_v8_5_4_sections.py`：既检查磁盘上的节表，也用
  `VirtualQueryEx` 验证已加载映像的页保护为 RX / R / RW / RW，并做一次真实
  窗口启动与干净退出。
- 新增 `.reloc` 节：每个映像页一个块，条目全部为 `IMAGE_REL_BASED_ABSOLUTE`
  （本映像没有绝对地址，语义就是"无需修正"）；`DllCharacteristics` 增设
  `DYNAMIC_BASE`，实测加载基址为 `0x7FF73D810000` 一类随机值而非首选基址，
  窗口启动、符号访问与干净退出均正常。测试同时校验重定位目录、块结构与
  实际基址已随机化。
- 生成 `.pdata` 栈回溯元数据：为全部非叶例程（42 条）生成 RUNTIME_FUNCTION，
  prologue 从生成的机器码反解；UNWIND_INFO 按链接器惯例放在 `.rdata`，异常
  目录大小只覆盖数组。dbghelp 能为我们的地址解析出条目，真实栈回溯能进入
  本模块，程序在 ASLR 下启动、工作、退出均正常。
  **已知限制**：回溯到达本模块帧后未能继续向上，完整回溯尚未证明；程序行为
  不受影响（代码不使用异常），该状态由 `test_v8_5_4_unwind.py` 显式打印而非
  断言通过。

### 剩余切片

- CFG/CET 可行性结论已完成，见 `V8_5_4_CFG_CET_FEASIBILITY.md`：两者本里程碑都不实现
  （CFG 缺少可被控制的间接调用目标，CET 声明不改变行为且带来加载风险），并记录
  了重新评估条件。
- （可选）继续排查完整栈回溯，需要时再投入；当前记录为发布门禁偏差。

### Release gate 偏差说明

原定"representative nested frames 的 unwind 测试通过"这一条**未完全达成**：
`.pdata` 结构合法、系统可解析条目、回溯能到达本模块，但 dbghelp 未从我们的帧
继续向上（尝试过规范修正与两个真实 bug 修复后仍未跨帧）。由于本程序不抛出异常，
该偏差不影响行为正确性；它被显式记录，而不是通过放宽断言掩盖：
`tools/test_v8_5_4_unwind.py` 会打印这一状态。

### Release gate

- writable application data 不可执行；
- 非首选基址加载矩阵通过；
- representative nested frames 的 unwind 测试通过；
- `inspect_pe`、反汇编与 Windows loader 观察一致；
- V8.5.2 数据完整性和 GUI 套件不变通过；
- 分节对启动、内存的影响已测量且无未解释回归。

## 6. V8.6：Workspace Foundation

### 目标

让用户可以在应用内浏览一个目录并打开其中的文件，同时保持"只有一个可写文档"
与既有的未保存保护不变。

### 设计取向（以及为什么不做某些事）

- **先做单层文件列表，不做 TreeView。** 工程里已有自绘 ListBox（大纲）、自绘
  滚动条几何、布局管理器与主题，这三样可整体复用；引入 `SysTreeView32` 需要新的
  控件类、`WM_NOTIFY` 处理与另一套主题适配。核心用途是"找到并打开文件"，单层列表
  加"进入目录 / 返回上级"就够用，层次导航等出现真实需求再考虑。
- **第一版只读。** 创建、重命名、删除都会破坏用户文件，收益低而验证成本高，
  推迟到有明确需求时单独提案。
- **不做后台监视。** 外部文件变化在"保存前"与"窗口重新获得焦点"时比较时间戳与
  大小即可，不引入 `ReadDirectoryChangesW` 常驻线程。
- **不持久化窗口几何。** 最近文件先放在内存里；磁盘配置读写会引入新的失败面，
  等确实需要跨会话记忆时再做。

### 已完成的切片

1. **WorkspaceModel 与目录枚举（无 UI）** —— 已完成
   - 根目录、当前目录与条目表；条目由自有 arena 提供，每条拥有名称（260 单元）、
     原始 `dwFileAttributes`、归一化的目录类别、64 位大小与最后写入 `FILETIME`，
     stride 544 字节；
   - `FindFirstFileW` / `FindNextFileW` 枚举，`FindClose` 始终执行；过滤出子目录与
     `.md` / `.markdown` / `.txt`；排序为目录在前，各自按名称升序；
   - 空目录、缺失路径、超长路径、非目录路径与拒绝访问都发布 win32 error 与空列表，
     之后的合法目录可正常重新枚举；
   - 验收：`tools/test_v8_6_workspace_enum.py` 通过（含 Unicode 与 255 字符名称、
     属性/大小/时间归属、130 条目跨 64 条目 arena 边界、恢复路径）。测试命令
     `cmd_workspace_probe` (1902) 只存在于显式测试构建。
   - 该切片暴露并修复两个真实缺陷：arena 扩容释放旧块前没有拷贝已发布条目；
     stride 常量与发射代码中的 `index*512 + index*16` 硬编码脱钩。

2. **侧边栏面板与文件列表控件** —— 已完成
   - `panel_mode` 决定既有 ListBox 显示文档大纲（默认）还是 workspace 条目；
     两种模式共用同一个控件、同一套布局几何、同一条永久 gutter 与同一个
     `sync_outline_scrollbar` 状态；没有第二套列表、滚动条或主题路径；
   - `set_panel_mode` 拥有模式切换，`refresh_panel_list` 拥有"重建当前列表"，
     新的工作区根目录也能据此刷新正在显示的文件列表；
   - 行绘制不引入新资源：目录行追加反斜杠并使用强调色，文件行保持正文色；
     文件分支直接从 workspace arena 读取类别，绝不读 `outline_level`；
   - 文件模式激活时，大纲扫描既不清空共用 ListBox 也不向其追加行；选中文件行
     不会跳转文档；
   - 验收：`tools/test_v8_6_panel.py` 通过（模式切换前后 ListBox 几何相同、
     两种主题下目录/文件行颜色不同、大纲调色板恢复后不变、文件行可选择且不
     移动文档、滚轮驱动共用滚动条并按 `count - visible_rows` 钳制、文件模式
     期间的编辑在切回大纲后被重新扫描）。菜单入口属于切片 4；本切片用只在
     测试构建存在的命令 1903/1904/1905 驱动。
   - 该切片暴露并修复一个真实缺陷：大纲扫描无条件清空共用 ListBox，导致
     文件模式期间编辑文档会清空文件列表。

3. **进入目录、返回上级、打开文件** —— 已完成
   - 双击目录行使其成为工作区根目录，列表与状态栏随之更新；Backspace 返回上级，
     但只有焦点在文件列表时才生效，编辑区的删除键行为不变；状态栏新增第七段
     发布当前工作区目录，大纲模式下清空；
   - 双击文件行不新增第二条打开路径：只填 `temp_path`、置
     `pending_destructive_action = 2`、升起 `open_bypass_picker`，然后进入既有
     `destructive_request`。共用的未保存保护先运行；用户确认后
     `destructive_open` 仅对这一次请求跳过选择器，继续走未改动的
     `cmd_open_selected` 读取/解码/提交路径。取消会清标志并保留当前文档；
   - 验收：`tools/test_v8_6_navigation.py` 通过（双击进入目录、Backspace 只在
     列表持焦时返回上级、状态栏画出目录并在大纲模式下清空、打开干净文件的正文
     正确、取消保留脏文档及其 revision 差、放弃后进入新文档、不可解码文件保持
     原文档、UTF-16LE 保持编码）。菜单入口仍属于切片 4；本切片用只在测试构建
     存在的命令 1906/1907 与真实的通知/按键消息驱动。
   - 该切片暴露并修复一个真实缺陷：列表激活跳入永不返回的 Open 路径时没有丢弃
     自身返回地址，栈永久错位 8 字节，在 Open 事务内崩溃。

### 剩余切片

每个切片独立可验证、可回滚，且任何时刻保持可构建。

1. **菜单与快捷键集成**
   - `File → Open Folder…`、`View → Files / Outline` 切换
   - 最近文件（内存内，最多 10 条）列在 File 菜单底部
   - 验收：菜单勾选状态与面板一致；最近文件项能正确打开

### Release gate

- 常见规模目录（数百条目，含子目录与 Unicode 名称）可浏览、可进入、可打开；
- 拒绝访问、空目录、名称过长、条目在枚举后被删除等情形有明确行为且不崩溃；
- 从列表打开文件完整经过未保存保护与 Open 事务，失败不改变当前文档；
- 切换面板模式与主题后，布局、绘制与滚动仍满足既有不变量；
- 空闲时不持续扫描磁盘（以重复打开 / 关闭浏览器验证 CPU 与句柄有界）；
- V8.5.4 的全部既有套件保持通过。

### 明确推迟（各自需要独立提案）

- create / rename / delete 等破坏性文件操作；
- 树形层次导航（`SysTreeView32`）；
- 拖拽打开；
- `ReadDirectoryChangesW` 常驻监视与冲突处理；
- 窗口几何与最近工作区的磁盘持久化；
- 多标签或多文档同时可写。

### 研究记录

V8.6 同时是"AI 原生软件工程"的实验样本：按 §11 的 Milestone 级要求记录 Agent
轮次与人工干预、每个切片的实际代码量、被反证的假设，以及"哪一类任务 Agent 做得
好、哪一类容易出错"的观察。这些观察是本项目的主要研究产出，与功能本身同等重要。

## 7. V8.7：Advanced Editing and Markdown Fidelity

### 目标

在保持原生效率可测量的前提下接近参照产品的核心编辑体验。

候选范围：

- line-number gutter 与 current line；
- search decorations；
- 基于 Source offset 的 fold model；
- 更完整的 block/inline Markdown contracts；
- incremental semantic invalidation；
- 生成式编辑的 Undo transaction；
- IME、selection、accessibility、high-DPI 改进。

RichEdit 并不预设需要替换。只有独立 ADR 和原型测量证明其不能满足行为契约时，
才启动 custom editor architecture。

### Release gate

- 约定的 Editor Core/Markdown parity score 达标；
- typing、scroll、mode transition 满足 p95 budget；
- 24 小时 stress editing 无无限内存或 handle 增长；
- IME 与 multilingual matrix 通过；
- malformed Markdown 不会崩溃或产生非法 PositionMap。

## 8. V8.8：Cross-Architecture Experiment Baseline

### 目标

先发布可复现比较方法，再提出架构优劣结论。

### Deliverables

- 冻结 Rabbit Electron reference commit；
- 与实现无关的 versioned feature contracts；
- shared small/medium/large/stress/headings/unicode workloads；
- deterministic UI action scripts；
- environment 与 release manifest schema；
- startup、memory、latency、stability、engineering-cost 方法；
- 可选的窄范围 C++/Rust native control。

### Release gate

- 各实现使用相同 contract/workload versions；
- 短操作结论至少 30 个样本；
- 结果包含 p50/p95/p99 与 validity limits；
- shipped footprint 与 runtime use 分开报告；
- 缺失功能和失败保留在 parity score 中。

规格工作可与 V8.5.2 并行，但在测量方法冻结前不得作正式比较结论。

## 9. V9：AI Native

### Phase A：Transport laboratory

- async WinHTTP lifecycle；
- cancellation、timeout、proxy；
- bounded UTF-8 与 JSON/SSE parser；
- 可确定分块的本地 mock server；
- token queue 与 backpressure 测量。

### Phase B：Bounded document actions

- immutable selection/request snapshot；
- Ctrl+K preview-before-apply；
- 与 Undo 集成的 insert/replace transaction；
- cancel 不产生 partial document mutation。

### Phase C：AI workspace

- 右侧 conversation panel 与 Ctrl+L；
- provider/model/settings abstraction；
- per-document conversation persistence；
- local/online OpenAI-compatible endpoints；
- secret storage 与 redaction policy。

### Release gate

- hostile fragmentation、malformed payload、response limit 测试通过；
- 慢流和 stalled stream 下 UI 保持响应；
- network completion 不能绕过 document transaction；
- credentials 不进入 repo、logs、crash evidence 或文档；
- mock benchmark 将客户端开销与模型延迟分离；
- V8.5 文件安全套件持续通过。

## 10. 明确延后

以下想法需要独立提案，不由本路线图自动授权：

- 多个同时可写文档或 tabs；
- PeMark 进程内 plugin execution；
- arbitrary HTML rendering；
- 自动更新 executable code；
- CPU-specific instruction variants；
- custom editor replacement；
- GPU rendering；
- 全量 Rabbit 功能身份复制。

## 11. Milestone Snapshot 分级

不同层级的记录要求不同。不要对每个日常提交套用发布级清单。

Commit 级（每个有界变更）：

```text
source commit
generator/EXE SHA-256
相关测试的 pass/fail
新增或更新的 known issue
binary size
```

Milestone 级（候选版与发布版）追加：

```text
version/channel
tested Windows environments
feature contract version/parity score
full regression pass/fail counts
已知限制与未解决发现
review identity
```

Release/Research 级（正式发布、性能专项、V8.8 对照实验）追加：

```text
workload hashes
startup/open/preview p50/p95/p99
idle/peak memory and commit
process/handle counts
Agent sessions/human interventions
```

跨越同一 milestone 的连续小提交可以共享一次 Milestone 级快照，不要求逐条
维护发布级指标。

## 12. 立即执行顺序

当前只做两件事，按顺序：

1. 收尾 V8.5.2 Document Safety 的发布门禁：确认 Commit/Milestone 两级证据齐全，
   记录已知限制，发布 V8.5.2。
2. 发布之后再决定 V8.5.3 Dynamic Capacity 的下一批 arena 切片，一次一个。

期间不新增长期架构文档、不预先实现后续版本需要的机制。新需求先回答
“这一步最低必要工程量是什么”，再决定是否进入计划。

历史准备步骤（契约、fixture、failure injection、baseline、ownership map）
已在 V8.5.2 前期完成，不再重复执行。
