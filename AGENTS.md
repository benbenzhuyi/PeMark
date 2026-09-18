# AGENTS.md — Mandatory Instructions for Codex and Other Development Agents

> **Language:** All user-visible agent reasoning, planning, progress reports, test conclusions, and final summaries must use **Simplified Chinese**. Code symbols, commands, API names, file names, identifiers, and necessary English technical terms remain unchanged.
>
> **Document language:** English is the canonical source language for project documentation. When a project document requires a Chinese mirror, update the English original first, then synchronize the `.zh-CN.md` / Chinese edition. This rule does **not** override the requirement that all user-visible agent communication be in Simplified Chinese.

## 1. Project identity

This is a **pure Direct-PE Windows x64 experiment**. The build-time Python generator constructs the PE32+ image, import table, static data, virtual BSS, and AMD64 machine-code bytes directly.

The purpose of the project is not merely to ship a Markdown editor. It is also an engineering experiment in AI-assisted direct machine-code software development. Preserve that research property when making architectural or implementation decisions.

### Non-negotiable build constraint

The production `.exe` must **not** be produced by:

- C/C++ compiler
- Rust compiler
- assembler
- linker
- .NET / managed compiler
- packager that embeds an interpreter

Analysis/debugging tools are allowed. Python is allowed as the build-time generator and test harness.

## 2. Working principle: context is a limited engineering resource

Treat model context as a **hard engineering budget**.

Do not maximize reading, searching, or tool use merely because those actions are available. Prefer the smallest amount of context sufficient to make and verify the current change.

### Context-efficient agent workflow

1. Work on **one clearly defined engineering slice at a time**.
2. Do not expand task scope unless required by a demonstrated failure.
3. Do not reread files, documents, logs, or conclusions already established by the current task summary unless new evidence requires it.
4. Prefer `rg`, `git diff`, `git log`, exact-symbol search, and narrow line-range reads over whole-file reading.
5. Do not read a large generator or document in full merely to "understand the project".
6. Run the most relevant existing test first. Inspect implementation only when a concrete failure requires it.
7. Keep command output small. Prefer filtered output, exact matches, summaries, and failure excerpts over large logs.
8. Do not repeatedly search the same symbols or reopen the same files without new evidence.
9. After a coherent engineering slice is implemented and verified, **stop and report a checkpoint** before starting another slice.
10. Before starting a new broad investigation, large-file read, unrelated subtask, or architectural expansion, first create a compact checkpoint containing only:
    - current goal
    - completed changes
    - verification results
    - next unfinished step
    - key files
    - key symbols / labels
11. If the host stops execution because the tool-call / thinking-round limit is reached, resume from the existing checkpoint. Do **not** re-audit completed work.
12. Do not assume the model can observe the exact remaining tool-call count or exact host-side context percentage. Do not make plans that depend on knowing those values.

### Stop conditions

Stop the current slice and report instead of continuing when:

- the requested change is implemented and the relevant verification passes;
- the next step would require a new subsystem or unrelated investigation;
- evidence is insufficient to justify expanding the hypothesis;
- the current failure has been isolated and the user should decide whether to proceed to the next phase;
- the host stops the task because of its own execution limit.

## 3. Before editing

Do **not** automatically reread all project documents before every change.

Use this default startup sequence:

1. Read this `AGENTS.md`.
2. Read the current task summary / handoff if present.
3. Check `git status` and the relevant `git diff`.
4. Locate the exact symbols, tests, and files related to the current task.
5. Read only the minimum directly relevant source ranges or project documents.

Read architecture, milestone, ABI, audit, failed-approach, or release documents **only when the current change actually touches that concern**.

Relevant project documents include, but are not limited to:

- `docs/SYSTEM_ARCHITECTURE_LONG_TERM.md`
- `docs/MILESTONE_PLAN.md`
- `docs/DEVELOPMENT_MANUAL_V8_5_PLUS.md`
- `docs/CURRENT_CODE_AUDIT.md`
- `docs/WIN64_ABI_RULES.md`
- `docs/ARCHITECTURE_V8_5_TARGET.md`
- `docs/FAILED_APPROACHES.md`

Do not read this entire set by default.

Rebuild and hash the current baseline only when:

- the task or verification level requires it;
- baseline identity is uncertain;
- deterministic build behavior is itself under test;
- a regression comparison requires a known baseline.

When documents conflict, the long-term architecture, milestone plan, and current development manual describe current policy. Historical audit/handoff files are evidence, not automatically current policy.

## 4. Hard engineering rules

