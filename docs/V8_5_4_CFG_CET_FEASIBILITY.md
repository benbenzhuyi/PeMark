# V8.5.4 附录：CFG / CET 可行性结论

状态：结论性评估，本里程碑不实现  
评估对象：PeMark V8.5.4 candidate（Direct-PE，六节，ASLR 开启）

## 现状事实

| 项目 | 值 |
|---|---|
| DllCharacteristics | `0x0140`（NX_COMPAT + DYNAMIC_BASE），未设 GUARD_CF |
| LOAD_CONFIG 目录 | 未设置（0） |
| 导入目录 / IAT | `0x13000` / `0x13410`，均存在 |
| 异常目录（.pdata） | `0x17000`，42 条 |
| 基址重定位目录 | `0x16000` |
| `call_iat` 调用点 | 480 |
| `call_label` 调用点 | 267（直接相对调用，不涉及 CFG） |
| `call_r64` 调用点 | 11（UxTheme 的 `SetPreferredAppMode` / `AllowDarkModeForWindow` / `FlushMenuThemes`，经 `GetProcAddress` 解析后调用） |
| 导出函数 | 无 |
| 运行时可替换的函数指针 | 无（调用目标只有导入表与上述三个系统导出） |

## CFG（Control Flow Guard）

### 需要什么

1. `DllCharacteristics` 设置 `IMAGE_DLLCHARACTERISTICS_GUARD_CF`（`0x4000`）；
2. 一个 LOAD_CONFIG 目录，至少包含 `GuardCFCheckFunctionPointer`（指向
   `ntdll` 的检查函数）与 `GuardCFFunctionTable` / `GuardCFFunctionCount`
   （本模块允许被间接调用的目标集合）；
3. **在每一个间接调用点插入检查**：x64 上是先 `call [GuardCFCheckFunctionPointer]`
   或使用 `notrack` 前缀，再执行原间接调用。漏插会让加载器判定映像不自洽。

### 本项目的成本

- 需要插桩的间接调用点：480（IAT）+ 11（寄存器）= **491 处**。插桩集中在
  生成器的 `call_iat()` 与 `call_r64()` 两个辅助函数里，改动面可控；代价是
  每次 API 调用多一次间接检查，而 UI 代码调用 User32/RichEdit 极频繁，属于
  可测量但真实的开销。
- `GuardCFFunctionTable` 对本模块几乎为空：我们不导出函数，也没有把内部函数
  地址交给外部。因此目标表本身很小，成本主要在插桩而非建表。

### 收益

CFG 防的是"被篡改的间接调用目标"，也就是函数指针/返回地址被外部数据改写后
跳入任意地址。本程序里：

- 所有 IAT 项由加载器按导入表填充，不来自文件内容；
- 11 个寄存器调用目标是三个系统 DLL 导出的地址；
- 没有插件、没有脚本引擎、没有把函数指针写进文档或配置数据的路径。

也就是说当前**不存在可被控制的间接调用目标**，CFG 的边际收益很低。它的价值
会在出现"运行时可替换的函数指针"时才体现，例如 V9 的 provider/model 回调。

### 结论

**本里程碑不实现 CFG。** 重新评估条件：一旦引入插件式回调、模型 provider
接口或任何把函数指针写入可变数据的机制，CFG 就是必要条件，届时按上述三点实现，
并用 `inspect_pe` 校验 GUARD_CF 位、LOAD_CONFIG 目录与每个间接调用点的插桩
完整性。

## CET（Shadow Stack）

### 需要什么

- 硬件支持（Intel CET 或 AMD Shadow Stack）与操作系统启用；
- 映像侧声明兼容性（具体字段随 SDK 版本而异，本例未做声明）；
- 代码不得把返回地址当作数据使用，也不得用 `ret` 跳到计算出的地址。

### 本项目的现状

发射的代码满足后一条：没有 SEH、没有 C++ 异常、没有 `ret` 到动态地址，也没有
改写返回地址的模式；栈上只写自己帧内的影子空间与参数槽。因此**行为上与 shadow
stack 兼容**。

### 结论

**本里程碑不做声明。** 声明 CET 兼容不会改变程序的控制流行为（我们本来就没有
可被劫持的 `ret`），却引入"声明字段是否正确"的加载风险。等 SDK 对该字段给出
稳定定义，或平台策略要求声明时再评估；届时只需在可选头/LOAD_CONFIG 中设置对应
位，并用同一套加载矩阵验证。

## 与 V8.5.4 Release Gate 的关系

本节两项都不进入 V8.5.4 的发布门禁：CFG 的收益条件尚未出现，CET 的声明不改变
行为。V8.5.4 实际达成的安全属性是**可写数据不可执行**与**地址随机化**，两者都已
在运行时验证。
