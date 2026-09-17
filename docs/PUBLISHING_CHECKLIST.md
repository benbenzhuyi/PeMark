# GitHub publishing checklist

English | [简体中文](PUBLISHING_CHECKLIST.zh-CN.md)

## Repository

- [x] Promote V8.5.1 to `src/current/` and `bin/current/`.
- [x] Promote V8.5.2 to `src/current/` and `bin/current/`.
- [x] Promote V8.5.3 to `src/current/` and `bin/current/`.
- [x] Promote V8.5.4 to `src/current/` and `bin/current/`.
- [x] Promote V8.6.3 to `src/current/` and `bin/current/`.
- [x] Make generator paths project-relative.
- [x] Add public README, security policy and contribution guide.
- [x] Add Git attributes, ignore rules, issue template and Windows CI.
- [x] Add deterministic build helper and per-version release notes.
- [x] Refresh manifest and repository SHA-256 inventory.
- [x] Add the MIT `LICENSE`.
- [x] Add English and Simplified Chinese public documentation.
- [ ] Create the GitHub repository and configure its description/topics.
- [ ] Enable private vulnerability reporting.
- [ ] Push `main` and confirm the Direct-PE validation workflow passes.

## V8.5.1 Preview release (published)

- [x] Create annotated tag `v8.5.1`.
- [x] Create a GitHub pre-release named `PeMark V8.5.1 Preview`.
- [x] Attach only `bin/current/pemark_x64_v8_5_1.exe` as the release asset.
- [x] Verify the uploaded asset SHA-256 is
  `b8b07fe43a20cb21e7e33d58a6300f4f2d388dcbc9a26e0306bdaa231f73a39f`.

## V8.5.2 Preview release (published)

- [x] Rerun the commit and milestone gates on the release commit and record them
  in `docs/V8_5_2_RELEASE_RESULTS.md`.
- [x] Create annotated tag `v8.5.2`.
- [x] Create a GitHub pre-release named `PeMark V8.5.2 Preview`.
- [x] Use `docs/RELEASE_V8_5_2_GITHUB.md` as the release body.
- [x] Attach only `bin/current/pemark_x64_v8_5_2.exe` as the release asset.
- [x] Verify the uploaded asset SHA-256 is
  `2c105660dbac96b7de18614f43753073b3b5613e22bba160ceb8058646040e30`.
- [x] Keep GitHub's “Set as a pre-release” option enabled.

## V8.5.3 Preview release

- [x] Rerun the commit and milestone gates on the release commit and record them
  in `docs/V8_5_3_RELEASE_RESULTS.md`.
- [x] Create annotated tag `v8.5.3`.
- [x] Create a GitHub pre-release named `PeMark V8.5.3 Preview`.
- [x] Use `docs/RELEASE_V8_5_3_GITHUB.md` as the release body.
- [x] Attach only `bin/current/pemark_x64_v8_5_3.exe` as the release asset.
- [x] Verify the uploaded asset SHA-256 is
  `6ad87c6dcb3b9d3a35041d1bc37e5792f3cfd16cb79046088a3426200d0bb7d0`.
- [x] Keep GitHub's “Set as a pre-release” option enabled.

## V8.5.4 Stable release

- [x] Rerun the commit and milestone gates on the release commit and record them
  in `docs/V8_5_4_RELEASE_RESULTS.md`.
- [x] Publish the independent-machine verification pack
  (`docs/V8_5_4_VERIFICATION_PACK.md`, `tools/verify_release_v8_5_4.py`).
- [x] Confirm the independent-machine JSON summary reports PASS
  (Windows 11 26200, Python 3.12.10, `failed_steps: []`, 17/17 GUI smoke,
  identical binary SHA-256 across machines).
- [x] Create annotated tag `v8.5.4`.
- [x] Create a GitHub release named `PeMark V8.5.4` **without** marking it a
  pre-release.
- [x] Use `docs/RELEASE_V8_5_4_GITHUB.md` as the release body.
- [x] Attach only `bin/current/pemark_x64_v8_5_4.exe` as the release asset.
- [x] Verify the uploaded asset SHA-256 is
  `aa8de9cda9ed90a2cf66a3a93e021dc91cc192073078a90c53fa9669f478c5cc`.

## V8.6.3 Stable release

- [x] Rerun the release gates on the formal channel and record them in
  `docs/V8_6_3_RELEASE_RESULTS.md`.
- [ ] Create annotated tag `v8.6.3`.
- [ ] Create a GitHub release named `PeMark V8.6.3` without marking it a
  pre-release.
- [ ] Use `docs/RELEASE_V8_6_3_GITHUB.md` as the release body.
- [ ] Attach only `bin/current/pemark_x64_v8_6_3.exe` as the release asset.
- [ ] Verify the uploaded asset SHA-256 is
  `6b26585bb453010e358c726931d96f43cf5c4ef27cd02d1aff6101ad378698df`.

## Repository settings

- [x] Set the default branch to `main`.
- [ ] Require the `build-and-test` status check before merging.
- [ ] Disable force pushes and branch deletion on `main`.
- [ ] Decide whether Discussions should be enabled.
- [ ] Add screenshots to the README when publication-ready images are selected.
