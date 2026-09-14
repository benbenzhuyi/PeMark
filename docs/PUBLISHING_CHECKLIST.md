# GitHub publishing checklist

English | [简体中文](PUBLISHING_CHECKLIST.zh-CN.md)

## Repository

- [x] Promote V8.5.1 to `src/current/` and `bin/current/`.
- [x] Make generator paths project-relative.
- [x] Add public README, security policy and contribution guide.
- [x] Add Git attributes, ignore rules, issue template and Windows CI.
- [x] Add deterministic build helper and V8.5.1 release notes.
- [x] Refresh manifest and repository SHA-256 inventory.
- [x] Add the MIT `LICENSE`.
- [x] Add English and Simplified Chinese public documentation.
- [ ] Create the GitHub repository and configure its description/topics.
- [ ] Enable private vulnerability reporting.
- [ ] Push `main` and confirm the Direct-PE validation workflow passes.

## V8.5.1 Preview release

- [ ] Create annotated tag `v8.5.1`.
- [ ] Create a GitHub pre-release named
  `PeMark V8.5.1 Preview`.
- [ ] Use `docs/RELEASE_V8_5_1_PREVIEW.md` as the release body.
- [ ] Attach only
  `bin/current/pemark_x64_v8_5_1.exe` as the release asset.
- [ ] Verify the uploaded asset SHA-256 is
  `b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`.
- [ ] Keep GitHub's “Set as a pre-release” option enabled.

## Repository settings

- [ ] Set the default branch to `main`.
- [ ] Require the `build-and-test` status check before merging.
- [ ] Disable force pushes and branch deletion on `main`.
- [ ] Decide whether Discussions should be enabled.
- [ ] Add screenshots to the README when publication-ready images are selected.