1. **One source of truth:** `DocumentModel` owns document text.
2. **One view-mode state:** SOURCE/PREVIEW must not be represented by multiple independent flags or visibility assumptions.
3. **Outline stores source offsets only.** Preview offsets are derived through `PositionMap`.
4. **Win64 volatile registers:** every Win64 API call may clobber `RAX`, `RCX`, `RDX`, `R8`, `R9`, `R10`, and `R11`. Never keep live values there across calls.
5. Before every nested call from emitted machine code, maintain Win64 stack alignment and 32-byte shadow space.
6. Treat stack-frame boundaries as contracts. Never write beyond the allocated local stack frame; do not reuse the saved return-address slot as temporary storage.
7. Distinguish **address** from **contents** explicitly. For inline BSS/static objects passed by pointer, use address-form emission (`lea`-style) unless the API truly expects the loaded value.
8. Geometry belongs to one `LayoutManager`. Do not let individual commands independently calculate or move panes.
9. Scrollbar paint, hit-test, and drag must consume the same cached `thumbRect`; never recompute three subtly different rectangles.
10. Theme changes swap Palette + invalidate. Theme must not reparse Markdown.
11. Zoom must not rebuild Markdown `RenderModel`.
12. Do not perform RichEdit full-document per-span formatting on large documents.
13. Do not claim a GUI bug fixed without Windows execution. Static checks are useful but insufficient.
14. Every real regression fix must add or update a deterministic regression case when a practical, cheaper guard is available.
15. **Minimum sufficient engineering:** implement the smallest mechanism that solves a demonstrated problem. Plans and architecture documents describe intent; they do not authorize building future infrastructure early.
16. Before adding a check, contract, ADR, gate, fixture, or diagnostic tool, state the failure it prevents and why a cheaper option is insufficient.
17. **Gate by level:** apply commit-level, milestone-level, or release-level verification as defined in the current development manual. Do not apply release-level process to every change.
18. **Causal isolation before system-level hypotheses:** when a regression appears, first inspect the most recent diff and perform a minimal A/B short-circuit or equivalent causal isolation. Do not expand to PE loader, TLS, BSS, DPI, USER32 initialization, or other system-level hypotheses without a falsifiable, evidence-based concrete hypothesis.
19. A small bad code block does not justify a project-wide debugging expedition.
20. When a bug is isolated, stop expanding diagnosis. Fix the isolated cause, verify it, add the cheapest useful regression guard, and return to the roadmap.

## 5. Regression and debugging discipline

When a regression appears, use this order:

1. Identify the first known-bad behavior and the last known-good evidence.
2. Inspect the most recent relevant diff.
3. Form one concrete, falsifiable hypothesis.
4. Perform the smallest A/B experiment that can confirm or falsify it.
5. If confirmed, fix only that cause.
6. Run the narrowest relevant regression first.
7. Expand the test set only after the narrow test passes.
8. Record the bug as a regression fixture/assertion only if doing so is cheaper than allowing recurrence.
9. Remove or archive temporary diagnostic scripts when they are no longer needed.

Do not:

- create multiple large diagnostic scripts before testing a simpler causal experiment;
- investigate loader/OS internals while a recent local code change remains untested;
- rerun already-passing broad suites repeatedly without a reason;
- treat a failed intermediate build as evidence about unrelated subsystems.

## 6. Tool and file-reading discipline

### Preferred order

1. `git status`
2. `git diff -- <relevant path>`
3. exact-symbol / exact-string search
4. narrow source-range read
5. relevant test execution
6. broader inspection only if required

### Avoid by default

- whole-file reads of the large generator;
- full project-wide searches for vague concepts;
- reading roadmap/changelog/release notes when the task is local code repair;
- dumping complete logs into context;
- reopening files already summarized in the current checkpoint;
- reading both English and Chinese editions of the same project document unless translation consistency is the task.

## 7. Change discipline

- Prefer bounded refactors over patch chains.
- Make one subsystem the owner of each state.
- Keep `CHANGELOG_UNRELEASED.md` while working, but update it only when the current slice warrants a changelog entry.
- Every new project document that requires bilingual publication ships in English and Simplified Chinese editions, cross-linked at the top.
- If changing PE layout, regenerate `docs/PE_MEMORY_MAP.md` and run `tools/inspect_pe.py`.
- If changing imports, update `docs/WIN32_API_SURFACE.md`.
- If changing shortcuts/menu commands, update `docs/FEATURE_AND_SHORTCUT_SPEC.md`.
- Do not modify unrelated tests merely to make a target test pass.
- Do not reset, rebase, clean, discard, or overwrite unrelated user/agent work without explicit instruction.
- Do not force-push.
- Treat uncommitted work as valuable state.

## 8. Verification policy

Verification must match the scope of the change.

### Commit-level

Use the narrowest checks that demonstrate the current change is correct.

Typical examples:

- generator assertions
- targeted unit/static regression
- targeted Windows runtime test
- deterministic build/hash check when relevant

### Milestone-level

Run the milestone-defined broader regression suite when completing a milestone slice.

### Release-level

Run the full release gate only when preparing a release or when explicitly requested.

Do not run a full historical release suite after every small fix.

For GUI/runtime claims, Windows execution is required.

## 9. Task completion and checkpoint format

At the end of each engineering slice, report briefly in Simplified Chinese:

```text
当前目标：
- ...

已完成：
- ...

验证：
- ...

未完成 / 下一步：
- ...

关键文件：
- ...

关键符号：
- ...
```

Do not automatically start the next engineering slice after reporting this checkpoint unless the user explicitly requested continuous execution and the next slice is already within the same bounded task.

If a later host-side Compact / context compression occurs, this checkpoint is the authoritative continuation seed. Do not rebuild project understanding from scratch.

## 10. Repository hygiene

Temporary diagnostics should be:

- clearly named as temporary;
- kept out of production paths;
- removed or archived once the issue is resolved;
- excluded from normal project context unless needed again.

Do not leave a debugging expedition behind as permanent project complexity.

## 11. Communication rules

All user-visible communication must use Simplified Chinese, including:

- reasoning summaries
- plans
- progress messages
- tool-call explanations
- test conclusions
- failure analysis
- final reports

Exceptions:

- source code
- commands
- API names
- file names
- identifiers
- exact error messages when quoting them is necessary

Do not use English prose merely because source code, Windows APIs, or tool output are in English.

Be concise and evidence-driven. Distinguish:

- observed fact
- inference
- hypothesis
- confirmed cause
- unverified assumption

Never present a hypothesis as a confirmed root cause before the causal experiment passes.
