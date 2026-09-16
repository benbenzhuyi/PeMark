# V8.5.4 独立机器验证包

用途：在一台与维护者不同的 Windows 机器上复现 V8.5.4 的发布验证。

## 前置条件

- 64 位 Windows 10 或 Windows 11，**交互式桌面会话**（GUI 测试需要真实桌面）；
- Python 3.10 或更高版本；
- Git 可访问仓库；
- 磁盘可用空间约 200 MB。

## 步骤

1. 取代码（分支名以维护者给出的提交为准）：

```powershell
git clone https://github.com/benbenzhuyi/PeMark.git
cd PeMark
git checkout v8.5.4-pe-hardening
git pull
```

2. 安装测试依赖（只有 `unicorn`，用于机器码回归）：

```powershell
python -m pip install -r requirements-dev.txt
```

3. 运行验证包：

```powershell
python tools/verify_release_v8_5_4.py
```

4. 把脚本最后输出的 **JSON 块**原样贴回给维护者。脚本退出码 0 表示全部通过。

## 预期结果

- 两次构建产生相同二进制；
- 二进制大小 91,648 字节，SHA-256 为
  `aa8de9cda9ed90a2cf66a3a93e021dc91cc192073078a90c53fa9669f478c5cc`；
- PE 检查显示 6 个节，`.text` 为 `0x60000020`（RX）、`.bss` 为 `0xC0000080`（RW），
  `dllChars=0x0140`；
- 机器码回归 13/13；
- 栈回溯元数据结构：42 条 `RUNTIME_FUNCTION`、版本 1 的 unwind info、dbghelp 能为
  我们的地址解析条目（脚本会打印"未跨帧"的备注，这属于已知限制，不算失败）；
- 节权限与 ASLR：加载后的 `.text` 为 `PAGE_EXECUTE_READ`、`.rdata` 为
  `PAGE_READONLY`、`.idata`/`.bss` 为 `PAGE_READWRITE`，且加载基址不等于
  `0x140000000`；
- 打开/编码事务矩阵通过；
- GUI 冒烟 17/17，普通关闭退出码 0。

## 如果出现失败

请不要只贴一句"失败了"，把 JSON 里的 `failed_steps` 与对应步骤的 `tail` /
`stderr_tail` 一起贴回来即可，这些字段就是为该用途准备的。

常见环境差异与处理：

- `import unicorn` 失败：先执行第 2 步；
- GUI 步骤报"找不到窗口"：确认是在交互式桌面会话中运行，而不是 SSH/服务会话；
- 关闭类检查偶发超时：脚本会如实报告；请重跑一次并在回报中说明，维护者会结合
  两次结果判断是环境干扰还是真实问题。

## 脚本行为说明

验证脚本会**重新构建**发布二进制（两次）并与清单中的 SHA-256 比对。构建是
确定性的，所以这一步不会改变文件内容；如果哈希不匹配，脚本会直接报 FAIL，而不会
静默通过。

节权限、ASLR、栈回溯、打开/编码这几个套件默认面向开发通道，验证脚本会通过
`PEMARK_GENERATOR` / `PEMARK_EXE` 把它们指向 `src/current` 与 `bin/current`，
确保验证对象就是发布产物本身。
