# light-v-structure

> **For human readers.** This file explains what the skill is for and how to navigate its files. The operative skill specification is in [SKILL.md](SKILL.md) — that file is primarily consumed by agents.

A lightweight V-model structure for projects developed by an agent and a single developer collaborating as a team.

## The V-model used here

Most V-model descriptions are waterfall-derived: stages complete in sequence, each gating the next. This is not that.

This skill uses the V as a **tri-axis gradient**:

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

- **Top edge** — user journey: from problem statement to working solution
- **Left edge** — decomposition: proposal, architecture, design
- **Right edge** — integration: test, validation, user acceptance
- **Bottom** — implementation: source code, the concrete artifact

Stage boundaries are **bidirectional** — architecture informs design and design feeds back into architecture. The V shows what belongs where and what cross-validates what; it does not prescribe the order in which work happens.

This structure works with any development workflow: iterative, TDD, spike-and-stabilise, or whatever fits the increment.

## Purpose

This skill provides:

- A written record of project decisions and intent that the implementation does not capture
- Distinct stages of development with documented homes for non-implementation activity
- Documentation stored alongside code, referenceable by an agent at any stage
- Consistent increment discipline that advances a documented goal
- A shared vocabulary between developer and agent
- A research and reference tracking framework
- A traceability mechanism between requirements, architecture, design, and tests

## What this skill does not do

- Prescribe a development workflow or enforce stage-gate sequencing
- Inhibit iterative development — stage boundaries are bidirectional exchanges, not inputs-then-outputs
- Add cognitive burden or toil

## Files in this directory

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | Operative skill spec — modes, rules, steps (agent-primary) |
| [documentation.md](documentation.md) | Documentation hierarchy, folder conventions, cross-validation pairs |
| [scaffold.md](scaffold.md) | Stub templates for each file type |
| [code-structure.md](code-structure.md) | Source and test organisation conventions |
| [responsibilities.md](responsibilities.md) | Agent vs developer ownership matrix |
| [glossary.md](glossary.md) | Terms used in this skill |
| [references.md](references.md) | External resources and specifications |
