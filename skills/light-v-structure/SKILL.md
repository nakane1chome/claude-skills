---
name: light-v-structure
description: "Defines V-model project structure conventions. ALWAYS ACTIVE for any planning or development work: before starting any task that creates, modifies, or organizes code or documentation, apply the 'planning and implementation' mode. Also invoked explicitly for scaffold, check, and explain."
argument-hint: "[scaffold|check|explain] — omit for implicit planning and decision-making modes"
allowed-tools: Read, Glob, Grep
---

> Human-readable overview: [README.md](README.md)

## Overview

**This [V-model](https://en.wikipedia.org/wiki/V-model_(software_development)) is not a waterfall.** Standard V-model descriptions treat stage boundaries as gates: requirements complete before architecture begins, architecture complete before design begins. That interpretation does not apply here. Do not enforce sequential stage completion.

This V-model is a **tri-axis gradient** — a map of what belongs where and what cross-validates what:

- **Top edge** — user journey: from problem statement to working solution
- **Left edge** — decomposition: proposal, architecture, design
- **Right edge** — integration: test, validation, user acceptance
- **Bottom** — implementation: source code

Stage boundaries are bidirectional. Architecture informs design; design feeds back into architecture. The V is a risk control system — it ensures that right-side activities validate left-side decisions — but it does not prescribe the order in which work is done.

This project is developed by an agent and a single developer collaborating as a team.

### The V-Model Structure

```
User Problem ─────────────────────────── Working User Solution
     │              (User Journey)                │
     │                                            │
     │  Solution Proposal              Validated  │
     │  Implementation Proposal        Solution   │
     │                                            │
     │    Architecture        Validation          │
     │        Design        Test                  │
     └──────────► Implementation ◄────────────────┘
                  (Developer)
```

If invoked with an argument that is not `scaffold`, `check`, or `explain`, treat the argument as context and apply the `planning and implementation` mode.

## Modes

### planning and implementation (implicit)

Before starting, identify what V-model stage the activity belongs to and its information dependencies — up and down the left side, and across to the right side.

**Cannot identify stage.** If the activity's V-model stage is unclear, ask the developer before proceeding.

**Left side (decomposition):**
- **Respect upstream.** Downstream activities must respect the decisions, architecture, and design upstream.
- **Missing upstream doc.** If no upstream document exists, the agent may assume an iterative implementation-first flow — but must confirm with the user. The plan must include creating the missing document.
- **Incomplete upstream doc.** If an upstream document exists but is incomplete, do not proceed. The document must be updated with user input before work continues.

**Right side (Verification and Validation):**
- **Validate the counterpart.** Right-side activities must validate or verify the corresponding left-side decisions, architecture, and design.
- **Missing left-side doc.** If the left-side counterpart does not exist, stop and inform the user.
- **Incomplete test information.** A test-first or TDD (Test-Driven Development) strategy may be assumed, but only if the left-side counterpart exists.

**All plans:** Specify cross-references to upstream or left-side sources of truth.

#### Increment Strategies

Choose an increment strategy before starting. Default to **completed increment** for simplicity; use **pipelined** (sashimi model — stages overlap across working units rather than completing sequentially) when units can be developed in parallel.

**Completed increment**: A set of stages are completed in one increment and finalized atomically (e.g., via one branch and a pull request).
1. Define Architecture → Checkpoint
2. Complete Design/Implementation/Test → Checkpoint
3. Validate

**Pipelined increment**: A single stage is completed in one increment per working unit. Working units may be done in parallel.
1. Define Architecture across Units A, B, and C → Checkpoint
2. Design Unit A → Checkpoint
3. Design Unit B; Implement Unit A → Checkpoint
4. Continue overlapping stages...

### Decision making (implicit)

Triggered when the agent encounters a technical choice with architectural consequences — a choice that constrains arch, design, or future decisions, or involves tradeoffs between paradigm principles.

Not every technical choice is a decision. A decision warrants an ADR when it:
- Constrains how arch or design must be structured going forward
- Chooses between options with meaningfully different consequences
- Conflicts with or extends an existing ADR

Tactical choices (library versions, naming conventions, local implementation details) do not warrant ADRs — record them in the relevant `docs/arch/` or `docs/design/` document instead.

**Steps:**

1. **Frame the decision.** State the problem, the constraints, and why a decision is needed now. Identify what stage of the V it affects.
2. **Check existing ADRs.** Has this been decided? Does an existing ADR constrain the options? If the decision is already made, stop — apply the existing ADR.
3. **Check the paradigm.** Read `docs/*paradigm*.md`. Do the core principles eliminate any options or clearly favour one?
4. **Evaluate options.** If multiple options remain, compare against the paradigm. Use numbered Technical Requirements and a summary table if ≥2 options with distinct tradeoffs (see ADR template). Use evaluation docs (`docs/evaluation/`) for evidence — do not inline lengthy research into the ADR.
5. **Determine ADR scope.** Write one ADR per decision. Do not bundle unrelated choices. If a decision depends on a prior undecided question, resolve that first.
6. **Draft the ADR.** Use `docs/adr/xx-template.md`. Present to the developer for acceptance before proceeding with any work that depends on it.
7. **After acceptance.** Add any unresolved questions or tensions with adjacent ADRs to `docs/adr/qa.md`.

### scaffold (invoked)

Propose and create the canonical directory structure and default files for the project.

1. Read `documentation.md` for the canonical folder structure and file conventions.
2. Inventory the existing `docs/` tree — do not overwrite files that already exist.
3. Propose the complete directory tree and missing placeholder files.
4. Stop and confirm with the developer before creating anything.
5. Create confirmed files using the stub templates in `scaffold.md`. Use the matching template for each file type; use section-headers-only for files with no template (e.g. `poc.md`).

### check

Audit the project against V-model traceability rules. Read `documentation.md` (in this skill's directory) for cross-validation pairs before starting.

1. Inventory existing artifacts at each V-model level: paradigm, adr, architecture, design, test, src. Treat `docs/architecture/` as equivalent to `docs/arch/`, and `docs/tests/` as equivalent to `docs/test/` — note the legacy name in findings but do not report it as a gap.
2. For each left-side artifact, verify a right-side counterpart exists (see cross-validation pairs in `documentation.md`):
   - For `docs/test/system/`, folder presence does not count — verify that `docs/test/system/README.md` contains a named entry for each use case in the use cases doc in `docs/arch/` (identify it by name).
   - For `docs/test/unit/`, folder presence does not count — verify that `docs/test/unit/README.md` contains a named entry for each design doc in `docs/design/`.
3. For each planning artifact, verify it identifies its upstream references:
   - Code plan or implementation → relevant design doc(s) in `docs/design/`
   - Design doc → relevant architecture doc(s) in `docs/arch/` and ADR(s) in `docs/adr/`
   - Architecture doc → relevant ADR(s) and `docs/paradigm.md`
4. Report findings as a checklist: pass / gap / missing.
5. For gaps, propose remediation steps — do not create files without developer approval.

> **Exempt from traceability:** Evaluation docs (`docs/evaluation/`) have no required right-side counterpart. Cross-cutting constraint docs (coding standards, format specs) do not require matching unit test plans. Infrastructure/tooling commits and hot-fix sprints do not require design-doc updates unless they reveal an architectural gap.

> **Relationship to `sdlc-cross-review`:** Use `check` for project-level structural audit — are the right files present, do V-model pairs exist, are upstream references in place? Use `sdlc-cross-review` for document-level review — does this specific document satisfy its SDLC context?

### explain

Explain V-model concepts, project conventions, or increment strategies in the context of this project.

1. Identify the topic: structure, increment strategy, traceability, document types, or a specific V-level.
2. Read the relevant supporting file(s): `documentation.md`, `code-structure.md`, `glossary.md`.
3. Explain using concrete examples from the current `docs/` structure — not generically.
4. If a convention is absent from the project, suggest next steps rather than stopping at the gap.
5. Scope the answer to the question asked. Do not produce a full V-model tutorial unless asked. Respond in prose; use a numbered list only for actionable steps. End with a concrete next step or open question if further action is warranted.

## Supporting Files

| File | Purpose |
|------|---------|
| [documentation.md](documentation.md) | Folder conventions, cross-validation pairs, document types |
| [scaffold.md](scaffold.md) | Stub templates for each file type |
| [code-structure.md](code-structure.md) | Source and test organisation conventions |
| [responsibilities.md](responsibilities.md) | Agent vs developer ownership matrix |
| [glossary.md](glossary.md) | Terms used in this skill |
| [references.md](references.md) | External resources and specifications |
| [sdd.md](sdd.md) | Relationship to Spec-Driven Development — points of difference |

## Skill Precedence

This skill is the authoritative source for project structure conventions. It takes precedence over other project documentation in case of conflict. Supporting files in this directory are maintained independently of project docs and are not subject to project doc conventions.
