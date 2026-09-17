# 文件面板重设计（对齐小野兔 Rabbit）

文档状态：范围与决策已确认，待实施  
参考实现：`benbenzhuyi/rabbit-editor` @ master  
被取代的决策：`MILESTONE_PLAN.md` §6 原定"单层列表、第一版只读、不做树形导航"。
用户明确要求文件界面全面参考 Rabbit，因此这些推迟项被撤销并重写为本方案。

本文件同时取代 V8.6 切片 2 的"两个模式复用同一个 ListBox"设计——Rabbit 的左边栏
是**文件浏览器与大纲上下同时存在**的双面板，见 §2.3。

## 1. 目的与范围

把 PeMark 的左边栏从"单个列表、在文件与大纲之间二选一"升级为 Rabbit 式的
**上下双面板**：上方文件浏览器（可展开目录树），下方大纲导航，中间可拖动的
分界线，两个标题栏都可点击切换三态。文件面板本身补齐树浏览器应有的文件操作。

范围仅限左边栏与其文件操作：双面板布局、树、标题栏、右键菜单、重命名/新建/
删除/刷新，以及打开文件的入口。

不在本方案内：编辑器行为、AI 面板、多标签、拖拽、目录监视、窗口几何持久化、
非文本文件的渲染。

## 2. Rabbit 参考行为（源码依据）

### 2.1 数据与安全层（`main.js`）

- 路径授权：`allowedRoots` / `allowedFiles` 集合；每个文件操作先
  `requireAllowedPath`，未授权路径直接拒绝（"拒绝访问未经用户授权的路径"）。
- 列目录 `file:list`：跳过 `.` 开头的隐藏项；目录在前、文件在后，同类按
  `localeCompare(name, 'zh-CN')` 排序。
- 新建文件 `file:new`：生成 `未命名.md`，重名时递增 `未命名_1.md`。
- 新建文件夹 `file:create-dir`：`新建文件夹`，重名时递增 `新建文件夹_1`。
- 重命名 `file:rename-entry`：拒绝路径分隔符、拒绝重名、拒绝重命名授权根目录。
- 删除 `file:delete-entry`：`rmSync(recursive)` / `unlinkSync`（**永久删除**），
  拒绝删除授权根目录。
- 保存 `file:write`：拒绝用空内容覆盖非空文件；覆盖前自动生成 `.bak.md`。

### 2.2 树交互层（`renderer/js/fileBrowser.js`）

- 树节点：`缩进 = depth * 16px`；目录节点 = 箭头 `▶/展开` + 图标 `📁/📂` +
  名称；文件节点 = 图标 + 名称。
- 箭头点击 = 展开/折叠该目录；`Shift` + 箭头点击 = 递归展开全部子目录。
- 目录行点击 = 展开/折叠（**不是**"进入为根"）。
- 文件行点击 = 直接打开（单击），高亮该行且**不抢焦点**（焦点留在文件树）。
- 双击任意行 = 内联重命名：名称处出现输入框，`Enter` 提交、`Esc` 取消、
  失焦提交。
- 右键菜单：
  - 目录：新建文件 / 新建文件夹 / 重命名 / 删除 / 复制路径
  - 文件：重命名 / 删除 / 复制路径
  - 点击别处关闭
- 标题栏右侧按钮：`全部折叠`、`刷新`；标题旁显示当前根路径（长路径缩略为
  `.../末两级`，`title` 给出全路径）。
- 树首行 `..` 父目录项，点击把父目录设为新根。
- 默认根目录 = 系统"文档"目录，启动即加载。
- 选中高亮跨刷新保持，并 `scrollIntoView({block:'nearest'})`。
- 文件类型图标按扩展名映射（md/txt/html/json/js/css/xml/yaml/csv/log/py/sh…）。
- 读取失败时树内显示"无法读取目录"提示，不抛异常。

### 2.3 左边栏双面板共享空间（`index.html` + `styles/sidebar.css` + `app.js`）

结构：`#left-sidebar` 是一个纵向 flex 容器，依次是
`#file-browser-panel`（`.sidebar-panel`）、`.panel-divider`、
`#outline-panel`（`.sidebar-panel`）。每个面板内部再纵向分成
`.sidebar-header`（固定 28px）与 `.tree-view`（`flex: 1`，各自独立滚动）。

两个面板的默认占比都是 `flex: 1 1 50%`，并且都带 `transition: flex .15s ease`。

**分界线拖动（`initPanelDivider`）**

- `mousedown`：记录起点 `clientY`、文件面板当前高度、`divider` 自身高度，给
  `divider` 加 `.active`（此时背景变成强调色，`cursor: row-resize`），
  并把整个 body 的光标与选择临时锁住。
- `mousemove`：`newFbHeight = 起点高度 + deltaY`，钳制到
  `[28, sidebarHeight - 28 - 4]`——上下各留 28px（一个标题栏高度），再扣掉
  4px 分界线；把钳制后的高度换算成百分比写回两个面板的 `flex`，
  `outlinePercent = 100 - fbPercent - 0.5`（0.5% 是给分界线预留的份额）。
  拖动期间 `transition: none`。
