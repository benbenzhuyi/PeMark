# GitHub 发布检查表

[English](PUBLISHING_CHECKLIST.md) | 简体中文

## 仓库

- [x] 将 V8.5.1 提升至 `src/current/` 和 `bin/current/`。
- [x] 将 V8.5.2 提升至 `src/current/` 和 `bin/current/`。
- [x] 将 V8.5.3 提升至 `src/current/` 和 `bin/current/`。
- [x] 将生成器路径改为项目相对路径。
- [x] 添加 MIT License。
- [x] 添加中英文 README、安全策略、贡献指南和发布说明。
- [x] 添加 Git 属性、忽略规则、Issue 模板和 Windows CI。
- [x] 更新 manifest 和全仓库 SHA-256 清单。
- [ ] 创建 GitHub 仓库并设置简介和 Topics。
- [ ] 开启私密漏洞报告。
- [ ] 推送 `main` 并确认 Direct-PE validation 工作流通过。

## V8.5.1 Preview（已发布）

- [x] 创建带说明的 `v8.5.1` 标签。
- [x] 创建名为 `PeMark V8.5.1 Preview` 的 GitHub Pre-release。
- [x] 只附加 `bin/current/pemark_x64_v8_5_1.exe`。
- [x] 确认附件 SHA-256 为
  `b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`。

## V8.5.2 Preview（已发布）

- [x] 在发布提交上重跑 commit 与 milestone 两级门禁，结果记录于
  `V8_5_2_RELEASE_RESULTS.md`。
- [x] 创建带说明的 `v8.5.2` 标签。
- [x] 创建名为 `PeMark V8.5.2 Preview` 的 GitHub Pre-release。
- [x] 使用 `RELEASE_V8_5_2_GITHUB.md` 作为发布正文。
- [x] 只附加 `bin/current/pemark_x64_v8_5_2.exe`。
- [x] 确认附件 SHA-256 为
  `2c105660dbac96b7de18614f43753073b3b5613e22bba160ceb8058646040e30`。
- [x] 保持 GitHub 的 “Set as a pre-release” 选项开启。

## V8.5.3 Preview

- [x] 在发布提交上重跑 commit 与 milestone 两级门禁，结果记录于
  `V8_5_3_RELEASE_RESULTS.md`。
- [x] 创建带说明的 `v8.5.3` 标签。
- [x] 创建名为 `PeMark V8.5.3 Preview` 的 GitHub Pre-release。
- [x] 使用 `RELEASE_V8_5_3_GITHUB.md` 作为发布正文。
- [x] 只附加 `bin/current/pemark_x64_v8_5_3.exe`。
- [x] 确认附件 SHA-256 为
  `6ad87c6dcb3b9d3a35041d1bc37e5792f3cfd16cb79046088a3426200d0bb7d0`。
- [x] 保持 GitHub 的 “Set as a pre-release” 选项开启。

## 仓库设置

- [x] 默认分支设为 `main`。
- [ ] 合并前要求 `build-and-test` 状态检查通过。
- [ ] 禁止对 `main` 强制推送和删除分支。
- [ ] 按需要开启 Discussions。
- [ ] 选定公开截图后加入 README。
