# PeMark · 码记 V8.6.3

PeMark V8.6.3 is the stable V8.6 desktop-workspace release of this native
Windows x64 Markdown editor. Its Python generator emits the PE32+ image and
AMD64 machine code directly, without a compiler, assembler or linker.

Highlights:

- compact custom title/menu row with Fluent tool icons and Windows controls;
- expandable workspace file tree with Fluent folder/document glyphs;
- single-click and keyboard activation, inline/context-menu rename, New File,
  New Folder, Recycle Bin delete, Copy Path, Refresh and Collapse All;
- stabilized Preview scrolling, thumb dragging and Outline jumps on large files;
- GDI-scaled DPI awareness and opaque ClearType sidebar drawing for crisp text;
- V8.5.4 document safety, dynamic arenas, ASLR and six permission-separated PE
  sections remain intact.

Validation includes deterministic builds, 13/13 emitted-machine-code groups,
210/210 scrollbar geometry cases, 17/17 real-GUI smoke checks, document-safety
and allocation-failure matrices, workspace/file-operation suites, and loaded
page checks confirming RX/R/RW/RW/R/R with no W+X page.

Asset: `pemark_x64_v8_6_3.exe`

SHA-256: `6b26585bb453010e358c726931d96f43cf5c4ef27cd02d1aff6101ad378698df`

---

PeMark · 码记 V8.6.3 是这款 Windows x64 原生 Markdown 编辑器的 V8.6
桌面工作区正式版。Python 生成器继续直接写出 PE32+ 映像与 AMD64 机器码，
不使用编译器、汇编器或链接器。

本版重点：

- 紧凑的自定义标题/菜单行、Fluent 工具图标和 Windows 窗口按钮；
- 带 Fluent 文件夹/文档图标的可展开工作区文件树；
- 单击与键盘打开、内联/右键重命名、新建文件/文件夹、回收站删除、复制路径、
  刷新和全部折叠；
- 修复大文档预览滚动、滑块拖动和大纲跳转后的渲染停滞；
- 通过 GDI 缩放 DPI 感知和不透明 ClearType 侧边栏绘制提升全窗口文字清晰度；
- 完整继承 V8.5.4 的文档安全、动态 arena、ASLR 和六节权限分离基线。

正式验证包括确定性构建、13/13 组机器码行为、210/210 组滚动条几何、17/17
项真实 GUI 冒烟、文档安全与分配失败矩阵、工作区/文件操作测试，以及已加载页
RX/R/RW/RW/R/R、无 W+X 的检查。

附件：`pemark_x64_v8_6_3.exe`

SHA-256：`6b26585bb453010e358c726931d96f43cf5c4ef27cd02d1aff6101ad378698df`

## Known limitations / 已知限制

The executable is unsigned. Settings and the right-sidebar switch are visual
placeholders. Full cross-frame stack walking is not demonstrated. / EXE 未签名；
设置和右边栏开关目前是视觉占位；完整跨帧栈回溯尚未证明。