- `mouseup`：移除 `.active`、恢复光标与 transition。

**标题栏点击/双击（`initPanelBehaviors`）**

每个面板有独立状态机，取值为 `0 = maximized`、`1 = half`、`2 = minimized`，
两者初始都是 `1`。标题栏（`.sidebar-header`，`cursor: pointer`，hover 变背景），
点击标题栏内部按钮或重命名输入框时不触发。

- 单击：先等 250ms（用于区分双击），然后 `state = (state + 1) % 3`，即
  `half → minimized → maximized → half` 循环。
- 双击：取消等待，直接 `state = (state === 2 ? 0 : 2)`，即在
  **minimized 与 maximized 之间对调**。
- 应用状态：
  - `maximized`：本面板加 `.maximized`（`flex: 1 1 90%`），另一面板被设成
    `flex: 1 1 20%`；
  - `half`：两者都回到 `flex: 1 1 50%`；
  - `minimized`：本面板加 `.minimized`（`flex: 0 0 28px`，内容区
    `display: none`，只剩标题栏），另一面板设成 `flex: 1 1 auto`。

**视觉**

- 标题栏 28px：左侧 11px 大写小标题（`letter-spacing: .5px`，次要色），中间是
  文件面板的当前根路径（过长省略，`title` 给出全路径），右侧是操作按钮组
  （全部折叠 `«`、刷新 `↻`，14px，hover 时变亮）。
- 分界线 4px，默认边框色，hover 或拖动中变强调色。
- 大纲标题按级别着色：h1–h6 各一色，深色主题用蓝/青/绿/黄/橙/灰，
  浅色主题换成对应的深色版本；选中时文字转为高对比色（深色主题白、浅色主题黑）。

## 3. PeMark 现状与差距

| 能力 | PeMark 现状（切片 1–3 + 切片 4 第一部分） | 目标 |
| --- | --- | --- |
| 左边栏形态 | 单个 ListBox，文件与大纲二选一（`panel_mode`） | 上下双面板同时存在：文件在上、大纲在下 |
| 面板框架 | 无标题栏，无面板分隔 | 每面板 28px 标题栏 + 4px 可拖动分界线 + 三态（half/minimized/maximized） |
| 滚动 | 一套 gutter/滚动条，两个模式轮流复用 | 每个面板各自一套滚动条与滚动状态 |
| 列表形态 | 单层列表，目录在前按名排序 | 可展开目录树（扁平化可见行） |
| 进入目录 | 双击目录 = 把它设为根 | 点击箭头/行 = 展开折叠；另设"设为根" |
| 打开文件 | 双击文件 | 单击打开（Rabbit 行为），不抢焦点 |
| 重命名 | 无 | 双击内联重命名 |
| 新建文件/文件夹 | 无 | 右键菜单 |
| 删除 | 无 | 右键菜单 + 确认 |
| 复制路径 | 无 | 右键菜单 |
| 刷新 / 全部折叠 | 无 | 文件标题栏右侧两个按钮 |
| 路径显示 | 状态栏第七段 | 文件标题栏内根路径缩略 + 状态栏保留 |
| 父目录 | Backspace / 菜单 | 树首行 `..` + Backspace 保留 |
| 图标 | 无 | 类型色标 + 箭头字形 |
| 隐藏项 | 未过滤 | 过滤 `.` 开头 |
| 授权 | 单个工作区根 | 工作区根 + 其子树（显式拒绝越界） |

## 4. 技术约束与实现策略

PeMark 是纯 Direct-PE 机器码生成，没有 DOM 与第三方控件，因此每条参考行为都要
落到现有自绘控件体系：

1. **树用"扁平化可见行"实现，不引入 `SysTreeView32`。**
   Rabbit 的 DOM 树本质也是可折叠列表。PeMark 维护一个"可见行数组"，每行记录
   `名称 / 完整路径 / 深度 / 是否目录 / 是否展开`，再用现有 owner-draw ListBox
   逐行绘制。滚动条、命中测试、主题与布局全部沿用现有机制。
2. **展开状态用"展开集合"记录，切换后整体重建可见行。**
   展开集合 = 一组已展开的目录路径；重建时从根目录递归枚举已展开目录，生成新
   的可见行数组。这样无需维护父子指针与节点缓存，目录变更后重新枚举即为最新。
