# PeMark V8.6.5 发布结果

[English](V8_6_5_RELEASE_RESULTS.md) | 简体中文

- 日期：2026-09-19
- 标签：`v8.6.5`
- 通道：stable
- 范围：深浅两种主题下的窗口边框区隔度

## 产物

| 项目 | 值 |
|---|---|
| 生成器 | `src/current/generate_markdown_editor_v8_6_5.py` |
| 生成器 SHA-256 | `2d18f4d1a1987d69b668252fdbd9450e1a33293919f62976746e4d7daadffbff` |
| 二进制 | `bin/current/pemark_x64_v8_6_5.exe` |
| 二进制 SHA-256 | `a038974bcd61c6a2720af5fb40ef7ad0c5c12c3745d801b8ef06e119b3b679e9` |
| 二进制大小 | 190976 字节 |
| `.text` | 59658，预算 61440（余量 1782） |
| 原始数据 | 189952 字节，6 个段，镜像大小 196608 |
| 虚拟 BSS | 102400 字节 |

## 本次构建执行的门禁

1. **确定性构建。** 连续两次运行生成器得到完全相同的 SHA-256
   `a038974b…`；`tools/build_current.py` 已改为锁定 V8.6.5 与同一摘要，
   因此第三次运行可由标准工具直接校验。
2. **机器码回归。** `python tools/test_v8_5_1.py
   src/current/generate_markdown_editor_v8_6_5.py` 输出 `"failures": []`。
   覆盖内容包括 210 组滚动条容量/高度/顶部边界组合、
   视口格式化与裁剪不变量、两端拖拽夹紧、排队鼠标处理消费消息坐标，
   以及窗口销毁后的退出路径。
3. **PE 检查。** `python tools/inspect_pe.py
   bin/current/pemark_x64_v8_6_5.exe` 报告 PE32+ AMD64（`0x8664`，
   可选头 `0x020B`），6 个段且保护属性依次为 RX / R / RW / RW / R / R，
   没有 W+X 页；导入面符合预期（KERNEL32、USER32、GDI32、DWMAPI、UXTHEME）。
4. **交互式桌面 GUI 冒烟。** `python tools/smoke_test_v8_5_1.py
   bin/current/pemark_x64_v8_6_5.exe` → 17/17 通过，其中包括"恰好 1 个可见
   文档表面"不变量（SOURCE 态）、20 次连续模式切换、主题与换行往返，
   以及干净 `WM_CLOSE` 退出（退出码 0）。
5. **运行窗口的边框像素实测。** 四边都携带主题边框色：浅色模式 `#B0B0B0`、
   深色模式 `#3C3C3C`，150% 显示缩放下宽 2 个物理像素，实时切换
   Light/Dark 时在一帧内同步更新。

## 顺带修复的基线问题

- `tools/build_current.py` 此前仍锁定 V8.6.3 的生成器与 V8.6.3 摘要，现已改为
  锁定 V8.6.5。
- 本次调用 `tools/smoke_test_v8_5_1.py` 时显式传入了可执行文件路径。它的默认
  参数仍指向 `bin/current/pemark_x64_v8_5_1.exe`，而 `CODEX_START_HERE.md` 原先
  让 Agent **不带参数**运行它——那会在声称检查当前构建的同时实际验证 V8.5.1 的
  二进制。首会话命令现已改为显式传参。
- `.github/workflows/direct-pe.yml` 把 V8.6.3 的生成器路径、二进制路径与期望摘要
  全部写死。V8.6.4 与 V8.6.5 两次发布都没有更新它们，导致 "Verify release hash"
  步骤在每次已发布的推送上都抛出 `SHA-256 mismatch`，而构建本身是正确的。
  该 workflow 现已改为从 `manifest.json` 读取生成器、二进制与期望摘要——而
  `manifest.json` 按定义就是每次发版必更的文件。
- CI 里的 V8.6 行为套件此前跑在 `src/candidate/` 上，那是 V8.6 的旧快照，早于
  `Ctrl+J` 右栏预留（1315），因此 `test_v8_6_keymap.py` 自 V8.6.4 起在每次推送
  上都报 `accelerator 09/004A must map to 1315, got None`，而发布构建本身是正确
  的。这些套件现已改为从 `manifest.json` 指定的 current 通道取
  `PEMARK_GENERATOR` / `PEMARK_EXE` / `PEMARK_TREE_EXE`；`test_v8_6_caption.py`
  的期望版本标签也改为读取 `current_snapshot`，不再硬编码 V8.6.3。本次发布的
  `Direct-PE validation` workflow 已通过——这是该 workflow 自 V8.6.3 以来首次成功。
- 本次发布首次推送后，已上线的 `README.md` 仍在宣传 V8.6.3：下载链接、预期
  哈希、构建与校验命令、验证结果链接以及仓库结构里的版本行都是旧的。现已连同
  `README.zh-CN.md`、`docs/README.md`、`docs/README.zh-CN.md` 与
  `docs/WIN32_API_SURFACE.md` 一并更新，发布清单也已把"对外入口文档"列为发版的
  必需步骤。

## 本次构建未覆盖的范围

- V8.6.5 没有独立的第二台机器验证包（V8.5.4 有）。
- 需要真实指针输入的 V8.6 GUI 套件不在本门禁内。`tools/test_v8_6_mouse_activate.py`
  在已冻结的 V8.6.4 基线上同样失败，因此该失败属于既有问题，与本次发布无关。
- 可执行文件仍未签名。
