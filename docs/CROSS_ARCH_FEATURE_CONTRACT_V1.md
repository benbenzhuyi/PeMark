# 跨架构功能契约 V1

状态：实验规范草案  
适用实现：Rabbit Electron、PeMark Direct-PE、未来 native control

## 1. 规则

契约只描述用户可观察行为和数据结果，不规定控件、语言或内部实现。每个实现报告
`PASS`、`FAIL` 或 `UNSUPPORTED`；缺失能力不能从统计分母删除。各实现必须使用
相同 hash 的 fixture、初始窗口、DPI、主题和语言。

每次失败保存输入、步骤、实际结果、日志、commit 与 binary hash。功能正确性和
性能分别判定。

## 2. Editor Core

### EC-OPEN-001 打开 UTF-8 文档

冷启动打开有效 UTF-8 fixture。完整文本必须可编辑，文件身份可见，无替换字符，
状态为 clean。失败时显示错误并保持旧文档不变。

### EC-EDIT-001 编辑与 Undo

在开头、中间、结尾插入中英文与 emoji。第一次修改后进入 dirty；逐步 Undo 必须
精确恢复文本，恢复后的 dirty 语义遵循公开政策。

### EC-SAVE-001 保存与重开

编辑、保存、关闭、重开。磁盘字节必须符合公开 encoding/EOL 政策，文本无损，
成功后状态为 clean。

### EC-SAVE-002 保存失败

对拒绝访问或注入失败目标保存。必须显示错误、保留 dirty 内存文本、保持原目标
逐字节不变，而且不能报告成功。

### EC-CLOSE-001 未保存关闭

分别选择 Save、Discard、Cancel。Save 只有成功才关闭；Discard 不写盘；Cancel
保持窗口、文档、选择与 dirty 状态。

### EC-FIND-001 查找替换

在含大小写、Unicode 和重复匹配的 fixture 中执行查找、下一项和全部替换。顺序、
数量与结果正确；替换应形成可撤销文档事务。

## 3. Markdown、Preview 与 Outline

### MD-PREVIEW-001 首次预览

冷启动打开 markdown-full fixture 后首次进入 Preview。支持元素符合语法契约；
Source 不变且不增加 document revision。

### MD-OUTLINE-001 H1-H6

混合 H1-H6、围栏代码伪标题和 Unicode 标题。只有真实标题进入 Outline，数量、
层级和文字正确。

### MD-NAV-001/002 Source 与 Preview 导航

分别在 Source 和首次 Preview 中点击 first/middle/last 标题。定位必须对应同一
Source heading，不能全部落到 EOF；PositionMap 必须属于当前 revision。

### MD-STATE-001 模式与主题稳定性

模式与主题各切换 20 次。任何时刻只有一个文档表面可见，文本、Outline、位置、
菜单和主题一致；主题和 Zoom 不产生 parser revision。

## 4. Capacity

### CAP-001 2600 headings

2600 项全部出现、可滚动，first/middle/last 导航正确。

### CAP-002 增长边界

在各实现声明边界执行 `n-1/n/n+1`。系统应成功增长或在修改模型前明确拒绝，
不能崩溃或截断。

### CAP-003 重复重建

连续 open/Preview/close large fixture 100 次。结果一致，内存和 handle 达到平台。

## 5. Workspace（V8.6）

- `WS-TREE-001`：共同 workspace 的层级、Unicode 名称和类型正确，大目录工作有界；
- `WS-FILE-001`：create/rename/delete 的磁盘和树状态一致，无 phantom entry；
- `WS-EXTERNAL-001`：检测外部修改，dirty 文档不得被静默覆盖。

## 6. AI（V9）

- `AI-STREAM-001`：预定 SSE 分块的 token、Unicode 与终态准确，UI 响应；
- `AI-CANCEL-001`：取消后请求与队列清理，文档无部分修改；
- `AI-APPLY-001`：只有明确操作才插入/替换，形成单个 Undo transaction，stale
  selection 需要重新确认。

## 7. Parity

每个里程碑冻结适用契约集合：

```text
parity = PASS / (PASS + FAIL + UNSUPPORTED)
```

P0/P1 failures 单独公布。高 parity 不能抵消数据丢失、崩溃或安全失败。