3. **缩进与箭头在绘制阶段偏移，不写进行文本。**
   行文本保持纯名称，绘制时 `left += depth * 16`，箭头占据缩进段末尾 12px。
   目录行文本追加 `\` 以区分类型，与现有画法一致。
4. **图标不使用 emoji。**
   面板字体为 `Microsoft YaHei UI`，emoji 显示不可靠。替代方案：目录用
   `▸` / `▾` 箭头 + 目录名反斜杠；文件按扩展名着色（`.md` 用强调色，纯文本
   正文色，其他灰色），并在行尾不显示无关信息。
5. **内联重命名用浮动 EDIT 子控件。**
   新建一个隐藏的 EDIT，重命名时移到目标行、设置文本、`SetFocus` 并全选；
   `Enter` 提交、`Esc` 取消、失焦提交，与 Rabbit 一致。
6. **右键菜单用 `TrackPopupMenu`（新增 USER32 导入）。**
   系统菜单自带键盘导航、Esc 关闭、主题跟随，比自绘更快且更稳。
   空闲时用 `GetMenuItemCount` 之外的状态无副作用——菜单一次性创建，条目文本
   随目标类型（目录/文件）用 `ModifyMenu` 或两个预建菜单切换。
7. **删除走回收站。**
   Rabbit 用 `rmSync/unlinkSync` 永久删除；PeMark 改为
   `SHFileOperationW(FO_DELETE, FOF_ALLOWUNDO)`，语义与资源管理器一致。
   这是与 Rabbit 的**有意偏差**，理由是 PeMark 的文档安全原则更强。
8. **路径授权对齐 Rabbit。**
   PeMark 的"授权根" = 当前工作区根目录。所有新建/重命名/删除目标必须位于该根
   之下（前缀匹配 + 长度边界检查），否则拒绝并提示。禁止对根目录本身重命名或
   删除。
9. **默认根目录 = 系统"文档"目录。**
   启动时若未显式选择工作区，用 `SHGetKnownFolderPath(FOLDERID_Documents)` 取路径
   并枚举，使面板开箱即用，与 Rabbit 一致。
10. **双面板用两套子控件，不再复用同一个 ListBox。**
    现状是"一个 ListBox + 一个 gutter + 一个滚动面"在两个模式间轮流使用；Rabbit
    的两个面板同时可见，因此必须让文件面板拥有自己的
    `hwnd_files`。**实现修正（2026-09-16，第二次实机反馈）**：两个面板最终都
    不自带 `WS_VSCROLL`，而是各自在自己的 17px 槽位里放一块同类的自绘滚动面
    （`hwnd_outline_scroll` / `hwnd_files_scroll`，同一个窗口类、同一段绘制与命中
    代码）？
    **最终结论（2026-09-16，第三次实机反馈）**：两处都用 **ListBox 自带的原生滚动条**
    （`WS_VSCROLL | LBS_DISABLENOSCROLL` + 与文档面同款的
    `AllowDarkModeForWindow` / `SetWindowTheme`）。自绘 overlay 方案退役：它要自己维护
    thumb 几何、命中区、悬停变粗、主题重绘，而且命中测试比较的是"主窗口客户坐标"与
    "overlay 局部坐标"，导致 outline 的滑块根本拖不动。原生滚动条把拖动、翻页、
    悬停变粗、暗色主题全部交给系统，和主编辑区右侧完全同源；`LBS_DISABLENOSCROLL`
    保证行数不足时滚动条不消失、列表宽度不跳。滚轮仍由消息泵按指针命中分流
    （让面板不必先获得焦点），驱动 `LB_SETTOPINDEX`，原生 thumb 自动跟随。
    切片 2 引入的"`panel_mode` 决定列表内容"随之取消，改为"两个列表始终各自维护内容"。
11. **面板高度用像素比例表达，不用 CSS flex。**
    侧边栏内部维护 `panel_split`（文件面板占内容高度的千分比，取值见 §5），
    `resize_children` 按它计算两个面板矩形与分界线位置：文件面板 =
    `header(28) + 列表`，分界线 4px，大纲面板 = `header(28) + 列表`。
    拖动只改 `panel_split`，三态只改"哪个面板被最小化/最大化"的枚举，两者共同
    决定最终几何，避免高度与状态互相覆盖。
12. **分界线拖动与标题点击沿用既有鼠标路径。**
    分界线是一个 4px 高的子窗口（`hwnd_panel_divider`），拖动复用
    `splitter_drag` 那套模式（`SetCapture` + `WM_MOUSEMOVE` + 绝对位置换算），
    命中时把光标设为 `IDC_SIZENS(32645)`；标题栏是自绘 STATIC
    （`hwnd_files_header` / `hwnd_outline_header`）。单击先用
    `SetTimer(0x4E, 250ms)` 挂起，双击用 `GetMessageTime` 的间隔（同一标题栏
    且不超过 500ms）判定并取消挂起。挂起的单击到点才走三态循环：这与 Rabbit 的
    `setTimeout` 同义，多花一个定时器 ID，换来的是双击的第二下必然落在**没有
    移动过**的标题栏上。若第一次单击立即应用，最小化会让标题栏当场移位，
    第二下就落空了。
13. **两个面板共用主题与命中路由。**
    hover/拖动/滚轮等现有逻辑（`update_outline_hover`、
    `outline_scroll_drag_move`、`mousewheel_event`）按"鼠标落在哪个面板矩形"分流，
    再作用于该面板的滚动状态；主题刷子继续共用一套。

## 5. 数据模型

新增状态（BSS，均为动态 arena 或定长小结构）：

| 名称 | 含义 |
| --- | --- |
| `panel_split` | 文件面板占侧边栏内容高度的千分比（默认 500，钳制到 `[80, 920]`） |
| `files_state` / `outline_state` | 各自的三态：0 = maximized，1 = half，2 = minimized（默认 half） |
| `files_visible` / `outline_visible` | 该面板是否参与布局（`View` 菜单的显示开关；默认都可见） |
| `hwnd_files` / `hwnd_files_scroll` | 文件面板列表 + 它自己的自绘细滚动面（与大纲同款） |
| `files_scroll_*` | 文件面板滚动状态：count/top/visible_rows/max_top/track/thumb/travel/可见性/拖动 |
| `hwnd_files_header` / `hwnd_outline_header` | 两个 28px 自绘标题栏（新增） |
| `hwnd_panel_divider` | 4px 分界线子窗口（新增） |
| `files_scroll_*` | 文件面板的滚动状态（count/top/visible_rows/thumb/track/travel…），与现有 `outline_scroll_*` 同构 |
| `tree_root_path` | 当前树的根（512 单元） |
| `tree_rows` | 可见行 arena，行为 `{name[260], path[512], depth, flags}` |
| `tree_row_count` / `tree_row_capacity` | arena 计数 |
| `tree_expanded` | 展开集合 arena，每项为一条目录路径（512 单元） |
| `tree_expanded_count` / `tree_expanded_capacity` | 展开集合计数 |
| `tree_selected_path` | 持久选中项路径（跨刷新保持高亮） |
| `rename_hwnd` / `rename_row` | 浮动 EDIT 与其目标行 |
| `tree_last_error` | 最近一次枚举的错误码，用于"无法读取目录"提示 |

行 `flags` 位：`bit0 = 目录`、`bit1 = 已展开`、`bit2 = 根行`、`bit3 = 授权子树外`
（保留，暂不使用）。

已被本方案取代的状态：`panel_mode` 与 `set_panel_mode` / `refresh_panel_list` 的
"二选一"语义。大纲的三张表（`outline_srcpos` / `outline_renderpos` /
`outline_level`）与 `outline_count` 保持不变，仍只描述大纲；文件树另用自己的
`tree_rows`。`outline_*` 滚动状态保留给大纲面板，新增同构的 `files_*` 一组。

几何计算（`resize_children` 内）：

1. 侧边栏内容高度 = `client_h - status_h`，减去两个标题栏（28×2）、分界线 4px，
   再按 `files_visible` / `outline_visible` 扣掉被隐藏面板的标题栏；
2. 剩余高度按 `panel_split` 分给两个列表；
3. 三态覆盖比例：某面板 `maximized` → 它拿 90%、另一个 10%；`minimized` →
   它只保留 28px 标题栏、列表高度为 0；两个都 `half` → 用 `panel_split`；
4. 分界线位于两个面板之间；某面板隐藏时不画分界线。

重建流程 `tree_rebuild()`：

1. 清空 `tree_rows`；若 `tree_root_path` 为空则尝试"文档"目录；
2. 写入首行 `..`（`tree_root_path` 的父目录存在时）；
3. 从根开始，对每个目录：写入目录行；若该路径在展开集合内，递归枚举其子项并
   按"目录在前、同类按名升序"插入；
4. 过滤掉 `.` 开头的名称；枚举失败时记录 `tree_last_error` 并在该行位置插入一条
   提示行（不可点击）；
5. 重新应用 `tree_selected_path` 的高亮，必要时滚动到可见。

## 6. 交互规范

| 输入 | 行为 |
| --- | --- |
| 单击文件面板标题栏 | 250ms 后三态循环 `half → minimized → maximized → half`（与 Rabbit 同义） |
| 双击文件面板标题栏 | 在 `minimized` 与 `maximized` 之间对调：最小化的面板双击后最大化，其余状态双击后最小化 |
| 单击/双击大纲标题栏 | 同上，状态机互相独立（与 Rabbit 一致） |
| 标题栏内的按钮（折叠/刷新） | 只触发按钮动作，不改变面板状态 |
| 拖动 4px 分界线 | 改 `panel_split`，按指针绝对位置换算，钳制到 `[80, 920]‰` |
| 分界线悬停 | 背景变强调色，光标变 `IDC_SIZENS` |
| 单击箭头区（缩进段末尾 12px） | 展开/折叠该目录（`Shift` 时递归展开） |
| 单击目录行其他区域 | 展开/折叠 |
| 单击文件行 | 打开（走现有 Open 事务，含未保存保护），高亮，焦点留在面板；`.md` 打开后切到预览 |
| 双击目录/文件行 | 进入内联重命名 |
| 右键 | 上下文菜单（目录/文件两套） |
| `Backspace` | 返回上级（把父目录设为新的根），焦点在面板时生效（已有） |
| `Enter` | 打开选中文件；选中目录则展开/折叠 |
| `↑` / `↓` | 移动选中行（ListBox 原生行为，保持） |
| 滚轮 | 滚动列表（已有共用滚动条几何） |
| 双击 `..` 行 | 与 Backspace 相同 |
| `Ctrl+Shift+O` | 打开文件夹（新增快捷键，与 Rabbit 一致） |

## 7. 视觉规范

- 侧边栏从上到下：文件标题栏 28px → 文件列表 → 分界线 4px → 大纲标题栏 28px →
  大纲列表；`minimized` 的面板只剩 28px 标题栏。
- 标题栏：左侧 11px 小标题（次要色），文件面板标题栏中间显示根路径缩略
  （过长省略），右侧两个 14px 按钮（`«` 全部折叠、`↻` 刷新）；hover 整条变背景色。
- 分界线：默认边框色，hover/拖动中变强调色。
- 行高 30px（沿用现有 owner-draw 行高）。
- 每级缩进 16px；箭头区宽 12px，箭头字形 `▸`（折叠）/`▾`（展开）。
- 目录：名称后追加 `\`，颜色使用当前主题的强调色（沿用切片 2 的目录色）。
- 文件：`.md` / `.markdown` 用强调色，`.txt` 用正文色，其他扩展名用次要色。
- 选中行：沿用现有选中背景（`hbrush_edit`），并保持文字对比度。
- `..` 行：用次要色，与普通目录行区分。
- 提示行：次要色，不可选中。
- 大纲面板的行沿用现有层级配色（H1–H3 强调色 + 正文色），选中行高对比；
  标题栏与文件面板共用同一套刷子。

## 8. 菜单与快捷键

- `File → Open Folder...`（已有 `1006`）
- `File → Refresh Tree`（新增）、`File → Collapse All`（新增）
- `View → Files Panel` / `View → Outline Panel`（已有 `1308` / `1309`）——语义由
  "切换面板内容"改为"显示/隐藏对应面板"，勾选态 = 可见；两者都隐藏时左边栏
  整体收起，等价于 Rabbit 的 `Ctrl+B`
- 新增 `Ctrl+Shift+O` 加速键映射到 `1006`，与 Rabbit 一致

## 9. 切片划分与验收

### 切片 0：左边栏双面板骨架

- 新增文件面板三件套（`hwnd_files` + gutter + 滚动面）、两个 28px 标题栏与
  4px 分界线子窗口；`resize_children` 改为按 `panel_split` 与三态计算几何；
- 标题栏单击三态循环、双击 min/max 对调；分界线拖动改比例并钳制；
  每面板独立滚动状态与命中路由；
  - 已完成：三件套、两个标题栏、4px 分界线；`panel_split` 三态几何；
    标题栏单击/双击（250ms 挂起 + `GetMessageTime` 判定）；分界线悬停高亮、
    `IDC_SIZENS` 光标、绝对位置拖动与 `[80, 920]‰` 钳制。证据：
    `tools/test_v8_6_panel.py` 用真实指针输入驱动以上全部行为。
  - 未完：文件面板自己的滚动条（当前 overlay 仍只服务大纲）、
    `View → Files/Outline Panel` 的显示开关语义、每面板独立滚动路由。
- 切片 2 的 `panel_mode` 二选一语义与相关测试在此切片被替换（大纲内容、
  层级配色、`outline_*` 三表与滚动状态全部保留，只是不再与文件共用控件）；
- 验收：两个列表同时可见且各滚各的；拖动分界、单击/双击标题的三态与钳制符合
  §6；坐标与命中测试无越界；主题切换后两个面板与标题栏重绘正确；
  `View → Files/Outline Panel` 改为显示开关后勾选态正确；V8.5.4 全套件与
  大纲相关既有测试保持通过。

### 切片 1：树模型与展开集合（无 UI 变化）

- `tree_root_path` / `tree_rows` / `tree_expanded` 与 `tree_rebuild()`；
- 保留现有 `ws_*` 目录枚举能力作为底层（改名或直接复用 `FindFirstFileW` 路径）；
- 验收：测试命令输出可见行列表；展开集合增删后行数与顺序正确；不可读目录产生
  提示行与错误码；隐藏项被过滤；排序为目录在前、同类按名升序。
  - 已完成：`tree_rows` 使用 544 字节行 arena，`tree_expanded` 保存展开路径，
    `tree_rebuild` 用“在展开目录后插入子行、再继续向前扫描”的迭代法生成扁平
    可见行，不需要递归；隐藏项和不可打开扩展名在插入前过滤；枚举失败发布
    `tree_last_error` 并返回失败。命令 `1910` 提供无 UI 的重建探针。
  - 证据：`tools/test_v8_6_tree_model.py` 用真实临时目录验证根层过滤、目录优先、
    一级/二级展开、depth 与缺失根错误；`smoke_test_v8_5_1.py` 仍为 17/17。

### 切片 2：树绘制与命中测试

- 按行 flags 绘制缩进、箭头、目录后缀与类型色；箭头区与行区命中分流；
- 验收：像素证据显示缩进行位移正确、箭头字形随展开状态变化；点击箭头区只切换
  展开（不改变根），点击行其他区域行为符合表格；滚动条几何与行数同步。
  - 已完成：文件列表现在是 `tree_rows` 的投影，行文本由
    `tree_display_name` 生成（缩进、`▸/▾`、末级名称、目录反斜杠）；每个
    ListBox 项通过 `LB_SETITEMDATA` 保存树行索引；owner-draw 从
    `DRAWITEMSTRUCT.itemData` 取行并读取 `TREE_OFF_FLAGS`。目录激活切换展开
    集合并重建投影，文件激活复用现有 Open 事务。枚举改为目录优先的两遍
    `FindFirstFileW`，保持旧的目录排序契约。
  - 证据：`tools/test_v8_6_tree_ui.py` 使用真实进程验证投影、itemData、目录展开
    和文件打开；`tools/test_v8_6_panel.py` 与 `test_v8_6_navigation.py` 已更新为
    新的树行文本契约。

### 切片 3：文件操作（重命名 / 新建 / 删除 / 复制路径）

- 浮动 EDIT 内联重命名；右键菜单；回收站删除 + 确认对话框；复制路径到剪贴板
  （`OpenClipboard`/`SetClipboardData`，新增导入）；
- 授权检查：目标必须在根目录子树内；根目录本身禁止重命名/删除；
- 验收：重命名后行名与磁盘一致；重名/非法名/越界路径被拒绝且文件未变；删除进
  回收站（可用资源管理器验证）；新建文件/文件夹自动去重命名；操作失败时文档与
  树状态不变。
  - 已完成：双击行落入 `rename_begin` 的浮动 EDIT，Enter 提交、Escape 取消、
    失焦即提交；提交前拒绝路径分隔符、空名与已存在的目标，带隐藏标记的根行
    不可重命名。右键落在文件行上弹出上下文菜单（目录 / 文件 / 根行三套），
    `TrackPopupMenu` 只把命令号 `PostMessage(0x8009)`，因此菜单动作与注入式
    测试走同一条代码路径。删除先确认再走 `SHFileOperationW`（`FOF_ALLOWUNDO`）
    进回收站，并就地压掉展开集合里落在被删子树内的路径；复制路径把整行绝对路径
    写成 `CF_UNICODETEXT`；新建文件/文件夹在选中目录（或选中文件的父目录）里
    自动去重命名（`New File.md` → `New File (2).md`），创建成功后展开目标目录、
    重建树、选中新行并直接进入内联重命名。`tree_rebuild` 会移除隐藏根行，所以
    列表里不存在可重命名、可删除的授权根行。
  - 证据：`tools/test_v8_6_file_ops.py` 用真实进程与临时目录验证剪贴板内容、
    Escape 取消、两轮新建去重、每一行都落在授权根子树内，以及确认后文件从磁盘
    消失；`tools/smoke_test_v8_5_1.py` 保持 17/17。

### 切片 4：标题栏按钮、刷新、全部折叠、默认根目录

- 文件标题栏右侧两个按钮（全部折叠、刷新）与根路径缩略；
- `Ctrl+Shift+O` 与新增菜单项；
- 启动默认加载系统"文档"目录；
- 验收：按钮命中区正确、主题切换后重绘正确；刷新后树反映外部变化且选中项保持；
  全部折叠后只剩根的子项；默认根目录可读。
  - 已完成：文件标题栏在 `Files` 与两个按钮之间用 `DT_PATH_ELLIPSIS` 显示当前根
    路径（首尾保留、中段省略）；右端两个按钮的矩形在绘制时缓存，命中测试与 hover
    共用同一份几何，因此不存在"画在这里、点在别处"。点按钮只 `PostMessage` 命令号
    （`1313` 刷新 / `1314` 全部折叠），不参与 half/minimized/maximized 三态循环，
    也不武装单击等待定时器。File 菜单同时暴露 `Refresh Tree` 与 `Collapse All`。
    刷新重新枚举目录后按路径找回原选中行；全部折叠清空展开集合后走同一条重建路径。
    `Ctrl+Shift+O` 打开文件夹的加速键此前已就位。启动时用 `SHGetFolderPathW`
    （`CSIDL_PERSONAL`）取系统"文档"目录并作为默认工作区；目录不存在或不可读时
    保持空工作区。初始化末尾发布 `init_done` 标志，测试宿主在写 BSS 前必须等它，
    否则会与"shell 查询 + 目录枚举"的启动期竞争。
  - 证据：`tools/test_v8_6_header_buttons.py` 用真实指针点击缓存矩形（先验证 hover
    命中，再按下抬起）确认折叠只清展开集合、面板状态与单击定时器不变；用临时目录
    验证刷新既拾取外部新文件又保持选中；两个命令再从 File 菜单走一遍同样的路径。
    `tools/smoke_test_v8_5_1.py` 保持 17/17，`tools/test_v8_5_1.py` 0 failures。

### 切片 5：键盘导航与选择持久化

- `Enter` 打开/展开、`Backspace` 返回上级、单击打开后焦点留在面板；
- 选中项跨刷新、跨展开折叠保持；
- 验收：键盘全流程可完成"展开 → 选文件 → 打开"；打开后焦点仍在列表；选中项在
  重建后仍高亮且可见。
  - 已完成：`Enter` 与 `Backspace` 在消息泵里共用同一条"焦点必须在文件列表"的门，
    `Enter` 激活选中行（目录展开/折叠走 `tree_toggle_path`，文件走已有 Open 事务），
    `Backspace` 把父目录设为新的工作区根。`ws_open_or_enter` 的两条出口（切换目录、
    打开文件）都显式 `SetFocus(hwnd_files)`，所以打开文件不会把焦点抢到编辑区。
    树的展开/折叠改用与刷新、全部折叠同一条"记住选中行路径 → 重建 → 按路径找回"
    的路径，选中项因此不会被 `LB_RESETCONTENT` 清成无选中。
  - 证据：`tools/test_v8_6_keyboard.py` 用真实进程与临时目录跑完整键盘流程——点击某行
    取得焦点 → `Enter` 展开目录（行数 3→4、选中仍是该目录）→ `Enter` 折叠（回到 3 行、
    选中不变）→ 再展开并选中文件 → `Enter` 经 Open 事务打开（`current_path` 落到该文件、
    焦点仍在列表、选中仍是该文件）→ `Backspace` 把父目录设为新根并只显示它的子项。

至此 [FILE_PANEL_REDESIGN.md](FILE_PANEL_REDESIGN.md) 的切片 0–5 全部完成：文件面板
具备树形浏览、完整文件管理、标题栏按钮与刷新/折叠、键盘导航与选择持久化。

每个切片独立可验证、可回滚，且任何时刻保持可构建。切片 2 之后文件树可用，
切片 3 之后具备完整文件管理能力。

## 10. 与既有决策的冲突记录

| 原决策（MILESTONE_PLAN §6） | 现在 | 原因 |
| --- | --- | --- |
| 先做单层列表，不做 TreeView | 改为可展开目录树 | 用户要求全面参考 Rabbit |
| 第一版只读 | 加入新建/重命名/删除 | 同上；并补授权与确认机制 |
| 不做后台监视 | 保持不做 | Rabbit 也只有手动刷新 |
| V8.6 切片 2：两个模式复用同一个 ListBox | 改为双面板、各自一套列表与滚动条 | Rabbit 的文件与大纲是上下同时存在的两个面板 |

被保留的原决策：不引入 `SysTreeView32`（改为自绘扁平树）、单一可写文档、
`ReadDirectoryChangesW` 仍推迟、窗口几何持久化仍推迟。

## 11. 与 Rabbit 的有意偏差

| 项 | Rabbit | PeMark | 理由 |
| --- | --- | --- | --- |
| 删除 | 永久删除 | 回收站 | PeMark 文档安全原则更强 |
| 图标 | emoji | 箭头 + 类型色 | 面板字体不保证 emoji 显示 |
| 文件过滤 | 显示全部非隐藏项 | 只显示 `.md` / `.markdown` / `.txt` | 用户决策：只列出可打开的文本 |
| 打开方式 | 单击打开 + 双击重命名 | 同 Rabbit | 用户决策 |
| 面板比例表达 | CSS flex 百分比 + 0.15s 过渡 | 像素千分比，无过渡动画 | 自绘窗口没有 CSS 过渡，瞬间重排更可预测 |
| 单双击区分 | 250ms `setTimeout` | 250ms `SetTimer` 挂起单击 + `GetMessageTime` 间隔判定双击 | 语义与 Rabbit 一致；立即应用会让标题栏在双击中间移位 |
| 保存备份 | 覆盖前 `.bak.md` | 不采用 | 已有事务化保存与 staging 保障 |
| 滚动条 | 浏览器原生滚动条 | 两个面板都用 ListBox 自带的 Windows 原生滚动条（深色主题与主编辑区一致） | 与主编辑区同源同款；自绘方案在命中坐标系上踩过坑，且维护成本高 |
| 选择文件夹 | Electron 的目录选择 | 通用项对话框 `IFileOpenDialog` + `FOS_PICKFOLDERS`（`SHBrowseForFolderW` 仅作回落） | 与"打开文件"的 `GetOpenFileNameW` 同属通用项对话框家族，风格一致 |

## 12.1 实机反馈带来的两条硬规则（2026-09-16）

1. **面板框架必须显式重绘。** 两个标题栏、分界线和 gutter 都是自绘子窗口：
   切主题时只换刷子不会自动重画，必须 `InvalidateRect` + `UpdateWindow`，
   否则会出现"标题栏/分界线还是上一个主题的颜色，收起再展开左栏才正常"。
2. **从消息泵 `jmp` 进入的命令处理器，栈帧必须是 16 的倍数。**
   这类处理器不是被 `call` 进入的，`sub rsp, 0x38` 会让 API 调用跑在未对齐的
   栈上：`CoCreateInstance` 会返回 `REGDB_E_CLASSNOTREG`，看起来像"类没注册"，
   实际是栈对齐问题。构建期断言会扫描所有路由命令标签的帧大小。
3. **自绘滚动槽位必须常驻显示，自己刷底色。**
   两个滚动面（`hwnd_outline_scroll` / `hwnd_files_scroll`）在侧栏可见期间一律
   显示：它们负责把 17px 槽位刷成面板底色，只有 thumb 取决于"能不能滚"。
   曾经"不可滚动就整窗隐藏"的写法会让这条槽位没人重画——启动时显出一条比列表
   更灰的竖条，反复开关侧栏后还会把文档画在这里的文字留在槽位上。
4. **任何几何变化后必须显式重绘文档面。**
   拖动分隔条、开关侧栏都会同时改变 EDIT/RichEdit 的位置与宽度；`MoveWindow`
   不会让它们重画全部内容，会留下旧像素（花屏）。`resize_children` 末尾统一
   `RedrawWindow(RDW_INVALIDATE|RDW_ERASE|RDW_ALLCHILDREN)`，并顺带重新同步
   文件面板滚动条。
5. **被 `call` 进入的例程，入口压栈与出口弹栈必须成对。**（2026-09-17）
   `tree_find_row_by_path` 入口只压了 3 个寄存器、出口却弹 4 个，把调用者的
   `rsp` 弹坏：新建目录本身成功，约两秒后才以 `0xC0000005` 崩溃，看起来像
   "创建之后的异步操作有问题"。构建期断言现在统计文件操作区域的 push/pop
   总数，并单独锁定几个例程的 4 寄存器 / `0x38` 帧。
6. **消息泵里的例程不得改写 `r12`。**（2026-09-17）
   泵把 `&MSG` 放在 `r12`；标题栏 hover 例程一度用 `xor32('r12')` 当临时变量，
   于是 mousemove 之后 `DispatchMessageW` 收到空指针，进程再也不进入输入空闲
   （`WaitForInputIdle` 一直超时）。构建期断言现在扫描该例程，禁止出现 `r12`。
7. **内联缓冲要取地址，不能按值读。**（2026-09-17）
   `tree_root_path` 是 BSS 里的 UTF-16 缓冲；标题栏路径缩略曾经用
   `mov r64, [tree_root_path]` 把字符串头 8 字节当成 `LPCWSTR` 交给 `DrawTextW`，
  首次重绘即在 user32 内 `0xC0000005`。凡是把内联缓冲交给 API，一律用
   `lea_rip` 传地址；构建期断言锁定这一处。
8. **单击激活由消息泵按坐标命中，不能挂在 `LBN_SELCHANGE` 上。**（2026-09-17）
   原来的判定是"选中变化通知 + `GetKeyState(VK_LBUTTON)` 有按下位"，它有两个
   缺陷：点已经选中的行不产生选中变化通知，于是永远不触发；某些输入状态下
   `GetKeyState` 也拿不到按下位。结果是"鼠标点不动，只有回车有效"。现在
   `lbd_files_row_click` 在泵里用 `LB_ITEMFROMPOINT` 命中行、`LB_SETCURSEL`
   选中、`SetFocus` 后走与双击/回车相同的 `ws_open_or_enter`；未命中任何行则
   `jmp dispatch` 把消息交还默认处理。`wp_command` 只保留 `LBN_DBLCLK`
   （内联重命名）。构建期断言禁止该区间再出现 `GetKeyState`。

## 12. 已确认的决策（2026-09-16）

1. **删除语义**：删除进回收站（`SHFileOperationW` + `FOF_ALLOWUNDO`），与
   Rabbit 的永久删除有意偏离。
2. **文件过滤**：只显示 `.md` / `.markdown` / `.txt` 与目录；其余文件类型不出现在
   树里（因此也不存在"不支持打开"的提示分支）。
3. **打开方式**：单击打开文件、双击进入内联重命名，与 Rabbit 一致。
4. **默认根目录**：启动即加载系统"文档"目录。

补充确认项（本次一并纳入）：左边栏采用 Rabbit 的**上下双面板**布局——文件浏览器
在上、大纲导航在下、中间可拖动分界线，两个标题栏可点击切换三态；这取代了切片 2
"两个模式复用同一个 ListBox"的设计。
