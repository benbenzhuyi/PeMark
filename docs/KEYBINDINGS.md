# 快捷键方案（对齐小野兔 Rabbit）

文档状态：现行规范  
参考实现：`benbenzhuyi/rabbit-editor` `renderer/js/keybindings.js` 与 README 快捷键表  
验证：生成期断言 (W) + `tools/test_v8_6_keymap.py`

## 1. 原则

1. **相同功能使用相同键位。** 只要 PeMark 与 Rabbit 有同一功能，键位一致；不一致
   的按 Rabbit 调整，并在 §4 记录裁决理由。
2. **为已规划的后续功能预留键位。** 后续里程碑会做的功能，其 Rabbit 键位现在就
   空出来，避免届时改键造成用户习惯断裂；预留键位不得被其它命令占用。
3. **菜单提示与加速键表必须一致。** 每条带快捷键的菜单项都在文本里写出该键，
   生成期断言会逐条比对；二进制内的加速键表由测试从进程内存解析核对。
4. **改动必须同时更新**：加速键表、菜单文本、生成期断言 (W)、
   `tools/test_v8_6_keymap.py` 的 `EXPECTED`/`RESERVED`，以及本文档。

## 2. 与 Rabbit 一致的功能（同键）

| 快捷键 | 功能 | PeMark 现状 |
| --- | --- | --- |
| `Ctrl+N` | 新建 | 已有，不变 |
| `Ctrl+O` | 打开文件 | 已有，不变 |
| `Ctrl+Shift+O` | 打开文件夹 | **本次新增** |
| `Ctrl+S` | 保存 | 已有，不变 |
| `Ctrl+Shift+S` | 另存为 | **本次改键**（原 `Ctrl+Alt+S`） |
| `Ctrl+W` | 关闭文件 | **本次新增** |
| `Ctrl+Z` | 撤销 | 已有，不变 |
| `Ctrl+X` / `Ctrl+C` / `Ctrl+V` | 剪切 / 复制 / 粘贴 | 已有，不变 |
| `Ctrl+A` | 全选 | 已有，不变 |
| `Ctrl+F` / `Ctrl+H` | 查找 / 替换 | 已有，不变 |
| `F3` | 查找下一个 | 已有，不变 |
| `Ctrl+B` | 左侧栏显隐 | 已有；语义从"仅大纲"扩展为"整个左边栏" |
| `Ctrl+Shift+P` | 源码 / 预览切换 | 已有，不变 |
| `Ctrl+Shift+W` | 自动换行 | 已有，不变 |
| `Ctrl+=` / `Ctrl+-` / `Ctrl+0` | 放大 / 缩小 / 重置缩放 | 已有，不变 |
| `Ctrl+鼠标滚轮` | 连续缩放 | 已有，不变 |
| `Ctrl+Alt+T` | 深色 / 浅色主题 | 已有，不变 |
| `F1` | 帮助 / 关于 | 已有（PeMark 打开关于对话框） |

## 3. PeMark 专有（Rabbit 未占用，保持不变）

