# Project Directory Guide

```text
PeMark/
├─ CODEX_START_HERE.md              First document for Codex
├─ AGENTS.md                        Mandatory agent constraints/invariants
├─ HANDOFF_TO_CODEX_AND_AGENTS.md   Executive transfer context
├─ DEVELOPMENT_MANUAL.md            Daily engineering workflow
├─ HANDOFF_CHECKLIST.md              Takeover checklist
├─ README.md                         Package overview
├─ manifest.json                     Machine-readable snapshot metadata
├─ SHA256SUMS.txt                    Integrity hashes
├─ src/current/                      Current V8.5.4 Preview generator
├─ bin/current/                      Matching V8.5.4 Preview EXE
├─ archive/
│  ├─ generators/                    Full V7..V8.4.23 lineage
│  ├─ binaries/                      Matching historical EXEs
│  └─ notepad_prototypes/            Earlier Direct-PE Notepad lineage
├─ docs/
│  ├─ ARCHITECTURE_V8_5_TARGET.md
│  ├─ CURRENT_CODE_AUDIT.md
│  ├─ DIRECT_PE_CODEGEN_GUIDE.md
│  ├─ WIN64_ABI_RULES.md
│  ├─ UI_STATE_LAYOUT_AND_MESSAGE_FLOW.md
│  ├─ MARKDOWN_RENDERER_AND_POSITION_MAP.md
│  ├─ LARGE_FILE_DESIGN.md
│  ├─ KNOWN_ISSUES_AND_TECH_DEBT.md
│  ├─ FAILED_APPROACHES.md
│  ├─ DEBUGGING_PLAYBOOK.md
│  ├─ REGRESSION_TEST_PLAN.md
│  ├─ FEATURE_AND_SHORTCUT_SPEC.md
│  ├─ WIN32_API_SURFACE.md
│  ├─ PE_MEMORY_MAP.md
│  ├─ FUNCTION_MAP.md
│  ├─ DECISION_LOG.md
│  ├─ VERSION_HISTORY.md
│  ├─ ROADMAP.md
│  └─ evidence/                      Curated historical screenshots
├─ patches/                          Confirmed defect/refactor guidance
├─ tests/                            Deterministic test corpus
└─ tools/                            Build/PE/hash/test helpers
```

The original architecture drafts are retained in `docs/` for historical
context. `V8_5_4_RELEASE_RESULTS.md` records the current baseline and
`ARCHITECTURE_V8_5_TARGET.md` remains the architectural direction.