| 快捷键 | 功能 | 说明 |
| --- | --- | --- |
| `Ctrl+1` … `Ctrl+6` | 标题 1–6 | Rabbit 未绑定（其 `Ctrl+Shift+1/2/3` 是窗口模式，不冲突） |
| `Ctrl+Alt+B` | 粗体 | `Ctrl+B` 归左侧栏（与 Rabbit 一致） |
| `Ctrl+I` | 斜体 | Rabbit 未绑定 |
| ``Ctrl+` `` | 行内代码 | Rabbit 未绑定 |
| `Ctrl+Alt+K` | 代码块 | **本次改键**（原 `Ctrl+Shift+K`，让位给"删除当前行"） |
| `Ctrl+Alt+L` | 插入链接 | **本次改键**（原 `Ctrl+K`，让位给 AI 快速编辑） |
| `Ctrl+Q` | 引用 | Rabbit 未绑定 |
| `Ctrl+Shift+8` | 无序列表 | Rabbit 未绑定 |
| `Ctrl+Alt+S` | 状态栏显隐 | **本次改键**（原 `Ctrl+Shift+S`，让位给另存为） |

Markdown 修饰键因此形成两个家族：`Ctrl+Alt+<字母>`（粗体 / 代码块 / 链接）留给
PeMark 自己的编辑动作，`Ctrl+Shift+<字母>` 留给与 Rabbit 对齐或后续里程碑的动作。

## 4. 冲突裁决记录

| 冲突 | Rabbit | PeMark 原 | 决定 | 理由 |
| --- | --- | --- | --- | --- |
| 另存为 vs 状态栏 | `Ctrl+Shift+S` = 另存为 | `Ctrl+Shift+S` = 状态栏 | 另存为用 `Ctrl+Shift+S`；状态栏移到 `Ctrl+Alt+S` | 另存为是高频且跨应用通用的键位，优先对齐 |
| 插入链接 vs AI 快速编辑 | `Ctrl+K` = 选区 AI 编辑 | `Ctrl+K` = 插入链接 | 链接移到 `Ctrl+Alt+L` | V9 的 Ctrl+K 已在里程碑中确定，不能再占 |
| 代码块 vs 删除当前行 | `Ctrl+Shift+K` = 删除当前行 | `Ctrl+Shift+K` = 代码块 | 代码块移到 `Ctrl+Alt+K` | 删除行属于 V8.7 编辑增强，键位须提前留出 |
| 侧边栏语义 | `Ctrl+B` = 整个左边栏 | `Ctrl+B` = 大纲面板 | 统一为整个左边栏 | 双面板改造后左边栏是文件+大纲的整体 |

菜单文本随之更新：`View → Outline` 改名为 `View → Left Sidebar`，
`File → Open Folder...` 与新增的 `File → Close` 带上各自键位提示。

## 5. 为后续功能预留（现在不占用）

| 快捷键 | 归属功能 | 计划阶段 |
| --- | --- | --- |
| `Ctrl+K` | 选区 AI 快速编辑（预览后应用） | V9 Phase B |
| `Ctrl+L` | 选区引用到 AI | V9 Phase B |
| `Ctrl+J` | 右侧 AI 对话面板显隐 | V9 Phase C |
| `Alt+L` | 聚焦 AI 输入框 | V9 Phase C |
| `Ctrl+Shift+C` | 复制最后一次 AI 回复 | V9 |
| `Ctrl+Shift+T` | 用 AI 回复替换选区 | V9 |
| `Ctrl+Shift+I` | 在选区后插入 AI 回复 | V9 |
| `Ctrl+Shift+K` | 删除当前行 | V8.7 编辑增强 |
| `Ctrl+D` | 复制当前行 | V8.7 |
| `Alt+↑` / `Alt+↓` | 上移 / 下移当前行 | V8.7 |
| `Alt+Shift+1`…`6` | 大纲折叠到指定级别 | 大纲折叠功能 |
| `Alt+Shift+9` | 展开全部大纲 | 同上 |
| `Ctrl+,` | 设置面板 | 设置功能 |
| `F11` / `Ctrl+Shift+1`…`3` | 窗口模式（正常 / 全屏有菜单 / 全屏无菜单） | 窗口模式功能 |
| `Ctrl+Alt+R` | 退出时保存窗口状态开关 | 窗口几何持久化 |

`Alt+F/E/V/A/S` 不需要单独实现：PeMark 菜单项本身带 `&` 助记符，Windows 已提供。

## 6. 未采纳的 Rabbit 键位

- `Ctrl+Shift+1/2/3`、`F11`、`Ctrl+Alt+R`、`Ctrl+,`：PeMark 尚无对应功能，仅预留；
- `Ctrl+Shift+C/T/I`、`Ctrl+K`、`Ctrl+L`、`Ctrl+J`、`Alt+L`：属于 V9 的 AI 能力，
  仅预留；
- `Ctrl+D`、`Ctrl+Shift+K`、`Alt+↑/↓`：属于 V8.7 编辑增强，仅预留。

以上键位在预留期内不得被任何新命令占用；`tools/test_v8_6_keymap.py` 的
`RESERVED` 列表会在 CI 中阻止误占用。
